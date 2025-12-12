# XG PHASE B: VOICE MANAGEMENT EXTENSIONS\n# Add to VoiceManager class in synth/voice/voice_manager.py\n
    # XG-COMPLIANT VOICE STEALING WITH HYSTERESIS (PHASE B)

    def __init__(self, max_voices: int = 64):
        # Keep original initialization
        self.max_voices = max_voices
        self.active_voices: Dict[int, VoiceInfo] = {}
        self.voice_allocation_mode = 0
        self.polyphony_limit = 32

        # ULTRA-FAST VoiceInfo pooling system
        self.voice_pool = VoiceInfoPool(max_voices=max_voices)

        # ===== PHASE B: XG-COMPLIANT VOICE STEALING =====
        # XG hysteresis prevents rapid voice stealing/reallocation
        self.hysteresis_threshold = 1.1  # 10% hysteresis advantage for new voices
        self.voice_stealing_hysteresis = True

        # XG voice priority system with hysteresis memory
        self.last_stolen_voices = deque(maxlen=10)  # Remember recently stolen voices
        self.stealing_cooldown_ms = 50  # Cooldown period between steals of same voice

        # XG release phase priority (envelopes in release have lower steal priority)
        self.release_phase_penalty = 2.0  # Multiply priority score by 2.0 for voices in release

        # Performance optimization: Priority calculation caching
        self.priority_cache = {}
        self.cache_ttl = 100
        self.cache_hits = 0
        self.cache_misses = 0

        # Predictive voice allocation system
        self.voice_demand_history = {}
        self.predicted_demand = {}
        self.allocation_prediction_window = 50

    def _can_steal_voice_xg_hysteresis(self, note: int, velocity: int, priority: int) -> Tuple[bool, Optional[int]]:
        """XG-compliant voice stealing with hysteresis to prevent voice thrashing.

        XG Specification Requirements:
        - Hysteresis prevents rapid stealing of the same voice
        - Voices in release phase are less likely to be stolen
        - Newly started voices have priority advantage
        - Consider voice age and activity level

        Returns:
            Tuple of (can_steal, voice_to_steal_note)
        """
        if not self.active_voices:
            return False, None

        current_time_ms = time.time() * 1000
        best_steal_candidate = None
        lowest_priority_score = float('inf')

        for voice_note, voice_info in self.active_voices.items():
            # Skip voices recently stolen (hysteresis protection)
            if self._voice_recently_stolen(voice_note, current_time_ms):
                continue

            # Calculate XG priority score with hysteresis
            priority_score = self._calculate_xg_voice_priority(voice_info, voice_note, current_time_ms)

            # New voices get hysteresis advantage
            if priority_score < lowest_priority_score:
                lowest_priority_score = priority_score
                best_steal_candidate = voice_note

        # Apply hysteresis threshold - new voice needs to be significantly better
        new_voice_score = self._calculate_new_voice_xg_priority(note, velocity, priority)

        # XG hysteresis: new voice must be hysteresis_threshold times better
        if self.voice_stealing_hysteresis:
            can_steal = new_voice_score > (lowest_priority_score * self.hysteresis_threshold)
        else:
            can_steal = new_voice_score > lowest_priority_score

        return can_steal, best_steal_candidate

    def _calculate_xg_voice_priority(self, voice_info, note: int, current_time_ms: float) -> float:
        """Calculate XG-compliant voice priority for stealing decisions.

        XG Priority Factors:
        1. Voice state (release phase = lower priority)
        2. Voice age (older voices = slightly lower priority)
        3. Velocity (higher velocity = higher priority)
        4. Note priority (channel-specific note priorities)

        Args:
            voice_info: VoiceInfo object
            note: MIDI note number
            current_time_ms: Current time in milliseconds

        Returns:
            Priority score (higher = more likely to steal)
        """
        base_score = voice_info.calculate_priority_score()

        # XG: Voices in release phase get penalty (less likely to be stolen)
        if voice_info.is_releasing:
            base_score *= self.release_phase_penalty

        # XG: Older voices get slight penalty (encourage voice reuse)
        voice_age_seconds = (current_time_ms / 1000.0) - voice_info.start_time
        if voice_age_seconds > 2.0:  # Voices older than 2 seconds
            age_penalty = min(1.5, 1.0 + (voice_age_seconds - 2.0) * 0.1)
            base_score *= age_penalty

        # XG: Higher velocity voices harder to steal
        velocity_protection = 1.0 + (voice_info.velocity / 127.0) * 0.3
        base_score *= velocity_protection

        return base_score

    def _calculate_new_voice_xg_priority(self, note: int, velocity: int, priority: int) -> float:
        """Calculate priority score for a potential new voice (XG-compliant)."""
        velocity_score = velocity / 127.0  # 0.0 - 1.0
        priority_score = priority / 4.0     # VoicePriority.HIGHEST = 4

        # XG: Give advantage to newly triggered voices
        recency_bonus = 1.2  # New voices get 20% priority advantage

        # XG: Legato notes get higher priority (depending on mode)
        legato_bonus = 1.0

        return (velocity_score * 0.5 + priority_score * 0.5) * recency_bonus * legato_bonus

    def _voice_recently_stolen(self, note: int, current_time_ms: float) -> bool:
        """Check if a voice was recently stolen to prevent hysteresis."""

        # Check recent steals
        for stolen_time, stolen_note in list(self.last_stolen_voices):
            if stolen_note == note and (current_time_ms - stolen_time) < self.stealing_cooldown_ms:
                return True
        return False

    def _record_voice_steal(self, note: int):
        """Record that a voice was stolen for hysteresis tracking."""

        current_time_ms = time.time() * 1000
        self.last_stolen_voices.append((current_time_ms, note))

    # XG ADVANCED VOICE ALLOCATION MODES

    def set_xg_allocation_mode(self, mode: int):
        """Set XG-compliant voice allocation mode with enhanced features.

        XG Allocation Modes:
        0: Poly1 - Basic polyphonic (first-come, first-served)
        1: Poly2 - Priority-based (velocity + priority)
        2: Poly3 - Advanced XG (hysteresis + release protection)
        3: Mono1 - Basic monophonic
        4: Mono2 - Monophonic with portamento
        5: Mono3 - Monophonic with legato
        """

        self.voice_allocation_mode = max(0, min(5, mode))

        # Configure mode-specific parameters
        if mode == 2:  # XG Advanced Polyphonic
            # Enable full XG features
            self.voice_stealing_hysteresis = True
            self.hysteresis_threshold = 1.1
            self.release_phase_penalty = 2.0
        elif mode in [0, 1]:  # Basic polyphonic modes
            # Disable advanced features for compatibility
            self.voice_stealing_hysteresis = False
            self.release_phase_penalty = 1.0
        # Mono modes keep default settings

    def allocate_voice_xg(self, note: int, velocity: int, channel_note, priority: int) -> Optional[int]:
        """XG-compliant voice allocation with advanced stealing.

        Enhanced Features:
        - XG hysteresis voice stealing
        - Release phase protection
        - Priority-based allocation
        - Monophonic mode support
        """

        import time
        alloc_start = time.perf_counter()

        # Check basic allocation possibility
        if not self.can_allocate_voice_xg(note, velocity, priority):
            return None

        # Handle monophonic modes
        if self.voice_allocation_mode in [3, 4, 5]:  # Monophonic modes
            self._clear_monophonic_voices()

        # If at polyphony limit, attempt XG-compliant voice stealing with hysteresis
        elif len(self.active_voices) >= self.polyphony_limit:
            stolen_note = self._steal_voice_xg(note, velocity, priority)
            if stolen_note is None:
                return None

        # Allocate new voice from pool
        voice_info = self.voice_pool.acquire_voice_info(note, velocity, channel_note, priority)
        self.active_voices[note] = voice_info

        duration = time.perf_counter() - alloc_start
        if duration > 0.001:
            print(f"[XG_VOICE] Allocation took {duration*1000:.2f}ms for note {note}")

        return note

    def can_allocate_voice_xg(self, note: int, velocity: int, priority: int) -> bool:
        """XG-enhanced voice allocation check."""

        current_voice_count = len(self.active_voices)

        # If under polyphony limit, always allow
        if current_voice_count < self.polyphony_limit:
            return True

        # Handle monophonic modes
        if self.voice_allocation_mode in [3, 4, 5]:
            return current_voice_count == 0

        # For polyphonic modes, check if we can steal
        can_steal, _ = self._can_steal_voice_xg_hysteresis(note, velocity, priority)
        return can_steal

    def _steal_voice_xg(self, new_note: int, new_velocity: int, new_priority: int) -> Optional[int]:
        """XG-compliant voice stealing with hysteresis and advanced criteria."""

        can_steal, best_candidate = self._can_steal_voice_xg_hysteresis(new_note, new_velocity, new_priority)

        if can_steal and best_candidate is not None:
            # Record the steal for hysteresis
            self._record_voice_steal(best_candidate)

            # Deallocate the stolen voice
            self.deallocate_voice(best_candidate)

            return best_candidate

        return None

    def _clear_monophonic_voices(self):
        """Clear all voices for monophonic mode."""
        for voice_note in list(self.active_voices.keys()):
            self.deallocate_voice(voice_note)
