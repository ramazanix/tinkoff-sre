FROM python:3.6

ADD . /code
RUN pip install prometheus_client requests environs

WORKDIR /code
ENV PYTHONPATH '/code/'
COPY .env /code
CMD ["python" , "/code/prober.py"]
