#!/usr/bin/env python3
"""
LDES Consumer Application
Reads and processes ldes-feeds.yaml from a mounted volume
Spawns Docker containers for each feed using ldes2sparql
"""

import yaml
import os
import sys
import signal
import time
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List

import docker
from docker.errors import DockerException, APIError

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def get_compose_labels(docker_client):
    """
    Detect if the current container is part of a Docker Compose project
    and return its labels to apply to spawned containers.

    Args:
        docker_client: Docker client instance

    Returns:
        dict: Dictionary of compose-related labels, or empty dict if not in compose
    """
    try:
        # Get the current container's hostname (container ID)
        hostname = os.getenv("HOSTNAME")
        if not hostname:
            return {}

        # Get the current container
        container = docker_client.containers.get(hostname)
        labels = container.labels

        # Extract compose-related labels
        compose_labels = {}
        compose_keys = [
            "com.docker.compose.project",
            "com.docker.compose.project.working_dir",
            "com.docker.compose.project.config_files",
        ]

        for key in compose_keys:
            if key in labels:
                compose_labels[key] = labels[key]

        if compose_labels:
            logger.info(
                f"Detected Docker Compose project: {compose_labels.get('com.docker.compose.project', 'unknown')}"
            )

        return compose_labels

    except Exception as e:
        logger.warning(f"Could not detect compose project: {e}")
        return {}


def get_parent_network(docker_client):
    """
    Detect the network that the current container is connected to.

    Args:
        docker_client: Docker client instance

    Returns:
        str: Network name, or None if detection fails
    """
    try:
        # Get the current container's hostname (container ID)
        hostname = os.getenv("HOSTNAME")
        if not hostname:
            return None

        # Get the current container
        container = docker_client.containers.get(hostname)
        networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})

        # Get the first network (usually there's only one, or we pick the first)
        if networks:
            network_name = list(networks.keys())[0]
            logger.info(f"Detected parent container network: {network_name}")
            return network_name

        return None

    except Exception as e:
        logger.warning(f"Could not detect parent network: {e}")
        return None


def load_ldes_feeds(config_path):
    """
    Load LDES feeds configuration from YAML file

    Args:
        config_path: Path to the ldes-feeds.yaml file

    Returns:
        Dictionary containing the feeds configuration
    """
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file: {e}")
        sys.exit(1)


