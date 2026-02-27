"""
Sample Editor - Basic Sample Editing Capabilities

Provides basic sample editing functionality for the XG synthesizer.
"""
from __future__ import annotations

class SampleEditor:
    """
    Basic sample editor for fundamental editing operations.
    """

    def __init__(self):
        """Initialize sample editor."""
        self.current_sample = None
        self.edit_history = []

    def load_sample(self, sample_data, sample_rate):
        """
        Load a sample for editing.

        Args:
            sample_data: Audio data array
            sample_rate: Sample rate in Hz

        Returns:
            Success status
        """
        self.current_sample = {
            'data': sample_data,
            'sample_rate': sample_rate,
            'original_length': len(sample_data)
        }
        return True

    def trim_sample(self, start_sample, end_sample):
        """
        Trim sample to specified range.

        Args:
            start_sample: Start sample index
            end_sample: End sample index

        Returns:
            Trimmed sample data
        """
        if self.current_sample:
            data = self.current_sample['data']
            return data[start_sample:end_sample]
        return None

    def normalize_sample(self, target_level=1.0):
        """
        Normalize sample to target level.

        Args:
            target_level: Target peak level (0.0-1.0)

        Returns:
            Normalized sample data
        """
        if self.current_sample:
            data = self.current_sample['data']
            max_val = abs(data).max()
            if max_val > 0:
                return data * (target_level / max_val)
        return self.current_sample['data'] if self.current_sample else None

    def reverse_sample(self):
        """
        Reverse the sample.

        Returns:
            Reversed sample data
        """
        if self.current_sample:
            return self.current_sample['data'][::-1]
        return None

    def get_sample_info(self):
        """Get information about current sample."""
        if self.current_sample:
            return {
                'length_samples': len(self.current_sample['data']),
                'sample_rate': self.current_sample['sample_rate'],
                'duration_seconds': len(self.current_sample['data']) / self.current_sample['sample_rate']
            }
        return None
