#!/bin/bash
# Health check for Virtuoso
# Virtuoso exposes a SPARQL endpoint at /sparql on port 8890
# An empty ASK query is a lightweight way to confirm the server is ready
HEALTH_CHECK_URI="http://localhost:8890/sparql?query=ASK+%7B+%7D"
# IMPORTANT NOTE -- being last statement this will produce exit code
curl --fail -X GET --url ${HEALTH_CHECK_URI}
