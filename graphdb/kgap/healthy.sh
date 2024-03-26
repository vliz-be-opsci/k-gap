#!/bin/bash
# 0. config reading from environment
REPONAME=${GDB_REPO:-kgap}
REPO_WRITE_URI="http://localhost:7200/repositories/${REPONAME}/statements" 
# 1. do the health-check
#   IMPORTANT NOTE -- being last statement this will produce bash exit code
curl --fail -X GET --url ${REPO_WRITE_URI} -H "Accept: application/n-triples"  