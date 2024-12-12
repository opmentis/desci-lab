# Decentralized Scientific Discovery Lab
DeSci Lab: Engage in groundbreaking protein folding research and advance scientific breakthroughs
A distributed protein sequence processing tool that generates Multiple Sequence Alignments (MSAs) and features for AlphaFold structure prediction. Join the Mentis network to contribute your computing power and earn rewards.

## System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ recommended
- **Storage**: 1GB free space for work files
- **Internet**: High-speed connection recommended for database streaming
- **Operating System**: Linux or macOS
- **Python**: 3.8 or higher

## Database Access

The miner uses AlphaFold's streaming approach:
- Databases are streamed in chunks as needed
- No local storage of full databases required
- Chunks are processed and discarded to save space

## Installation

1. Clone the repository:

```bash
git clone https://github.com/opmentis/desci-lab.git
cd desci-lab
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
```
##### REGISTRATION

```bash
pip install opmentis
```

##### Registering as Miner
```python
from opmentis import register_user

# Register as a miner
wallet_address = "your_wallet_address"
labid = "your_lab_id"
role_type = "miner"
register_response = register_user(wallet_address, labid, role_type)
print("Registration Response:", register_response)
```

3. Install system dependencies:

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

4. Install Python dependencies:

```bash
pip install -r requirements.txt
```

5. Add WALLET_ADDRESS in .env:

```bash
#create a .env file
WALLET_ADDRESS=
```

## Usage

1. Start the miner:

```bash
python miner.py --wallet YOUR_WALLET_ADDRESS
```

On first run, the miner will:
1. Set up HMMER search environment
2. Begin processing protein sequences

## Troubleshooting

### Performance Issues
- Ensure at least 8GB RAM
- Check CPU usage with `htop` or Task Manager
- Consider reducing CPU cores if system becomes unresponsive:

```bash
export CPU_CORES=2  # Use only 2 cores
python miner.py --wallet YOUR_WALLET_ADDRESS
```

### Common Errors
- "Database not found": Re-run installation script
- "Out of memory": Increase available RAM or reduce CPU cores
- "Permission denied": Run install script with sudo
- "Database corrupted": Clean and redownload databases

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- Join our [Telegram](https://t.me/opmentisai) for community support
- Visit [DeSci Platform](https://desci.opmentis.xyz) for documentation
- Support: [Technical Support Group](https://t.me/Opmentissupport)
