FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y iproute2 iputils-ping curl bash && \
    rm -rf /var/lib/apt/lists/*

# Install Locust for human-like load generation
RUN pip install --no-cache-dir locust requests

WORKDIR /scripts
COPY locustfile.py /scripts/locustfile.py
COPY ramp.sh /scripts/ramp.sh
RUN chmod +x /scripts/ramp.sh

CMD ["tail", "-f", "/dev/null"]