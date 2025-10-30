#!/bin/bash

# Host-side SHACL Validation Script
# This script executes SHACL validation inside the GraphDB container
#
# Usage:
#   ./validate-shacl-host.sh [REPOSITORY] [NAMED_GRAPH]
#
# Arguments:
#   REPOSITORY    - GraphDB repository name (default: from GDB_REPO env or 'kgap')
#   NAMED_GRAPH   - Optional named graph to validate (default: validates all graphs)
#
# Environment Variables:
#   COMPOSE_PROJECT_NAME - Docker compose project name (default: 'kgap')
#   GDB_REPO             - Default repository name (default: 'kgap')
#
# Examples:
#   ./validate-shacl-host.sh                          # Validate default repository
#   ./validate-shacl-host.sh kgap                     # Validate 'kgap' repository
#   ./validate-shacl-host.sh kgap http://example/g1   # Validate specific named graph

set -e

# Configuration
COMPOSE_PROJECT=${COMPOSE_PROJECT_NAME:-kgap}
CONTAINER_NAME="${COMPOSE_PROJECT}_graphdb_1"
REPOSITORY=${1:-${GDB_REPO:-kgap}}
NAMED_GRAPH=${2:-}

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if container exists and is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # Try alternative naming pattern
    CONTAINER_NAME="${COMPOSE_PROJECT}-graphdb-1"
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        # Try test pattern
        CONTAINER_NAME="test_kgap_graphdb"
        if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo -e "${RED}Error: GraphDB container not found or not running${NC}"
            echo "Looked for: ${COMPOSE_PROJECT}_graphdb_1, ${COMPOSE_PROJECT}-graphdb-1, test_kgap_graphdb"
            echo ""
            echo "Running containers:"
            docker ps --format 'table {{.Names}}\t{{.Status}}'
            exit 1
        fi
    fi
fi

echo "Using container: ${CONTAINER_NAME}"
echo ""

# Execute validation inside the container
if [ -n "${NAMED_GRAPH}" ]; then
    docker exec -it "${CONTAINER_NAME}" /kgap/validate-shacl.sh "${REPOSITORY}" "${NAMED_GRAPH}"
else
    docker exec -it "${CONTAINER_NAME}" /kgap/validate-shacl.sh "${REPOSITORY}"
fi
