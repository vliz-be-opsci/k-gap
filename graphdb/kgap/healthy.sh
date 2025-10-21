#!/bin/bash
# Use GraphDB's native passive health-check endpoint
# This is the least intrusive check that doesn't scale with triple count
# See: https://graphdb.ontotext.com/documentation/10.4/database-health-checks.html
HEALTH_CHECK_URI="http://localhost:7200/rest/monitor/infrastructure?passive"
# do the health-check
#   IMPORTANT NOTE -- being last statement this will produce bash exit code
curl --fail -X GET --url ${HEALTH_CHECK_URI}  