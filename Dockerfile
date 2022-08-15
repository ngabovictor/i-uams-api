# pull official base image
FROM python:3.9-alpine3.15

# set work directory
RUN mkdir /app
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies for Postgresql
RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev

# install Zlib dependencies for Pillow
RUN apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements-vps.txt requirements-vps.txt
RUN pip install -r requirements-vps.txt

# copy project
COPY . /app

# create and run user
RUN adduser -D uams
USER uams
