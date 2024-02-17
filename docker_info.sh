#! /usr/bin/env bash

name=${1:-kgap}

echo "info on docker processes with name containing '${name}':"

for dn in $(docker ps --format='{{.Names}}' | grep ${name}); do
  echo -ne ">> $dn >>"
  echo " to open shell to it, use >> docker exec -it ${dn} /bin/bash"
  
  # get the docker inspect json and parse it using jq
  dj=$(docker inspect --type=container $dn --format='{{json .}}')

  echo "  id     : $(echo $dj | jq '.Id')"
  echo "  created: $(echo $dj | jq '.Created')"
  echo "  name   : $(echo $dj | jq '.Name')"
  echo "  dir    : $(echo $dj | jq '.Config.Labels. "com.docker.compose.project.working_dir"')"
  echo "--"
done 


# todo
#- list logging output folders
#- list http entrypoints for browser ?  open ports?
#- check if jq dependency is installed and advise to do so
#- check if config path matches location of this script! --> would indicate services are running from different location!