FROM jupyter/base-notebook
VOLUME /notebooks
WORKDIR /notebooks

COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
