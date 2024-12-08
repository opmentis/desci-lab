import logging
import pickle
from .hmmer import HMMER
import asyncio
from tqdm import tqdm
import sys

logger = logging.getLogger(__name__)

class SequenceProcessor:
    def __init__(self):
        self.hmmer = HMMER()
        # Create progress bars
        self.pbar = None
        self.db_pbar = None
        self.miner_service = None
        self.current_task_id = None
        self.current_wallet = None

    def _progress_callback(self, db_name: str, chunk: int, total: int, sequences_found: int):
        """Callback for progress updates during HMMER search"""
        try:
            # Update overall progress bar
            self.pbar.update(1)
            
            # Update database progress bar
            db_progress = (chunk / total) * 100
            self.db_pbar.n = db_progress
            self.db_pbar.set_description(f"Searching {db_name}")
            self.db_pbar.refresh()
            
            # Log meaningful stats
            if sequences_found > 0:
                logger.info(f"Found {sequences_found} sequences in {db_name}")
            
            if self.current_task_id and self.current_wallet and self.miner_service:
                progress = self.pbar.n / self.pbar.total
                asyncio.create_task(self._update_progress(
                    self.current_task_id,
                    {
                        'status': 'searching_msa',
                        'progress': progress,
                        'message': f'Searching {db_name} (chunk {chunk}/{total})',
                        'wallet_address': self.current_wallet
                    }
                ))
        except Exception as e:
            logger.error(f"Error in progress callback: {e}")

    async def _update_progress(self, task_id: str, progress_data: dict):
        """Update task progress through miner service"""
        try:
            if self.miner_service:
                await self.miner_service.update_task_progress(
                    task_id=task_id,
                    progress=progress_data['progress'],
                    status=progress_data['status']
                )
            else:
                return
        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def _clean_sequence(self, sequence: str) -> str:
        """Clean and validate protein sequence"""
        try:
            # Convert to string if needed
            if isinstance(sequence, (list, tuple)):
                sequence = ''.join(map(str, sequence))
            elif not isinstance(sequence, str):
                sequence = str(sequence)
                
            # Remove non-letters and normalize
            sequence = ''.join(c for c in sequence if c.isalpha())
            sequence = sequence.strip().upper()
            
            # Validate
            if not sequence:
                raise ValueError("Empty sequence after cleaning")
                
            # Check for valid amino acids
            valid_aa = set('ACDEFGHIKLMNPQRSTVWY')
            invalid_chars = set(sequence) - valid_aa
            if invalid_chars:
                raise ValueError(f"Invalid amino acid characters: {invalid_chars}")
                
            return sequence
            
        except Exception as e:
            logger.error(f"Error cleaning sequence: {e}")
            raise

    async def process_sequence(self, task_id: str, sequence: str, wallet_address: str, miner_service=None):
        """Process a sequence and report progress"""
        self.miner_service = miner_service
        self.current_task_id = task_id
        self.current_wallet = wallet_address
        
        try:
            # Detailed sequence inspection
            logger.debug("\nSequence inspection in processor:")
            logger.debug(f"Type: {type(sequence)}")
            logger.debug(f"Length: {len(sequence)}")
            if isinstance(sequence, (list, tuple)):
                logger.debug("Sequence is a list/tuple!")
                logger.debug(f"First few items: {sequence[:30]}")
                for i, item in enumerate(sequence):
                    logger.debug(f"Item {i}: type={type(item)}, value={item}")
                    if i > 30:
                        break
            else:
                logger.debug(f"First 50 chars: {sequence[:50]}")
            
            # Ensure sequence is a string
            if isinstance(sequence, (list, tuple)):
                sequence = ''.join(str(s) for s in sequence)
            sequence = str(sequence).strip()
            
            logger.info(f"Starting sequence processing for task {task_id}")
            logger.info(f"Sequence length: {len(sequence)}")
            
            # Initialize progress bars
            total_chunks = sum(db['num_streamed_chunks'] for db in self.hmmer.jackhmmer.databases)
            self.pbar = tqdm(total=total_chunks, desc="Overall progress", 
                           bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
            self.db_pbar = tqdm(total=100, desc="Current database", leave=False,
                              bar_format='{desc}: {percentage:3.0f}%|{bar}| [{elapsed}<{remaining}]')
            
            # Start MSA search
            await self._update_progress(task_id, {
                'status': 'searching_msa',
                'progress': 0.0,
                'message': 'Starting MSA search',
                'wallet_address': wallet_address
            })
            
            try:
                # Run search with progress tracking
                stockholm_strings, \
                    features, \
                        features_dict, \
                            MSAs = await self.hmmer.search_with_progress(sequence, self._progress_callback)   
                # Process results
                logger.info("Processing alignments...")
                await self._update_progress(task_id, {
                    'status': 'processing',
                    'progress': 0.9,
                    'message': 'Processing alignments',
                    'wallet_address': wallet_address
                })
                
                # features = self._generate_features(alignments)
                
                # Complete
                logger.info(f"Task {task_id} completed successfully")
                await self._update_progress(task_id, {
                    'status': 'completed',
                    'progress': 1.0,
                    'message': 'Task completed successfully',
                    'wallet_address': wallet_address
                })
                
                # Save results
                logger.info("Saving results...")

                with open('raw_features.pkl', 'wb') as rf:
                    pickle.dump(features_dict, rf)
                
                with open('chain_features.pkl', 'wb') as cf:
                    pickle.dump(features, cf)

                with open('result.pkl', 'wb') as r:
                    pickle.dump(MSAs, r)
                
                with open('stockholm.txt', 'w') as f:
                    f.write(stockholm_strings)
                
                result_path = {
                    'raw_features': 'raw_features.pkl',
                    'msa': 'result.pkl',
                    'features': 'chain_features.pkl',
                    'stockholm_string': 'stockholm.txt'
                }
                return result_path
                
            except Exception as e:
                logger.error(f"HMMER search failed: {e}")
                await self._update_progress(task_id, {
                    'status': 'failed',
                    'progress': 0.0,
                    'message': f'HMMER search failed: {str(e)}',
                    'wallet_address': wallet_address
                })
                raise
                
        finally:
            # Clean up
            if self.pbar:
                self.pbar.close()
            if self.db_pbar:
                self.db_pbar.close()
            self.current_task_id = None
            self.current_wallet = None