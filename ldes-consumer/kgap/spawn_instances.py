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
from typing import List, Dict, Any

from logger import setup_logger

# Set up logger
logger = setup_logger("ldes-consumer", os.getenv("LOG_LEVEL", "INFO"))

# Global list to track spawned container names
spawned_containers: List[str] = []


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down LDES consumers...")
    for container_name in spawned_containers:
        try:
            logger.info(f"Stopping container: {container_name}")
            subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                timeout=30
            )
        except Exception as e:
            logger.error(f"Error stopping container {container_name}: {e}")
    sys.exit(0)


def load_config(config_file: str) -> Dict[str, Any]:
    """Load and parse the YAML configuration file."""
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load config file {config_file}: {e}")
        sys.exit(1)


def spawn_ldes2sparql_instance(
    feed: Dict[str, Any], network_name: str, image: str, project_name: str
) -> subprocess.Popen:
    """
    Spawn a single ldes2sparql Docker container instance.

    Args:
        feed: Dictionary containing feed configuration
        network_name: Docker network to attach to
        image: Docker image to use for ldes2sparql
        project_name: Docker Compose project name for container labeling

    Returns:
        Subprocess object for the spawned container
    """
    feed_name = feed.get("name", "unnamed")
    feed_url = feed.get("url")
    sparql_endpoint = feed.get("sparql_endpoint")

    if not feed_url or not sparql_endpoint:
        logger.error(
            f"Feed '{feed_name}' is missing required 'url' or 'sparql_endpoint'"
        )
        return None

    container_name = f"ldes-consumer-{feed_name}"

    # Build docker run command
    cmd = [
        "docker",
        "run",
        "-d",  # Run in detached mode
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
        f"/data/ldes-state-{feed_name}:/state",
    ]

    # Add environment variables with defaults
    cmd.extend(["-e", f"LDES={feed_url}"])
    cmd.extend(["-e", f"SPARQL_ENDPOINT={sparql_endpoint}"])
    cmd.extend(["-e", f"SHAPE={feed.get('shape', '')}"])
    cmd.extend(["-e", f"TARGET_GRAPH={feed.get('target_graph', '')}"])
    cmd.extend(["-e", f"FAILURE_IS_FATAL={feed.get('failure_is_fatal', 'false')}"])
    cmd.extend(["-e", f"FOLLOW={feed.get('follow', 'true')}"])
    cmd.extend(["-e", f"MATERIALIZE={feed.get('materialize', 'false')}"])
    cmd.extend(["-e", f"ORDER={feed.get('order', 'none')}"])
    cmd.extend(["-e", f"LAST_VERSION_ONLY={feed.get('last_version_only', 'false')}"])

    # Polling interval: convert seconds to milliseconds
    polling_interval = feed.get("polling_interval", 60)
    try:
        polling_frequency = int(float(polling_interval) * 1000)
    except (TypeError, ValueError):
        logger.warning(
            f"Invalid polling_interval '{polling_interval}' for feed '{feed_name}', using default 60000ms"
        )
        polling_frequency = 60000
    cmd.extend(["-e", f"POLLING_FREQUENCY={polling_frequency}"])
    
    # Add timestamp filters if provided
    if 'before' in feed:
        cmd.extend(["-e", f"BEFORE={feed['before']}"])
    if 'after' in feed:
        cmd.extend(["-e", f"AFTER={feed['after']}"])
    
    # Add concurrent fetches option
    concurrent_fetches = feed.get('concurrent_fetches', 10)
    cmd.extend(["-e", f"CONCURRENT_FETCHES={int(concurrent_fetches)}"])
    
    # Add SPARQL-specific options
    cmd.extend(["-e", f"FOR_VIRTUOSO={feed.get('for_virtuoso', 'false')}"])
    cmd.extend(["-e", f"QUERY_TIMEOUT={feed.get('query_timeout', '1800')}"])
    
    # Add access token if provided
    if 'access_token' in feed:
        cmd.extend(["-e", f"ACCESS_TOKEN={feed['access_token']}"])
    
    # Add performance options
    if 'perf_name' in feed:
        cmd.extend(["-e", f"PERF_NAME={feed['perf_name']}"])

    # log cmd
    logger.debug(f"Docker command for feed '{feed_name}': {' '.join(cmd)}")

    # Add any additional custom environment variables
    extra_env = feed.get("environment") or {}
    if isinstance(extra_env, dict):
        for key, value in extra_env.items():
            # Validate and sanitize environment variable values
            if value is not None:
                # Convert to string and escape special characters
                safe_value = str(value).replace('"', '\\"')
                cmd.extend(["-e", f"{key}={safe_value}"])
            else:
                logger.warning(f"Skipping environment variable '{key}' with None value for feed '{feed_name}'")
    elif extra_env is not None:
        logger.warning(
            f"'environment' for feed '{feed_name}' is not a mapping; skipping"
        )

    # Add the image name
    cmd.append(image)

    logger.info(f"Starting LDES consumer for feed: {feed_name}")
    logger.info(f"  URL: {feed_url}")
    logger.info(f"  SPARQL Endpoint: {sparql_endpoint}")
    logger.debug(f"  Command: {' '.join(cmd)}")

    try:
        # Run docker command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"Failed to start container {container_name}: {result.stderr}")
            return None
        
        # Give the container a moment to start
        time.sleep(2)

        # Check if the container is actually running
        check_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
        try:
            check_result = subprocess.run(
                check_cmd, capture_output=True, text=True, timeout=5
            )
            if check_result.returncode == 0 and check_result.stdout.strip() == "true":
                # Container is running successfully
                logger.info(f"Successfully started container: {container_name}")
                return True
            else:
                # Container failed to start or is not running
                logger.error(f"Container '{container_name}' failed to start properly")
                # Try to get logs
                logs_cmd = ["docker", "logs", container_name]
                logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)
                if logs_result.stdout or logs_result.stderr:
                    logger.error(
                        f"Container logs:\n{logs_result.stdout}\n{logs_result.stderr}"
                    )
                return None
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout checking container status for '{container_name}'")
            return None
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout starting container {container_name}")
        return None
    except Exception as e:
        logger.error(f"Failed to spawn container for feed '{feed_name}': {e}")
        return None


