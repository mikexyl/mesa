FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    git \
    curl \
    wget \
    unzip \
    software-properties-common \
    # Graphics and visualization libraries
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libxrandr-dev \
    libxinerama-dev \
    libxcursor-dev \
    libxi-dev \
    libxext-dev \
    libx11-dev \
    x11-apps \
    # Additional development tools
    gdb \
    valgrind \
    tree \
    htop \
    vim \
    nano \
    nlohmann-json3-dev libboost-all-dev libmetis-dev libeigen3-dev \
    libsuitesparse-dev libtbb-dev libgoogle-glog-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Switch to vscode user
USER $USERNAME

# Install pixi
RUN curl -fsSL https://pixi.sh/install.sh | bash

# Add pixi to PATH
ENV PATH="/home/$USERNAME/.pixi/bin:$PATH"

# Set working directory
WORKDIR /workspace

# Expose common ports for development
EXPOSE 8080 8888 5000 3000

# Default command
CMD ["/bin/zsh"]
