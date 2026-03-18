#!/bin/bash
# 0. config reading from environment
FUSEKI_DATASET=${FUSEKI_DATASET:-kgap}
FUSEKI_HOME=${FUSEKI_HOME:-/fuseki}
FUSEKI_BASE=${FUSEKI_BASE:-${FUSEKI_HOME}}

# 1. ensure the dataset configuration is present
CONFIG_DIR="${FUSEKI_BASE}/configuration"
CONFIG_FILE="${CONFIG_DIR}/${FUSEKI_DATASET}.ttl"

mkdir -p "${CONFIG_DIR}"
mkdir -p "${FUSEKI_BASE}/databases/${FUSEKI_DATASET}"

if test -f "${CONFIG_FILE}"; then
  echo "Fuseki dataset '${FUSEKI_DATASET}' config already exists at ${CONFIG_FILE}"
else
  # envsubst needs exported variables
  export FUSEKI_DATASET
  envsubst < /kgap/template-dataset-config.ttl > "${CONFIG_FILE}"
  echo "Fuseki dataset '${FUSEKI_DATASET}' config created at ${CONFIG_FILE}"
fi

echo "--- dataset config ---"
cat "${CONFIG_FILE}"
echo "---------------------"

# 2. delegate to the original Fuseki entrypoint
# The underlying image entrypoint was detected via:
#   docker inspect --type=image --format='{{json .Config.Entrypoint}}' apache/jena-fuseki
exec /docker-entrypoint.sh "$@"
