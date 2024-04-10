FROM python:3.9
COPY ./kgap /kgap
RUN python -m pip install -r /kgap/requirements.txt
RUN chmod +x /kgap/main.py
ENTRYPOINT ["/kgap/main.py"]
