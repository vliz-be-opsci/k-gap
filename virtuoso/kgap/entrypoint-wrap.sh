#!/bin/bash
# 0. config reading from environment
# In Virtuoso, the "database per project" concept maps to a named graph.
# VIRTUOSO_GRAPH sets the default named graph URI for this project.
KGAP_REPO=${KGAP_REPO:-kgap}
VIRTUOSO_GRAPH=${VIRTUOSO_GRAPH:-"http://kgap.vliz.be/graph/${KGAP_REPO}"}

# Export as DEFAULT_GRAPH so the redpencil/virtuoso image picks it up
export DEFAULT_GRAPH=${DEFAULT_GRAPH:-${VIRTUOSO_GRAPH}}

echo "Virtuoso default graph set to: ${DEFAULT_GRAPH}"

# 1. delegate to the original entrypoint command
# The underlying image entrypoint was detected via:
#   docker inspect --type=image --format='{{json .Config.Entrypoint}}' redpencil/virtuoso
exec /docker-entrypoint.sh "$@"
