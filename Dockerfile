FROM python:3.6.1-slim

# Python optimization to run on docker
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Maybe run upgrade as well???
RUN apt-get update

# Requirements
COPY requirements.apt .
RUN xargs apt install -y --force-yes < requirements.apt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# User, home, and app basics
RUN useradd --create-home app
WORKDIR /home/app
USER app

COPY . .

ARG build_info
RUN echo ${build_info} > build_info.txt


ENTRYPOINT [ "./gunicorn.sh" ]

# gunicorn --bind 0.0.0.0:$PORT --worker-class gevent --workers $WORKERS --log-file - host_provider.main:app



# ENV PYTHONUNBUFFERED 1
# ENV DEBIAN_FRONTEND "noninteractive apt-get install PACKAGE"
# COPY ./requirements.txt /tmp/requirements.txt
# RUN  mkdir -p /app &&\
#      useradd -ms /bin/bash python && \
#      chown -R python: /app && \
#      apt-get update && \
#      apt-get install -y --no-install-recommends \
#              python3-pip \
#              build-essential \
#              libsasl2-dev \
#              python-dev \
#              libldap2-dev \
#              libssl-dev \
#              gcc \
#      && rm -rf /var/lib/apt/lists/* \
#      && pip3 install -r /tmp/requirements.txt \
#      && chown -R python: /usr/local/lib/python3.6/ \
#      && ipython profile create
# WORKDIR /app
# COPY ./.ipython_config.py /root/.ipython/profile_default/ipython_config.py
# COPY ./.startup_dev.py /etc/.startup_dev.py