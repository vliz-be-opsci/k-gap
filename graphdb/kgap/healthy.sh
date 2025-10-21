#!/bin/bash
# 0. config reading from environment
REPONAME=${GDB_REPO:-kgap}
# Use the repository size endpoint - lightweight O(1) operation that checks repo exists
# This doesn't scale with triple count unlike the statements endpoint
HEALTH_CHECK_URI="http://localhost:7200/repositories/${REPONAME}/size" 
# 1. do the health-check
#   IMPORTANT NOTE -- being last statement this will produce bash exit code
curl --fail -X GET --url ${HEALTH_CHECK_URI}  