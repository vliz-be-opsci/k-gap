#!/bin/bash
set -e

# Detect operation mode based on environment variables
# Mode 1: Coordinator - LDES_CONFIG_PATH is set (folder or file)
# Mode 2: Consumer instance - LDES and SPARQL_ENDPOINT are set

if [ -n "$LDES" ] && [ -n "$SPARQL_ENDPOINT" ]; then
    # Mode 2: Consumer instance - execute as actual ldes2sparql container
    echo "Running as LDES consumer instance"
    cd /rdfc-pipeline
    exec ./run.sh
elif [ -n "$LDES_CONFIG_PATH" ]; then
    # Mode 1: Coordinator - spawn containers based on config
    echo "Running as LDES coordinator"
    echo "Configuration path: $LDES_CONFIG_PATH"
    
    # Use docker inspect to get own container info
    # HOSTNAME env variable points to current docker container id
    inspect=$(docker inspect $HOSTNAME)
    
    # Extract essential info using jq
    image=$(echo $inspect | jq -r '.[0].Config.Image')
    network=$(echo $inspect | jq -r '.[0].NetworkSettings.Networks | keys | first')
    project=$(echo $inspect | jq -r '.[0].Config.Labels."com.docker.compose.project"')
    
    echo "Docker image: ${image}"
    echo "Docker network: ${network}"
    echo "Docker compose project: ${project}"
    
    # Pass the detected info to spawn_instances.js via environment
    export DOCKER_IMAGE="${image}"
    export DOCKER_NETWORK="${network}"
    export COMPOSE_PROJECT_NAME="${project}"
    
    exec node /kgap/spawn_instances.js
else
    echo "ERROR: Invalid configuration"
    echo ""
    echo "Either set:"
    echo "  - LDES_CONFIG_PATH to a directory or file (coordinator mode)"
    echo "  - LDES and SPARQL_ENDPOINT (consumer instance mode)"
    exit 1
fi
