from alphafold.data.tools import jackhmmer
from typing import Dict
import logging
from pathlib import Path
from alphafold.notebooks import notebook_utils
from urllib import request
import socket
# from .sequence_validator import SequenceValidator

logger = logging.getLogger(__name__)

class JackHMMER:
    def __init__(self, binary_path: str = "jackhmmer"):
        self.binary_path = binary_path
        
        # Match Colab settings
        self.max_hits = {
            'uniref90': 10_000,
            'smallbfd': 5_000,
            'mgnify': 501,
        }
        
        # Find closest mirror with timeout
        self.db_root = self._find_db_mirror()
        
        # Database configurations
        self.databases = [
            {'db_name': 'uniref90',
             'db_path': f'{self.db_root}uniref90_2022_01.fasta',
             'num_streamed_chunks': 62,
             'z_value': 144_113_457},
            {'db_name': 'smallbfd',
             'db_path': f'{self.db_root}bfd-first_non_consensus_sequences.fasta',
             'num_streamed_chunks': 17,
             'z_value': 65_984_053},
            {'db_name': 'mgnify',
             'db_path': f'{self.db_root}mgy_clusters_2022_05.fasta',
             'num_streamed_chunks': 120,
             'z_value': 623_796_864}
        ]

    def _find_db_mirror(self) -> str:
        """Find closest database mirror with timeout"""
        test_pattern = 'https://storage.googleapis.com/alphafold-colab{:s}/latest/uniref90_2022_01.fasta.1'
        mirrors = ['', '-europe', '-asia']
        
        # Set default socket timeout
        socket.setdefaulttimeout(10)  # 10 seconds timeout
        
        def fetch_with_timeout(source):
            try:
                logger.info(f"Testing mirror: alphafold-colab{source}")
                url = test_pattern.format(source)
                # Just do a HEAD request to check availability
                req = request.Request(url, method='HEAD')
                request.urlopen(req, timeout=10)
                return source
            except Exception as e:
                logger.debug(f"Mirror alphafold-colab{source} failed: {e}")
                return None

        # Try mirrors sequentially with timeout
        for source in mirrors:
            try:
                result = fetch_with_timeout(source)
                if result is not None:
                    logger.info(f"Using mirror: alphafold-colab{source}")
                    return f'https://storage.googleapis.com/alphafold-colab{source}/latest/'
            except Exception as e:
                logger.warning(f"Error testing mirror {source}: {e}")
                continue

        # If all mirrors fail, use default
        logger.warning("All mirrors failed, using default mirror")
        return 'https://storage.googleapis.com/alphafold-colab/latest/'

    def _write_fasta(self, sequence: str, file_path: str):
        """Write sequence to FASTA file safely"""
        # Convert sequence to list of single characters
        sequence_list = list(sequence)
        # Join with newlines every 80 characters
        sequence_lines = [''.join(sequence_list[i:i+80]) 
                         for i in range(0, len(sequence_list), 80)]
        
        with open(file_path, 'w') as f:
            f.write('>query\n')
            f.write('\n'.join(sequence_lines))
            f.write('\n')
            
        logger.debug(f"Wrote FASTA file to {file_path}")
        logger.debug(f"FASTA contents:\n{open(file_path).read()}")

    def _clean_sequence(self, sequence: str) -> str:
        """Clean and validate sequence"""
        # Convert list to string if needed
        if isinstance(sequence, (list, tuple)):
            sequence = ''.join(str(s) for s in sequence)
            
        # Remove non-letters and normalize
        sequence = ''.join(c for c in str(sequence) if c.isalpha())
        return sequence.strip().upper()

    async def search_with_progress(self, sequence: str, progress_callback) -> Dict:
        """Run jackhmmer search with progress tracking"""
        query_paths = []
        try:
            # Write sequence to FASTA file exactly as AlphaFold does
            fasta_path = f'target_01.fasta'  # Match AlphaFold's naming
            with open(fasta_path, 'wt') as f:  # Note: they use 'wt' mode
                f.write(f'>query\n{sequence}')  # No extra newline
            query_paths = [fasta_path]  # Store as list like AlphaFold

            raw_results = {}
            
            for db_config in self.databases:
                db_name = db_config['db_name']
                total_chunks = db_config['num_streamed_chunks']
                
                logger.info(f"Starting search against {db_name} ({total_chunks} chunks)")
                
                runner = jackhmmer.Jackhmmer(
                    binary_path=self.binary_path,
                    database_path=db_config['db_path'],
                    num_streamed_chunks=total_chunks,
                    z_value=db_config['z_value'],
                    get_tblout=True
                )
                
                def streaming_callback(chunk_idx):
                    progress_callback(
                        db_name=db_name,
                        chunk=chunk_idx + 1,
                        total=total_chunks,
                        sequences_found=0
                    )
                
                runner.streaming_callback = streaming_callback
                
                # Use query_multiple like AlphaFold does
                results = runner.query_multiple(query_paths)[0]
                raw_results[db_name] = results
                
                # Process results exactly like AlphaFold
                merged = notebook_utils.merge_chunked_msa(
                    results=results,
                    max_hits=self.max_hits[db_name]
                )
                if merged.sequences:
                    sequences_found = len(set(merged.sequences))
                    logger.info(f"Found {sequences_found} unique sequences in {db_name}")

            return raw_results
            
        finally:
            for path in query_paths:
                try:
                    Path(path).unlink(missing_ok=True)
                except:
                    pass