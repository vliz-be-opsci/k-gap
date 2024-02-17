#! /usr/bin/env bash
project=${1:-.}  # matching all if no $1 is provided

# note: annoyed by the interactive dialogue of this script?
#       then try feeding it with 'y' answers via the yes command with:
#       $ yes | ./docker_clean.sh kgap

# CONTAINERS
if [[ -z $1 ]]; then 
    echo "skipping search for exited container if no limiting argument is passed"
else     # only actually do this if there was real arg to narrow down to
    echo "interactively cleaning not running containers matching '${project}'"
    for cid in $(docker ps --filter "status=exited" | tail -n +2 | grep "${project}" | awk '{print $1}'); do
        echo "found container ${id}:"
        docker inspect \
          --type=container ${cid} \
          --format='  - id: {{println .Id}}  - created: {{println .Created}}  - image: {{println .Config.Image}}  - name: {{ .Name}}'; 
        read -p "  type 'y' to remove? " ans; 
        if [[ "${ans}" == "y" ]]; then docker rm $cid && echo "  > removed ${cid}" || echo "  > removal failed."; 
        else                                             echo "  > skipped ${cid}"; 
        fi 
        echo;
    done
fi 

# IMAGES
echo "interactively cleaning images matching '${project}'"
for iid in $(docker images | tail -n +2 | grep "${project}" | awk '{print $3} '); do 
    echo "found image ${iid}:" ; 
    docker inspect --type=image ${iid} --format='  - id: {{println .Id}}  - tags: {{ .RepoTags}}'; 
    read -p "  type 'y' to remove? " ans; 
    if [[ "${ans}" == "y" ]]; then docker rmi $iid && echo "  > removed ${iid}" || echo "  > removal failed."; 
    else                                              echo "  > skipped ${iid}"; 
    fi 
    echo; 
done

echo "cleaning any dangling docker images"
docker image prune -f  > /dev/null 2>&1 # clean dangling images 

echo "done."