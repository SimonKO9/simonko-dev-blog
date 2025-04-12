# Use a specific version of Ubuntu as the base image
FROM ubuntu:24.04

# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ARG HUGO_VERSION=0.145.0

# Update package lists, install necessary packages, and install Hugo
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    && wget https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_${HUGO_VERSION}_linux-amd64.deb \
    && dpkg -i hugo_${HUGO_VERSION}_linux-amd64.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/* hugo_${HUGO_VERSION}_linux-amd64.deb

# Set the working directory
WORKDIR /app

# Default command
CMD ["bash"]