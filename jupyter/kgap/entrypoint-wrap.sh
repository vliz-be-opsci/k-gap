#!/bin/bash
# 0. config reading from environment


# 1. merge in some useful kgap stuff (if it does not exist)
SRC_FOLDER=${SRC_FOLDER:-/kgap/notebooks}
TGT_FOLDER=/notebooks
echo "merging ${SRC_FOLDER} to ${TGT_FOLDER}"
# -R == recursive, 
# -n == no-clobber, meaning safely merge and skip if target exists, 
# -v == verbose, shows what is actually done
cp -R -n -v ${SRC_FOLDER}/* ${TGT_FOLDER}

for lnk in data config; do
  echo "checking link for ${lnk}"
  if [ -d /${lnk} ]; then                    # if these exist at the root
    ln -s /${lnk} ${TGT_FOLDER}/${lnk}     #   then symlink under target
  else                                       # if not
    rm -rf ${TGT_FOLDER}/${lnk}            #   be sure to remove the link again
  fi
done

# 2. delegate to the original entrypoint command 
# note: the underlying entrypoint was detected using:
# - $ docker inspect --type=image --format='{{json .Config.WorkingDir}}' jupyter/base-notebook
#   "/home/jovyan"
# - $ docker inspect --type=image --format='{{json .Config.Entrypoint}}' jupyter/base-notebook
#   ["tini","-g","--"]
# - $ docker inspect --type=image --format='{{json .Config.Cmd}}' jupyter/minimal-notebook
#   ["start-notebook.sh"]

(cd ${TGT_FOLDER} && tini -g -- start-notebook.sh $@)