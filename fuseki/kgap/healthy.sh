#!/bin/bash
# Health check for Apache Jena Fuseki
# 0. config reading from environment
FUSEKI_DATASET=${FUSEKI_DATASET:-kgap}
# Fuseki provides a dedicated ping endpoint and a per-dataset SPARQL endpoint
# Use the dataset SPARQL endpoint with a minimal ASK query to confirm
# both the server and the specific dataset are ready
HEALTH_CHECK_URI="http://localhost:3030/${FUSEKI_DATASET}/sparql?query=ASK+%7B+%7D"
# IMPORTANT NOTE -- being last statement this will produce exit code
curl --fail -X GET --url ${HEALTH_CHECK_URI}
