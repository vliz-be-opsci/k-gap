#!/bin/bash
set -e

# Environment variables
LDES_CONFIG_FILE="${LDES_CONFIG_FILE:-/data/ldes-feeds.yaml}"
LDES2SPARQL_IMAGE="${LDES2SPARQL_IMAGE:-brechtvdv/ldes2sparql:latest}"

# Check if config file exists
if [ ! -f "$LDES_CONFIG_FILE" ]; then
    echo "ERROR: LDES config file not found at $LDES_CONFIG_FILE"
    echo "Please create a YAML file with your LDES feeds configuration."
    echo "Example format:"
    echo "feeds:"
    echo "  - name: feed1"
    echo "    url: http://example.com/feed1"
    echo "    sparql_endpoint: http://graphdb:7200/repositories/kgap/statements"
    exit 1
fi

echo "Starting LDES consumer with config: $LDES_CONFIG_FILE"
echo "Using ldes2sparql image: $LDES2SPARQL_IMAGE"

# Parse YAML and start ldes2sparql instances
python3 /kgap/spawn_instances.py "$LDES_CONFIG_FILE"
