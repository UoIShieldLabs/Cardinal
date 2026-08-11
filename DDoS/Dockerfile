FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y hping3 iproute2 net-tools iputils-ping curl && \
    rm -rf /var/lib/apt/lists/*

CMD ["tail", "-f", "/dev/null"]