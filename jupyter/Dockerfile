FROM jupyter/base-notebook

USER root
RUN sudo apt-get update && sudo apt-get install -y git 
COPY ./kgap /kgap
RUN chown -R jovyan:users /kgap

USER jovyan
RUN pip install -r /kgap/requirements.txt && \
    echo 'import sema.query as q; q.install_templates("/kgap/notebooks/queries")' | python

VOLUME /notebooks
VOLUME /data
VOLUME /config

WORKDIR /notebooks
ENTRYPOINT [ "/kgap/entrypoint-wrap.sh" ]