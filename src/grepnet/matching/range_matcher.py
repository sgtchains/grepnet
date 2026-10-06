"""
IP range matching.

Compares IP ranges against patterns using interval arithmetic.

Unlike CIDR networks, ranges can have true partial overlap.
"""

from typing import List, Tuple


class RangeMatcher:
    """
    Match IP ranges against search patterns.
    
    Ranges are stored as (start_int, end_int) tuples.
    Unlike CIDR networks, ranges can have partial overlap.
    """
    
    def __init__(self, file_ranges: List[Tuple[int, int]]):
        """
        Initialize matcher with file ranges.
        
        Args:
            file_ranges: List of (start_int, end_int) tuples from file
        """
        self.file_ranges = sorted(file_ranges, key=lambda r: r[0])
    
    def find_equal_matches(self, pattern_start: int, pattern_end: int) -> List[int]:
        """
        Find file ranges equal to pattern.
        
        Args:
            pattern_start: Start address (int)
            pattern_end: End address (int)
        
        Returns:
            List of indices into self.file_ranges
        """
        matches = []
        for idx, (start, end) in enumerate(self.file_ranges):
            if start == pattern_start and end == pattern_end:
                matches.append(idx)
        return matches
    
    def find_subset_matches(self, pattern_start: int, pattern_end: int) -> List[int]:
        """
        Find file ranges that are subsets of pattern.
        (file_range is subset ⟹ pattern contains file_range)
        
        Args:
            pattern_start: Start address
            pattern_end: End address
        
        Returns:
            List of indices
        """
        matches = []
        for idx, (start, end) in enumerate(self.file_ranges):
            # File range is subset if: start >= pattern_start AND end <= pattern_end
            if start >= pattern_start and end <= pattern_end:
                matches.append(idx)
        return matches
    
    def find_superset_matches(self, pattern_start: int, pattern_end: int) -> List[int]:
        """
        Find file ranges that are supersets of pattern.
        (file_range is superset ⟹ file_range contains pattern)
        
        Args:
            pattern_start: Start address
            pattern_end: End address
        
        Returns:
            List of indices
        """
        matches = []
        for idx, (start, end) in enumerate(self.file_ranges):
            # File range is superset if: start <= pattern_start AND end >= pattern_end
            if start <= pattern_start and end >= pattern_end:
                matches.append(idx)
        return matches
    
    def find_overlap_matches(self, pattern_start: int, pattern_end: int) -> List[int]:
        """
        Find file ranges that overlap with pattern.
        
        Overlap: Some addresses shared but neither is subset of other.
        
        Args:
            pattern_start: Start address
            pattern_end: End address
        
        Returns:
            List of indices
        """
        matches = []
        for idx, (start, end) in enumerate(self.file_ranges):
            # Check for overlap: ranges overlap if:
            # - start_a <= end_b AND end_a >= start_b
            if start <= pattern_end and end >= pattern_start:
                # Ranges overlap, but check if one is subset of other
                # (in which case it's not "overlap", it's subset/superset)
                is_file_subset = start >= pattern_start and end <= pattern_end
                is_file_superset = start <= pattern_start and end >= pattern_end
                
                if not is_file_subset and not is_file_superset:
                    # Partial overlap (not subset/superset)
                    matches.append(idx)
        
        return matches
