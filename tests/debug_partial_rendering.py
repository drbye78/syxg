"""
Enhanced debug partial generator audio rendering with test SF2 sine wave.
Generates 5-second audio for multiple notes and saves to WAV files.
"""
from __future__ import annotations

import sys
import os
import numpy as np
import argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from synth.engines.optimized_xg_synthesizer import OptimizedXGSynthesizer
from synth.io.midi import MIDIMessage
import scipy.io.wavfile


def detect_pitch_autocorr(audio, sample_rate, min_freq=50, max_freq=2000):
    """Detect fundamental frequency using autocorrelation."""
    # Normalize audio
    audio = audio - np.mean(audio)
    if np.max(np.abs(audio)) == 0:
        return 0.0
    audio = audio / np.max(np.abs(audio))

    # Compute autocorrelation
    corr = np.correlate(audio, audio, mode="full")
    corr = corr[len(corr) // 2 :]

    # Find the first significant peak
    min_period = int(sample_rate / max_freq)
    max_period = int(sample_rate / min_freq)

    # Look for the maximum in the valid range
    valid_corr = corr[min_period : max_period + 1]
    if len(valid_corr) == 0:
        return 0.0

    peak_idx = np.argmax(valid_corr)
    period = min_period + peak_idx

    if corr[period] > 0.1:  # Minimum correlation threshold
        return sample_rate / period
    return 0.0



def generate_note_audio(synthesizer: OptimizedXGSynthesizer, note, channel=0, bank_msb=0, bank_lsb=0, program=0, duration_seconds=5.0):
    """Generate audio for a specific note."""
    sample_rate = 44100
    block_size = 1024
    total_samples = int(duration_seconds * sample_rate)
    blocks_needed = int(np.ceil(total_samples / block_size))

    from synth.io.midi.constants import MSG_TYPE_NOTE_ON, MSG_TYPE_NOTE_OFF, MSG_TYPE_CONTROL_CHANGE, MSG_TYPE_PROGRAM_CHANGE

    # Send bank/program change and note events
    events = [
        MIDIMessage(time=0.0, type="control_change", channel=channel, controller=0, value=bank_msb),
        MIDIMessage(time=0.0, type="control_change", channel=channel, controller=32, value=bank_lsb),
        MIDIMessage(time=0.0, type="program_change", channel=channel, program=program),
        MIDIMessage(
            time=0.0,
            type=MSG_TYPE_NOTE_ON,
            channel=channel,
            note=note,
            velocity=127,
        ),
        MIDIMessage(
            time=3.0,
            type=MSG_TYPE_NOTE_OFF,
            channel=channel,
            note=note,
            velocity=127,
        ),
    ]

    # Reset message queue and effects state to prevent accumulation between tests
    synthesizer.reset()
    synthesizer.send_midi_message_block(events)

    # Generate audio - CRITICAL FIX: Copy blocks immediately to avoid buffer reuse
    audio_blocks = []
    for i in range(blocks_needed):
        block = synthesizer.generate_audio_block()
        block_copy = block.copy()  # Copy immediately to avoid buffer reuse!
        audio_blocks.append(block_copy)
        
        # Debug: check each block for stereo issues
        block_rms_left = np.sqrt(np.mean(block_copy[:, 0]**2))
        block_rms_right = np.sqrt(np.mean(block_copy[:, 1]**2))
        print(f"Block {i}: Left RMS = {block_rms_left:.6f}, Right RMS = {block_rms_right:.6f}")
        
        # Check if right channel is all zeros
        if np.all(block_copy[:, 1] == 0):
            print(f"WARNING: Block {i} has all-zero right channel!")

    # Concatenate blocks
    audio_data = np.concatenate(audio_blocks, axis=0)

    # Debug stereo issue
    last_10_blocks = audio_blocks[-10:]
    for i, block in enumerate(last_10_blocks):
        right_rms = np.sqrt(np.mean(block[:, 1]**2))
        if right_rms == 0:
            print(f"Note {note}: Last blocks: Block {len(audio_blocks) - 10 + i} right RMS = 0")

    # Debug: check if there's audio
    mono_debug = (audio_data[:, 0] + audio_data[:, 1]) * 0.5
    rms_debug = np.sqrt(np.mean(mono_debug**2))
    print(f"Debug: generated audio RMS = {rms_debug:.4f}")
    
    # Debug: check stereo balance
    left_rms = np.sqrt(np.mean(audio_data[:, 0]**2))
    right_rms = np.sqrt(np.mean(audio_data[:, 1]**2))
    print(f"Final audio: Left RMS = {left_rms:.6f}, Right RMS = {right_rms:.6f}")
    
    # Check if right channel is all zeros
    if np.all(audio_data[:, 1] == 0):
        print("ERROR: Final audio has all-zero right channel!")

    return audio_data


def analyze_audio_quality(audio_data, sample_rate, expected_freq, note):
    """Analyze pitch, volume, and quality of audio."""
    # Convert to mono
    mono_audio = (audio_data[:, 0] + audio_data[:, 1]) * 0.5

    # Use steady state during actual note playback (skip attack, avoid release/silence)
    # Note plays from 0-3s, so analyze 0.5-2.5s (well within the note)
    steady_start = int(0.5 * sample_rate)
    steady_end = int(2.5 * sample_rate)
    steady_audio = mono_audio[steady_start:steady_end]

    if len(steady_audio) < sample_rate:  # At least 1 second
        return None

    # Detect pitch using multiple methods
    detected_freq_autocorr = detect_pitch_autocorr(steady_audio, sample_rate)

    # Also try FFT peak detection
    fft = np.fft.fft(steady_audio)
    freqs = np.fft.fftfreq(len(steady_audio), 1 / sample_rate)
    pos_freqs = freqs[: len(freqs) // 2]
    pos_fft = np.abs(fft[: len(fft) // 2])

    # Find peak in expected frequency range
    freq_range = (expected_freq * 0.8, expected_freq * 1.2)
    mask = (pos_freqs >= freq_range[0]) & (pos_freqs <= freq_range[1])
    if np.any(mask):
        peak_idx = np.argmax(pos_fft[mask])
        detected_freq_fft = pos_freqs[mask][peak_idx]
    else:
        detected_freq_fft = 0.0

    # Use FFT result if autocorrelation failed
    detected_freq = (
        detected_freq_fft if detected_freq_fft > 0 else detected_freq_autocorr
    )
    print(f"Note {note}: Autocorr freq = {detected_freq_autocorr:.2f}, FFT freq = {detected_freq_fft:.2f}, used = {'FFT' if detected_freq_fft > 0 else 'autocorr'}")

    # Volume analysis
    rms = np.sqrt(np.mean(steady_audio**2))
    peak = np.max(np.abs(steady_audio))

    # THD analysis using FFT
    # Find fundamental
    fundamental_idx = np.argmin(np.abs(pos_freqs - expected_freq))
    fundamental = pos_fft[fundamental_idx]

    # Sum harmonics
    harmonics = 0
    for h in range(2, 6):  # H2 to H5
        h_freq = expected_freq * h
        h_idx = np.argmin(np.abs(pos_freqs - h_freq))
        harmonics += pos_fft[h_idx]

    thd = (harmonics / fundamental * 100) if fundamental > 0 else 0

    return {
        "detected_freq": detected_freq,
        "expected_freq": expected_freq,
        "freq_error": abs(detected_freq - expected_freq),
        "rms": rms,
        "peak": peak,
        "thd": thd,
        "steady_samples": len(steady_audio),
    }


def test_enhanced_audio_rendering(channel=0, bank_msb=0, bank_lsb=0, program=0):
    """Enhanced testing with multiple notes and file output."""

    # Create synthesizer with test SF2
    sf2_path = "sine_test.sf2"
    if not os.path.exists(sf2_path):
        print(f"SF2 file {sf2_path} not found")
        return False

    # Debug: Check SF2 file contents
    print("=== SF2 File Analysis ===")
    from synth.io.sf2.manager import SF2Manager
    from synth.io.sf2.core.soundfont_manager import SoundFontManager
    
    sf2_manager = SF2Manager()
    sf2_manager.set_sf2_files([sf2_path])
    wavetable_manager = sf2_manager.get_manager()
    
    # Get program parameters
    params = wavetable_manager.get_program_parameters(bank_msb, bank_lsb, 60, 64)
    if params:
        print(f"Program {program} has {len(params.get('partials', []))} partials")
        for i, partial in enumerate(params.get('partials', [])):
            print(f"  Partial {i}: stereo={partial.get('stereo', False)}, pan={partial.get('pan', 0.0)}")
            
            # Try to get sample data
            sample_data = wavetable_manager.get_partial_table(60, 0, i, 64, 0)
            if sample_data is not None:
                if isinstance(sample_data, tuple):
                    left, right = sample_data
                    print(f"    Sample data: STEREO - left shape={left.shape}, right shape={right.shape}")
                    print(f"    Left sample values: min={np.min(left):.6f}, max={np.max(left):.6f}")
                    print(f"    Right sample values: min={np.min(right):.6f}, max={np.max(right):.6f}")
                else:
                    print(f"    Sample data: MONO - shape={sample_data.shape}")
                    print(f"    Sample values: min={np.min(sample_data):.6f}, max={np.max(sample_data):.6f}")
            else:
                print("    Sample data: None")

    synthesizer = OptimizedXGSynthesizer(
        sample_rate=44100, max_polyphony=16, sf2_files=[sf2_path], render_log_level=0
    )

    # Create synthesizer

    # Test notes (spread across range)
    test_notes = [36, 48, 60, 72, 84]  # C2, C3, C4, C5, C6

    # Debug for note 84
    if 84 in test_notes:
        params_84 = wavetable_manager.get_program_parameters(bank_msb, bank_lsb, 84, 64)
        if params_84:
            print(f"Program {program} for note 84 has {len(params_84.get('partials', []))} partials")
            for i, partial in enumerate(params_84.get('partials', [])):
                print(f"  Partial {i}: stereo={partial.get('stereo', False)}, pan={partial.get('pan', 0.0)}")
                sample_data = wavetable_manager.get_partial_table(84, bank_msb, i, 64, channel)
                if sample_data is not None:
                    if isinstance(sample_data, tuple):
                        left, right = sample_data
                        print(f"    Sample data: STEREO - left shape={left.shape}, right shape={right.shape}")
                    else:
                        print(f"    Sample data: MONO - shape={sample_data.shape}")
                else:
                    print("    Sample data: None")

    # Theoretical frequencies
    note_freqs = {
        36: 65.41,  # C2
        48: 130.81,  # C3
        60: 261.63,  # C4
        72: 523.25,  # C5
        84: 1046.50,  # C6
    }

    # Will use scipy for WAV writing

    results = []

    for note in test_notes:
        print(f"\n=== Testing Note {note} (MIDI) ===")
        expected_freq = note_freqs[note]

        # Generate 5-second audio
        audio_data = generate_note_audio(synthesizer, note, channel, bank_msb, bank_lsb, program, duration_seconds=5.0)

        # Analyze quality
        analysis = analyze_audio_quality(audio_data, 44100, expected_freq, note)

        if analysis is None:
            print(f"ERROR: Could not analyze note {note}")
            continue

        # Print results
        print(f"Expected frequency: {expected_freq:.2f} Hz")
        print(f"Detected frequency: {analysis['detected_freq']:.2f} Hz")
        print(
            f"Frequency error: {analysis['freq_error']:.2f} Hz ({analysis['freq_error'] / expected_freq * 100:.2f}%)"
        )
        print(f"RMS level: {20 * np.log10(analysis['rms']):.1f} dB")
        print(f"Peak level: {20 * np.log10(analysis['peak']):.1f} dB")
        print(f"THD: {analysis['thd']:.2f}%")
        print(f"Steady state samples: {analysis['steady_samples']}")

        # Save to WAV file using scipy
        wav_filename = f"test_note_{note}.wav"
        try:
            # Convert float32 to int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            scipy.io.wavfile.write(wav_filename, 44100, audio_int16)
            print(f"Saved audio to {wav_filename}")
        except Exception as e:
            print(f"ERROR saving {wav_filename}: {e}")

        results.append((note, analysis))

    # Summary
    print("\n=== SUMMARY ===")
    print("Note | Expected | Detected | Error | RMS dB | THD % | Status")
    print("-" * 55)

    all_passed = True
    for note, analysis in results:
        expected = note_freqs[note]
        detected = analysis["detected_freq"]
        error = analysis["freq_error"]
        error_pct = error / expected * 100
        rms_db = 20 * np.log10(analysis["rms"])
        thd = analysis["thd"]

        status = "PASS" if error_pct < 5.0 and rms_db > -30 and thd < 10.0 else "FAIL"
        if status == "FAIL":
            all_passed = False

        print(f"{note:4d} | {expected:8.2f} | {detected:8.2f} | {error:6.2f} | {rms_db:6.1f} | {thd:6.2f} | {status}")

    print(f"\nOverall result: {'PASS' if all_passed else 'FAIL'}")
    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug partial rendering with configurable MIDI parameters")
    parser.add_argument('--channel', type=int, default=0, help='MIDI channel (0-15)')
    parser.add_argument('--bank-msb', type=int, default=0, help='Bank MSB')
    parser.add_argument('--bank-lsb', type=int, default=0, help='Bank LSB')
    parser.add_argument('--program', type=int, default=0, help='Program number')

    args = parser.parse_args()
    success = test_enhanced_audio_rendering(args.channel, args.bank_msb, args.bank_lsb, args.program)
    sys.exit(0 if success else 1)
