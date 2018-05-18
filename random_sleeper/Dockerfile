FROM alpine

MAINTAINER  Manuel guidon <guidon@itis.ethz.ch>

RUN apk add --no-cache g++ bash

WORKDIR /work

ADD ./code /work
ADD ./simcore.sdk /simcore.sdk
RUN chmod +x /simcore.sdk/*

ENV PATH="/simcore.sdk:${PATH}"

RUN g++ -std=c++11 -o sleeper main.cpp
