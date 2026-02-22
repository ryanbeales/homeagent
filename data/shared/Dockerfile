# Dockerfile for building and loading eBPF program
# Use a recent Ubuntu image with clang, llvm, and libbpf
FROM ubuntu:22.04

# Install build tools and dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        clang \
        llvm \
        libbpf-dev \
        iproute2 \
        iputils-ping \
        make \
        gcc \
        libelf-dev \
        ca-certificates \
        wget \
        && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /bpf

# Copy source files
COPY program.c /bpf/program.c
COPY build.sh /bpf/build.sh
COPY load.sh /bpf/load.sh

# Make scripts executable
RUN chmod +x build.sh load.sh

# Build the eBPF program on image build
RUN ./build.sh

# Default command to keep container running for debugging
CMD ["sleep", "infinity"]
