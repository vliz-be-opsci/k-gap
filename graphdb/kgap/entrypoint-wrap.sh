#!/bin/bash
# 0. config reading from environment
REPONAME=${GDB_REPO:-kgap}
REPOLABEL=${REPOLABEL:-"KGAP repo for ${REPONAME}"}
GDB_HOME_FOLDER=${GDB_HOME_FOLDER:-/opt/graphdb/home} 
GDB_MAX_HEADER=${GDB_MAX_HEADER:-65536}
# 1. ensure the config for the needed repo is there
REPODIR="${GDB_HOME_FOLDER}/data/repositories/${REPONAME}"
REPOFILE="${REPODIR}/config.ttl"
if test -f ${REPOFILE}; then # all is well
  echo "repo ${REPONAME} db config already exists at ${REPOFILE}" 
else # we need a config.ttl file to be made
  # which needs a location to put it in
  mkdir -p ${REPODIR}
  # then envsubst needs actual (exported) environment variables, not just in script local ones
  export REPONAME REPOLABEL
  # apply template-like replace of $REPONAME
  envsubst < /kgap/template-repo-config.ttl > ${REPOFILE}
  echo "repo ${REPONAME} created at ${REPOFILE}" 
fi

echo "dumping cat ${REPOFILE}:"
cat ${REPOFILE}
echo "as executed from pwd=$(pwd)"

# 2. delegate to the original entrypoint command 
# note: the underlying entrypoint was detected using:
#   $ docker inspect --type=image --format='{{json .Config.Entrypoint}}' ontotext/graphdb:10.0.2
#   ["/opt/graphdb/dist/bin/graphdb"]

/opt/graphdb/dist/bin/graphdb -Dgraphdb.home=${GDB_HOME_FOLDER} -Dgraphdb.connector.maxHttpHeaderSize=${GDB_MAX_HEADER} $@