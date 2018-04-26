FROM continuumio/miniconda3
LABEL maintainer="Manuel Guidon <guidon@itis.ethz.ch"

RUN conda update conda
RUN conda install flask networkx sqlalchemy psycopg2
RUN conda install -c conda-forge celery
RUN pip install sqlalchemy-json pika

EXPOSE 8010

WORKDIR /work/director

# OK for now, if PYTHONTPATH is not empty that is bad
#ENV PYTHONPATH "$ADDITIONAL_PYTHON_PATH"
ENV TZ=Europe/Zurich
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

CMD ["python", "director.py"]