#!/usr/bin/env python3
"""
LDES Consumer Spawner
Reads a YAML configuration file and spawns ldes2sparql Docker container instances.
Supports dynamic feed addition/removal via watchdog file monitoring.
"""
import os
import sys
import yaml
import subprocess
import signal
import time
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Any
from logger import setup_logger, Logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# === Global config / data and logger setup ===
# Set up logger
loglevel: str = os.getenv("LOG_LEVEL", "INFO")
pfx: str = os.getenv("LDES_CONSUMER_PREFIX", "ldes-consumer")
log: Logger = setup_logger(pfx, loglevel)

# Get configuration options
# note that js based ldes2sparql expects lowercase log levels
ldes_loglevel = os.getenv("LDES_LOG_LEVEL", loglevel).lower()
image_name: str = os.getenv(
    "LDES2SPARQL_IMAGE", "ghcr.io/maregraph-eu/ldes2sparql:latest"  # default image
)
project_name: str = os.getenv("COMPOSE_PROJECT_NAME", "kgap")  # default kgap
gdb_repo: str = os.getenv("GDB_REPO", "kgap")  # default kgap
default_sparql_endpoint: str = os.getenv(
    "DEFAULT_SPARQL_ENDPOINT", f"http://graphdb:7200/repositories/{gdb_repo}/statements"
)  # default endpoint for updates
network_name: str = os.getenv(
    "DOCKER_NETWORK", f"{project_name}_default"
)  # default network name derived from compose project name
remove_containers: bool = (
    os.getenv("LDES_REMOVE_CONTAINERS", "1") == "1"
)  # default to true
monitor_interval: int = int(
    os.getenv("LDES_MONITOR_INTERVAL", "120")
)  # in seconds, default 2 minutes

host_pwd: str = os.getenv(
    "HOST_PWD", "/tmp"
)  # passed working dir from host env - fallback to /tmp

# path conversion setup between guest and host
guest_data_root: Path = Path("/data")  # main mounted /data inside docker guest
host_data_path: Path = Path(host_pwd) / "data"  # assumed corresponding host data path


def guest2host_data_path(path: Path) -> Path:
    """Convert a guest data path to the corresponding host data path."""
    return host_data_path / path.relative_to(guest_data_root)


# paths in use
ldes_consumer_root: Path = (
    guest_data_root / "ldes-consumer"
)  # main ldes-consumer data path in guest
logs_path: Path = ldes_consumer_root / "logs"  # subfolder for logs in guest
state_path: Path = ldes_consumer_root / "state"  # subfolder for state in guest
host_state_path: Path = guest2host_data_path(
    state_path
)  # corresponding host path for state (for volume mount)

# Global list to track feeds in use
feeds: dict[str, dict] = None

# Global to track config file path and last modified time
config_file_path: Path = None
config_file_mtime: float = None


# === Docker container management functions ===
def docker_container_name(feedname: str) -> str:
    """Generate the Docker container name for a given feed."""
    return f"{pfx}-{feedname}"


@contextmanager
def check_docker_container_running(
    feedname: str, feed: dict
) -> Generator[bool, None, None]:
    """Check if a Docker container for a given feed is running."""
    container_name = docker_container_name(feedname)
    cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        is_running = result.returncode == 0 and result.stdout.strip() == "true"
        yield is_running
    except subprocess.TimeoutExpired:
        log.error(f"Timeout checking container status for '{container_name}'")
        yield False


def _check_docker_container_exists(feedname: str, feed: dict) -> bool:
    """Check if a Docker container for a given feed exists."""
    container_name = docker_container_name(feedname)
    cmd = ["docker", "inspect", container_name]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log.error(f"Timeout checking container existence for '{container_name}'")
        return False


def docker_container_remove(feedname: str, feed: dict) -> None:
    """Remove a Docker container for a given feed if it exists.
    But only if it exists and the wrapper is configured to do so."""
    if not _check_docker_container_exists(feedname, feed):
        log.info(f"No existing container to remove for feed '{feedname}'")
        return
    # else
    if not remove_containers:
        log.info(
            f"Skipping removal of existing container for feed '{feedname}' as per configuration."
        )
        log.info(
            "This may lead to (1) not launching now if it is already running, or (2) reusing an old stopped container."
        )
        return
    # else - proceed to remove
    log.info(f"Removing existing container for feed '{feedname}'")
    container_name = docker_container_name(feedname)
    cmd: list[str] = ["docker", "container", "remove", "-f", container_name]
    try:
        subprocess.run(cmd, timeout=10)
        log.info(f"Removed container '{container_name}' successfully.")
    except Exception as e:
        log.error(f"Error removing container '{container_name}'")
        log.exception(e, exc_info=True)


