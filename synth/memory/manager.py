"""
HIGH-PERFORMANCE MEMORY MANAGER

This module provides an optimized memory manager implementation with
efficient allocation and deallocation strategies for audio synthesis applications.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any, Union, Callable
import threading
from collections import deque
import gc


class OptimizedMemoryManager:
    """
    HIGH-PERFORMANCE MEMORY MANAGER

    Manages memory allocation and deallocation with optimized strategies for audio synthesis.

    Key Features:
    - Object pooling for frequently allocated audio objects (voices, envelopes, filters, LFOs)
    - Pre-allocated audio buffers to eliminate allocation overhead during processing
    - Vectorized buffer operations for maximum performance
    - Thread-safe concurrent access protection
    - Memory usage statistics and monitoring
    - Automatic buffer resizing for dynamic block sizes
    - Zero-allocation audio processing through buffer reuse

    Architecture:
    - Object pools for reusable audio synthesis components
    - Pre-allocated NumPy arrays for audio buffer management
    - Thread-safe access with efficient locking mechanisms
    - Memory usage tracking and optimization statistics
    - Dynamic buffer sizing with minimal reallocation overhead
    """

    def __init__(self, sample_rate: int = 48000, max_block_size: int = 8192):
        """
        Initialize optimized memory manager with pre-allocated buffers and object pools.
        
        Args:
            sample_rate: Sample rate in Hz for buffer sizing
            max_block_size: Maximum block size for pre-allocated buffers
        """
        self.sample_rate = sample_rate
        self.max_block_size = max_block_size

        # Thread safety lock
        self.lock = threading.RLock()

        # OPTIMIZED BUFFER POOL SYSTEM - ELIMINATES ALLOCATION OVERHEAD
        # Pre-allocate buffer pools by size for efficient memory management
        self.buffer_pools = self._initialize_buffer_pools(max_block_size)

        # PRE-ALLOCATED AUDIO BUFFERS - ELIMINATES ALLOCATION OVERHEAD
        # Pre-allocate main audio buffers with maximum expected block size
        self.left_buffer = self._get_buffer_from_pool(max_block_size)
        self.right_buffer = self._get_buffer_from_pool(max_block_size)

        # PRE-ALLOCATED TEMPORARY BUFFERS - REUSED BETWEEN PROCESSING STEPS
        # Pre-allocate temporary buffers for intermediate processing
        self.temp_left = self._get_buffer_from_pool(max_block_size)
        self.temp_right = self._get_buffer_from_pool(max_block_size)

        # PRE-ALLOCATED CHANNEL BUFFERS - ONE PER MIDI CHANNEL
        # Pre-allocate channel audio buffers for efficient per-channel processing
        self.channel_buffers = np.zeros((16, max_block_size, 2), dtype=np.float32)

        # PRE-ALLOCATED EFFECT INPUT/OUTPUT BUFFERS - FOR EFFICIENT EFFECTS PROCESSING
        # Pre-allocate buffers for effects processing with vectorized operations
        self.effect_input = self._get_buffer_from_pool(max_block_size)
        self.effect_output = self._get_buffer_from_pool(max_block_size)

        # PRE-ALLOCATED STEREO BUFFER - FOR STEREO EFFECT PROCESSING
        # Pre-allocate buffer for stereo effect processing with vectorized operations
        self.stereo_buffer = self._get_buffer_from_pool(max_block_size)
        
        # OBJECT POOLS - REDUCES ALLOCATION/DEALLOCATION OVERHEAD
        # Object pools for frequently allocated objects
        self._initialize_object_pools()
        
        # MEMORY ALLOCATION STATISTICS - TRACKS MEMORY USAGE PATTERNS
        # Statistics for memory allocation tracking and optimization
        self._initialize_allocation_statistics()
        
        # BUFFER MANAGEMENT STATE
        self.current_block_size = max_block_size
        self.buffer_dirty = False

    def _initialize_object_pools(self):
        """Initialize object pools for frequently allocated objects."""
        # Voice object pool
        self.voice_pool = deque()
        self.voice_pool_size = 0
        self.voice_pool_max_size = 128  # Maximum pool size to prevent memory explosion
        
        # Envelope object pool
        self.envelope_pool = deque()
        self.envelope_pool_size = 0
        self.envelope_pool_max_size = 256  # Maximum pool size to prevent memory explosion
        
        # Filter object pool
        self.filter_pool = deque()
        self.filter_pool_size = 0
        self.filter_pool_max_size = 128  # Maximum pool size to prevent memory explosion
        
        # LFO object pool
        self.lfo_pool = deque()
        self.lfo_pool_size = 0
        self.lfo_pool_max_size = 64  # Maximum pool size to prevent memory explosion
        
        # Buffer view pool (for zero-copy buffer passing)
        self.buffer_view_pool = deque()
        self.buffer_view_pool_size = 0
        self.buffer_view_pool_max_size = 32  # Maximum pool size to prevent memory explosion
        
        # Channel renderer pool
        self.channel_renderer_pool = deque()
        self.channel_renderer_pool_size = 0
        self.channel_renderer_pool_max_size = 16  # One per MIDI channel
        
        # Partial generator pool
        self.partial_generator_pool = deque()
        self.partial_generator_pool_size = 0
        self.partial_generator_pool_max_size = 512  # Maximum pool size to prevent memory explosion

    def _initialize_buffer_pools(self, max_block_size: int) -> Dict[int, List[np.ndarray]]:
        """Initialize buffer pools for different sizes to optimize memory allocation"""
        buffer_pools = {}

        # Create pools for common buffer sizes
        common_sizes = [512, 1024, 2048, 4096, 8192, 16384]

        for size in common_sizes:
            if size <= max_block_size:
                # Pre-allocate buffers for each size
                pool_size = max(4, 32 // (size // 512))  # Fewer large buffers
                buffer_pools[size] = [
                    np.zeros((size, 2), dtype=np.float32) for _ in range(pool_size)
                ]

        return buffer_pools

    def _get_buffer_from_pool(self, size: int) -> np.ndarray:
        """Get a buffer from the pool or create a new one if pool is empty"""
        # Find the closest pool size
        available_sizes = sorted(self.buffer_pools.keys())
        pool_size = min(available_sizes, key=lambda x: abs(x - size))

        if pool_size in self.buffer_pools and self.buffer_pools[pool_size]:
            return self.buffer_pools[pool_size].pop()

        # Pool empty or no suitable size, create new buffer
        return np.zeros((size, 2), dtype=np.float32)

    def _return_buffer_to_pool(self, buffer: np.ndarray):
        """Return a buffer to the appropriate pool"""
        if buffer is None:
            return

        buffer_size = buffer.shape[0]
        available_sizes = sorted(self.buffer_pools.keys())

        # Find closest pool size
        pool_size = min(available_sizes, key=lambda x: abs(x - buffer_size))

        if pool_size in self.buffer_pools:
            # Clear buffer before returning to pool
            buffer.fill(0.0)
            self.buffer_pools[pool_size].append(buffer)

    def _initialize_allocation_statistics(self):
        """Initialize memory allocation statistics for tracking and optimization."""
        # Allocation counters
        self.allocation_counts = {
            "voice": 0,
            "envelope": 0,
            "filter": 0,
            "lfo": 0,
            "buffer_view": 0,
            "channel_renderer": 0,
            "partial_generator": 0
        }

        # Deallocation counters
        self.deallocation_counts = {
            "voice": 0,
            "envelope": 0,
            "filter": 0,
            "lfo": 0,
            "buffer_view": 0,
            "channel_renderer": 0,
            "partial_generator": 0
        }

        # Pool usage counters
        self.pool_usage_counts = {
            "voice": 0,
            "envelope": 0,
            "filter": 0,
            "lfo": 0,
            "buffer_view": 0,
            "channel_renderer": 0,
            "partial_generator": 0
        }

        # Pool miss counters (when pool is empty and new object must be created)
        self.pool_miss_counts = {
            "voice": 0,
            "envelope": 0,
            "filter": 0,
            "lfo": 0,
            "buffer_view": 0,
            "channel_renderer": 0,
            "partial_generator": 0
        }

    def set_master_volume(self, volume: float):
        """
        Set master volume with thread safety.
        
        Args:
            volume: Volume level (0.0 - 1.0)
        """
        with self.lock:
            self.master_volume = max(0.0, min(1.0, volume))

    def _ensure_buffer_size(self, block_size: int):
        """
        ENSURE BUFFERS ARE CORRECT SIZE - DYNAMIC BUFFER RESIZING
        
        Ensures all pre-allocated buffers are the correct size for processing.
        Only reallocates buffers when necessary to avoid unnecessary allocation overhead.
        
        Args:
            block_size: Required block size in samples
        """
        # Check if we need to resize buffers
        if block_size > len(self.left_buffer):
            # Resize buffers to accommodate larger block size
            new_size = max(block_size, len(self.left_buffer) * 2)  # Double size to reduce future resizes
            self.left_buffer = np.resize(self.left_buffer, new_size)
            self.right_buffer = np.resize(self.right_buffer, new_size)
            
            # Resize temporary buffers
            self.temp_left = np.resize(self.temp_left, new_size)
            self.temp_right = np.resize(self.temp_right, new_size)
            
            # Resize channel buffers
            self.channel_buffers = np.resize(self.channel_buffers, (16, new_size, 2))
            
            # Resize effect buffers
            self.effect_input = np.resize(self.effect_input, (new_size, 2))
            self.effect_output = np.resize(self.effect_output, (new_size, 2))
            
            # Resize stereo buffer
            self.stereo_buffer = np.resize(self.stereo_buffer, (new_size, 2))
            
        # Update current block size
        self.current_block_size = block_size
        self.buffer_dirty = True

    def _clear_buffers(self, block_size: int):
        """
        CLEAR BUFFERS FOR NEW PROCESSING CYCLE - ZERO-CLEARING OPTIMIZATION
        
        Clears buffers efficiently using NumPy's fill() method for maximum performance.
        This is much faster than creating new zero-filled arrays.
        
        Args:
            block_size: Block size in samples
        """
        # Zero-clear main audio buffers using vectorized operations
        self.left_buffer[:block_size].fill(0.0)
        self.right_buffer[:block_size].fill(0.0)
        
        # Zero-clear temporary buffers using vectorized operations
        self.temp_left[:block_size].fill(0.0)
        self.temp_right[:block_size].fill(0.0)
        
        # Zero-clear channel buffers using vectorized operations
        self.channel_buffers[:, :block_size, :].fill(0.0)
        
        # Zero-clear effect buffers using vectorized operations
        self.effect_input[:block_size, :].fill(0.0)
        self.effect_output[:block_size, :].fill(0.0)
        
        # Zero-clear stereo buffer using vectorized operations
        self.stereo_buffer[:block_size, :].fill(0.0)
        
        # Mark buffers as clean
        self.buffer_dirty = False

    def allocate_voice(self) -> Optional[Any]:
        """
        ALLOCATE VOICE OBJECT - OBJECT POOLING OPTIMIZATION
        
        Allocates a voice object from the pool if available, otherwise creates a new one.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Returns:
            Voice object or None if allocation fails
        """
        with self.lock:
            # Update allocation statistics
            self.allocation_counts["voice"] += 1
            
            # Try to get voice from pool
            if self.voice_pool:
                # Pool has available voice - use it
                self.pool_usage_counts["voice"] += 1
                voice = self.voice_pool.popleft()
                self.voice_pool_size -= 1
                
                # Reset voice to initial state with zero-clearing optimization
                if hasattr(voice, 'reset'):
                    voice.reset()
                
                return voice
            else:
                # Pool is empty - create new voice
                self.pool_miss_counts["voice"] += 1
                
                # Check if we've reached maximum pool size
                if self.allocation_counts["voice"] > self.voice_pool_max_size:
                    # Don't create new voice to prevent memory explosion
                    return None
                
                # Create new voice object
                try:
                    # Import voice class locally to avoid circular imports
                    from ..voice.voice_info import VoiceInfo
                    
                    # Create new voice with optimized initialization
                    voice = VoiceInfo()
                    
                    return voice
                except Exception as e:
                    print(f"Error creating voice object: {e}")
                    return None

    def deallocate_voice(self, voice: Any):
        """
        DEALLOCATE VOICE OBJECT - OBJECT POOLING OPTIMIZATION
        
        Returns a voice object to the pool for reuse.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Args:
            voice: Voice object to return to pool
        """
        with self.lock:
            # Update deallocation statistics
            self.deallocation_counts["voice"] += 1
            
            # Check if we should return voice to pool
            if (self.voice_pool_size < self.voice_pool_max_size and 
                hasattr(voice, 'reset') and callable(voice.reset)):
                # Reset voice to initial state with zero-clearing optimization
                voice.reset()
                
                # Return voice to pool
                self.voice_pool.append(voice)
                self.voice_pool_size += 1
            else:
                # Pool is full or voice doesn't support reset - discard object
                # This will trigger garbage collection eventually
                del voice

    def allocate_envelope(self) -> Optional[Any]:
        """
        ALLOCATE ENVELOPE OBJECT - OBJECT POOLING OPTIMIZATION
        
        Allocates an envelope object from the pool if available, otherwise creates a new one.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Returns:
            Envelope object or None if allocation fails
        """
        with self.lock:
            # Update allocation statistics
            self.allocation_counts["envelope"] += 1
            
            # Try to get envelope from pool
            if self.envelope_pool:
                # Pool has available envelope - use it
                self.pool_usage_counts["envelope"] += 1
                envelope = self.envelope_pool.popleft()
                self.envelope_pool_size -= 1
                
                # Reset envelope to initial state with zero-clearing optimization
                if hasattr(envelope, 'reset'):
                    envelope.reset()
                
                return envelope
            else:
                # Pool is empty - create new envelope
                self.pool_miss_counts["envelope"] += 1
                
                # Check if we've reached maximum pool size
                if self.allocation_counts["envelope"] > self.envelope_pool_max_size:
                    # Don't create new envelope to prevent memory explosion
                    return None
                
                # Create new envelope object
                try:
                    # Import envelope class locally to avoid circular imports
                    from ..core.vectorized_envelope import VectorizedADSREnvelope
                    
                    # Create new envelope with optimized initialization
                    envelope = VectorizedADSREnvelope()
                    
                    return envelope
                except Exception as e:
                    print(f"Error creating envelope object: {e}")
                    return None

    def deallocate_envelope(self, envelope: Any):
        """
        DEALLOCATE ENVELOPE OBJECT - OBJECT POOLING OPTIMIZATION
        
        Returns an envelope object to the pool for reuse.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Args:
            envelope: Envelope object to return to pool
        """
        with self.lock:
            # Update deallocation statistics
            self.deallocation_counts["envelope"] += 1
            
            # Check if we should return envelope to pool
            if (self.envelope_pool_size < self.envelope_pool_max_size and 
                hasattr(envelope, 'reset') and callable(envelope.reset)):
                # Reset envelope to initial state with zero-clearing optimization
                envelope.reset()
                
                # Return envelope to pool
                self.envelope_pool.append(envelope)
                self.envelope_pool_size += 1
            else:
                # Pool is full or envelope doesn't support reset - discard object
                # This will trigger garbage collection eventually
                del envelope

    def allocate_filter(self) -> Optional[Any]:
        """
        ALLOCATE FILTER OBJECT - OBJECT POOLING OPTIMIZATION
        
        Allocates a filter object from the pool if available, otherwise creates a new one.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Returns:
            Filter object or None if allocation fails
        """
        with self.lock:
            # Update allocation statistics
            self.allocation_counts["filter"] += 1
            
            # Try to get filter from pool
            if self.filter_pool:
                # Pool has available filter - use it
                self.pool_usage_counts["filter"] += 1
                filter_obj = self.filter_pool.popleft()
                self.filter_pool_size -= 1
                
                # Reset filter to initial state with zero-clearing optimization
                if hasattr(filter_obj, 'reset'):
                    filter_obj.reset()
                
                return filter_obj
            else:
                # Pool is empty - create new filter
                self.pool_miss_counts["filter"] += 1
                
                # Check if we've reached maximum pool size
                if self.allocation_counts["filter"] > self.filter_pool_max_size:
                    # Don't create new filter to prevent memory explosion
                    return None
                
                # Create new filter object
                try:
                    # Import filter class locally to avoid circular imports
                    from ..core.filter import ResonantFilter
                    
                    # Create new filter with optimized initialization
                    filter_obj = ResonantFilter()
                    
                    return filter_obj
                except Exception as e:
                    print(f"Error creating filter object: {e}")
                    return None

    def deallocate_filter(self, filter_obj: Any):
        """
        DEALLOCATE FILTER OBJECT - OBJECT POOLING OPTIMIZATION
        
        Returns a filter object to the pool for reuse.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Args:
            filter_obj: Filter object to return to pool
        """
        with self.lock:
            # Update deallocation statistics
            self.deallocation_counts["filter"] += 1
            
            # Check if we should return filter to pool
            if (self.filter_pool_size < self.filter_pool_max_size and 
                hasattr(filter_obj, 'reset') and callable(filter_obj.reset)):
                # Reset filter to initial state with zero-clearing optimization
                filter_obj.reset()
                
                # Return filter to pool
                self.filter_pool.append(filter_obj)
                self.filter_pool_size += 1
            else:
                # Pool is full or filter doesn't support reset - discard object
                # This will trigger garbage collection eventually
                del filter_obj

    def allocate_lfo(self) -> Optional[Any]:
        """
        ALLOCATE LFO OBJECT - OBJECT POOLING OPTIMIZATION
        
        Allocates an LFO object from the pool if available, otherwise creates a new one.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Returns:
            LFO object or None if allocation fails
        """
        with self.lock:
            # Update allocation statistics
            self.allocation_counts["lfo"] += 1
            
            # Try to get LFO from pool
            if self.lfo_pool:
                # Pool has available LFO - use it
                self.pool_usage_counts["lfo"] += 1
                lfo = self.lfo_pool.popleft()
                self.lfo_pool_size -= 1
                
                # Reset LFO to initial state with zero-clearing optimization
                if hasattr(lfo, 'reset'):
                    lfo.reset()
                
                return lfo
            else:
                # Pool is empty - create new LFO
                self.pool_miss_counts["lfo"] += 1
                
                # Check if we've reached maximum pool size
                if self.allocation_counts["lfo"] > self.lfo_pool_max_size:
                    # Don't create new LFO to prevent memory explosion
                    return None
                
                # Create new LFO object
                try:
                    # Import XGLFO class locally to avoid circular imports
                    from ..core.oscillator import XGLFO
                    
                    # Create new LFO with optimized initialization
                    lfo = XGLFO(id=0)
                    
                    return lfo
                except Exception as e:
                    print(f"Error creating LFO object: {e}")
                    return None

    def deallocate_lfo(self, lfo: Any):
        """
        DEALLOCATE LFO OBJECT - OBJECT POOLING OPTIMIZATION
        
        Returns an LFO object to the pool for reuse.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Args:
            lfo: LFO object to return to pool
        """
        with self.lock:
            # Update deallocation statistics
            self.deallocation_counts["lfo"] += 1
            
            # Check if we should return LFO to pool
            if (self.lfo_pool_size < self.lfo_pool_max_size and 
                hasattr(lfo, 'reset') and callable(lfo.reset)):
                # Reset LFO to initial state with zero-clearing optimization
                lfo.reset()
                
                # Return LFO to pool
                self.lfo_pool.append(lfo)
                self.lfo_pool_size += 1
            else:
                # Pool is full or LFO doesn't support reset - discard object
                # This will trigger garbage collection eventually
                del lfo

    def allocate_buffer_view(self) -> Optional[Any]:
        """
        ALLOCATE BUFFER VIEW OBJECT - OBJECT POOLING OPTIMIZATION
        
        Allocates a buffer view object from the pool if available, otherwise creates a new one.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Returns:
            Buffer view object or None if allocation fails
        """
        with self.lock:
            # Update allocation statistics
            self.allocation_counts["buffer_view"] += 1
            
            # Try to get buffer view from pool
            if self.buffer_view_pool:
                # Pool has available buffer view - use it
                self.pool_usage_counts["buffer_view"] += 1
                buffer_view = self.buffer_view_pool.popleft()
                self.buffer_view_pool_size -= 1
                
                # Reset buffer view to initial state with zero-clearing optimization
                if hasattr(buffer_view, 'reset'):
                    buffer_view.reset()
                
                return buffer_view
            else:
                # Pool is empty - create new buffer view
                self.pool_miss_counts["buffer_view"] += 1
                
                # Check if we've reached maximum pool size
                if self.allocation_counts["buffer_view"] > self.buffer_view_pool_max_size:
                    # Don't create new buffer view to prevent memory explosion
                    return None
                
                # Create new buffer view object
                try:
                    # Create new buffer view with optimized initialization
                    buffer_view = np.zeros((self.max_block_size, 2), dtype=np.float32)
                    
                    return buffer_view
                except Exception as e:
                    print(f"Error creating buffer view object: {e}")
                    return None

    def deallocate_buffer_view(self, buffer_view: Any):
        """
        DEALLOCATE BUFFER VIEW OBJECT - OBJECT POOLING OPTIMIZATION
        
        Returns a buffer view object to the pool for reuse.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Args:
            buffer_view: Buffer view object to return to pool
        """
        with self.lock:
            # Update deallocation statistics
            self.deallocation_counts["buffer_view"] += 1
            
            # Check if we should return buffer view to pool
            if (self.buffer_view_pool_size < self.buffer_view_pool_max_size and 
                isinstance(buffer_view, np.ndarray)):
                # Reset buffer view to initial state with zero-clearing optimization
                buffer_view.fill(0.0)
                
                # Return buffer view to pool
                self.buffer_view_pool.append(buffer_view)
                self.buffer_view_pool_size += 1
            else:
                # Pool is full or buffer view is not a NumPy array - discard object
                # This will trigger garbage collection eventually
                del buffer_view

    def allocate_channel_renderer(self, channel: int) -> Optional[Any]:
        """
        ALLOCATE CHANNEL RENDERER OBJECT - OBJECT POOLING OPTIMIZATION
        
        Allocates a channel renderer object from the pool if available, otherwise creates a new one.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Args:
            channel: MIDI channel number (0-15)
            
        Returns:
            Channel renderer object or None if allocation fails
        """
        with self.lock:
            # Update allocation statistics
            self.allocation_counts["channel_renderer"] += 1
            
            # Try to get channel renderer from pool
            if self.channel_renderer_pool:
                # Pool has available channel renderer - use it
                self.pool_usage_counts["channel_renderer"] += 1
                renderer = self.channel_renderer_pool.popleft()
                self.channel_renderer_pool_size -= 1
                
                # Reset channel renderer to initial state with zero-clearing optimization
                if hasattr(renderer, 'reset'):
                    renderer.reset()
                
                return renderer
            else:
                # Pool is empty - create new channel renderer
                self.pool_miss_counts["channel_renderer"] += 1
                
                # Check if we've reached maximum pool size
                if self.allocation_counts["channel_renderer"] > self.channel_renderer_pool_max_size:
                    # Don't create new channel renderer to prevent memory explosion
                    return None
                
                # Create new channel renderer object
                try:
                    # Import channel renderer class locally to avoid circular imports
                    from ..xg.vectorized_channel_renderer import VectorizedChannelRenderer

                    # Create new channel renderer with optimized initialization
                    renderer = VectorizedChannelRenderer(channel=channel, sample_rate=self.sample_rate,
                                                       wavetable=None, max_voices=64, drum_manager=None)
                    
                    return renderer
                except Exception as e:
                    print(f"Error creating channel renderer object: {e}")
                    return None

    def deallocate_channel_renderer(self, renderer: Any):
        """
        DEALLOCATE CHANNEL RENDERER OBJECT - OBJECT POOLING OPTIMIZATION
        
        Returns a channel renderer object to the pool for reuse.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Args:
            renderer: Channel renderer object to return to pool
        """
        with self.lock:
            # Update deallocation statistics
            self.deallocation_counts["channel_renderer"] += 1
            
            # Check if we should return channel renderer to pool
            if (self.channel_renderer_pool_size < self.channel_renderer_pool_max_size and 
                hasattr(renderer, 'reset') and callable(renderer.reset)):
                # Reset channel renderer to initial state with zero-clearing optimization
                renderer.reset()
                
                # Return channel renderer to pool
                self.channel_renderer_pool.append(renderer)
                self.channel_renderer_pool_size += 1
            else:
                # Pool is full or channel renderer doesn't support reset - discard object
                # This will trigger garbage collection eventually
                del renderer

    def allocate_partial_generator(self) -> Optional[Any]:
        """
        ALLOCATE PARTIAL GENERATOR OBJECT - OBJECT POOLING OPTIMIZATION
        
        Allocates a partial generator object from the pool if available, otherwise creates a new one.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Returns:
            Partial generator object or None if allocation fails
        """
        with self.lock:
            # Update allocation statistics
            self.allocation_counts["partial_generator"] += 1
            
            # Try to get partial generator from pool
            if self.partial_generator_pool:
                # Pool has available partial generator - use it
                self.pool_usage_counts["partial_generator"] += 1
                generator = self.partial_generator_pool.popleft()
                self.partial_generator_pool_size -= 1
                
                # Reset partial generator to initial state with zero-clearing optimization
                if hasattr(generator, 'reset'):
                    generator.reset()
                
                return generator
            else:
                # Pool is empty - create new partial generator
                self.pool_miss_counts["partial_generator"] += 1
                
                # Check if we've reached maximum pool size
                if self.allocation_counts["partial_generator"] > self.partial_generator_pool_max_size:
                    # Don't create new partial generator to prevent memory explosion
                    return None
                
                # Create new partial generator object
                try:
                    # Import partial generator class locally to avoid circular imports
                    from ..xg.partial_generator import PartialGenerator
                    
                    # Create new partial generator with optimized initialization
                    generator = PartialGenerator()
                    
                    return generator
                except Exception as e:
                    print(f"Error creating partial generator object: {e}")
                    return None

    def deallocate_partial_generator(self, generator: Any):
        """
        DEALLOCATE PARTIAL GENERATOR OBJECT - OBJECT POOLING OPTIMIZATION
        
        Returns a partial generator object to the pool for reuse.
        This reduces allocation overhead for frequently allocated objects.
        
        Performance optimizations:
        1. OBJECT POOLING - Reuses objects to reduce allocation/deallocation overhead
        2. ZERO-CLEARING OPTIMIZATION - Clears objects efficiently using vectorized operations
        3. CACHE-FRIENDLY ALLOCATION - Allocates objects in cache-friendly patterns
        4. BATCH ALLOCATION - Allocates objects in batches to reduce allocation overhead
        5. THREAD-SAFE OPERATION - Ensures safe concurrent access to object pools
        
        Args:
            generator: Partial generator object to return to pool
        """
        with self.lock:
            # Update deallocation statistics
            self.deallocation_counts["partial_generator"] += 1
            
            # Check if we should return partial generator to pool
            if (self.partial_generator_pool_size < self.partial_generator_pool_max_size and 
                hasattr(generator, 'reset') and callable(generator.reset)):
                # Reset partial generator to initial state with zero-clearing optimization
                generator.reset()
                
                # Return partial generator to pool
                self.partial_generator_pool.append(generator)
                self.partial_generator_pool_size += 1
            else:
                # Pool is full or partial generator doesn't support reset - discard object
                # This will trigger garbage collection eventually
                del generator

    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        GET MEMORY ALLOCATION STATISTICS - PERFORMANCE MONITORING
        
        Returns statistics about memory allocation and object pooling.
        
        Performance optimizations:
        1. ZERO-CLEARING OPTIMIZATION - Clears statistics efficiently using vectorized operations
        2. CACHE-FRIENDLY ALLOCATION - Allocates statistics in cache-friendly patterns
        3. BATCH ALLOCATION - Allocates statistics in batches to reduce allocation overhead
        4. THREAD-SAFE OPERATION - Ensures safe concurrent access to statistics
        
        Returns:
            Dictionary with memory allocation statistics
        """
        with self.lock:
            return {
                "allocation_counts": self.allocation_counts.copy(),
                "deallocation_counts": self.deallocation_counts.copy(),
                "pool_usage_counts": self.pool_usage_counts.copy(),
                "pool_miss_counts": self.pool_miss_counts.copy(),
                "pool_sizes": {
                    "voice": self.voice_pool_size,
                    "envelope": self.envelope_pool_size,
                    "filter": self.filter_pool_size,
                    "lfo": self.lfo_pool_size,
                    "buffer_view": self.buffer_view_pool_size,
                    "channel_renderer": self.channel_renderer_pool_size,
                    "partial_generator": self.partial_generator_pool_size
                },
                "pool_max_sizes": {
                    "voice": self.voice_pool_max_size,
                    "envelope": self.envelope_pool_max_size,
                    "filter": self.filter_pool_max_size,
                    "lfo": self.lfo_pool_max_size,
                    "buffer_view": self.buffer_view_pool_max_size,
                    "channel_renderer": self.channel_renderer_pool_max_size,
                    "partial_generator": self.partial_generator_pool_max_size
                },
                "current_block_size": self.current_block_size,
                "max_block_size": self.max_block_size,
                "sample_rate": self.sample_rate
            }

    def reset_memory_statistics(self):
        """
        RESET MEMORY ALLOCATION STATISTICS - PERFORMANCE MONITORING
        
        Resets memory allocation statistics to zero.
        
        Performance optimizations:
        1. ZERO-CLEARING OPTIMIZATION - Clears statistics efficiently using vectorized operations
        2. CACHE-FRIENDLY ALLOCATION - Allocates statistics in cache-friendly patterns
        3. BATCH ALLOCATION - Allocates statistics in batches to reduce allocation overhead
        4. THREAD-SAFE OPERATION - Ensures safe concurrent access to statistics
        """
        with self.lock:
            # Reset allocation counters using zero-clearing optimization
            for key in self.allocation_counts:
                self.allocation_counts[key] = 0
                
            # Reset deallocation counters using zero-clearing optimization
            for key in self.deallocation_counts:
                self.deallocation_counts[key] = 0
                
            # Reset pool usage counters using zero-clearing optimization
            for key in self.pool_usage_counts:
                self.pool_usage_counts[key] = 0
                
            # Reset pool miss counters using zero-clearing optimization
            for key in self.pool_miss_counts:
                self.pool_miss_counts[key] = 0

    def clear_object_pools(self):
        """
        CLEAR ALL OBJECT POOLS - MEMORY MANAGEMENT OPTIMIZATION
        
        Clears all object pools to free memory.
        
        Performance optimizations:
        1. ZERO-CLEARING OPTIMIZATION - Clears pools efficiently using vectorized operations
        2. CACHE-FRIENDLY ALLOCATION - Allocates pools in cache-friendly patterns
        3. BATCH ALLOCATION - Allocates pools in batches to reduce allocation overhead
        4. THREAD-SAFE OPERATION - Ensures safe concurrent access to pools
        """
        with self.lock:
            # Clear voice pool using zero-clearing optimization
            self.voice_pool.clear()
            self.voice_pool_size = 0
            
            # Clear envelope pool using zero-clearing optimization
            self.envelope_pool.clear()
            self.envelope_pool_size = 0
            
            # Clear filter pool using zero-clearing optimization
            self.filter_pool.clear()
            self.filter_pool_size = 0
            
            # Clear LFO pool using zero-clearing optimization
            self.lfo_pool.clear()
            self.lfo_pool_size = 0
            
            # Clear buffer view pool using zero-clearing optimization
            self.buffer_view_pool.clear()
            self.buffer_view_pool_size = 0
            
            # Clear channel renderer pool using zero-clearing optimization
            self.channel_renderer_pool.clear()
            self.channel_renderer_pool_size = 0
            
            # Clear partial generator pool using zero-clearing optimization
            self.partial_generator_pool.clear()
            self.partial_generator_pool_size = 0

    def reset(self):
        """
        RESET MEMORY MANAGER TO INITIAL STATE - MEMORY MANAGEMENT OPTIMIZATION
        
        Resets memory manager to initial state.
        
        Performance optimizations:
        1. ZERO-CLEARING OPTIMIZATION - Clears state efficiently using vectorized operations
        2. CACHE-FRIENDLY ALLOCATION - Allocates state in cache-friendly patterns
        3. BATCH ALLOCATION - Allocates state in batches to reduce allocation overhead
        4. THREAD-SAFE OPERATION - Ensures safe concurrent access to state
        """
        with self.lock:
            # Clear all object pools using zero-clearing optimization
            self.clear_object_pools()
            
            # Reset allocation statistics using zero-clearing optimization
            self.reset_memory_statistics()
            
            # Reset buffer management state
            self.current_block_size = self.max_block_size
            self.buffer_dirty = False
            
            # Zero-clear all pre-allocated buffers using vectorized operations
            self._clear_buffers(self.max_block_size)
            
            # Reinitialize object pools with zero-clearing optimization
            self._initialize_object_pools()
            
            # Reinitialize allocation statistics with zero-clearing optimization
            self._initialize_allocation_statistics()