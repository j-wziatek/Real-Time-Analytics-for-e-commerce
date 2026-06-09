FROM quay.io/jupyter/pyspark-notebook:python-3.11

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    vim \
    git \
    netcat-openbsd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    fix-permissions "/home/${NB_USER}"

USER ${NB_USER}

WORKDIR /home/jovyan/work