def process_feeds(feeds_config, docker_client, ldes2sparql_image):
    """
    Process the LDES feeds from configuration and spawn Docker containers

    Args:
        feeds_config: Dictionary containing feeds configuration
        docker_client: Docker client instance
        ldes2sparql_image: Docker image to use for spawning containers

    Returns:
        List of spawned container objects
    """
    if "feeds" not in feeds_config:
        logger.warning("No 'feeds' section found in configuration")
        return []

    feeds = feeds_config["feeds"]
    logger.info(f"Found {len(feeds)} feed(s) in configuration")

    containers = []
    host_pwd = os.getenv("HOST_PWD", os.getcwd())
    graph_prefix = os.getenv("GRAPH_PREFIX", "ldes")

    # Get restart policy from environment (default: no, no automatic restart)
    default_restart_policy = os.getenv("RESTART", "no")
    logger.debug(f"Default restart policy: {default_restart_policy}")

    # Get remove orphans setting from environment
    remove_orphans = os.getenv("REMOVE_ORPHANS", "false").lower() == "true"
    if remove_orphans:
        logger.info(
            "Remove orphans mode enabled - will remove containers not in config"
        )
        # Remove any ldes-consumer-* containers that aren't in the current config
        try:
            all_containers = docker_client.containers.list(all=True)
            configured_names = {f"ldes-consumer-{fname}" for fname in feeds.keys()}
            for container in all_containers:
                container_name = container.attrs.get("Name", "").lstrip("/")
                if (
                    container_name.startswith("ldes-consumer-")
                    and container_name not in configured_names
                ):
                    logger.info(f"Removing orphaned container: {container_name}")
                    try:
                        # Capture logs before removing
                        capture_container_logs(container)
                        # Stop if running
                        if container.status == "running":
                            container.stop(timeout=5)
                        # Remove container
                        container.remove()
                        logger.info(f"  ✓ Orphaned container removed: {container_name}")
                    except Exception as e:
                        logger.warning(
                            f"  ✗ Error removing orphaned container {container_name}: {e}"
                        )
        except Exception as e:
            logger.error(f"Error processing orphaned containers: {e}")

    # Detect compose project labels
    compose_labels = get_compose_labels(docker_client)

    # Detect parent container's network
    docker_network = get_parent_network(docker_client)
    if not docker_network:
        # Fall back to environment variable if detection fails
        docker_network = os.getenv("DOCKER_NETWORK", None)
        if docker_network:
            logger.info(f"Using network from env var: {docker_network}")

    gdb_repo = os.getenv("GDB_REPO", "kgap")
    default_sparql_endpoint: str = os.getenv(
        "DEFAULT_SPARQL_ENDPOINT",
        f"http://graphdb:7200/repositories/{gdb_repo}/statements",
    )
    logger.info(
        f"Default SPARQL endpoint (if not overridden by feed config): {default_sparql_endpoint}"
    )

    for feed_name, feed_data in feeds.items():
        logger.info(f"Feed: {feed_name}")
        logger.info(f"  URL: {feed_data.get('url', 'N/A')}")

        # Prepare per-feed volume mounts
        feed_state_dir = f"{host_pwd}/data/ldes-consumer/state/{feed_name}"

        # Ensure state directory exists
        Path(feed_state_dir).mkdir(parents=True, exist_ok=True)

        volumes = {feed_state_dir: {"bind": "/state", "mode": "rw"}}
        logger.info(f"  State directory: {feed_state_dir} -> /state")

        # Get feed-specific configuration
        feed_url = feed_data.get("url", "")
        default_target_graph = f"urn:kgap:{graph_prefix}:{feed_name}"
        feed_env = feed_data.get("environment", {})
        feed_remove = feed_data.get("REMOVE", False)
        feed_restart = feed_env.get("RESTART", default_restart_policy)

        target_graph = feed_env.get(
            "TARGET_GRAPH", feed_data.get("target_graph", default_target_graph)
        )
        logger.info(f"  Target graph: {target_graph}")
        logger.debug(f"  Restart policy: {feed_restart}")
        if feed_remove:
            logger.debug(f"  Remove on stop: True")

        # Build environment variables by retrieving from feed config with defaults
        env_vars = {
            # Core feed identifiers
            "SPARQL_ENDPOINT": feed_env.get(
                "SPARQL_ENDPOINT", os.environ.get("DEFAULT_SPARQL_ENDPOINT", "")
            ),
            "TARGET_GRAPH": target_graph,
            "FOLLOW": feed_env.get("FOLLOW", "false"),
            "MEMBER_BATCH_SIZE": feed_env.get("MEMBER_BATCH_SIZE", "500"),
            "MATERIALIZE": feed_env.get("MATERIALIZE", "false"),
            "LOG_LEVEL": feed_env.get(
                "LOG_LEVEL",
                os.getenv("LDES_LOG_LEVEL", os.getenv("LOG_LEVEL", "DEBUG")),
            ).lower(),
            "LDES": feed_url,
            "POLLING_FREQUENCY": feed_env.get("POLLING_FREQUENCY", "60000"),  # in ms
            "FAILURE_IS_FATAL": feed_env.get("FAILURE_IS_FATAL", "false"),
            "OPERATION_MODE": feed_env.get("OPERATION_MODE", "Replication"),
            "SHAPE": feed_env.get("SHAPE", ""),
        }

        # Add any additional custom environment variables from feed configuration
        for env_key, env_value in feed_env.items():
            if env_key not in env_vars:  # Don't override already-set variables
                env_vars[env_key] = str(env_value)

        # Log all environment variables
        logger.info("  Environment variables:")
        for env_key, env_value in env_vars.items():
            logger.debug(f"    {env_key}: {env_value}")

        # Spawn the Docker container
        try:
            logger.info(f"  Spawning container with image: {ldes2sparql_image}")

            container_config = {
                "image": ldes2sparql_image,
                "name": f"ldes-consumer-{feed_name}",
                "environment": env_vars,
                "detach": True,  # Run in background to return container object
                "remove": feed_remove,  # Remove container when it exits if configured
                "volumes": volumes,  # Mount log directories
                "restart_policy": {"Name": feed_restart},  # Apply restart policy
            }

            # Add compose labels if parent is in a compose project
            if compose_labels:
                # Add compose service label to identify spawned containers
                labels = compose_labels.copy()
                labels["com.docker.compose.service"] = f"ldes-consumer-{feed_name}"
                container_config["labels"] = labels

            # Add network if specified
            if docker_network:
                container_config["network"] = docker_network

            container = docker_client.containers.run(**container_config)
            containers.append(container)

            logger.info(f"  ✓ Container started: {container.short_id}")
        except DockerException as e:
            logger.error(f"  ✗ Error spawning container: {e}")
        except Exception as e:
            logger.error(f"  ✗ Unexpected error: {e}")

    return containers


