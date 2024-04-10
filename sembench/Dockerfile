FROM python:3.9
COPY ./kgap /kgap
RUN python -m pip install -r /kgap/requirements.txt
ENTRYPOINT ["/kgap/main.py"]
