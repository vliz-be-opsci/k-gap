FROM jupyter/base-notebook

USER root
RUN sudo apt-get update && sudo apt-get install -y git 

USER jovyan
COPY ./kgap /kgap
RUN pip install -r /kgap/requirements.txt

VOLUME /notebooks
VOLUME /data
VOLUME /config

WORKDIR /notebooks
ENTRYPOINT [ "/kgap/entrypoint-wrap.sh" ]