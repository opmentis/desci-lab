from setuptools import setup, find_packages

setup(
    name="mentis-alphafold-miner",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "tenacity",
        "backoff",
        "pydantic-settings",
        "hmmer",
        "numpy",
        "pandas",
        "biopython",
        "psutil"
    ],
    entry_points={
        'console_scripts': [
            'opmentis-miner=miner:main',
        ],
    },
    python_requires=">=3.8",
) 