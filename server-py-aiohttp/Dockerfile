# FROM node:8.9.2
# 
# LABEL maintainer=pcrespov
# 
# ENV NPM_CONFIG_LOGLEVEL warn
# 
# WORKDIR /home/node/
# 
# RUN npm install qxcompiler
# ENV PATH="/home/node/node_modules/.bin/:${PATH}"
# 
# WORKDIR /home/node/qxapp
# COPY client-qx/source source
# COPY client-qx/*.json ./
# RUN qx compile
# 
# 
# #------------------------------------------------------------------------

FROM python:3

# Selects appropriate 'server-py-*/' folder
ARG serverdir

ENV SIMCORE_WEB_OUTDIR=/usr/src/app/client
ENV SIMCORE_WEB_HOSTNAME='0.0.0.0'
ENV SIMCORE_WEB_PORT=8080

WORKDIR /usr/src/app

VOLUME ${SIMCORE_WEB_OUTDIR}
VOLUME /usr/src/app

COPY $serverdir/requirements.txt requirements.txt
RUN python --version \
    && pip3 install --no-cache-dir -r ./requirements.txt \
    && pip list --format=columns

EXPOSE $SIMCORE_WEB_PORT

ENTRYPOINT ["/bin/sh", "-c", "adev runserver --host ${SIMCORE_WEB_HOSTNAME} --port ${SIMCORE_WEB_PORT} --app-factory create_app server.py"]
