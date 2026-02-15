#!/bin/bash

# SHACL Validation Script for GraphDB
# This script triggers SHACL validation on a GraphDB repository and retrieves the validation report
#
# Usage:
#   validate-shacl.sh [REPOSITORY] [NAMED_GRAPH]
#
# Arguments:
#   REPOSITORY    - GraphDB repository name (default: from GDB_REPO env or 'kgap')
#   NAMED_GRAPH   - Optional named graph to validate (default: validates all graphs)
#
# Environment Variables:
#   GDB_HOST      - GraphDB host (default: localhost)
#   GDB_PORT      - GraphDB port (default: 7200)
#   GDB_REPO      - Default repository name
#
# Examples:
#   validate-shacl.sh                          # Validate default repository (all graphs)
#   validate-shacl.sh kgap                     # Validate 'kgap' repository (all graphs)
#   validate-shacl.sh kgap http://example/g1   # Validate specific named graph in 'kgap' repository

set -e

# Configuration
GDB_HOST=${GDB_HOST:-localhost}
GDB_PORT=${GDB_PORT:-7200}
REPOSITORY=${1:-${GDB_REPO:-kgap}}
NAMED_GRAPH=${2:-}

# GraphDB SHACL validation endpoint
BASE_URL="http://${GDB_HOST}:${GDB_PORT}"
VALIDATION_ENDPOINT="${BASE_URL}/repositories/${REPOSITORY}/shacl/validate"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "GraphDB SHACL Validation"
echo "================================================"
echo "Repository: ${REPOSITORY}"
echo "Endpoint: ${VALIDATION_ENDPOINT}"

# Build the request
if [ -n "${NAMED_GRAPH}" ]; then
    echo "Named Graph: ${NAMED_GRAPH}"
    # Validate specific named graph
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        "${VALIDATION_ENDPOINT}" \
        -H "Accept: text/turtle" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --data-urlencode "context=${NAMED_GRAPH}")
else
    echo "Named Graph: (all graphs)"
    # Validate all graphs
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        "${VALIDATION_ENDPOINT}" \
        -H "Accept: text/turtle")
fi

# Extract HTTP status code and body
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "================================================"

# Check HTTP response
if [ "$HTTP_CODE" -eq 200 ]; then
    echo -e "${GREEN}✓ Validation completed successfully${NC}"
    echo "================================================"
    echo "Validation Report (Turtle format):"
    echo "================================================"
    echo "$BODY"
    echo "================================================"
    
    # Check if validation passed (no sh:ValidationResult in the report)
    if echo "$BODY" | grep -q "sh:ValidationResult"; then
        echo -e "${RED}⚠ Validation found constraint violations${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ No constraint violations found${NC}"
        exit 0
    fi
elif [ "$HTTP_CODE" -eq 404 ]; then
    echo -e "${RED}✗ Error: Repository '${REPOSITORY}' not found${NC}"
    echo "Available repositories:"
    curl -s "${BASE_URL}/rest/repositories" | grep -o '"id":"[^"]*"' | cut -d'"' -f4
    exit 1
else
    echo -e "${RED}✗ Error: HTTP ${HTTP_CODE}${NC}"
    echo "Response:"
    echo "$BODY"
    exit 1
fi
