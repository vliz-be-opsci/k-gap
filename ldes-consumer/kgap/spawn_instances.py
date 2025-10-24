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
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"ERROR: Failed to load config file {config_file}: {e}")
        sys.exit(1)


def spawn_ldes2sparql_instance(feed: Dict[str, Any], network_name: str, image: str) -> subprocess.Popen:
    """
    Spawn a single ldes2sparql Docker container instance.
    
    Args:
        feed: Dictionary containing feed configuration
        network_name: Docker network to attach to
        image: Docker image to use for ldes2sparql
    
    Returns:
        Subprocess object for the spawned container
    """
    feed_name = feed.get('name', 'unnamed')
    feed_url = feed.get('url')
    sparql_endpoint = feed.get('sparql_endpoint')
    
    if not feed_url or not sparql_endpoint:
        print(f"ERROR: Feed '{feed_name}' is missing required 'url' or 'sparql_endpoint'")
        return None
    
    container_name = f"ldes-consumer-{feed_name}"
    
    # Build docker run command
    cmd = [
        'docker', 'run',
        '--rm',
        '--name', container_name,
        '--network', network_name,
    ]
    
    # Add environment variables
    cmd.extend(['-e', f'LDES_URL={feed_url}'])
    cmd.extend(['-e', f'SPARQL_ENDPOINT={sparql_endpoint}'])
    
    # Add optional polling interval (default to 60 seconds if not specified)
    polling_interval = feed.get('polling_interval', 60)
    cmd.extend(['-e', f'POLLING_INTERVAL={polling_interval}'])
    
    # Add any additional environment variables from the feed config
    extra_env = feed.get('environment', {})
    for key, value in extra_env.items():
        cmd.extend(['-e', f'{key}={value}'])
    
    # Add the image name
    cmd.append(image)
    
    print(f"Starting LDES consumer for feed: {feed_name}")
    print(f"  URL: {feed_url}")
    print(f"  SPARQL Endpoint: {sparql_endpoint}")
    print(f"  Command: {' '.join(cmd)}")
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc
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
    feeds = config.get('feeds', [])
    if not feeds:
        print("ERROR: No feeds defined in configuration file")
        sys.exit(1)
    
    # Get configuration options
    ldes2sparql_image = os.getenv('LDES2SPARQL_IMAGE', 'brechtvdv/ldes2sparql:latest')
    network_name = os.getenv('DOCKER_NETWORK', 'kgap_default')
    
    print(f"Found {len(feeds)} LDES feed(s) to process")
    
    # Spawn instances for each feed
    for feed in feeds:
        proc = spawn_ldes2sparql_instance(feed, network_name, ldes2sparql_image)
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
        
        # Check if any process has terminated
        for i, proc in enumerate(spawned_processes):
            if proc.poll() is not None:
                # Process has terminated
                returncode = proc.returncode
                feed = feeds[i]
                feed_name = feed.get('name', 'unnamed')
                
                print(f"WARNING: LDES consumer for feed '{feed_name}' terminated with code {returncode}")
                
                # Try to restart the process
                print(f"Attempting to restart consumer for feed '{feed_name}'...")
                new_proc = spawn_ldes2sparql_instance(feed, network_name, ldes2sparql_image)
                if new_proc:
                    spawned_processes[i] = new_proc
                    print(f"Successfully restarted consumer for feed '{feed_name}'")
                else:
                    print(f"Failed to restart consumer for feed '{feed_name}'")


if __name__ == '__main__':
    main()
