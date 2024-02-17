FROM jupyter/base-notebook

COPY ./kgap /kgap
RUN pip install -r /kgap/requirements.txt

VOLUME /notebooks
VOLUME /data
VOLUME /config

WORKDIR /notebooks
ENTRYPOINT [ "/kgap/entrypoint-wrap.sh" ]