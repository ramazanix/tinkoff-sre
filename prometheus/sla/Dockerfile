FROM python:3.7

ADD . /code
RUN pip install mysql-connector-python requests environs

WORKDIR /code
ENV PYTHONPATH '/code/'
COPY .env /code
CMD ["python" , "/code/sla.py"]
