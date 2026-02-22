"""
FM Region - Frequency Modulation region with per-note parameter scaling.

Part of the unified region-based synthesis architecture.
FMRegion implements algorithmic FM synthesis with:
- Per-note key scaling
- Per-note velocity scaling
- FM operator configuration
- Algorithm selection
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import logging

from ..engine.region_descriptor import RegionDescriptor
from ..partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class FMRegion(IRegion):
    """
    FM region with per-note parameter scaling.
    
    Algorithmic synthesis - no sample loading needed.
    Parameters are scaled based on note and velocity.
    
    Attributes:
        descriptor: Region metadata with FM algorithm parameters
        sample_rate: Audio sample rate
    """
    
    __slots__ = [
        '_algorithm', '_operators', '_lfo', '_feedback',
        '_note_scaling', '_velocity_scaling', '_output_level'
    ]
    
    def __init__(
        self, 
        descriptor: RegionDescriptor, 
        sample_rate: int = 44100
    ):
        """
        Initialize FM region.
        
        Args:
            descriptor: Region metadata with FM algorithm parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(descriptor, sample_rate)
        
        # FM-specific parameters from descriptor
        algo_params = descriptor.algorithm_params or {}
        
        self._algorithm = algo_params.get('algorithm', 1)
        self._operators = algo_params.get('operators', [])
        self._lfo = algo_params.get('lfo', {})
        self._feedback = algo_params.get('feedback', 0)
        
        # Scaling parameters
        self._note_scaling = algo_params.get('note_scaling', {})
        self._velocity_scaling = algo_params.get('velocity_scaling', {})
        self._output_level = algo_params.get('output_level', 1.0)
    
    def _load_sample_data(self) -> Optional[np.ndarray]:
        """No sample data for FM (algorithmic synthesis)."""
        return None
    
    def _create_partial(self) -> Optional[Any]:
        """
        Create FM partial with scaled parameters.
        
        Returns:
            FMPartial instance or None if creation failed
        """
        try:
            # Apply key and velocity scaling to operator parameters
            scaled_params = self._build_scaled_params()
            
            # Import FM partial
            from ..partial.fm_partial import FMPartial
            
            # Create FM partial
            partial = FMPartial(scaled_params, self.sample_rate)
            return partial
            
        except Exception as e:
            logger.error(f"Failed to create FM partial: {e}")
            return None
    
    def _build_scaled_params(self) -> Dict[str, Any]:
        """
        Build FM parameters with note and velocity scaling.
        
        Returns:
            Dictionary of scaled FM parameters
        """
        # Start with base algorithm parameters
        params = {
            'algorithm': self._algorithm,
            'feedback': self._feedback,
            'lfo': self._lfo.copy() if self._lfo else {},
            'output_level': self._output_level,
        }
        
        # Scale operators based on note and velocity
        scaled_operators = []
        for op in self._operators:
            scaled_op = op.copy()
            
            # Apply key scaling
            if self._note_scaling:
                scaled_op = self._apply_key_scaling(scaled_op)
            
            # Apply velocity scaling
            if self._velocity_scaling:
                scaled_op = self._apply_velocity_scaling(scaled_op)
            
            scaled_operators.append(scaled_op)
        
        params['operators'] = scaled_operators
        
        # Add current note and velocity
        params['note'] = self.current_note
        params['velocity'] = self.current_velocity
        
        return params
    
    def _apply_key_scaling(self, operator: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply key scaling to operator parameters.
        
        Args:
            operator: Operator parameters
        
        Returns:
            Scaled operator parameters
        """
        if not self._note_scaling:
            return operator
        
        # Get scaling parameters for this operator
        op_key_scaling = self._note_scaling.get(
            f'op{operator.get("id", 0)}', 
            self._note_scaling.get('all', {})
        )
        
        # Apply key scaling depth
        key_scaling_depth = op_key_scaling.get('depth', 0)
        if key_scaling_depth != 0:
            # Calculate scaling factor based on note position
            key_center = op_key_scaling.get('center', 60)  # C4 default
            key_offset = self.current_note - key_center
            
            # Scale amplitude based on key position
            scale_factor = 1.0 + (key_offset / 127.0) * (key_scaling_depth / 7.0)
            
            if 'amplitude' in operator:
                operator['amplitude'] = operator.get('amplitude', 1.0) * scale_factor
        
        # Apply key scaling rate
        key_scaling_rate = op_key_scaling.get('rate', 0)
        if key_scaling_rate != 0:
            # Adjust envelope rates based on key position
            for rate_key in ['attack_rate', 'decay_rate', 'release_rate']:
                if rate_key in operator:
                    rate_factor = 1.0 + (key_scaling_rate / 7.0) * 0.5
                    operator[rate_key] = operator.get(rate_key, 0.5) * rate_factor
        
        return operator
    
    def _apply_velocity_scaling(self, operator: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply velocity scaling to operator parameters.
        
        Args:
            operator: Operator parameters
        
        Returns:
            Scaled operator parameters
        """
        if not self._velocity_scaling:
            return operator
        
        # Get scaling parameters for this operator
        op_vel_scaling = self._velocity_scaling.get(
            f'op{operator.get("id", 0)}',
            self._velocity_scaling.get('all', {})
        )
        
        # Apply velocity sensitivity
        velocity_sensitivity = op_vel_scaling.get('sensitivity', 0)
        if velocity_sensitivity != 0:
            # Scale amplitude based on velocity
            # velocity_sensitivity: 0-7, where 7 = full scaling
            vel_factor = (self.current_velocity / 127.0) ** (velocity_sensitivity / 7.0)
            
            if 'amplitude' in operator:
                operator['amplitude'] = operator.get('amplitude', 1.0) * vel_factor
        
        # Apply velocity to envelope
        vel_to_envelope = op_vel_scaling.get('to_envelope', 0)
        if vel_to_envelope != 0:
            # Scale envelope rates based on velocity
            vel_rate_factor = 1.0 - (vel_to_envelope / 7.0) * (1.0 - self.current_velocity / 127.0)
            
            for rate_key in ['attack_rate', 'decay_rate']:
                if rate_key in operator:
                    operator[rate_key] = operator.get(rate_key, 0.5) * vel_rate_factor
        
        return operator
    
    def _init_envelopes(self) -> None:
        """Initialize operator envelopes from generator parameters."""
        # FM operators have their own envelopes built into the partial
        # No separate envelope initialization needed here
        pass
    
    def _init_filters(self) -> None:
        """Initialize filters from generator parameters."""
        try:
            from ..core.filter import UltraFastResonantFilter
            
            # Get filter parameters from descriptor
            cutoff = self._get_generator_param('filter_cutoff', 20000.0)
            resonance = self._get_generator_param('filter_resonance', 0.0)
            filter_type = self._get_generator_param('filter_type', 'lowpass')
            
            # Apply velocity to filter cutoff (common FM technique)
            vel_to_filter = self._get_generator_param('vel_to_filter', 0.0)
            if vel_to_filter != 0:
                cutoff *= (1.0 + vel_to_filter * (self.current_velocity / 127.0))
            
            filter_obj = UltraFastResonantFilter(
                cutoff=cutoff,
                resonance=resonance,
                filter_type=filter_type,
                sample_rate=self.sample_rate
            )
            self._filters['filter'] = filter_obj
            
        except Exception as e:
            logger.error(f"Failed to initialize FM filter: {e}")
    
    def generate_samples(
        self, 
        block_size: int, 
        modulation: Dict[str, float]
    ) -> np.ndarray:
        """
        Generate samples from FM partial.
        
        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values
        
        Returns:
            Stereo audio buffer (block_size * 2,) as float32
        """
        if not self._partial:
            return np.zeros(block_size * 2, dtype=np.float32)
        
        try:
            # Generate samples from FM partial
            samples = self._partial.generate_samples(block_size, modulation)
            
            # Apply filter if present
            if 'filter' in self._filters:
                filter_obj = self._filters['filter']
                if hasattr(filter_obj, 'process_block'):
                    try:
                        filtered = filter_obj.process_block(samples)
                        if filtered is not None:
                            samples = filtered
                    except Exception as e:
                        logger.error(f"FM filter processing failed: {e}")
            
            return samples
            
        except Exception as e:
            logger.error(f"FM sample generation failed: {e}")
            return np.zeros(block_size * 2, dtype=np.float32)
    
    def is_active(self) -> bool:
        """Check if FM region is still producing sound."""
        if self.state == RegionState.RELEASED:
            return False
        
        if self._partial:
            return self._partial.is_active()
        
        return self.state in (RegionState.ACTIVE, RegionState.INITIALIZED)
    
    def get_region_info(self) -> Dict[str, Any]:
        """Get region information."""
        info = super().get_region_info()
        info.update({
            'algorithm': self._algorithm,
            'operator_count': len(self._operators),
            'feedback': self._feedback,
            'current_note': self.current_note,
            'current_velocity': self.current_velocity
        })
        return info
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"FMRegion(id={self.descriptor.region_id}, "
            f"algo={self._algorithm}, ops={len(self._operators)})"
        )
