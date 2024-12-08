#!/usr/bin/env python3

import os
import sys
import libvirt
import logging
import yaml
import subprocess
from pathlib import Path
import uuid
import time
import paramiko
import base64
import requests
from tempfile import NamedTemporaryFile

class VMProvisioner:
    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.conn = None
        self.vms = {}
        self.project_root = Path(__file__).parent.parent.absolute()
        self.setup_directories()

    def _load_config(self, config_path):
        """Load VM configurations from YAML file."""
        logging.info(f"Loading VM config from: {config_path}")
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Failed to load config file: {e}")
            raise
        
    def setup_directories(self):
        """Create necessary directories for VM management"""
        dirs = ['images', 'cloud-init', 'keys']
        for dir_name in dirs:
            (self.project_root / dir_name).mkdir(exist_ok=True)

    def connect(self):
        """Establish connection to QEMU/KVM hypervisor."""
        try:
            self.conn = libvirt.open('qemu:///system')
            logging.info("Successfully connected to QEMU/KVM")
        except libvirt.libvirtError as e:
            logging.error(f'Failed to connect to QEMU/KVM: {e}')
            sys.exit(1)
            
    def _download_ubuntu_image(self):
        """Download Ubuntu cloud image if not present"""
        image_path = self.project_root / 'images/ubuntu-base.img'
        if not image_path.exists():
            logging.info("Downloading Ubuntu cloud image...")
            url = "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img"
            response = requests.get(url, stream=True)
            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        return image_path
    
    def _generate_ssh_key(self):
        """Generate SSH key pair if not exists"""
        key_path = self.project_root / 'keys/vm_key'
        if not key_path.exists():
            subprocess.run([
                'ssh-keygen',
                '-t', 'rsa',
                '-b', '2048',
                '-f', str(key_path),
                '-N', ''
            ])
        return key_path
    
    def _create_cloud_init(self, vm_name):
        """Create cloud-init configuration for VM"""
        key_path = self._generate_ssh_key()
        with open(f"{key_path}.pub") as f:
            public_key = f.read().strip()
            
        # Create meta-data
        meta_data = f"instance-id: {vm_name}\nlocal-hostname: {vm_name}\n"
        meta_path = self.project_root / f'cloud-init/meta-data-{vm_name}'
        with open(meta_path, 'w') as f:
            f.write(meta_data)
            
        # Create user-data
        user_data = f"""#cloud-config
users:
  - name: benchmark
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - {public_key}

package_update: true
package_upgrade: true

packages:
  - sysbench
  - fio
  - iperf3
  - python3
  - python3-pip
  - sysstat
  - htop

runcmd:
  - systemctl enable ssh
  - systemctl start ssh
  - echo "Installation and configuration complete" > /var/log/cloud-init-complete.log
"""
        user_path = self.project_root / f'cloud-init/user-data-{vm_name}'
        with open(user_path, 'w') as f:
            f.write(user_data)
            
        # Create ISO
        iso_path = self.project_root / f'cloud-init/{vm_name}-config.iso'
        subprocess.run([
            'genisoimage',
            '-output', str(iso_path),
            '-volid', 'cidata',
            '-joliet',
            '-rock',
            str(meta_path),
            str(user_path)
        ])
        
        return iso_path

    def _generate_vm_xml(self, name, vcpus, memory_mb, disk_path, cloud_init_iso):
        """Generate libvirt XML for VM creation with cloud-init configuration"""
        
        # Create the root element
        domain = ET.Element('domain', type='kvm')
        
        # Basic VM metadata
        ET.SubElement(domain, 'name').text = name
        ET.SubElement(domain, 'uuid').text = str(uuid.uuid4())
        ET.SubElement(domain, 'memory').text = str(memory_mb * 1024)  # Convert to KB
        ET.SubElement(domain, 'currentMemory').text = str(memory_mb * 1024)
        ET.SubElement(domain, 'vcpu', placement='static').text = str(vcpus)
        
        # OS configuration
        os = ET.SubElement(domain, 'os')
        ET.SubElement(os, 'type', arch='x86_64', machine='pc-q35-6.2').text = 'hvm'
        ET.SubElement(os, 'boot', dev='hd')
        
        # Features
        features = ET.SubElement(domain, 'features')
        ET.SubElement(features, 'acpi')
        ET.SubElement(features, 'apic')
        
        # CPU configuration
        cpu = ET.SubElement(domain, 'cpu', mode='host-model')
        ET.SubElement(cpu, 'topology', sockets='1', dies='1', cores=str(vcpus), threads='1')
        
        # Devices
        devices = ET.SubElement(domain, 'devices')
        
        # Main disk
        disk = ET.SubElement(devices, 'disk', type='file', device='disk')
        ET.SubElement(disk, 'driver', name='qemu', type='qcow2')
        ET.SubElement(disk, 'source', file=str(disk_path))
        ET.SubElement(disk, 'target', dev='vda', bus='virtio')
        
        # Cloud-init ISO
        disk_cloudinit = ET.SubElement(devices, 'disk', type='file', device='cdrom')
        ET.SubElement(disk_cloudinit, 'driver', name='qemu', type='raw')
        ET.SubElement(disk_cloudinit, 'source', file=str(cloud_init_iso))
        ET.SubElement(disk_cloudinit, 'target', dev='sda', bus='sata')
        
        # Network
        interface = ET.SubElement(devices, 'interface', type='network')
        ET.SubElement(interface, 'source', network='default')
        ET.SubElement(interface, 'model', type='virtio')
        
        # Console
        console = ET.SubElement(devices, 'console', type='pty')
        ET.SubElement(console, 'target', type='serial', port='0')
        
        return ET.tostring(domain).decode()
    
    def create_vm(self, name, config_size='medium'):
        """Create and initialize a new VM"""
        try:
            vm_config = self.config['vm_configs'][config_size]
            
            # Download base image if needed
            base_image = self._download_ubuntu_image()
            
            # Create VM disk
            disk_path = self.project_root / f'images/{name}.qcow2'
            subprocess.run([
                'qemu-img', 'create',
                '-f', 'qcow2',
                '-F', 'qcow2',
                '-b', str(base_image),
                str(disk_path),
                f"{vm_config['disk_size_gb']}G"
            ])
            
            # Create cloud-init ISO
            cloud_init_iso = self._create_cloud_init(name)
            
            # Generate VM XML
            xml = self._generate_vm_xml(
                name,
                vm_config['vcpus'],
                vm_config['memory_mb'],
                disk_path,
                cloud_init_iso
            )
            
            # Create and start VM
            dom = self.conn.defineXML(xml)
            dom.create()
            self.vms[name] = dom
            
            # Wait for VM to be ready
            ip_address = self._wait_for_vm_ip(dom)
            if not ip_address:
                raise Exception("Failed to get VM IP address")
                
            # Wait for cloud-init to complete
            self._wait_for_cloud_init(ip_address)
            
            logging.info(f"Successfully created and initialized VM: {name}")
            return dom, ip_address
            
        except Exception as e:
            logging.error(f"Failed to create VM {name}: {e}")
            raise

    def _wait_for_vm_ip(self, domain, timeout=300):
        """Wait for VM to get an IP address"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                ifaces = domain.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)
                for iface in ifaces.values():
                    for addr in iface['addrs']:
                        if addr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                            return addr['addr']
            except libvirt.libvirtError:
                pass
            time.sleep(5)
        return None
        
    def _wait_for_cloud_init(self, ip_address, timeout=300):
        """Wait for cloud-init to complete VM initialization"""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        key_path = self.project_root / 'keys/vm_key'
        pkey = paramiko.RSAKey.from_private_key_file(str(key_path))
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                ssh.connect(
                    ip_address,
                    username='benchmark',
                    pkey=pkey,
                    timeout=10
                )
                stdin, stdout, stderr = ssh.exec_command(
                    'cat /var/log/cloud-init-complete.log'
                )
                if stdout.channel.recv_exit_status() == 0:
                    logging.info(f"Cloud-init completed successfully on {ip_address}")
                    break
            except Exception:
                time.sleep(10)
            finally:
                ssh.close()
                
        if time.time() - start_time >= timeout:
            raise Exception("Cloud-init initialization timed out")

    def cleanup(self):
        """Clean up all resources"""
        for name, dom in self.vms.items():
            try:
                if dom.isActive():
                    dom.destroy()
                dom.undefine()
                # Clean up disk and cloud-init files
                disk_path = self.project_root / f'images/{name}.qcow2'
                cloud_init_iso = self.project_root / f'cloud-init/{name}-config.iso'
                
                if disk_path.exists():
                    disk_path.unlink()
                if cloud_init_iso.exists():
                    cloud_init_iso.unlink()
            except Exception as e:
                logging.error(f"Error cleaning up VM {name}: {e}")
                
        if self.conn:
            self.conn.close()
            logging.info("Cleanup completed")