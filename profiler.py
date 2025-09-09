import cProfile
from synth.xg.channel_renderer import XGChannelRenderer
from synth.xg.channel_note import ChannelNote  # Added import for ChannelNote
from synth.voice.voice_manager import VoiceManager

def profile_generate_sample():
    # Create an XGChannelRenderer instance
    renderer = XGChannelRenderer(channel=0, sample_rate=44100)
    
    # Set up some active voices
    voice_manager = VoiceManager(8)
    renderer.voice_manager = voice_manager
    
    # Create proper mock ChannelNote that inherits from ChannelNote
    class MockChannelNote(ChannelNote):
        def __init__(self, note):
            # Required parameters for ChannelNote base class
            super().__init__(
                note=note,
                velocity=64,
                program=0,
                bank=0,
                wavetable=None,
                sample_rate=44100,
                is_drum=False
            )
            self._active = True  # Track active state
            
        def is_active(self) -> bool:
            return self._active
            
        def generate_sample(self, mod_wheel=0, breath_controller=0, foot_controller=0, 
                           brightness=64, harmonic_content=64, channel_pressure_value=0,
                           key_pressure=0, volume=100, expression=127, global_pitch_mod=0.0):
            return (0.1, 0.2)
    
    # Set up active notes with proper types
    renderer.active_notes = {
        60: MockChannelNote(60),
        62: MockChannelNote(62),
        64: MockChannelNote(64)
    }

    # Pre-warm the renderer
    for _ in range(100):
        renderer.generate_sample()
    
    # Profiling run
    pr = cProfile.Profile()
    pr.enable()
    
    for _ in range(10000):
        renderer.generate_sample()
    
    pr.disable()
    pr.print_stats(sort='time')

if __name__ == '__main__':
    profile_generate_sample()
