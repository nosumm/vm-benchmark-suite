# VM Performance Benchmark Suite

A comprehensive automated testing framework for measuring and analyzing VM performance using QEMU-KVM. This suite automates the deployment of VMs, runs a series of performance benchmarks, and generates detailed reports and visualizations.

## Features

- Automated VM provisioning with QEMU-KVM
- Multiple VM size configurations (small, medium, large)
- Comprehensive benchmark suite:
  - CPU performance (sysbench)
  - Memory throughput (sysbench)
  - Disk I/O (fio)
  - Network performance (iperf3)
- Automated result collection and analysis
- Interactive visualizations
- Detailed HTML reports with recommendations

## Prerequisites

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
    qemu-kvm \
    libvirt-daemon-system \
    libvirt-clients \
    bridge-utils \
    python3-pip \
    python3-libvirt \
    cloud-image-utils \
    genisoimage

# Install Python dependencies
pip3 install \
    libvirt-python \
    pyyaml \
    pandas \
    matplotlib \
    seaborn \
    plotly \
    paramiko \
    requests
```

## Project Structure

```
vm-benchmark-suite/
├── scripts/
│   ├── test_orchestrator.py     # Main orchestration script
│   ├── vm_provisioner.py        # VM creation and management
│   ├── benchmark_runner.py      # Benchmark execution
│   └── results_visualizer.py    # Results analysis and visualization
├── configs/
│   ├── main_config.yaml         # Main configuration
│   ├── vm_config.yaml           # VM specifications
│   └── benchmark_config.yaml    # Benchmark parameters
├── results/
│   ├── raw_data/               # Benchmark result data
│   └── visualizations/         # Generated graphs and reports
├── images/                     # VM disk images
├── cloud-init/                 # VM initialization configs
└── keys/                      # SSH keys for VM access
```

## Configuration Files

### main_config.yaml
```yaml
test_matrix:
  - small
  - medium
  - large

vm_credentials:
  username: benchmark
  password: your_password

email:
  enabled: false
  smtp_server: smtp.example.com
  smtp_port: 587
  username: your_email@example.com
  password: your_email_password
  from: your_email@example.com
  to: recipient@example.com
```

### vm_config.yaml
```yaml
vm_configs:
  small:
    vcpus: 2
    memory_mb: 2048
    disk_size_gb: 20
  medium:
    vcpus: 4
    memory_mb: 4096
    disk_size_gb: 40
  large:
    vcpus: 8
    memory_mb: 8192
    disk_size_gb: 80

storage:
  pool_name: default
  pool_path: /var/lib/libvirt/images
```

### benchmark_config.yaml
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
```

## Usage

1. Clone the repository and set up the environment:
```bash
git clone [your-repo-url]
cd vm-benchmark-suite
```

2. Install dependencies:
```bash
sudo apt-get update
sudo apt-get install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils \
    python3-pip python3-libvirt cloud-image-utils genisoimage
pip3 install -r requirements.txt
```

3. Configure the benchmark suite:
- Update configurations in `configs/` directory
- Ensure proper permissions for libvirt
```bash
sudo usermod -a -G libvirt $USER
sudo usermod -a -G kvm $USER
```

4. Run the benchmark suite:
```bash
cd scripts
python3 test_orchestrator.py
```

5. View results:
- Raw data: `results/raw_data/`
- Visualizations: `results/visualizations/`
- HTML report: `results/visualizations/benchmark_report.html`

## Results

The benchmark suite generates:
- Interactive HTML plots for each benchmark type
- Performance comparison graphs
- Comprehensive HTML report with:
  - Detailed performance metrics
  - Comparative analysis
  - Optimization recommendations

## Troubleshooting

1. Permission issues:
```bash
sudo chmod 666 /var/run/libvirt/libvirt-sock
```

2. VM creation fails:
```bash
sudo chmod 777 /var/lib/libvirt/images
```

3. Network issues:
```bash
sudo virsh net-list --all
sudo virsh net-start default
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The MIT License is a permissive license that is short and to the point. It lets people do anything they want with your code as long as they provide attribution back to you and don't hold you liable.

## Author

Noah Staveley

## Contributing

Contributions are welcome! Feel free to:
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.