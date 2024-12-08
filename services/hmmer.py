from alphafold.notebooks import notebook_utils
from alphafold.data import pipeline, msa_pairing, pipeline_multimer, feature_processing
from alphafold.common import protein
from .jackhmmer import JackHMMER
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from alphafold.data.tools import jackhmmer
import enum

logger = logging.getLogger(__name__)

class ModelType(enum.Enum):
    MONOMER = 0
    MULTIMER = 1

class HMMER:
    def __init__(self, binary_path: str = "jackhmmer", database_paths: Optional[Dict[str, str]] = None):
        self.jackhmmer = JackHMMER(binary_path=binary_path)
        self.databases = self.jackhmmer.databases
        self.max_hits = self.jackhmmer.max_hits
        
    def _ensure_string_sequence(self, sequence: Any) -> str:
        """Convert sequence to string and validate"""
        # Convert to string if needed
        if isinstance(sequence, (list, tuple)):
            sequence = ''.join(str(s) for s in sequence)
        elif not isinstance(sequence, str):
            sequence = str(sequence)
            
        # Clean and normalize
        sequence = ''.join(c for c in sequence if c.isalpha())
        sequence = sequence.strip().upper()
        
        if not sequence:
            raise ValueError("Empty sequence after cleaning")
            
        return sequence

    def search(self, sequence: str) -> str:
        """Run jackhmmer search and return merged alignments"""
        try:
            # Clean and validate sequence
            sequence = self._ensure_string_sequence(sequence)
            logger.debug(f"Searching with sequence: {sequence[:50]}...")
            
            raw_results = self.jackhmmer.search(sequence)
            
            # Extract and merge alignments
            alignments = []
            for db_name, results in raw_results.items():
                try:
                    merged = notebook_utils.merge_chunked_msa(
                        results=results,
                        max_hits=self.jackhmmer.max_hits[db_name]
                    )
                    if merged.sequences:
                        alignments.append(merged)
                except Exception as e:
                    logger.error(f"Error merging results for {db_name}: {e}")
                    continue
                    
            if not alignments:
                raise ValueError("No valid alignments found")
                
            return self._merge_alignments([a.to_string() for a in alignments])
            
        except Exception as e:
            logger.error(f"Error in HMMER search: {e}")
            raise
            
    def _merge_alignments(self, alignments: List[Any], sequence: str):
        """Merge multiple MSA alignments"""
        try:
            model_type_to_use = ModelType.MONOMER

            if not alignments:
                raise ValueError("No alignments to merge")
            
            
            single_chain_msas=alignments
        # _____________________________________________________________________________________________________                    
            full_single_chain_msa = []                                                                        #|
            for single_chain_msa in single_chain_msas:                                                        #|
                full_single_chain_msa.extend(single_chain_msa.sequences)                                      #|
                                                                                                              #|
                                                                                                              #|
            deduped_full_single_chain_msa = list(dict.fromkeys(full_single_chain_msa))                        #|
        # _____________________________________________________________________________________________________|
      
            logger.info(f"generating features...")
            
            feature_dict = {}
            features_for_chain = {}
            sequence_index = 1
            
            feature_dict.update(pipeline.make_sequence_features(
                sequence=sequence, description='query', num_res=len(sequence)))
            feature_dict.update(pipeline.make_msa_features(msas=single_chain_msas))
            feature_dict.update(notebook_utils.empty_placeholder_template_features(
                num_templates=0, num_res=len(sequence)))

            # Construct the all_seq features only for heteromers, not homomers.
            if model_type_to_use == ModelType.MULTIMER and len(set(sequences)) > 1:
                valid_feats = msa_pairing.MSA_FEATURES + (
                    'msa_species_identifiers',
                )
                all_seq_features = {
                    f'{k}_all_seq': v for k, v in pipeline.make_msa_features(single_chain_msas).items()
                    if k in valid_feats}
            
                feature_dict.update(all_seq_features)

            features_for_chain[protein.PDB_CHAIN_IDS[sequence_index - 1]] = feature_dict
            # Do further feature post-processing depending on the model type.

            if model_type_to_use == ModelType.MONOMER:
                np_example = features_for_chain[protein.PDB_CHAIN_IDS[0]]

            elif model_type_to_use == ModelType.MULTIMER:
                all_chain_features = {}
                for chain_id, chain_features in features_for_chain.items():
                    all_chain_features[chain_id] = pipeline_multimer.convert_monomer_features(
                        chain_features, chain_id)

                all_chain_features = pipeline_multimer.add_assembly_features(all_chain_features)

                np_example = feature_processing.pair_and_merge(
                    all_chain_features=all_chain_features)

                # Pad MSA to avoid zero-sized extra_msa.
                np_example = pipeline_multimer.pad_msa(np_example, min_num_seq=512)
            MSAss = []
            # Convert MSA objects to Stockholm format
            stockholm_strings = []
            for msa in alignments:
                # Extract sequences and descriptions
                sequences = msa.sequences
                descriptions = msa.descriptions
                MSAss.append(sequences)
                
                # Build Stockholm format string
                stockholm = "# STOCKHOLM 1.0\n"
                for seq, desc in zip(sequences, descriptions):
                    stockholm += f"{desc} {seq}\n"
                stockholm += "//\n"
                stockholm_strings.append(stockholm)
                
            # Merge all Stockholm strings
            return "\n".join(stockholm_strings), features_for_chain, feature_dict, deduped_full_single_chain_msa
            
        except Exception as e:
            logger.error(f"Error merging alignments: {e}")
            raise

    async def search_with_progress(self, sequence: str, progress_callback):
        """Run jackhmmer search with progress tracking"""
        query_paths = []
        alignments = []  # Initialize alignments list
        try:
            # Write sequence to FASTA file exactly as AlphaFold does
            fasta_path = f'target_01.fasta'
            with open(fasta_path, 'wt') as f:
                f.write(f'>query\n{sequence}')
            query_paths = [fasta_path]

            raw_results = {}
            
            for db_config in self.databases:
                db_name = db_config['db_name']
                total_chunks = db_config['num_streamed_chunks']
                
                logger.info(f"Starting search against {db_name} ({total_chunks} chunks)")

                runner = jackhmmer.Jackhmmer(
                    binary_path=self.jackhmmer.binary_path,  # Use jackhmmer's binary path
                    database_path=db_config['db_path'],
                    num_streamed_chunks=total_chunks,
                    z_value=db_config['z_value'],
                    get_tblout=True
                )
                
                def streaming_callback(chunk_idx):
                    progress_callback(db_name=db_name,
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
                    alignments.append(merged)


            # Merge all MSAs into Stockholm format
            return self._merge_alignments(alignments, sequence)
            
        except Exception as e:
            logger.error(f"Error in HMMER search: {e}")
            raise
        finally:
            for path in query_paths:
                try:
                    Path(path).unlink(missing_ok=True)
                except:
                    pass