def docker_container_start(
    feedname: str, feed: dict, image_name: str, project_name: str, network_name: str
) -> None:
    """Start a Docker container for a given feed."""
    # 1| get relevant parts from feed config
    feed_url = feed.get("url")
    sparql_endpoint = feed.get("sparql_endpoint", default_sparql_endpoint)
    target_graph = feed.get("target_graph", f"urn:kgap:{pfx}:{feedname}")
    container_name = docker_container_name(feedname)
    # Note: The config uses 'polling_interval' (seconds) for user-friendliness,
    # but ldes2sparql expects 'POLLING_FREQUENCY' (milliseconds)
    polling_frequency = feed.get("polling_interval", 60) * 1000

    # 2| Compose build the docker run command
    cmd: list[str] = [
        "docker",
        "run",
        "--name",
        container_name,
        "--network",
        network_name,
        # Add labels to link container to the docker-compose project
        "--label",
        f"com.docker.compose.project={project_name}",
        "--label",
        "com.docker.compose.service=ldes-consumer",
        "-v",
        f"{host_data_path}:/data",
        "-v",
        f"{host_state_path}/{feedname}:/state",
    ]

    # Add environment variables
    cmd.extend(["-e", f"LDES={feed_url}"])
    cmd.extend(["-e", f"SPARQL_ENDPOINT={sparql_endpoint}"])
    cmd.extend(["-e", f"TARGET_GRAPH={target_graph}"])
    cmd.extend(["-e", f"POLLING_FREQUENCY={polling_frequency}"])
    cmd.extend(["-e", "FAILURE_IS_FATAL=false"])
    cmd.extend(["-e", "FOLLOW=true"])

    # Add any additional environment variables from the feed config
    added_envs: set[str] = set()
    extra_env = feed.get("environment", {})
    if isinstance(extra_env, dict):
        for key, value in extra_env.items():
            if key in {
                "LDES",
                "SPARQL_ENDPOINT",
                "TARGET_GRAPH",
                "FAILURE_IS_FATAL",
                "FOLLOW",
                "POLLING_FREQUENCY",
            }:
                log.warning(
                    f"Environment variable '{key}' for feed '{feedname}' is reserved and cannot be overridden; ignoring..."
                )
                continue
            cmd.extend(["-e", f"{key}={value}"])
            added_envs.add(key)
    else:
        log.warning(
            f"'environment' for feed '{feedname}' is not a mapping; ignoring..."
        )
    # Ensure OPERATION_MODE is set, default to 'sync' if not provided
    if "OPERATION_MODE" not in added_envs:
        cmd.extend(["-e", "OPERATION_MODE=Sync"])
    # Ensure MAXIMUM_BATCH_SIZE is set, default to 500 if not provided
    if "MEMBER_BATCH_SIZE" not in added_envs:
        cmd.extend(["-e", "MEMBER_BATCH_SIZE=500"])
    # Ensure SHAPE is set, even if empty
    if "SHAPE" not in added_envs:
        cmd.extend(["-e", "SHAPE="])
    # Ensure MATERIALIZE is set, even if empty
    if "MATERIALIZE" not in added_envs:
        cmd.extend(["-e", "MATERIALIZE=true"])
    # Ensure LOG_LEVEL is set correctly
    if "LOG_LEVEL" not in added_envs:
        cmd.extend(["-e", f"LOG_LEVEL={ldes_loglevel}"])

    # Add the image name
    cmd.append(image_name)

    # 3| Prepare state directory
    state_path_for_feed = state_path / feedname
    state_path_for_feed.mkdir(parents=True, exist_ok=True)
    json_state_file = state_path_for_feed / "ldes-client_state.json"
    if json_state_file.exists():
        log.info(
            f"Note that existing state file exists for feed '{feedname}' it will be reused."
        )

    log.info(f"Starting LDES consumer for feed: {feedname}")
    log.info(f"  URL: {feed_url}")
    log.info(f"  SPARQL Endpoint: {sparql_endpoint}")
    log.info(f"  Target Graph: {target_graph}")
    log.info(f"  Polling Frequency (ms): {polling_frequency}")
    log.info(f"  State path: {host_state_path}/{feedname}")
    log.debug(f"Starting LDES feed instance with command:\n{' '.join(cmd)}")

    # 4| Run the docker container
    try:
        proc: subprocess.Popen = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        # Give the container a moment to start
        time.sleep(2)

        # Check if the container is actually running
        with check_docker_container_running(feedname, feed) as is_running:
            if is_running:
                active_feed(feedname, feed, proc)
                return
            # else
            log.error(f"Container '{feedname}' failed to start properly.")
            docker_container_capture_logs(feedname, feed)
            docker_container_remove(feedname, feed)
            fail_feed(feedname, feed, "Container failed to start.")
            return

    except Exception as e:
        log.error(f"Failed to spawn container for feed '{feedname}'")
        log.exception(e, exc_info=True)
        fail_feed(feedname, feed, "Exception during container start.")
    return


