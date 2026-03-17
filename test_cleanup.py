#!/usr/bin/env python3
"""
Test script to verify LDES consumer child container cleanup.
"""
import subprocess
import time
import sys


def run_command(cmd, description):
    """Run a command and print output."""
    print(f"\n>>> {description}")
    print(f"    Command: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        for line in result.stdout.split("\n")[:10]:
            if line.strip():
                print(f"    {line}")
    if result.stderr:
        print(f"    ERROR: {result.stderr[:200]}")
    return result.returncode


def main():
    print("=" * 60)
    print("LDES Consumer Child Container Cleanup Test")
    print("=" * 60)

    # Test 1: Check initial state
    run_command(
        "docker ps -a --filter 'name=ldes-consumer' --format 'table {{.Names}}'",
        "Test 1: Check current containers",
    )

    # Test 2: Start the stack
    print("\n>>> Test 2: Starting k-gap stack...")
    run_command(
        "docker compose -f data/ldes-feeds.yaml up -d --no-deps ldes-consumer 2>&1 || true",
        "Starting ldes-consumer",
    )

    # Test 3: Wait for containers to spawn
    print("\n>>> Test 3: Waiting 10 seconds for child containers to spawn...")
    time.sleep(10)

    # Test 4: Check if child containers exist
    print("\n>>> Test 4: Checking for spawned child containers...")
    rc = run_command(
        "docker ps -a --filter 'name=ldes-consumer' --format 'table {{.Names}}\t{{.Status}}'",
        "Checking spawned containers",
    )

    # Test 5: Stop the stack
    print("\n>>> Test 5: Running 'docker compose stop'...")
    run_command("docker compose stop", "Stopping stack")

    # Test 6: Wait a moment
    time.sleep(3)

    # Test 7: Check if child containers were removed
    print("\n>>> Test 6: Checking if child containers were removed after stop...")
    rc = run_command(
        "docker ps -a --filter 'name=ldes-consumer-' --format 'table {{.Names}}'",
        "Checking for remaining child containers (name=ldes-consumer-*)",
    )

    if rc == 0:
        # Also check with broader filter
        run_command(
            "docker ps -a --filter 'name=ldes-consumer' --format 'table {{.Names}}\t{{.Status}}'",
            "All ldes-consumer containers (broader filter)",
        )

    print("\n" + "=" * 60)
    print("Test complete. Check above for results:")
    print("- If child containers (ldes-consumer-*) are removed: CLEANUP WORKS ✓")
    print("- If child containers still exist: CLEANUP FAILED ✗")
    print("=" * 60)


if __name__ == "__main__":
    main()
