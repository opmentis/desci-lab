from asyncio.log import logger
from concurrent import futures
from pathlib import Path
from typing import Optional
from urllib import request
import psutil
from pydantic_settings import BaseSettings
from typing import ClassVar
import requests
from tqdm import tqdm
import gzip
import subprocess
from concurrent.futures import ThreadPoolExecutor as Executor

class Settings(BaseSettings):
    """Miner configuration settings"""
    
    # API Settings
    API_URL: str = "http://ds.opmentis.xyz"
    TASK_POLL_INTERVAL: int = 100  # seconds
    
    # Authentication
    WALLET_ADDRESS: str
    
    # Directories
    WORK_DIR: str = "/tmp/ramdisk/work"
    HMMER_DB_DIR: str = "/tmp/ramdisk/db"
    
    # Processing Settings
    MAX_SEQUENCE_LENGTH: int = 4000
    MIN_SEQUENCE_LENGTH: int = 16
    CPU_CORES: Optional[int] = None
    
    # File Types
    FILE_TYPES: ClassVar[dict] = {
        "msa": "alignment.sto",
        "features": "features.pkl",
        "results": "results.json"
    }
    
    # Database paths (for reference only, actual streaming happens in jackhmmer)
    UNIREF90_PATH: str = "/tmp/ramdisk/work/uniref90.fasta"
    SMALLBFD_PATH: str = "/tmp/ramdisk/work/smallbfd.fasta"
    MGNIFY_PATH: str = "/tmp/ramdisk/work/mgnify.fasta"
    
    # MSA database configurations
    MSA_DATABASES: ClassVar[list] = [
        {'db_name': 'uniref90',
         'num_streamed_chunks': 62,
         'z_value': 144_113_457},
        {'db_name': 'smallbfd',
         'num_streamed_chunks': 17,
         'z_value': 65_984_053},
        {'db_name': 'mgnify',
         'num_streamed_chunks': 120,
         'z_value': 623_796_864},
    ]
    
    MAX_HITS: ClassVar[dict] = {
        'uniref90': 10_000,
        'smallbfd': 5_000,
        'mgnify': 501,
    }
    
    @property
    def num_cpu_cores(self) -> int:
        """Get number of CPU cores to use"""
        if self.CPU_CORES is not None:
            # If manually set, ensure it's within reasonable bounds
            total_cpu = psutil.cpu_count(logical=True)
            return max(1, min(self.CPU_CORES, total_cpu))
        
        try:
            total_cpu = psutil.cpu_count(logical=True)
            # Use half of available CPUs, minimum 1, maximum 8
            recommended = max(1, min(total_cpu // 2, 8))
            return recommended
        except:
            # Fallback to 2 if can't detect
            return 2
            
    @property
    def hmmer_db_path(self) -> Path:
        """Get HMMER database path"""
        db_path = Path(self.HMMER_DB_DIR) / "pfam" / "Pfam-A.hmm"
        
        if not db_path.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._download_hmmer_db(db_path)
            
        return db_path
        
    def _download_hmmer_db(self, path: Path):
        """Download HMMER database if not found"""
        # Download from official source
        url = "http://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz"
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        print(f"Downloading HMMER database to {path}...")
        with open(path.with_suffix('.gz'), 'wb') as f:
            with tqdm(total=total_size, unit='iB', unit_scale=True) as pbar:
                for data in response.iter_content(chunk_size=1024):
                    size = f.write(data)
                    pbar.update(size)
                    
        # Decompress
        with gzip.open(path.with_suffix('.gz'), 'rb') as f_in:
            with open(path, 'wb') as f_out:
                f_out.write(f_in.read())
                
        # Remove compressed file
        path.with_suffix('.gz').unlink()
        
        # Press the database
        subprocess.run(["hmmpress", str(path)], check=True)
    
    def setup_databases(self):
        """Ensure work directories exist"""
        Path("/tmp/ramdisk/work").mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