def capture_container_logs(container):
    """
    Capture logs from a container and save to file

    Args:
        container: Docker container object
    """
    try:
        # Get container name and feed name from container
        container_name = container.attrs.get("Name", "").lstrip("/")
        if container_name.startswith("ldes-consumer-"):
            feed_name = container_name.replace("ldes-consumer-", "")
        else:
            feed_name = container.short_id

        # Create logs directory if it doesn't exist
        logs_dir = Path("/data/ldes-consumer/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for log file
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        # Capture stdout and stderr
        try:
            logs = container.logs(stdout=True, stderr=True)
            log_file = logs_dir / f"{feed_name}_{timestamp}.log"
            with open(log_file, "w") as f:
                f.write(logs.decode("utf-8", errors="replace"))
            logger.info(f"✓ Container logs saved: {log_file}")
        except Exception as e:
            logger.warning(f"Could not capture logs for {container_name}: {e}")
    except Exception as e:
        logger.error(f"Error in capture_container_logs: {e}")


def cleanup_containers(containers: List):
    """
    Stop and remove spawned containers

    Args:
        containers: List of container objects to cleanup
    """
    if not containers:
        return

    logger.info("Cleaning up spawned containers...")

    for container in containers:
        try:
            # Capture logs before removing
            capture_container_logs(container)

            container_info = container.attrs.get("Name", container.short_id)
            logger.info(f"Stopping container: {container_info}")
            container.stop(timeout=10)
            logger.info(f"  ✓ Stopped successfully")
            logger.info(f"Removing container: {container_info}")
            container.remove()
            logger.info(f"  ✓ Removed successfully")
        except Exception as e:
            logger.error(f"  ✗ Error cleaning up container: {e}")


def monitor_containers_with_events(
    docker_client, containers: List, container_name_prefix: str = "ldes-consumer-"
):
    """
    Monitor spawned containers using Docker event stream instead of polling.
    Runs in a background thread and listens for container status events.

    Args:
        docker_client: Docker client instance
        containers: List of container objects to monitor (will be populated dynamically)
        container_name_prefix: Prefix of container names to monitor
    """
    logger.info(
        f"[Event Listener] Starting (watching for containers with prefix: {container_name_prefix})"
    )
    logger.info("Listening for container events (start, stop, die, health_status)...")

    # Track container statuses dynamically
    container_status = {}
    tracked_containers = set()

    def update_tracked_containers():
        """Refresh the list of containers we're tracking"""
        new_containers = set()
        for container in containers:
            full_id = container.id
            new_containers.add(full_id)
            if full_id not in container_status:
                name = container.attrs.get("Name", "unknown")
                logger.debug(
                    f"  [New Container] Tracking: {name} (ID: {container.short_id})"
                )
                container_status[full_id] = "unknown"
        return new_containers

    try:
        # Listen for events WITHOUT the 'since' parameter to get all events going forward
        # (containers may already be spawned by the time this listener starts)
        logger.info(
            "[Event Listener] Starting event stream (no since filter - listening from now)..."
        )

        # Listen for container events in real-time
        # We'll manually filter by container ID since events can come from any container
        events_stream = docker_client.events(decode=True)

        logger.info("[Event Listener] Stream started, listening for events...")
        event_count = 0

        for event in events_stream:
            try:
                event_count += 1

                # Extract event info
                event_type = event.get("Type", "unknown")
                action = event.get("Action", "unknown")

                # Only process container events
                if event_type != "container":
                    continue

                # Get container ID from Actor.ID (not from top-level "id")
                actor = event.get("Actor", {})
                container_id = actor.get("ID", "")
                attributes = actor.get("Attributes", {})
                container_name = attributes.get("name", f"unknown-{container_id[:12]}")

                # Check if this is one of our containers by prefix
                is_our_container = container_name.startswith(container_name_prefix)

                # Also check if it's in our tracked list
                if not is_our_container and container_id not in container_status:
                    # Not one of our containers
                    continue

                # Map Docker actions to status values
                if action in ["create"]:
                    container_status[container_id] = "created"
                    logger.info(
                        f"[Event] CREATE - {container_name} ({container_id[:12]})"
                    )

                elif action in ["start"]:
                    container_status[container_id] = "running"
                    logger.info(
                        f"[Event] START ✓ - {container_name} ({container_id[:12]})"
                    )

                elif action in ["stop", "stopped"]:
                    container_status[container_id] = "stopped"
                    logger.info(
                        f"[Event] STOP ⊘ - {container_name} ({container_id[:12]})"
                    )

                elif action in ["die"]:
                    container_status[container_id] = "exited"
                    exit_code = attributes.get("exitCode", "unknown")
                    logger.info(
                        f"[Event] DIE ✗ - {container_name} ({container_id[:12]}) exit code: {exit_code}"
                    )
                    # Capture logs when container dies
                    try:
                        container = docker_client.containers.get(container_id)
                        capture_container_logs(container)
                    except Exception as e:
                        logger.warning(
                            f"Could not capture logs for dying container {container_name}: {e}"
                        )

                elif action in ["health_status"]:
                    health = attributes.get("health", "unknown")
                    logger.info(
                        f"[Event] HEALTH - {container_name} ({container_id[:12]}) - {health}"
                    )

                elif action in ["destroy"]:
                    container_status[container_id] = "removed"
                    logger.info(
                        f"[Event] DESTROY ← - {container_name} ({container_id[:12]})"
                    )

                # Display current status summary (only if we have tracked containers)
                if container_status:
                    running_count = sum(
                        1 for s in container_status.values() if s == "running"
                    )
                    total_count = len(container_status)
                    logger.info(
                        f"    [Status] {running_count}/{total_count} containers running"
                    )

            except Exception as e:
                logger.error(f"  ✗ Error processing event: {e}")
                import traceback

                traceback.print_exc()

    except KeyboardInterrupt:
        logger.info("[Event Listener] Monitoring stopped.")
    except Exception as e:
        logger.error(f"  ✗ Event listener error: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Main entry point for the LDES consumer application"""

    # Default path for the configuration file (from mounted volume)
    config_path = os.getenv("LDES_CONFIG_PATH", "/data/ldes-feeds.yaml")

    # Docker image to use for spawning containers
    ldes2sparql_image = os.getenv(
        "LDES2SPARQL_IMAGE", "ghcr.io/maregraph-eu/ldes2sparql:latest"
    )

    logger.info("=" * 60)
    logger.info("LDES Consumer Application")
    logger.info("=" * 60)
    logger.info(f"Reading configuration from: {config_path}")
    logger.info(f"LDES2SPARQL Image: {ldes2sparql_image}")

    # Initialize Docker client
    try:
        docker_client = docker.from_env()
        docker_client.ping()
        logger.info("✓ Docker connection established")
    except Exception as e:
        logger.error(f"✗ Error connecting to Docker: {e}")
        logger.error("Make sure Docker socket is mounted at /var/run/docker.sock")
        sys.exit(1)

    # Load feeds BEFORE starting containers
    feeds_config = load_ldes_feeds(config_path)

    # Initialize empty containers list that will be filled after spawning
    containers = []

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal...")
        cleanup_containers(containers)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start event monitoring in background BEFORE spawning containers
    # This way we catch all events from the start
    logger.info("Starting event listener before spawning containers...")

    monitoring_thread = threading.Thread(
        target=monitor_containers_with_events,
        args=(docker_client, containers),  # containers will be populated shortly
        daemon=False,
    )
    monitoring_thread.start()

    # Give the event listener a moment to start listening
    time.sleep(1)

    logger.info("Now spawning containers...")

    # NOW spawn containers - event listener is already listening
    containers = process_feeds(feeds_config, docker_client, ldes2sparql_image)

    logger.info(f"Configuration loaded successfully!")
    logger.info(f"Spawned {len(containers)} container(s)")

    try:
        # Keep the main thread alive to handle signals and do fallback monitoring
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        cleanup_containers(containers)


if __name__ == "__main__":
    main()
