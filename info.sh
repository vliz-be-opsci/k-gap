#! /usr/bin/env bash

echo "info on docker processes in this project"

for dn in $(docker ps --format {{.Names}} | grep lwua_); do
  echo -e ">> $dn >>"
  echo "  open shell with > docker exec -it ${dn} /bin/bash"

  # get the docker inspect json and parse it using jq
  djson=$(docker inspect $dn)

  id=$(echo $djson | jq '.[].Id')
  echo "  id == ${id}"

  dir=$(echo $djson | jq '.[].Config.Labels. "com.docker.compose.project.working_dir"')
  echo "  dir == ${dir}"

  echo

done 


# todo
#- list logging output folders
#- list http entrypoints for browser ?  open ports?
#- check if jq dependency is installed and advise to do so
#- check if config path matches location of this script! --> would indicate services are running from different location!