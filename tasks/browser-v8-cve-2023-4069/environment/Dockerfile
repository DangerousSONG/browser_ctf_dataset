# Harbor environment Dockerfile
#
# Format-unified wrapper. The V8 compile recipe is NOT invented here.
# After bootstrap_bug.py, wrap copies the generated bench-v8 Dockerfile
# into environment/task-deps/inner/Dockerfile.
#
# Do not COPY tests/private (image history would leak).
# This file does not compile V8; authors can submit without a 70GB build.
#
# Others compile on Ubuntu x86_64 with scripts/build_inner.py
# (ExploitBench 9d0173bc, depot_tools 364ccfdd).

FROM debian:bookworm-20231030@sha256:fab22df37377621693c68650b06680c0d8f7c6bf816ec92637944778db3ca2c0

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /workspace
RUN mkdir -p /workspace /rlenv/workspace \
    && chmod 1777 /workspace /rlenv/workspace

ENV HARBOR_SUBMIT=/workspace/exploit.py