def docker_container_stop(feedname: str, feed: dict) -> bool:
    """Stop a Docker container for a given feed."""
    container_name = docker_container_name(feedname)
    cmd: list[str] = ["docker", "stop", container_name]
    try:
        subprocess.run(cmd, timeout=60)
        log.info(f"Terminated process for feed '{feedname}'")
    except subprocess.TimeoutExpired:
        log.error(f"Timeout while trying to stop docker for feed '{feedname}'")
    except Exception as e:
        log.error(f"Error terminating process for feed '{feedname}'")
        log.exception(e, exc_info=True)


def docker_container_capture_logs(feedname: str, feed: dict) -> None:
    """Capture logs from a Docker container for a given feed."""
    container_name = docker_container_name(feedname)
    # Try to get logs
    cmd: list[str] = ["docker", "logs", container_name]
    # allocate filenames to capture stdout and stderr
    ts = time.strftime("%Y%m%d-%H%M%S")
    stdout_log = logs_path / f"{feedname}_{ts}_stdout.log"
    stderr_log = logs_path / f"{feedname}_{ts}_stderr.log"

    with open(stdout_log, "w") as stdout_file, open(stderr_log, "w") as stderr_file:
        capture_logs = subprocess.run(
            cmd, stdout=stdout_file, stderr=stderr_file, timeout=5
        )
        if capture_logs.returncode == 0:
            log.error(
                f"Container logs can be found in {logs_path}/{feedname}_{ts}*.log"
            )


# === File monitoring helpers ===
def get_file_mtime(file_path: Path) -> float:
    """Get the modification time of a file. Returns 0.0 on error."""
    try:
        return os.stat(file_path).st_mtime
    except Exception as e:
        log.error(f"Error getting modification time for {file_path}: {e}")
        return 0.0


class ConfigFileEventHandler(FileSystemEventHandler):
    """Handler for config file modification events."""

    def __init__(self, config_path: Path, sync_callback):
        super().__init__()
        self.config_path = config_path
        self.sync_callback = sync_callback

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Check if the modified file is our config file
        if Path(event.src_path).resolve() == self.config_path.resolve():
            log.info(f"Config file modification detected: {event.src_path}")
            self.sync_callback()


