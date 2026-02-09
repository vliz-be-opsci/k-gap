#!/bin/bash
set -e

# Environment variables
LDES_CONFIG_FILE="${LDES_CONFIG_FILE:-/data/ldes-feeds.yaml}"
LDES2SPARQL_IMAGE="${LDES2SPARQL_IMAGE:-ghcr.io/maregraph-eu/ldes2sparql:latest}"
LDES_CONSUMER_PREFIX="${LDES_CONSUMER_PREFIX:-ldes-consumer}"

# Wrapper echo function
wecho() {
    echo "${LDES_CONSUMER_PREFIX}-wrapper: $1"
}

# Check if config file exists
if [ ! -f "$LDES_CONFIG_FILE" ]; then
    wecho "ERROR: LDES config file not found at $LDES_CONFIG_FILE"
    wecho "Please create a YAML file with your LDES feeds configuration."
    wecho "Example format:"
    wecho "feeds:"
    wecho "  - name: unique-feed-name"
    wecho "    url: http://example.com/path-to-ldes-feed"
    wecho "    sparql_endpoint: http://graphdb:7200/repositories/${GDB_REPO:-kgap}/statements"
    exit 1
fi

wecho "Starting LDES consumer with config: $LDES_CONFIG_FILE"
wecho "Using ldes2sparql image: $LDES2SPARQL_IMAGE"

# make sure that the ldes2sparql image is available
docker pull "$LDES2SPARQL_IMAGE"


# trap to pass down SIGNALS TERM (143) and INT (130)
# $1 == signal to send , $2 == exit code to use
signal_child() {  
    wecho "passing down signal $1 to child $child"
    kill -$1 "$child" 2>/dev/null
    wait "$child"
    exit $2
}
wecho "initialising signal traps..."
trap 'signal_child "TERM" 143' SIGTERM
trap 'signal_child "INT" 130' SIGINT

wecho "yielding to child process to spawn instances..."
# Ensure state and logs directories exist
mkdir -p /data/ldes-consumer/state
mkdir -p /data/ldes-consumer/logs
wecho "Clearing logs directory..."
rm -rf /data/ldes-consumer/logs/*

if [ "${LDES_CLEAR_STATE:-0}" = "1" ]; then
    wecho "Clearing state directory as LDES_CLEAR_STATE is set to 1"
    rm -rf /data/ldes-consumer/state/*
fi

# Start the child process and capture its PID
# Parse YAML and start ldes2sparql instances
/usr/bin/env python3 /kgap/spawn_instances.py "$LDES_CONFIG_FILE" &
child=$! #
wecho "started spawn-instances with pid $child"

# Wait for the child process to exit
wait "$child" || true
child_status=$?
wecho "spawn-instances exited with status $child_status"
exit $child_status

