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
from pathlib import Path

from logger import setup_logger

# Set up logger
logger = setup_logger("ldes-consumer", os.getenv("LOG_LEVEL", "INFO"))


# Global list to track spawned processes
spawned_processes: List[Dict[str, subprocess.Popen | Dict]] = []


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down LDES consumers...")
    for spawned in spawned_processes:
        try:
            proc = spawned["proc"]
            feed = spawned["feed"]
            proc.terminate()
        except Exception as e:
            logger.error(f"Error terminating process for feed [{feed.get('name')}]: {e}")
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
    feed_name = feed.get("name")
    if not feed_name:
        logger.error("Feed is missing required 'name' field")
        return None

    feed_url = feed.get("url")
    if not feed_url:
        logger.error(f"Feed '{feed_name}' is missing required 'url' field")
        return None

    sparql_endpoint = feed.get("sparql_endpoint")
    if not sparql_endpoint:
        logger.error(f"Feed '{feed_name}' is missing required 'sparql_endpoint' field")
        return None

    target_graph = feed.get("target_graph", f"urn:kgap:ldes-consumer:{feed_name}")
    container_name = f"ldes-consumer-{feed_name}"

    # Build docker run command
    cmd = [
        "docker",
        "run",
        # "--rm", # Uncomment to auto-remove container on exit
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

    # Add environment variables
    cmd.extend(["-e", f"LDES={feed_url}"])
    cmd.extend(["-e", f"SPARQL_ENDPOINT={sparql_endpoint}"])
    cmd.extend(["-e", "SHAPE="])
    cmd.extend(["-e", f"TARGET_GRAPH={target_graph}"])
    cmd.extend(["-e", "FAILURE_IS_FATAL=false"])
    cmd.extend(["-e", "FOLLOW=true"])
    cmd.extend(["-e", "MATERIALIZE=true"])

    # Note: The config uses 'polling_interval' (seconds) for user-friendliness,
    # but ldes2sparql expects 'POLLING_FREQUENCY' (milliseconds)
    polling_frequency = feed.get("polling_interval", 60) * 1000
    cmd.extend(["-e", f"POLLING_FREQUENCY={polling_frequency}"])

    # log cmd
    logger.debug(f"Docker command for feed '{feed_name}': {' '.join(cmd)}")

    # Add any additional environment variables from the feed config
    extra_env = feed.get("environment") or {}
    if isinstance(extra_env, dict):
        for key, value in extra_env.items():
            cmd.extend(["-e", f"{key}={value}"])
    elif extra_env is not None:
        logger.warning(
            f"'environment' for feed '{feed_name}' is not a mapping; skipping"
        )

    # Add the image name
    cmd.append(image)

    logger.info(f"Starting LDES consumer for feed: {feed_name}")
    logger.info(f"  URL: {feed_url}")
    logger.info(f"  SPARQL Endpoint: {sparql_endpoint}")
    logger.info(f"  Target Graph: {target_graph}")
    logger.info(f"  Polling Frequency (ms): {polling_frequency}")
    logger.debug(f"  Command: {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        # Give the container a moment to start
        time.sleep(2)

        # Check if the container is actually running
        check_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
        try:
            result = subprocess.run(
                check_cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip() == "true":
                # Container is running successfully
                return proc
            else:
                # Container failed to start or is not running
                logger.error(f"Container '{container_name}' failed to start properly. Capturing logs...")
                # Try to get logs
                capture_logs_cmd = ["docker", "logs", container_name]
                # allocate filenames to capture stdout and stderr
                Path("/data/logs").mkdir(parents=True, exist_ok=True)
                stdout_log = f"/data/logs/{container_name}_stdout.log"
                stderr_log = f"/data/logs/{container_name}_stderr.log"

                with open(stdout_log, "w") as stdout_file, open(stderr_log, "w") as stderr_file:
                    capture_logs = subprocess.run(capture_logs_cmd, stdout=stdout_file, stderr=stderr_file, timeout=5)
                    if capture_logs.returncode == 0:
                        logger.error(f"Container logs can be found in data/logs/{container_name}_*.log")
                return None
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout checking container status for '{container_name}'")
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
    project_name = os.getenv("COMPOSE_PROJECT_NAME", "kgap")
    network_name = os.getenv("DOCKER_NETWORK", f"{project_name}_default")

    logger.info(f"Found {len(feeds)} LDES feed(s) to process")

    # Spawn instances for each feed
    def spawn_and_register(feed, register_list):
        proc = spawn_ldes2sparql_instance(
            feed, network_name, ldes2sparql_image, project_name
        )
        if proc:
            register_list.append(dict(feed=feed, proc=proc))

    for feed in feeds:
        spawn_and_register(feed, spawned_processes)

    if not spawned_processes:
        logger.error(f"No LDES consumers (out of {len(feeds)}) were started successfully")
        sys.exit(1)

    logger.info(f"Successfully started {len(spawned_processes)} of {len(feeds)} LDES consumer(s)")
    logger.info("Starting to monitor started processes... (Press Ctrl+C to stop)")

    # Monitor processes and restart if they fail
    while True:
        time.sleep(300)  # 5 minutes
        updated_processes = []
        for spawned in spawned_processes:
            feed = spawned["feed"]
            proc = spawned["proc"]
            proc_poll = proc.poll()
            if proc_poll is None:
                # Process is still running
                updated_processes.append(spawned)
            else:
                # Process has terminated
                returncode = proc.returncode
                feed_name = feed.get("name", "unnamed")
                logger.warning(
                    f"LDES consumer for feed '{feed_name}' terminated with code {returncode} - attempting restart"
                )
                spawn_and_register(feed, updated_processes)
        spawned_processes[:] = updated_processes


if __name__ == "__main__":
    main()
