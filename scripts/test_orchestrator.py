#!/usr/bin/env python3

"""
VM Performance Benchmark Suite - Test Orchestrator
==============================================
"""

import argparse
import logging
import yaml
import sys
import time
from pathlib import Path
from datetime import datetime
import concurrent.futures
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Import our components
from vm_provisioner import VMProvisioner
from benchmark_runner import BenchmarkRunner
from results_visualizer import BenchmarkVisualizer

# Get the project root directory (one level up from scripts)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / 'benchmark_run.log')
    ]
)

class TestOrchestrator:
    def __init__(self, config_path):
        """
        Initialize the test orchestrator.
        
        Args:
            config_path (str): Path to main configuration file
        """
        self.config = self._load_config(config_path)
        self.results_dir = PROJECT_ROOT / 'results/raw_data'
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.provisioner = None
        self.vm_ips = {}  # Track VM IPs for cleanup
        
    def _load_config(self, config_path):
        """Load main configuration file."""
        config_file = PROJECT_ROOT / config_path
        logging.info(f"Loading config from: {config_file}")
        with open(config_file) as f:
            return yaml.safe_load(f)
    
    def _send_notification(self, subject, body):
        """Send email notification if configured."""
        if 'email' not in self.config:
            return
            
        email_config = self.config['email']
        if not email_config.get('enabled', False):
            return
            
        msg = MIMEMultipart()
        msg['From'] = email_config['from']
        msg['To'] = email_config['to']
        msg['Subject'] = f"Benchmark Results: {subject}"
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            logging.info("Notification email sent successfully")
        except Exception as e:
            logging.error(f"Failed to send notification: {e}")
    
    def provision_vms(self):
        """Provision all required VMs for testing."""
        try:
            self.provisioner = VMProvisioner(PROJECT_ROOT / 'configs/vm_config.yaml')
            self.provisioner.connect()
            
            # Create VMs for each configuration
            for vm_config in self.config['test_matrix']:
                vm_name = f'benchmark-vm-{vm_config}-{self.run_id}'
                vm = self.provisioner.create_vm(vm_name, vm_config)
                
                # Wait for VM to be ready and get its IP
                time.sleep(30)  # Basic wait for VM startup
                
                # Store VM IP for later use
                self.vm_ips[vm_name] = '192.168.122.100'  # Replace with actual IP detection
                
            logging.info(f"Successfully provisioned {len(self.config['test_matrix'])} VMs")
            
        except Exception as e:
            logging.error(f"Failed to provision VMs: {e}")
            self.cleanup()
            raise
    
    def run_benchmarks(self):
        """Execute benchmarks on all VMs."""
        results = {}
        
        try:
            # Run benchmarks on each VM
            for vm_name, vm_ip in self.vm_ips.items():
                logging.info(f"Starting benchmarks on {vm_name}")
                
                runner = BenchmarkRunner(
                    PROJECT_ROOT / 'configs/benchmark_config.yaml',
                    vm_ip,
                    self.config['vm_credentials']['username'],
                    self.config['vm_credentials']['password']
                )
                
                # Run benchmark suite
                benchmark_results = {
                    'cpu': runner.run_cpu_benchmark(),
                    'memory': runner.run_memory_benchmark(),
                    'disk': runner.run_disk_benchmark()
                }
                
                if vm_name != list(self.vm_ips.keys())[0]:
                    server_ip = list(self.vm_ips.values())[0]
                    benchmark_results['network'] = runner.run_network_benchmark(server_ip)
                
                results[vm_name] = benchmark_results
                runner.cleanup()
                
            logging.info("Successfully completed all benchmarks")
            return results
            
        except Exception as e:
            logging.error(f"Failed to run benchmarks: {e}")
            raise

    def cleanup(self):
        """Clean up all resources."""
        if self.provisioner:
            try:
                self.provisioner.cleanup()
                logging.info("Successfully cleaned up all resources")
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")

    def run_test_suite(self):
        """
        Run the complete test suite including:
        - VM provisioning
        - Benchmark execution
        - Visualization generation
        - Cleanup
        """
        start_time = datetime.now()
        
        try:
            # Start test suite
            logging.info(f"Starting benchmark test suite - Run ID: {self.run_id}")
            self._send_notification(
                "Test Suite Started",
                f"Benchmark test suite started at {start_time}"
            )
            
            # Provision VMs
            logging.info("Provisioning VMs...")
            self.provision_vms()
            
            # Run benchmarks
            logging.info("Running benchmarks...")
            results = self.run_benchmarks()
            
            # Generate visualizations
            logging.info("Generating visualizations...")
            visualizer = BenchmarkVisualizer(self.results_dir)
            visualizer.visualize_cpu_performance()
            visualizer.visualize_memory_performance()
            visualizer.visualize_disk_performance()
            visualizer.visualize_network_performance()
            visualizer.generate_summary_report()
            
            # Calculate execution time
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Send completion notification
            self._send_notification(
                "Test Suite Completed",
                f"""
                Benchmark test suite completed successfully.
                Start time: {start_time}
                End time: {end_time}
                Duration: {duration}
                
                Results have been generated in the results directory.
                """
            )
            
            logging.info(f"Test suite completed successfully. Duration: {duration}")
            
        except Exception as e:
            logging.error(f"Test suite failed: {e}")
            self._send_notification(
                "Test Suite Failed",
                f"Benchmark test suite failed: {str(e)}"
            )
            raise
            
        finally:
            # Always cleanup
            self.cleanup()

def main():
    parser = argparse.ArgumentParser(description='VM Performance Benchmark Suite')
    parser.add_argument('--config', default='configs/main_config.yaml',
                      help='Path to main configuration file')
    args = parser.parse_args()
    
    logging.info(f"Project root directory: {PROJECT_ROOT}")
    orchestrator = TestOrchestrator(args.config)
    orchestrator.run_test_suite()

if __name__ == '__main__':
    main()