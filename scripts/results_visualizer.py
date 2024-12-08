#!/usr/bin/env python3

"""
VM Performance Benchmark Suite - Results Visualizer
==============================================

This script analyzes benchmark results and creates visualizations using matplotlib and plotly.
It processes the JSON output files from the benchmark runner and generates:
- CPU performance comparisons across different configurations
- Memory throughput analysis
- Disk I/O performance graphs
- Network performance charts
- Summary reports
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import re
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import logging

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

class BenchmarkVisualizer:
    def __init__(self, results_dir):
        self.results_dir = Path(results_dir)
        self.output_dir = Path('results/visualizations')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        plt.style.use('seaborn')
        self.colors = px.colors.qualitative.Set3

    def _load_benchmark_results(self, benchmark_type):
        results = []
        pattern = f"{benchmark_type}_benchmark_*.json"
        
        for result_file in self.results_dir.glob(pattern):
            with open(result_file) as f:
                data = json.load(f)
                results.extend(data)
        
        return results

    def _parse_sysbench_output(self, raw_output):
        metrics = {}
        patterns = {
            'events_per_second': r'events per second:\s*(\d+\.?\d*)',
            'total_time': r'total time:\s*(\d+\.?\d*)s',
            'total_events': r'total number of events:\s*(\d+)',
            'latency_min': r'min:\s*(\d+\.?\d*)',
            'latency_avg': r'avg:\s*(\d+\.?\d*)',
            'latency_max': r'max:\s*(\d+\.?\d*)'
        }
        
        for metric, pattern in patterns.items():
            match = re.search(pattern, raw_output)
            if match:
                metrics[metric] = float(match.group(1))
        
        return metrics

    def visualize_cpu_performance(self):
        results = self._load_benchmark_results('cpu')
        if not results:
            logging.warning("No CPU benchmark results found")
            return

        df_list = []
        for result in results:
            metrics = self._parse_sysbench_output(result['raw_output'])
            metrics['threads'] = result['threads']
            df_list.append(metrics)
        
        df = pd.DataFrame(df_list)
        
        # Events per second vs threads
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['threads'],
            y=df['events_per_second'],
            mode='lines+markers',
            name='Events per Second'
        ))
        
        fig.update_layout(
            title='CPU Performance vs Thread Count',
            xaxis_title='Number of Threads',
            yaxis_title='Events per Second',
            template='plotly_white'
        )
        
        fig.write_html(self.output_dir / 'cpu_performance.html')
        
        # Latency analysis
        plt.figure(figsize=(10, 6))
        plt.boxplot([df['latency_min'], df['latency_avg'], df['latency_max']], 
                   labels=['Min Latency', 'Avg Latency', 'Max Latency'])
        plt.title('CPU Benchmark Latency Analysis')
        plt.ylabel('Latency (ms)')
        plt.savefig(self.output_dir / 'cpu_latency.png')
        plt.close()

    def visualize_memory_performance(self):
        results = self._load_benchmark_results('memory')
        if not results:
            logging.warning("No memory benchmark results found")
            return
        
        df_list = []
        for result in results:
            metrics = self._parse_sysbench_output(result['raw_output'])
            metrics['block_size'] = result['block_size']
            metrics['threads'] = result['threads']
            df_list.append(metrics)
        
        df = pd.DataFrame(df_list)
        
        fig = px.bar(df, 
                    x='block_size',
                    y='events_per_second',
                    color='threads',
                    barmode='group',
                    title='Memory Throughput by Block Size')
        
        fig.update_layout(
            xaxis_title='Block Size',
            yaxis_title='Operations per Second',
            template='plotly_white'
        )
        
        fig.write_html(self.output_dir / 'memory_performance.html')

    def visualize_disk_performance(self):
        results = self._load_benchmark_results('disk')
        if not results:
            logging.warning("No disk benchmark results found")
            return
        
        df_list = []
        for result in results:
            fio_data = json.loads(result['raw_output'])
            job_data = fio_data['jobs'][0]
            
            metrics = {
                'test_name': result['test_name'],
                'iops': job_data['read' if 'read' in result['test_name'] else 'write']['iops'],
                'bandwidth': job_data['read' if 'read' in result['test_name'] else 'write']['bw'],
                'latency': job_data['read' if 'read' in result['test_name'] else 'write']['lat_ns']['mean'] / 1000000
            }
            df_list.append(metrics)
        
        df = pd.DataFrame(df_list)
        
        fig = make_subplots(rows=2, cols=1,
                           subplot_titles=('IOPS by Test', 'Bandwidth by Test'))
        
        fig.add_trace(
            go.Bar(x=df['test_name'], y=df['iops'], name='IOPS'),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(x=df['test_name'], y=df['bandwidth'], name='Bandwidth (KB/s)'),
            row=2, col=1
        )
        
        fig.update_layout(height=800, title_text='Disk I/O Performance Analysis')
        fig.write_html(self.output_dir / 'disk_performance.html')

    def visualize_network_performance(self):
        results = self._load_benchmark_results('network')
        if not results:
            logging.warning("No network benchmark results found")
            return
        
        df_list = []
        for result in results:
            iperf_data = json.loads(result['raw_output'])
            
            for interval in iperf_data['intervals']:
                metrics = {
                    'timestamp': interval['sum']['start'],
                    'bandwidth': interval['sum']['bits_per_second'] / 1000000,
                    'retransmits': interval['sum'].get('retransmits', 0),
                    'protocol': iperf_data['start']['test_start']['protocol']
                }
                df_list.append(metrics)
        
        df = pd.DataFrame(df_list)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['bandwidth'],
            mode='lines+markers',
            name='Bandwidth (Mbps)'
        ))
        
        fig.update_layout(
            title='Network Performance Over Time',
            xaxis_title='Time (seconds)',
            yaxis_title='Bandwidth (Mbps)',
            template='plotly_white'
        )
        
        fig.write_html(self.output_dir / 'network_performance.html')

    def generate_summary_report(self):
        """Generate a comprehensive summary report of all benchmarks."""
        cpu_results = self._load_benchmark_results('cpu')
        memory_results = self._load_benchmark_results('memory')
        disk_results = self._load_benchmark_results('disk')
        network_results = self._load_benchmark_results('network')

        report_template = """
        <html>
        <head>
            <title>VM Performance Benchmark Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #2c3e50; }
                .section { margin: 20px 0; }
                .metric { margin: 10px 0; }
                .timestamp { color: #7f8c8d; }
            </style>
        </head>
        <body>
            <h1>VM Performance Benchmark Summary Report</h1>
            <div class="timestamp">Generated: {timestamp}</div>
            
            <div class="section">
                <h2>CPU Performance</h2>
                {cpu_summary}
            </div>
            
            <div class="section">
                <h2>Memory Performance</h2>
                {memory_summary}
            </div>
            
            <div class="section">
                <h2>Disk I/O Performance</h2>
                {disk_summary}
            </div>
            
            <div class="section">
                <h2>Network Performance</h2>
                {network_summary}
            </div>
            
            <div class="section">
                <h2>Recommendations</h2>
                {recommendations}
            </div>
        </body>
        </html>
        """
        
        report_content = report_template.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            cpu_summary=self._generate_cpu_summary(cpu_results),
            memory_summary=self._generate_memory_summary(memory_results),
            disk_summary=self._generate_disk_summary(disk_results),
            network_summary=self._generate_network_summary(network_results),
            recommendations=self._generate_recommendations(
                cpu_results, memory_results, disk_results, network_results
            )
        )
        
        with open(self.output_dir / 'benchmark_report.html', 'w') as f:
            f.write(report_content)

    def _generate_cpu_summary(self, results):
        if not results:
            return "<p>No CPU benchmark data available</p>"
        
        summary = "<ul>"
        for result in results:
            metrics = self._parse_sysbench_output(result['raw_output'])
            summary += f"""
                <li>Thread count: {result['threads']}
                    <ul>
                        <li>Events per second: {metrics['events_per_second']:.2f}</li>
                        <li>Average latency: {metrics['latency_avg']:.2f} ms</li>
                    </ul>
                </li>"""
        summary += "</ul>"
        return summary

    def _generate_memory_summary(self, results):
        if not results:
            return "<p>No memory benchmark data available</p>"
        
        summary = "<ul>"
        for result in results:
            metrics = self._parse_sysbench_output(result['raw_output'])
            summary += f"""
                <li>Block size: {result['block_size']}, Threads: {result['threads']}
                    <ul>
                        <li>Operations per second: {metrics['events_per_second']:.2f}</li>
                        <li>Average latency: {metrics['latency_avg']:.2f} ms</li>
                    </ul>
                </li>"""
        summary += "</ul>"
        return summary

    def _generate_disk_summary(self, results):
        if not results:
            return "<p>No disk benchmark data available</p>"
        
        summary = "<ul>"
        for result in results:
            fio_data = json.loads(result['raw_output'])
            job_data = fio_data['jobs'][0]
            rw_data = job_data['read' if 'read' in result['test_name'] else 'write']
            
            summary += f"""
                <li>{result['test_name']}
                    <ul>
                        <li>IOPS: {rw_data['iops']:.2f}</li>
                        <li>Bandwidth: {rw_data['bw']:.2f} KB/s</li>
                        <li>Average latency: {rw_data['lat_ns']['mean'] / 1000000:.2f} ms</li>
                    </ul>
                </li>"""
        summary += "</ul>"
        return summary

    def _generate_network_summary(self, results):
        if not results:
            return "<p>No network benchmark data available</p>"
        
        summary = "<ul>"
        for result in results:
            iperf_data = json.loads(result['raw_output'])
            
            total_bandwidth = 0
            interval_count = 0
            total_retransmits = 0
            
            for interval in iperf_data['intervals']:
                total_bandwidth += interval['sum']['bits_per_second'] / 1000000
                total_retransmits += interval['sum'].get('retransmits', 0)
                interval_count += 1
            
            avg_bandwidth = total_bandwidth / interval_count if interval_count > 0 else 0
            
            summary += f"""
                <li>Protocol: {iperf_data['start']['test_start']['protocol']}
                    <ul>
                        <li>Average Bandwidth: {avg_bandwidth:.2f} Mbps</li>
                        <li>Total Retransmits: {total_retransmits}</li>
                        <li>Test Duration: {iperf_data['start']['test_start']['duration']} seconds</li>
                    </ul>
                </li>"""
        summary += "</ul>"
        return summary

    def _generate_recommendations(self, cpu_results, memory_results, disk_results, network_results):
        recommendations = "<ul>"
        
        if cpu_results:
            max_threads = max(result['threads'] for result in cpu_results)
            max_events = max(self._parse_sysbench_output(result['raw_output'])['events_per_second'] 
                           for result in cpu_results)
            recommendations += f"""
                <li>CPU Performance:
                    <ul>
                        <li>Optimal thread count appears to be {max_threads}</li>
                        <li>Peak performance: {max_events:.2f} events per second</li>
                        <li>Consider CPU pinning for better performance</li>
                        <li>Evaluate if hyperthreading is beneficial for your workload</li>
                    </ul>
                </li>"""
        
        if memory_results:
            best_block_size = max(memory_results, 
                                key=lambda x: self._parse_sysbench_output(x['raw_output'])['events_per_second'])['block_size']
            recommendations += f"""
                <li>Memory Performance:
                    <ul>
                        <li>Optimal block size appears to be {best_block_size}</li>
                        <li>Consider enabling huge pages for better memory performance</li>
                        <li>Evaluate NUMA settings if available</li>
                        <li>Monitor memory bandwidth saturation</li>
                    </ul>
                </li>"""
        
        if disk_results:
            recommendations += """
                <li>Disk I/O Performance:
                    <ul>
                        <li>Consider using virtio-blk for better disk performance</li>
                        <li>Enable disk cache if not performance testing</li>
                        <li>Use appropriate block sizes for your workload</li>
                        <li>Evaluate IO scheduler settings</li>
                        <li>Consider using direct I/O for database workloads</li>
                    </ul>
                </li>"""
        
        if network_results:
            recommendations += """
                <li>Network Performance:
                    <ul>
                        <li>Enable vhost-net for better network performance</li>
                        <li>Consider using multiple queue virtio-net</li>
                        <li>Tune TCP parameters for your specific workload</li>
                        <li>Evaluate network driver settings</li>
                        <li>Monitor network bandwidth utilization</li>
                    </ul>
                </li>"""
        
        recommendations += "</ul>"
        return recommendations

if __name__ == '__main__':
    # Example usage
    visualizer = BenchmarkVisualizer('results/raw_data')
    visualizer.visualize_cpu_performance()
    visualizer.visualize_memory_performance()
    visualizer.visualize_disk_performance()
    visualizer.visualize_network_performance()
    visualizer.generate_summary_report()