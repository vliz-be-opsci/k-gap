#!/usr/bin/env python3
"""
LDES Consumer Folder Watcher
Monitors a folder for YAML files and spawns/stops ldes2sparql containers accordingly.
"""
import os
import sys
import yaml
import subprocess
import signal
import time
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from logger import setup_logger

# Set up logger
logger = setup_logger("ldes-folder-watcher", os.getenv("LOG_LEVEL", "INFO"))

# Global tracking of containers
active_containers: Dict[str, Dict] = {}  # {filename: {container_name: str, proc: Popen, config: dict}}


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down all LDES consumers...")
    cleanup_all_containers()
    sys.exit(0)


def cleanup_all_containers():
    """Stop and remove all spawned containers."""
    for filename, container_info in list(active_containers.items()):
        stop_container(filename)


def load_yaml_config(yaml_file: Path) -> Optional[Dict]:
    """Load and validate a YAML configuration file."""
    try:
        with open(yaml_file, "r") as f:
            config = yaml.safe_load(f)
        
        if not config:
            logger.warning(f"Empty YAML file: {yaml_file}")
            return None
        
        # Validate required fields
        if "url" not in config or "sparql_endpoint" not in config:
            logger.error(
                f"YAML file {yaml_file} missing required fields 'url' or 'sparql_endpoint'"
            )
            return None
        
        return config
    except Exception as e:
        logger.error(f"Failed to load YAML file {yaml_file}: {e}")
        return None


def get_container_name(yaml_filename: str) -> str:
    """Generate a container name from the YAML filename."""
    # Remove .yaml or .yml extension
    name = yaml_filename.replace(".yaml", "").replace(".yml", "")
    # Sanitize name for docker
    name = name.replace("_", "-").replace(" ", "-").lower()
    return f"ldes-consumer-{name}"


