#!/bin/bash
set -e

# Detect operation mode based on environment variables
# Mode 1: Master spawner - LDES_CONFIG_PATH is set (folder or file)
# Mode 2: Spawned instance - LDES and SPARQL_ENDPOINT are set

if [ -n "$LDES" ] && [ -n "$SPARQL_ENDPOINT" ]; then
    # Mode 2: Spawned instance - execute as actual ldes2sparql container
    echo "Running as spawned LDES consumer instance"
    cd /rdfc-pipeline
    exec ./run.sh
elif [ -n "$LDES_CONFIG_PATH" ]; then
    # Mode 1: Master spawner - spawn containers based on config
    echo "Running as master LDES consumer spawner"
    echo "Configuration path: $LDES_CONFIG_PATH"
    exec node /kgap/spawn_instances.js
else
    echo "ERROR: Invalid configuration"
    echo ""
    echo "Either set:"
    echo "  - LDES_CONFIG_PATH to a directory or file (master spawner mode)"
    echo "  - LDES and SPARQL_ENDPOINT (spawned instance mode)"
    exit 1
fi
