#!/usr/bin/env python3
"""
Standalone cleanup utility for orphaned LDES consumer containers.
Can be run manually to remove all child containers spawned by the LDES consumer.

Usage:
    python3 cleanup_containers.py [project_name] [prefix]

Examples:
    python3 cleanup_containers.py kgap ldes-consumer
    python3 cleanup_containers.py my-project my-prefix
"""
import sys
import os
import docker
from docker.errors import NotFound, APIError, DockerException


def cleanup_containers(project_name: str, prefix: str) -> None:
    """Remove all child containers spawned by LDES consumer for a project."""
    try:
        client = docker.from_env()
    except DockerException as e:
        print(f"ERROR: Failed to connect to Docker daemon: {e}")
        sys.exit(1)

    try:
        # Query containers with the project label
        filters = {"label": f"com.docker.compose.project={project_name}"}
        containers = client.containers.list(all=True, filters=filters)
        print(
            f"[INFO] Found {len(containers)} container(s) with project label '{project_name}'"
        )

        # Filter to only those with the matching prefix
        child_containers = [c for c in containers if c.name.startswith(f"{prefix}-")]

        if not child_containers:
            print(
                f"[INFO] No containers to clean up with prefix '{prefix}' for project '{project_name}'"
            )
            return

        print(f"[INFO] Found {len(child_containers)} container(s) to remove:")
        for c in child_containers:
            print(f"      - {c.name}")

        # Remove each container
        removed_count = 0
        for container in child_containers:
            try:
                # Reload to get current status
                container.reload()
                print(
                    f"[INFO] Removing container '{container.name}' (status: {container.status})..."
                )

                # Stop if running
                if container.status in ("running", "created"):
                    try:
                        container.stop(timeout=10)
                        print(f"[INFO]   Stopped '{container.name}'")
                    except Exception as e:
                        print(f"[WARN]   Failed to stop '{container.name}': {e}")

                # Remove
                container.remove(force=True)
                print(f"[INFO]   Removed '{container.name}' successfully")
                removed_count += 1

            except NotFound:
                print(
                    f"[INFO] Container '{container.name}' not found (already removed)"
                )
            except APIError as e:
                print(f"[ERROR] Docker API error for '{container.name}': {e}")
            except Exception as e:
                print(f"[ERROR] Error removing '{container.name}': {e}")

        print(
            f"\n[INFO] Cleanup complete: {removed_count}/{len(child_containers)} container(s) removed"
        )

    except APIError as e:
        print(f"ERROR: Docker API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Default values
    project_name = os.getenv("COMPOSE_PROJECT_NAME", "kgap")
    prefix = os.getenv("LDES_CONSUMER_PREFIX", "ldes-consumer")

    # Override with CLI arguments
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
    if len(sys.argv) > 2:
        prefix = sys.argv[2]

    print(
        f"[INFO] Starting cleanup for project '{project_name}' with prefix '{prefix}'"
    )
    cleanup_containers(project_name, prefix)