def spawn_container(yaml_file: Path) -> bool:
    """
    Spawn a ldes2sparql container from a YAML configuration file.
    
    Args:
        yaml_file: Path to the YAML configuration file
    
    Returns:
        True if container was spawned successfully, False otherwise
    """
    filename = yaml_file.name
    
    # Check if container already exists for this file
    if filename in active_containers:
        logger.warning(f"Container already exists for {filename}")
        return False
    
    # Load configuration
    config = load_yaml_config(yaml_file)
    if not config:
        return False
    
    container_name = get_container_name(filename)
    
    # Get configuration options
    ldes2sparql_image = os.getenv(
        "LDES2SPARQL_IMAGE", "ghcr.io/rdf-connect/ldes2sparql:latest"
    )
    network_name = os.getenv("DOCKER_NETWORK", "kgap_default")
    project_name = os.getenv("COMPOSE_PROJECT_NAME", "kgap")
    
    # Build docker run command
    cmd = [
        "docker",
        "run",
        "-d",  # Run in detached mode
        "--name",
        container_name,
        "--network",
        network_name,
        "--label",
        f"com.docker.compose.project={project_name}",
        "--label",
        "com.docker.compose.service=ldes-consumer",
        "--label",
        f"ldes.config.file={filename}",
        "-v",
        f"/data/ldes-state-{container_name}:/state",
    ]
    
    # Add required environment variables
    cmd.extend(["-e", f"LDES={config['url']}"])
    cmd.extend(["-e", f"SPARQL_ENDPOINT={config['sparql_endpoint']}"])
    
    # Add optional environment variables with defaults
    cmd.extend(["-e", f"SHAPE={config.get('shape', '')}"])
    cmd.extend(["-e", f"TARGET_GRAPH={config.get('target_graph', '')}"])
    cmd.extend(["-e", f"FAILURE_IS_FATAL={config.get('failure_is_fatal', 'false')}"])
    cmd.extend(["-e", f"FOLLOW={config.get('follow', 'true')}"])
    cmd.extend(["-e", f"MATERIALIZE={config.get('materialize', 'false')}"])
    cmd.extend(["-e", f"ORDER={config.get('order', 'none')}"])
    cmd.extend(["-e", f"LAST_VERSION_ONLY={config.get('last_version_only', 'false')}"])
    
    # Polling interval: convert seconds to milliseconds if provided
    polling_interval = config.get('polling_interval', 5)
    try:
        polling_frequency = int(float(polling_interval) * 1000)
    except (TypeError, ValueError):
        logger.warning(
            f"Invalid polling_interval '{polling_interval}', using default 5000ms"
        )
        polling_frequency = 5000
    cmd.extend(["-e", f"POLLING_FREQUENCY={polling_frequency}"])
    
    # Add timestamp filters if provided
    if 'before' in config:
        cmd.extend(["-e", f"BEFORE={config['before']}"])
    if 'after' in config:
        cmd.extend(["-e", f"AFTER={config['after']}"])
    
    # Add concurrent fetches option
    concurrent_fetches = config.get('concurrent_fetches', 10)
    cmd.extend(["-e", f"CONCURRENT_FETCHES={int(concurrent_fetches)}"])
    
    # Add SPARQL-specific options
    cmd.extend(["-e", f"FOR_VIRTUOSO={config.get('for_virtuoso', 'false')}"])
    cmd.extend(["-e", f"QUERY_TIMEOUT={config.get('query_timeout', '1800')}"])
    
    # Add access token if provided
    if 'access_token' in config:
        cmd.extend(["-e", f"ACCESS_TOKEN={config['access_token']}"])
    
    # Add performance options
    if 'perf_name' in config:
        cmd.extend(["-e", f"PERF_NAME={config['perf_name']}"])
    
    # Add any additional custom environment variables
    extra_env = config.get("environment") or {}
    if isinstance(extra_env, dict):
        for key, value in extra_env.items():
            # Validate and sanitize environment variable values
            if value is not None:
                # Convert to string and escape special characters
                safe_value = str(value).replace('"', '\\"')
                cmd.extend(["-e", f"{key}={safe_value}"])
            else:
                logger.warning(f"Skipping environment variable '{key}' with None value")
    
    # Add the image name
    cmd.append(ldes2sparql_image)
    
    logger.info(f"Starting LDES consumer from config file: {filename}")
    logger.info(f"  Container name: {container_name}")
    logger.info(f"  URL: {config['url']}")
    logger.info(f"  SPARQL Endpoint: {config['sparql_endpoint']}")
    logger.debug(f"  Command: {' '.join(cmd)}")
    
    try:
        # Run docker command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"Failed to start container {container_name}: {result.stderr}")
            return False
        
        # Give the container a moment to start
        time.sleep(2)
        
        # Verify container is running
        check_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
        
        if check_result.returncode == 0 and check_result.stdout.strip() == "true":
            logger.info(f"Successfully started container: {container_name}")
            active_containers[filename] = {
                "container_name": container_name,
                "config": config,
            }
            return True
        else:
            logger.error(f"Container {container_name} failed to start properly")
            # Try to get logs
            logs_cmd = ["docker", "logs", container_name]
            logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)
            if logs_result.stdout or logs_result.stderr:
                logger.error(f"Container logs:\n{logs_result.stdout}\n{logs_result.stderr}")
            return False
    
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout starting container {container_name}")
        return False
    except Exception as e:
        logger.error(f"Failed to spawn container for {filename}: {e}")
        return False


def stop_container(yaml_filename: str) -> bool:
    """
    Stop and remove a container associated with a YAML file.
    
    Args:
        yaml_filename: Name of the YAML file
    
    Returns:
        True if container was stopped successfully, False otherwise
    """
    if yaml_filename not in active_containers:
        logger.warning(f"No active container found for {yaml_filename}")
        return False
    
    container_info = active_containers[yaml_filename]
    container_name = container_info["container_name"]
    
    logger.info(f"Stopping container: {container_name}")
    
    try:
        # Stop the container
        stop_cmd = ["docker", "stop", container_name]
        result = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.warning(f"Failed to stop container {container_name}: {result.stderr}")
        
        # Remove the container
        rm_cmd = ["docker", "rm", container_name]
        rm_result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=30)
        
        if rm_result.returncode != 0:
            logger.warning(f"Failed to remove container {container_name}: {rm_result.stderr}")
        
        # Remove from tracking
        del active_containers[yaml_filename]
        logger.info(f"Successfully stopped and removed container: {container_name}")
        return True
    
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout stopping container {container_name}")
        return False
    except Exception as e:
        logger.error(f"Failed to stop container {container_name}: {e}")
        return False


