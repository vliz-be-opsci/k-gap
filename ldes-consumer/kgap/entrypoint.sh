#!/bin/bash
set -e

# Environment variables
LDES_CONFIG_FILE="${LDES_CONFIG_FILE:-/data/ldes-feeds.yaml}"
LDES2SPARQL_IMAGE="${LDES2SPARQL_IMAGE:-ghcr.io/rdf-connect/ldes2sparql:latest}"

# Wrapper echo function
wecho() {
    echo "wrapper: $1"
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
# Start the child process and capture its PID
# Parse YAML and start ldes2sparql instances
/usr/bin/env python3 /kgap/spawn_instances.py "$LDES_CONFIG_FILE" &
child=$! #
wecho "started spawn-instances with pid $child"

# Wait for the child process to exit
wait "$child"
wecho "spawn-instances exited with status $?"

