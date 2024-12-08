from typing import Tuple, Optional

class SequenceValidator:
    VALID_AA = set('ACDEFGHIKLMNPQRSTVWY')
    
    @classmethod
    def validate(cls, sequence: str) -> Tuple[bool, Optional[str]]:
        """Validate a protein sequence"""
        try:
            # Convert to string if needed
            if isinstance(sequence, (list, tuple)):
                sequence = ''.join(str(s) for s in sequence)
            
            # Basic checks
            if not sequence:
                return False, "Empty sequence"
                
            # Clean sequence
            sequence = ''.join(c for c in str(sequence) if c.isalpha()).upper()
            
            # Check for valid amino acids
            invalid_chars = set(sequence) - cls.VALID_AA
            if invalid_chars:
                return False, f"Invalid amino acids: {invalid_chars}"
                
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}" 