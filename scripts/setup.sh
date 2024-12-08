#!/bin/bash

# setup.sh - Configure environment for VM benchmarking

# Exit on any error
set -e

echo "Setting up VM Benchmark Suite environment..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo"
    exit 1
fi

# Install required packages
echo "Installing required packages..."
apt-get update
apt-get install -y \
    qemu-kvm \
    libvirt-daemon-system \
    libvirt-clients \
    bridge-utils \
    python3-pip \
    python3-libvirt \
    cloud-image-utils \
    genisoimage

# Install Python dependencies
echo "Installing Python packages..."
pip3 install \
    libvirt-python \
    pyyaml \
    pandas \
    matplotlib \
    seaborn \
    plotly \
    paramiko \
    requests

# Setup libvirt permissions
echo "Configuring libvirt permissions..."
usermod -a -G libvirt $SUDO_USER
usermod -a -G kvm $SUDO_USER
chmod 666 /var/run/libvirt/libvirt-sock

# Setup directory structure and permissions
echo "Setting up project directories..."
PROJECT_DIR=$(dirname $(readlink -f $0))
DIRS=("images" "cloud-init" "keys")

for dir in "${DIRS[@]}"; do
    mkdir -p "$PROJECT_DIR/$dir"
    chown -R $SUDO_USER:libvirt "$PROJECT_DIR/$dir"
    chmod -R 775 "$PROJECT_DIR/$dir"
done

# Configure libvirt storage
echo "Configuring libvirt storage..."
chmod 775 /var/lib/libvirt/images
chown :libvirt /var/lib/libvirt/images

# Ensure libvirt is running
echo "Starting libvirt service..."
systemctl enable libvirtd
systemctl start libvirtd

# Configure network
echo "Configuring network..."
if ! virsh net-list --all | grep -q "default"; then
    virsh net-define /usr/share/libvirt/networks/default.xml
    virsh net-autostart default
    virsh net-start default
fi

echo "Setup complete! Please log out and back in for group changes to take effect."
echo "You can then run the benchmark suite with: python3 scripts/test_orchestrator.py"
