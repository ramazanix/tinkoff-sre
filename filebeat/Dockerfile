FROM elastic/filebeat:8.10.2

COPY ./filebeat/filebeat.yml /usr/share/filebeat/filebeat.yml

USER root

RUN chown root /usr/share/filebeat/filebeat.yml
RUN chmod go-w /usr/share/filebeat/filebeat.yml
