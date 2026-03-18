#!/bin/sh
# Health check for Oxigraph
# Oxigraph exposes a SPARQL query endpoint at /query
# An empty ASK query is a lightweight way to confirm the server is ready
HEALTH_CHECK_URI="http://localhost:7878/query?query=ASK+%7B+%7D"
# IMPORTANT NOTE -- being last statement this will produce exit code
curl --fail -X GET --url ${HEALTH_CHECK_URI}
