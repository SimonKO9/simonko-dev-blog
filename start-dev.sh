#!/bin/bash

podman build . -t simonko-dev-blog
podman run -it --rm \
    -p 1313:1313 \
    -v ./blog:/app \
    simonko-dev-blog:latest \
    hugo server -s /app --bind 0.0.0.0
