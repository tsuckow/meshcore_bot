FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# Install BlueZ and D-Bus utilities for Bluetooth support
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    bluetooth \
    dbus \
    libbluetooth-dev \
    libdbus-1-dev \
    && rm -rf /var/lib/apt/lists/*

# Add vscode user to the bluetooth group so it can access BT without sudo
RUN groupadd -f bluetooth && usermod -aG bluetooth vscode
