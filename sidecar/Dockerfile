FROM continuumio/miniconda3
LABEL maintainer="Manuel Guidon <guidon@itis.ethz.ch"

RUN conda update conda
RUN conda install networkx sqlalchemy psycopg2
RUN conda install -c conda-forge celery

RUN pip install sqlalchemy-json docker pika

EXPOSE 8000

WORKDIR /work/sidecar

# ENV TZ=Europe/Zurich
# RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# NO clue why this does not work without explicitly specifying
ENV PYTHONPATH="/work/models"
ENTRYPOINT celery -A sidecar worker -c 2 --loglevel=info
