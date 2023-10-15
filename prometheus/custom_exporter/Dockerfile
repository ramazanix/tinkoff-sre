FROM python:3.6

ADD . /code
RUN pip install prometheus_client

WORKDIR /code
ENV PYTHONPATH '/code/'

CMD ["python" , "/code/custom_collector.py"]
