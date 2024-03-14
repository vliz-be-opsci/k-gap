FROM python:3.10
COPY main.py /main.py
COPY requirements.txt /requirements.txt
RUN python -m pip install -r /requirements.txt
ENTRYPOINT ["/main.py"]