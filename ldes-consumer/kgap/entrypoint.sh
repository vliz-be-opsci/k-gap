#!/bin/bash
set -e

# Environment variables
LDES_CONFIG_PATH="${LDES_CONFIG_PATH:-}"
LDES2SPARQL_IMAGE="${LDES2SPARQL_IMAGE:-ghcr.io/rdf-connect/ldes2sparql:latest}"

# Determine the operation mode
# Mode 1: No LDES_CONFIG_PATH provided - run as direct ldes2sparql container
# Mode 2: LDES_CONFIG_PATH is a file - legacy single file mode
# Mode 3: LDES_CONFIG_PATH is a directory - folder watcher mode

if [ -z "$LDES_CONFIG_PATH" ]; then
    # Mode 1: Direct mode - no config path provided
    # Run directly as ldes2sparql container using environment variables
    echo "=== Running in DIRECT mode ==="
    echo "No LDES_CONFIG_PATH provided, running as direct ldes2sparql container"
    echo "Using environment variables for configuration"
    
    # Check if required environment variables are set
    if [ -z "$LDES" ]; then
        echo "ERROR: LDES environment variable is required in direct mode"
        echo "Please set LDES to the URL of your LDES feed"
        exit 1
    fi
    
    if [ -z "$SPARQL_ENDPOINT" ]; then
        echo "ERROR: SPARQL_ENDPOINT environment variable is required in direct mode"
        echo "Please set SPARQL_ENDPOINT to your SPARQL endpoint URL"
        exit 1
    fi
    
    echo "LDES: $LDES"
    echo "SPARQL_ENDPOINT: $SPARQL_ENDPOINT"
    
    # Install Node.js and dependencies as in the ldes2sparql Dockerfile
    echo "Installing Node.js and ldes2sparql dependencies..."
    
    # Install Node.js LTS (pinned version for security)
    NODEJS_VERSION="20.x"
    curl -fsSL "https://deb.nodesource.com/setup_${NODEJS_VERSION}" | bash -
    apt-get install -y nodejs
    
    # Clone and setup ldes2sparql
    cd /tmp
    git clone https://github.com/rdf-connect/ldes2sparql.git
    cd ldes2sparql
    
    # Create state and performance directories
    mkdir -p /state
    mkdir -p /performance
    
    # Install dependencies
    npm ci
    
    # Make run.sh executable
    chmod +x run.sh
    
    # Set default environment variables if not provided
    export SHAPE="${SHAPE:-}"
    export TARGET_GRAPH="${TARGET_GRAPH:-}"
    export FAILURE_IS_FATAL="${FAILURE_IS_FATAL:-false}"
    export FOLLOW="${FOLLOW:-true}"
    export MATERIALIZE="${MATERIALIZE:-false}"
    export ORDER="${ORDER:-none}"
    export POLLING_FREQUENCY="${POLLING_FREQUENCY:-5000}"
    export CONCURRENT_FETCHES="${CONCURRENT_FETCHES:-10}"
    export FOR_VIRTUOSO="${FOR_VIRTUOSO:-false}"
    export QUERY_TIMEOUT="${QUERY_TIMEOUT:-1800}"
    export LAST_VERSION_ONLY="${LAST_VERSION_ONLY:-false}"
    
    # Execute the ldes2sparql run.sh script
    echo "Starting ldes2sparql..."
    exec ./run.sh

elif [ -d "$LDES_CONFIG_PATH" ]; then
    # Mode 3: Folder watcher mode
    echo "=== Running in FOLDER WATCHER mode ==="
    echo "Configuration directory: $LDES_CONFIG_PATH"
    echo "Using ldes2sparql image: $LDES2SPARQL_IMAGE"
    
    # Make sure that the ldes2sparql image is available
    echo "Pulling ldes2sparql image..."
    docker pull "$LDES2SPARQL_IMAGE"
    
    # Start folder watcher
    python3 /kgap/folder_watcher.py "$LDES_CONFIG_PATH"

elif [ -f "$LDES_CONFIG_PATH" ]; then
    # Mode 2: Legacy single file mode
    echo "=== Running in LEGACY SINGLE FILE mode ==="
    echo "Configuration file: $LDES_CONFIG_PATH"
    echo "Using ldes2sparql image: $LDES2SPARQL_IMAGE"
    
    # Make sure that the ldes2sparql image is available
    echo "Pulling ldes2sparql image..."
    docker pull "$LDES2SPARQL_IMAGE"
    
    # Parse YAML and start ldes2sparql instances
    python3 /kgap/spawn_instances.py "$LDES_CONFIG_PATH"

else
    echo "ERROR: LDES_CONFIG_PATH does not point to a valid file or directory: $LDES_CONFIG_PATH"
    echo ""
    echo "Usage modes:"
    echo "1. Direct mode: Do not set LDES_CONFIG_PATH, use LDES and SPARQL_ENDPOINT environment variables"
    echo "2. Folder mode: Set LDES_CONFIG_PATH to a directory containing YAML files"
    echo "3. Legacy mode: Set LDES_CONFIG_PATH to a single YAML file"
    exit 1
fi