class YAMLFileEventHandler(FileSystemEventHandler):
    """Handler for file system events on YAML files."""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        super().__init__()
    
    def is_yaml_file(self, path: str) -> bool:
        """Check if a file is a YAML file."""
        return path.endswith(".yaml") or path.endswith(".yml")
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if self.is_yaml_file(event.src_path):
            yaml_file = Path(event.src_path)
            logger.info(f"Detected new YAML file: {yaml_file.name}")
            time.sleep(1)  # Brief delay to ensure file is fully written
            spawn_container(yaml_file)
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        if self.is_yaml_file(event.src_path):
            yaml_filename = Path(event.src_path).name
            logger.info(f"Detected deleted YAML file: {yaml_filename}")
            stop_container(yaml_filename)
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if self.is_yaml_file(event.src_path):
            yaml_file = Path(event.src_path)
            yaml_filename = yaml_file.name
            logger.info(f"Detected modified YAML file: {yaml_filename}")
            
            # Stop existing container if it exists
            if yaml_filename in active_containers:
                stop_container(yaml_filename)
            
            # Wait a moment for file to be fully written
            time.sleep(1)
            
            # Start new container with updated config
            spawn_container(yaml_file)


def scan_and_start_containers(config_dir: Path):
    """Scan directory for existing YAML files and start containers."""
    logger.info(f"Scanning directory for YAML files: {config_dir}")
    
    yaml_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))
    
    if not yaml_files:
        logger.warning(f"No YAML files found in {config_dir}")
        return
    
    logger.info(f"Found {len(yaml_files)} YAML file(s)")
    
    for yaml_file in yaml_files:
        spawn_container(yaml_file)


def main():
    """Main function to watch folder and manage containers."""
    if len(sys.argv) < 2:
        logger.error("Usage: folder_watcher.py <config_directory>")
        sys.exit(1)
    
    config_dir = Path(sys.argv[1])
    
    if not config_dir.exists():
        logger.error(f"Configuration directory does not exist: {config_dir}")
        sys.exit(1)
    
    if not config_dir.is_dir():
        logger.error(f"Path is not a directory: {config_dir}")
        sys.exit(1)
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info(f"Starting LDES consumer folder watcher on: {config_dir}")
    
    # Initial scan and start of containers
    scan_and_start_containers(config_dir)
    
    # Set up file system watcher
    event_handler = YAMLFileEventHandler(config_dir)
    observer = Observer()
    observer.schedule(event_handler, str(config_dir), recursive=False)
    observer.start()
    
    logger.info("File watcher started. Monitoring for changes...")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(10)
            
            # Health check: verify all containers are still running
            for filename in list(active_containers.keys()):
                container_info = active_containers[filename]
                container_name = container_info["container_name"]
                
                check_cmd = ["docker", "inspect", "-f", "{{.State.Running}}", container_name]
                try:
                    result = subprocess.run(
                        check_cmd, capture_output=True, text=True, timeout=5
                    )
                    if result.returncode != 0 or result.stdout.strip() != "true":
                        logger.warning(f"Container {container_name} is not running, restarting...")
                        # Remove from tracking and restart
                        del active_containers[filename]
                        yaml_file = config_dir / filename
                        if yaml_file.exists():
                            spawn_container(yaml_file)
                except Exception as e:
                    logger.error(f"Error checking container {container_name}: {e}")
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        observer.stop()
        observer.join()
        cleanup_all_containers()
        logger.info("Folder watcher stopped")


if __name__ == "__main__":
    main()
