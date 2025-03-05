# based on https://github.com/mar10/wsgidav/blob/master/Dockerfile
#FROM docker.io/python:3.12.4-slim-bookworm@sha256:d5f16749562233aa4bd26538771d76bf0dfd0a0ea7ea8771985e267451397ae4
FROM python:3.12.7-slim-bookworm@sha256:2a6386ad2db20e7f55073f69a98d6da2cf9f168e05e7487d2670baeb9b7601c5
LABEL maintainer="jorge@terraops.org"

# Set environment variables
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
# Update package lists and install necessary packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        tini \
    && rm -rf /var/lib/apt/lists/*

    # Create directories and set permissions
RUN mkdir -p /app /config /var/www && \
    chown www-data:www-data -R /app /config /var/www

# Clone the repository and copy requirements
WORKDIR /tmp
RUN 
RUN git config --global advice.detachedHead false \
    && git clone --branch v4.3.3 --depth 1 https://github.com/mar10/wsgidav.git /tmp/wsgidav \
    && cd /tmp/wsgidav \
    && cp -r /tmp/wsgidav /app \
    && rm -rf /tmp/wsgidav

#COPY  ./style /app/wsgidav/wsgidav/dir_browser/htdocs
COPY  ./style /www
COPY --chown=www-data:www-data requirements-s3.txt /app/wsgidav/requirements-s3.txt

# Install Python dependencies
# Not using S3 but still leaving the code and build
WORKDIR /app/wsgidav
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/wsgidav/requirements-dev.txt -r /app/wsgidav/requirements-s3.txt && \
    pip install --no-cache-dir -e .

COPY --chown=www-data:www-data src/aws_s3_provider.py /app/wsgidav/wsgidav/aws_s3_provider.py 


USER www-data

# Set entrypoint and default command
ENTRYPOINT ["/usr/bin/tini","-g","--"]
CMD ["wsgidav","--config", "/config/wsgidav.yaml"]