# === Signal handling for graceful shutdown ===
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully to stop all spawned docker images for individual feeds."""
    global feeds
    log.info(f"Received signal {signum}, checking {len(feeds)} LDES consumers...")
    active_feeds: dict[str, dict] = get_active_feeds()
    log.info(
        f"Processing signal {signum}, shutting down {len(active_feeds)} active LDES consumers..."
    )
    for feedname, feed in active_feeds.items():
        with check_docker_container_running(feedname, feed) as is_running:
            if not is_running:
                log.info(
                    f"active LDES consumer for feed '{feedname}' not running, so not stopping"
                )
            else:
                log.info(f"Stopping active LDES consumer for feed '{feedname}'...")
                docker_container_stop(feedname, feed)
        docker_container_remove(feedname, feed)
    log.info(
        f"Done handling signal {signum}, all feed instances should have stopped..."
    )
    sys.stdout.flush()
    sys.exit(0)


# === Configuration loading and feed spawning logic ===
def load_config(feed_config_path: Path) -> dict[str, Any]:
    """Load and parse the YAML configuration file."""
    try:
        with open(feed_config_path, "r") as feed_config_file:
            feed_config = yaml.safe_load(feed_config_file)
        return feed_config
    except Exception as e:
        log.error(f"Failed to load config file {feed_config_path}")
        log.exception(e, exc_info=True)
        log.info("Exiting due to configuration load failure.")
        sys.exit(1)


def fail_feed(feedname: str, feed: dict, reason: str) -> None:
    """Helper to log feed failure reasons."""
    log.error(f"Feed {feedname} setup failed: {reason}")
    feed["active"] = False
    feed["failure_reason"] = reason
    return


def active_feed(feedname: str, feed: dict, proc: subprocess.Popen) -> None:
    """Helper to log feed success."""
    log.info(f"Feed {feedname} docker instance started successfully.")
    feed["active"] = True
    feed["process"] = proc
    feed.pop("failure_reason", None)  # remove any previous failure reason
    return


def get_active_feeds() -> dict[str, dict]:
    """Get a dictionary of currently active feeds."""
    global feeds
    return {fname: f for fname, f in feeds.items() if f.get("active", True)}


def spawn_feed_instance(
    feedname: str,
    feed: dict[str, Any],
    image_name: str,
    project_name: str,
    network_name: str,
) -> None:
    """
    Spawn a single ldes2sparql Docker container instance.

    Args:
        feedname: unique name of the feed
        feed: dictionary containing feed configuration
        image_name: ref to docker image to use for ldes2sparql
        project_name: docker-compose project name for container labeling
        network_name: docker network to attach to in order to reach triple store (graphdb)

    Returns:
        Nothing. Logs errors if spawning fails. Adds flag 'active' flag to the feed dict on success.
    """

    if "url" not in feed:
        fail_feed(feedname, feed, "Missing URL in feed configuration")
        return

    with check_docker_container_running(feedname, feed) as is_running:
        if is_running:
            fail_feed(
                feedname,
                feed,
                "Container is already running. Stop it or give a different name.",
            )
            return

    docker_container_remove(feedname, feed)
    docker_container_start(feedname, feed, image_name, project_name, network_name)
    return


def sync_feeds(new_config_path: Path = None) -> None:
    """
    Synchronize running feed containers with the configuration file.

    This function:
    - Loads the current config (or reloads if path is provided)
    - Compares new feeds with currently running feeds
    - Spawns new containers for added feeds
    - Stops and removes containers for removed feeds
    - Restarts containers if their configuration changed

    Args:
        new_config_path: Optional path to config file (uses global if None)
    """
    global feeds, config_file_path, config_file_mtime

    # Use provided path or global
    cfg_path = new_config_path or config_file_path
    if cfg_path is None:
        log.error("No config file path available for sync")
        return

    # Get file modification time
    new_mtime = get_file_mtime(cfg_path)
    if new_mtime == 0.0:
        log.error("Failed to get modification time for config file, skipping sync")
        return

    # Check if file actually changed (modification time is greater than previous)
    if config_file_mtime is not None and new_mtime <= config_file_mtime:
        log.debug("Config file modification time unchanged, skipping sync")
        return

    log.info("Synchronizing feeds with configuration file...")

    # Load new configuration
    try:
        new_config = load_config(cfg_path)
        new_feeds = new_config.get("feeds", {})

        if not isinstance(new_feeds, dict):
            log.error(
                "Invalid feeds format in config (expected dict), keeping old state"
            )
            return

    except Exception as e:
        log.error(
            f"Failed to load new configuration, keeping old state: {e}", exc_info=True
        )
        return

    # Get current active feeds (old state)
    old_feeds = feeds if feeds is not None else {}

    # Determine changes
    old_feed_names = set(old_feeds.keys())
    new_feed_names = set(new_feeds.keys())

    added_feeds = new_feed_names - old_feed_names
    removed_feeds = old_feed_names - new_feed_names
    potentially_modified_feeds = old_feed_names & new_feed_names

    # Process removed feeds
    for feedname in removed_feeds:
        log.info(f"Feed '{feedname}' removed from config, stopping container...")
        feed = old_feeds[feedname]

        # Check if container is running
        with check_docker_container_running(feedname, feed) as is_running:
            if is_running:
                docker_container_stop(feedname, feed)

        # Remove container
        docker_container_remove(feedname, feed)
        log.info(f"Container for feed '{feedname}' stopped and removed")

    # Process modified feeds (check if config changed)
    modified_feeds = []
    for feedname in potentially_modified_feeds:
        old_feed = old_feeds[feedname]
        new_feed = new_feeds[feedname]

        # Compare feed configurations (excluding runtime fields)
        old_config = {
            k: v
            for k, v in old_feed.items()
            if k not in ["active", "process", "failure_reason"]
        }
        new_config = {
            k: v
            for k, v in new_feed.items()
            if k not in ["active", "process", "failure_reason"]
        }

        if old_config != new_config:
            log.info(
                f"Feed '{feedname}' configuration changed, restarting container..."
            )
            modified_feeds.append(feedname)

            # Stop and remove old container
            with check_docker_container_running(feedname, old_feed) as is_running:
                if is_running:
                    docker_container_stop(feedname, old_feed)
            docker_container_remove(feedname, old_feed)

            # Start new container with updated config
            spawn_feed_instance(
                feedname, new_feed, image_name, project_name, network_name
            )
        else:
            # Configuration unchanged, keep existing state
            new_feed["active"] = old_feed.get("active", False)
            new_feed["process"] = old_feed.get("process")
            if "failure_reason" in old_feed:
                new_feed["failure_reason"] = old_feed["failure_reason"]

    # Process added feeds
    for feedname in added_feeds:
        log.info(f"New feed '{feedname}' detected, spawning container...")
        feed = new_feeds[feedname]
        spawn_feed_instance(feedname, feed, image_name, project_name, network_name)

    # Update global state
    feeds = new_feeds
    config_file_mtime = new_mtime

    # Log summary
    active_count = len(get_active_feeds())
    log.info(
        f"Feed synchronization complete: {active_count} active of {len(feeds)} total feeds"
    )
    if added_feeds:
        log.info(f"  Added: {', '.join(added_feeds)}")
    if removed_feeds:
        log.info(f"  Removed: {', '.join(removed_feeds)}")
    if modified_feeds:
        log.info(f"  Modified: {', '.join(modified_feeds)}")


# === Main execution logic ===
def main():
    """Main function to spawn all ldes2sparql instances."""
    log.info(f"Spawner started with {len(sys.argv)} cli arguments")
    log.info(f"Logger initialized with level {loglevel}")

    if len(sys.argv) < 2:
        log.error("Usage: spawn_instances.py <config_file>")
        sys.exit(1)

    config_file: str = sys.argv[1]

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Set global config file path
    global config_file_path
    config_file_path = Path(config_file)

    # Initial feed synchronization (replaces old startup logic)
    log.info("Performing initial feed synchronization...")
    sync_feeds(config_file_path)

    active_feeds: dict[str, dict] = get_active_feeds()

    if not active_feeds:
        log.error(
            f"No LDES consumers (out of {len(feeds) if feeds else 0}) were started successfully"
        )
        sys.exit(1)

    log.info(
        f"Successfully started {len(active_feeds)} of {len(feeds)} LDES consumer(s)"
    )

    # Set up watchdog observer for config file monitoring
    log.info(f"Setting up file watcher for {config_file_path}...")
    event_handler = ConfigFileEventHandler(
        config_file_path, lambda: sync_feeds(config_file_path)
    )
    observer = Observer()
    observer.schedule(event_handler, str(config_file_path.parent), recursive=False)
    observer.start()
    log.info("File watcher started - config changes will be detected automatically")

    log.info("Starting to monitor started processes... (Press Ctrl+C to stop)")

    # Monitor processes and restart if they have ended
    # Also check config file for changes (polling as fallback to watchdog)
    try:
        while True:
            time.sleep(monitor_interval)

            # Check for config file changes via polling (more reliable than watchdog on shared volumes)
            log.debug("Checking for config file changes via polling...")
            sync_feeds(config_file_path)

            active_feeds: dict[str, dict] = get_active_feeds()

            log.info(f"Monitoring of {len(active_feeds)} LDES consumer(s)...")
            for feedname, feed in active_feeds.items():
                log.info(f"Checking LDES consumer for feed '{feedname}'...")
                with check_docker_container_running(feedname, feed) as is_running:
                    if is_running:
                        log.info(
                            f"LDES consumer for feed '{feedname}' is still running"
                        )
                        continue  # still running
                    # else - container has stopped - attempt restart
                    log.warning(
                        f"LDES consumer for feed '{feedname}' has stopped - capturing logs and attempting restart"
                    )
                    docker_container_capture_logs(feedname, feed)
                    docker_container_start(
                        feedname,
                        feed,
                        image_name,
                        project_name,
                        network_name,
                    )
    finally:
        # Clean up observer
        observer.stop()
        observer.join()
        log.info("File watcher stopped")


if __name__ == "__main__":
    main()