def main():
    """Main function to spawn all ldes2sparql instances."""
    if len(sys.argv) < 2:
        logger.error("Usage: spawn_instances.py <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Load configuration
    config = load_config(config_file)

    # Get feeds list
    feeds = config.get("feeds", [])
    if not feeds:
        logger.error("No feeds defined in configuration file")
        sys.exit(1)

    # Get configuration options
    ldes2sparql_image = os.getenv(
        "LDES2SPARQL_IMAGE", "ghcr.io/rdf-connect/ldes2sparql:latest"
    )
    network_name = os.getenv("DOCKER_NETWORK", "kgap_default")
    project_name = os.getenv("COMPOSE_PROJECT_NAME", "kgap")

    logger.info(f"Found {len(feeds)} LDES feed(s) to process")

    # Spawn instances for each feed
    successful_spawns = []
    for feed in feeds:
        result = spawn_ldes2sparql_instance(
            feed, network_name, ldes2sparql_image, project_name
        )
        if result:
            feed_name = feed.get("name", "unnamed")
            container_name = f"ldes-consumer-{feed_name}"
            successful_spawns.append(feed_name)
            spawned_containers.append(container_name)

    if not successful_spawns:
        logger.error("No LDES consumers were started successfully")
        sys.exit(1)

    logger.info(f"Successfully started {len(successful_spawns)} LDES consumer(s)")
    logger.info("Containers running in detached mode")
    
    # Monitor container health
    logger.info("Monitoring containers... (Press Ctrl+C to stop)")
    
    while True:
        time.sleep(30)
        # Check that all spawned containers are still running
        for feed_name in successful_spawns:
            container_name = f"ldes-consumer-{feed_name}"
            check_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
            try:
                result = subprocess.run(
                    check_cmd, capture_output=True, text=True, timeout=5
                )
                if result.returncode != 0 or result.stdout.strip() != "true":
                    logger.warning(
                        f"Container {container_name} is not running. It may have stopped or been removed."
                    )
            except Exception as e:
                logger.error(f"Error checking container {container_name}: {e}")


if __name__ == "__main__":
    main()
