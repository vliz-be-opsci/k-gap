#!/bin/bash
# 0. config reading from environment
REPONAME=${GDB_REPO:-kgap}
# Use a lightweight endpoint that doesn't scale with triple count
HEALTH_CHECK_URI="http://localhost:7200/rest/repositories" 
# 1. do the health-check
#   IMPORTANT NOTE -- being last statement this will produce bash exit code
curl --fail -X GET --url ${HEALTH_CHECK_URI}  