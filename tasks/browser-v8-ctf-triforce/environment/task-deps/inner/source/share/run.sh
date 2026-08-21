#!/bin/bash

export FLAG=$(ls /*.txt)

socat \
-T20 \
TCP-LISTEN:1337,reuseaddr,fork \
EXEC:"timeout 20 python3 -u /home/ctf/server.py"