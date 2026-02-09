#!/usr/bin/env python3
"""
LDES Consumer Spawner
Reads a YAML configuration file and spawns ldes2sparql Docker container instances.
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
    os.getenv("LDES_MONITOR_INTERVAL", "300")
)  # in seconds, default 5 minutes

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

    # Load configuration
    config = load_config(config_file)

    # Populate feeds list
    global feeds
    feeds = config.get("feeds", [])
    if not feeds:
        log.error("No feeds defined in configuration file")
        sys.exit(1)

    log.info(f"Found {len(feeds)} LDES feed(s) to process")

    for feedname, feed in feeds.items():
        spawn_feed_instance(
            feedname,
            feed,
            image_name,
            project_name,
            network_name,
        )

    active_feeds: dict[str, dict] = get_active_feeds()

    if not active_feeds:
        log.error(f"No LDES consumers (out of {len(feeds)}) were started successfully")
        sys.exit(1)

    log.info(
        f"Successfully started {len(active_feeds)} of {len(feeds)} LDES consumer(s)"
    )
    log.info("Starting to monitor started processes... (Press Ctrl+C to stop)")

    # Monitor processes and restart if they have ended
    while True:
        time.sleep(monitor_interval)
        active_feeds: dict[str, dict] = get_active_feeds()

        log.info(f"Monitoring of {len(active_feeds)} LDES consumer(s)...")
        for feedname, feed in active_feeds.items():
            log.info(f"Checking LDES consumer for feed '{feedname}'...")
            with check_docker_container_running(feedname, feed) as is_running:
                if is_running:
                    log.info(f"LDES consumer for feed '{feedname}' is still running")
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


if __name__ == "__main__":
    main()
