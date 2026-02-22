"""
AN Region - Production-grade analog physical modeling region.

Part of the unified region-based synthesis architecture.
ANRegion implements analog physical modeling with:
- RP-PR (Resonant Peak - Physical Resonance) synthesis
- String/pipe/membrane models
- Real-time parameter control
- Jupiter-X AN engine integration
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import logging

from ..engine.region_descriptor import RegionDescriptor
from ..partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class ANRegion(IRegion):
    """
    Production-grade AN (Analog) physical modeling region.
    
    Features:
    - RP-PR (Resonant Peak - Physical Resonance) synthesis
    - Multiple physical models (string, pipe, membrane, bar)
    - Real-time resonator parameter control
    - Exciter modeling (pluck, strike, bow, blow)
    - Coupling between resonators
    - Material and body size control
    
    Attributes:
        descriptor: Region metadata with AN parameters
        sample_rate: Audio sample rate
    """
    
    __slots__ = [
        '_model_type', '_resonator_params', '_exciter_params',
        '_coupling_params', '_an_model', '_material', '_body_size'
    ]
    
    MODEL_TYPES = ['string', 'pipe', 'membrane', 'bar', 'plate', 'tube']
    EXCITER_TYPES = ['pluck', 'strike', 'bow', 'blow', 'noise']
    
    def __init__(
        self, 
        descriptor: RegionDescriptor, 
        sample_rate: int = 44100
    ):
        """
        Initialize AN region.
        
        Args:
            descriptor: Region metadata with AN parameters
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(descriptor, sample_rate)
        
        # Get parameters from descriptor
        algo_params = descriptor.algorithm_params or {}
        
        # Model parameters
        self._model_type = algo_params.get('model_type', 'string')
        self._material = algo_params.get('material', 'steel')
        self._body_size = algo_params.get('body_size', 0.5)
        
        # Resonator parameters
        self._resonator_params = {
            'tension': algo_params.get('tension', 0.5),
            'damping': algo_params.get('damping', 0.5),
            'brightness': algo_params.get('brightness', 0.5),
            'decay': algo_params.get('decay', 0.7)
        }
        
        # Exciter parameters
        self._exciter_params = {
            'type': algo_params.get('exciter_type', 'pluck'),
            'strength': algo_params.get('exciter_strength', 0.5),
            'position': algo_params.get('exciter_position', 0.25)
        }
        
        # Coupling parameters (for multi-resonator models)
        self._coupling_params = {
            'enabled': algo_params.get('coupling_enabled', False),
            'strength': algo_params.get('coupling_strength', 0.3)
        }
        
        # Runtime state
        self._an_model: Optional[Any] = None
    
    def _load_sample_data(self) -> Optional[np.ndarray]:
        """No sample data for AN (algorithmic synthesis)."""
        return None
    
    def _create_partial(self) -> Optional[Any]:
        """
        Create AN physical modeling partial.
        
        Returns:
            ANPartial instance or None if creation failed
        """
        try:
            # Create AN model
            self._an_model = self._create_an_model()
            
            if self._an_model is None:
                logger.warning("Failed to create AN model")
                return None
            
            # Set model type
            self._an_model.set_model_type(self._model_type)
            
            # Configure resonator
            self._an_model.set_resonator_parameters({
                'frequency': self._calculate_frequency(),
                'tension': self._resonator_params['tension'],
                'damping': self._resonator_params['damping'],
                'brightness': self._resonator_params['brightness'],
                'decay': self._resonator_params['decay'],
                'body_size': self._body_size,
                'material': self._material
            })
            
            # Configure exciter
            self._an_model.set_exciter_parameters(self._exciter_params)
            
            # Configure coupling if enabled
            if self._coupling_params['enabled']:
                self._an_model.set_coupling_parameters(self._coupling_params)
            
            # Build partial parameters
            partial_params = {
                'an_model': self._an_model,
                'model_type': self._model_type,
                'exciter_type': self._exciter_params['type'],
                'note': self.current_note,
                'velocity': self.current_velocity
            }
            
            # Import and create AN partial
            from ..partial.an_partial import ANPartial
            partial = ANPartial(partial_params, self.sample_rate)
            
            return partial
            
        except Exception as e:
            logger.error(f"Failed to create AN partial: {e}")
            return None
    
    def _create_an_model(self) -> Optional[Any]:
        """
        Create AN physical model instance.
        
        Returns:
            ANPhysicalModel instance or None
        """
        try:
            # Try to import Jupiter-X AN engine
            from ..jupiter_x.an_engine import ANPhysicalModel
            
            model = ANPhysicalModel(self.sample_rate)
            return model
            
        except ImportError:
            logger.warning("Jupiter-X AN engine not available, using fallback")
            # Fallback to basic physical model
            from ..core.waveguide import DigitalWaveguide
            
            waveguide = DigitalWaveguide(self.sample_rate)
            return waveguide
            
        except Exception as e:
            logger.error(f"Failed to create AN model: {e}")
            return None
    
    def _calculate_frequency(self) -> float:
        """
        Calculate frequency for current note.
        
        Returns:
            Frequency in Hz
        """
        # MIDI note to frequency
        frequency = 440.0 * (2.0 ** ((self.current_note - 69) / 12.0))
        
        # Apply fine tuning
        fine_tune = self.descriptor.generator_params.get('fine_tune', 0.0)
        frequency *= 2.0 ** (fine_tune / 1200.0)
        
        return frequency
    
    def _init_envelopes(self) -> None:
        """Initialize envelopes (handled by AN model)."""
        pass
    
    def _init_filters(self) -> None:
        """Initialize filters for AN region."""
        try:
            from ..core.filter import UltraFastResonantFilter
            
            # Get filter parameters
            cutoff = self.descriptor.generator_params.get('filter_cutoff', 20000.0)
            resonance = self.descriptor.generator_params.get('filter_resonance', 0.0)
            
            self._filters['filter'] = UltraFastResonantFilter(
                cutoff=cutoff,
                resonance=resonance,
                filter_type='lowpass',
                sample_rate=self.sample_rate
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize filter: {e}")
    
    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this AN region.
        
        Args:
            velocity: MIDI velocity
            note: MIDI note number
        
        Returns:
            True if region should play
        """
        if not super().note_on(velocity, note):
            return False
        
        # Excite the AN model
        if self._an_model:
            # Velocity affects exciter strength
            exciter_strength = velocity / 127.0
            if hasattr(self._an_model, 'excite'):
                self._an_model.excite(exciter_strength)
            elif hasattr(self._an_model, 'set_exciter_parameters'):
                self._exciter_params['strength'] = exciter_strength
                self._an_model.set_exciter_parameters(self._exciter_params)
        
        return True
    
    def generate_samples(
        self, 
        block_size: int, 
        modulation: Dict[str, float]
    ) -> np.ndarray:
        """
        Generate samples from AN model.
        
        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values
        
        Returns:
            Stereo audio buffer (block_size * 2,) as float32
        """
        if not self._partial:
            return np.zeros(block_size * 2, dtype=np.float32)
        
        try:
            # Apply modulation
            self._apply_modulation(modulation)
            
            # Generate samples from partial
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
                        logger.error(f"AN filter processing failed: {e}")
            
            return samples
            
        except Exception as e:
            logger.error(f"AN sample generation failed: {e}")
            return np.zeros(block_size * 2, dtype=np.float32)
    
    def _apply_modulation(self, modulation: Dict[str, float]) -> None:
        """
        Apply modulation to AN parameters.
        
        Args:
            modulation: Modulation values dictionary
        """
        if not self._an_model:
            return
        
        # Mod wheel to brightness
        mod_wheel = modulation.get('mod_wheel', 0.0)
        if mod_wheel > 0 and hasattr(self._an_model, 'set_brightness'):
            brightness = self._resonator_params['brightness'] * (1.0 + mod_wheel)
            self._an_model.set_brightness(min(1.0, brightness))
        
        # Aftertouch to tension
        aftertouch = modulation.get('channel_aftertouch', 0.0)
        if aftertouch > 0 and hasattr(self._an_model, 'set_tension'):
            tension = self._resonator_params['tension'] * (1.0 + aftertouch * 0.5)
            self._an_model.set_tension(min(1.0, tension))
    
    def update_modulation(self, modulation: Dict[str, float]) -> None:
        """
        Update modulation state.
        
        Args:
            modulation: Modulation parameter updates
        """
        super().update_modulation(modulation)
        self._apply_modulation(modulation)
    
    def is_active(self) -> bool:
        """Check if AN region is still producing sound."""
        if self.state == RegionState.RELEASED:
            return False
        
        # Check if model still has energy
        if self._an_model and hasattr(self._an_model, 'is_active'):
            return self._an_model.is_active()
        
        if self._partial:
            return self._partial.is_active()
        
        return self.state in (RegionState.ACTIVE, RegionState.INITIALIZED)
    
    def get_region_info(self) -> Dict[str, Any]:
        """Get region information."""
        info = super().get_region_info()
        info.update({
            'model_type': self._model_type,
            'material': self._material,
            'body_size': self._body_size,
            'exciter_type': self._exciter_params['type'],
            'tension': self._resonator_params['tension'],
            'damping': self._resonator_params['damping']
        })
        return info
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"ANRegion(model={self._model_type}, "
            f"material={self._material}, exciter={self._exciter_params['type']})"
        )
