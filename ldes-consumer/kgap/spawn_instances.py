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

# Global list to track spawned processes
spawned_processes: List[subprocess.Popen] = []


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\nReceived signal {signum}, shutting down LDES consumers...")
    for proc in spawned_processes:
        try:
            proc.terminate()
        except Exception as e:
            print(f"Error terminating process: {e}")
    sys.exit(0)


def load_config(config_file: str) -> Dict[str, Any]:
    """Load and parse the YAML configuration file."""
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"ERROR: Failed to load config file {config_file}: {e}")
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
        print(
            f"ERROR: Feed '{feed_name}' is missing required 'url' or 'sparql_endpoint'"
        )
        return None

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
    cmd.extend(["-e", "TARGET_GRAPH="])
    cmd.extend(["-e", "FAILURE_IS_FATAL=false"])
    cmd.extend(["-e", "FOLLOW=true"])
    cmd.extend(["-e", "MATERIALIZE=false"])

    # Note: The config uses 'polling_interval' (seconds) for user-friendliness,
    # but ldes2sparql expects 'POLLING_FREQUENCY' (milliseconds)
    polling_frequency = feed.get("polling_interval", 60) * 1000
    # cmd.extend(["-e", f"POLLING_FREQUENCY={polling_frequency}"])

    # log cmd
    print(f"DEBUG: Docker command for feed '{feed_name}': {' '.join(cmd)}")

    # Add any additional environment variables from the feed config
    extra_env = feed.get("environment") or {}
    if isinstance(extra_env, dict):
        for key, value in extra_env.items():
            cmd.extend(["-e", f"{key}={value}"])
    elif extra_env is not None:
        print(
            f"WARNING: 'environment' for feed '{feed_name}' is not a mapping; skipping"
        )

    # Add the image name
    cmd.append(image)

    print(f"Starting LDES consumer for feed: {feed_name}")
    print(f"  URL: {feed_url}")
    print(f"  SPARQL Endpoint: {sparql_endpoint}")
    print(f"  Command: {' '.join(cmd)}")

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
                print(f"ERROR: Container '{container_name}' failed to start properly")
                # Try to get logs
                logs_cmd = ["docker", "logs", container_name]
                logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)
                if logs_result.stdout or logs_result.stderr:
                    print(
                        f"Container logs:\n{logs_result.stdout}\n{logs_result.stderr}"
                    )
                return None
        except subprocess.TimeoutExpired:
            print(f"ERROR: Timeout checking container status for '{container_name}'")
            return None
    except Exception as e:
        print(f"ERROR: Failed to spawn container for feed '{feed_name}': {e}")
        return None


def main():
    """Main function to spawn all ldes2sparql instances."""
    if len(sys.argv) < 2:
        print("Usage: spawn_instances.py <config_file>")
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
        print("ERROR: No feeds defined in configuration file")
        sys.exit(1)

    # Get configuration options
    ldes2sparql_image = os.getenv(
        "LDES2SPARQL_IMAGE", "ghcr.io/rdf-connect/ldes2sparql:latest"
    )
    network_name = os.getenv("DOCKER_NETWORK", "kgap_default")
    project_name = os.getenv("COMPOSE_PROJECT_NAME", "kgap")

    print(f"Found {len(feeds)} LDES feed(s) to process")

    # Spawn instances for each feed
    for feed in feeds:
        proc = spawn_ldes2sparql_instance(
            feed, network_name, ldes2sparql_image, project_name
        )
        if proc:
            spawned_processes.append(proc)

    if not spawned_processes:
        print("ERROR: No LDES consumers were started successfully")
        sys.exit(1)

    print(f"\nSuccessfully started {len(spawned_processes)} LDES consumer(s)")
    print("Monitoring processes... (Press Ctrl+C to stop)")

    # Monitor processes and restart if they fail
    while True:
        time.sleep(10)
        for i, proc in enumerate(spawned_processes):
            feed = feeds[i]
            feed_name = feed.get("name", "unnamed")
            if proc.poll() is not None:
                # Process has terminated
                returncode = proc.returncode
                print(
                    f"WARNING: LDES consumer for feed '{feed_name}' terminated with code {returncode}"
                )
                """
                # Try to read final output
                stdout, stderr = proc.communicate()
                if stdout:
                    print(f"STDOUT: {stdout}")
                if stderr:
                    print(f"STDERR: {stderr}")
                print(f"Attempting to restart consumer for feed '{feed_name}'...")
                new_proc = spawn_ldes2sparql_instance(
                    feed, network_name, ldes2sparql_image
                )
                if new_proc:
                    spawned_processes[i] = new_proc
                    print(f"Successfully restarted consumer for feed '{feed_name}'")
                else:
                    print(f"Failed to restart consumer for feed '{feed_name}'")
                """


if __name__ == "__main__":
    main()
