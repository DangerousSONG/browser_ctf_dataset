FROM debian:bookworm-20231030@sha256:fab22df37377621693c68650b06680c0d8f7c6bf816ec92637944778db3ca2c0

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bash ca-certificates coreutils file findutils make python3 nodejs npm \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY task-deps/inner /challenge
ENV HARBOR_SUBMIT=/workspace/exploit.py
ENV CTF_CHALLENGE_DIR=/challenge
