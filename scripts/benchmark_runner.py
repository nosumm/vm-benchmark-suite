#!/usr/bin/env python3

"""
VM Performance Benchmark Suite - Benchmark Runner
=============================================

This script implements a comprehensive benchmarking framework for testing VM performance
across multiple dimensions: CPU, memory, disk I/O, and network performance. It uses
industry-standard tools and provides structured output for analysis.

Benchmark Tools Used:
- sysbench: CPU and memory benchmarks
- fio: Disk I/O benchmarks
- iperf3: Network performance benchmarks

Features:
- Automated benchmark execution
- Configurable test parameters
- JSON output for easy analysis
- SSH-based remote execution
- Proper cleanup and resource management

Configuration:
The script expects a YAML configuration file (benchmark_config.yaml) with the following structure:
```yaml
cpu_benchmark:
  sysbench_cpu:
    max_prime: 20000
    threads: [1, 2, 4]
    time: 60

memory_benchmark:
  sysbench_memory:
    total_size: 10G
    block_size: [4K, 1M]
    threads: [1, 2, 4]
    time: 60

disk_benchmark:
  fio:
    runtime: 60
    filesize: 4G
    tests:
      - name: random_read
        rw: randread
        bs: 4k
      - name: random_write
        rw: randwrite
        bs: 4k

network_benchmark:
  iperf3:
    time: 60
    parallel: 4
    protocol: tcp
```

Requirements:
- paramiko (SSH client)
- PyYAML
- Python 3.8+
- Target VM must have: sysbench, fio, iperf3
"""

import subprocess
import json
import os
import yaml
from datetime import datetime
from pathlib import Path
import logging
import paramiko
import time

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

class BenchmarkRunner:
    """
    A class to manage and execute various performance benchmarks on a VM.
    
    This class handles:
    - SSH connection to target VM
    - Execution of different types of benchmarks
    - Result collection and storage
    - Resource cleanup
    """

    def __init__(self, config_path, vm_ip, vm_user='ubuntu', vm_password='password'):
        """
        Initialize the benchmark runner.
        
        Args:
            config_path (str): Path to benchmark configuration YAML
            vm_ip (str): IP address of target VM
            vm_user (str): SSH username for VM access
            vm_password (str): SSH password for VM access
        """
        self.config = self._load_config(config_path)
        self.results_dir = Path('results/raw_data')
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # SSH connection details
        self.vm_ip = vm_ip
        self.vm_user = vm_user
        self.vm_password = vm_password
        self.ssh = None
    
    def _load_config(self, config_path):
        """
        Load benchmark configurations from YAML file.
        
        Args:
            config_path (str): Path to configuration file
            
        Returns:
            dict: Loaded configuration
        """
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def connect_ssh(self):
        """
        Establish SSH connection to target VM.
        
        This method handles:
        - Creating SSH client
        - Setting up host key policy
        - Establishing connection
        
        Raises:
            Exception: If SSH connection fails
        """
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.vm_ip, username=self.vm_user, password=self.vm_password)
            logging.info(f"Successfully connected to VM at {self.vm_ip}")
        except Exception as e:
            logging.error(f"Failed to connect to VM: {e}")
            raise
    
    def _run_ssh_command(self, command):
        """
        Execute command on VM via SSH and return output.
        
        Args:
            command (str): Command to execute
            
        Returns:
            tuple: (stdout, stderr) from command execution
        """
        if not self.ssh:
            self.connect_ssh()
        
        stdin, stdout, stderr = self.ssh.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()
    
    def run_cpu_benchmark(self):
        """
        Run CPU benchmarks using sysbench.
        
        This benchmark tests:
        - Prime number calculation
        - Multiple thread counts
        - Fixed duration tests
        
        Returns:
            list: List of benchmark results
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results = []
        
        cpu_config