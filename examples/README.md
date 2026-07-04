# Examples

This directory contains example scripts, configurations, and style files demonstrating the XG Synthesizer and Vibexg workstation.

## Quick Start

```bash
# Run a basic SF2 example
python examples/sf2_comprehensive_test.py

# Explore FM-X synthesis
python examples/fm_x_demo.py

# Try the SFZ sample playback engine
python examples/sfz_demo.py
```

## Example Index

### Python Scripts

| File | Description |
|------|-------------|
| `sf2_comprehensive_test.py` | Complete testing framework for SF2 specification compliance, generators, modulators, controllers, and performance validation. |
| `sfz_demo.py` | Demonstrates the SFZ synthesis engine with professional sample playback and XG compliance. |
| `fm_x_demo.py` | Showcases the FM-X compatible engine with 8 operators, 8-stage envelopes, ring modulation, formant synthesis, and LFO modulation. |
| `spectral_demo.py` | Demonstrates spectral synthesis including FFT processing, spectral filtering, granular synthesis, and real-time sound design. |
| `specialized_engines_demo.py` | Showcases advanced engines: convolution reverb, MPE support, and physical modeling for professional production. |
| `workstation_integration_example.py` | Full XG workstation integration with real-time control, automated mixing, and professional production environment features. |
| `xg_gs_mpe_workstation_example.py` | Demonstrates XG specification compliance, GS compatibility, and MPE support in a complete workstation setup. |
| `production_readiness_demo.py` | Showcases production infrastructure: validation framework, configuration management, and zero-allocation buffer pool. |
| `jupiter_x_lfo_envelope_demo.py` | Demonstrates Jupiter-X LFO waveforms, audio-rate LFO capability, per-engine LFO architecture, and advanced envelope features. |
| `jupiter_x_modern_synth_integration_demo.py` | Shows Jupiter-X engine registration with the modern synthesizer framework and multi-engine synthesis (Jupiter-X + SF2 + FM + others). |
| `jv2080_demo.py` | Showcases Roland JV-2080 workstation-level GS implementation with multi-part architecture, MFX effects, and NRPN control. |
| `motif_arpeggiator_demo.py` | Demonstrates the Yamaha Motif-compatible arpeggiator subsystem with SYSEX and NRPN control support. |

### XGML / XG DSL Configurations

| File | Description |
|------|-------------|
| `xgml_v3_workstation_config.xgml` | Professional XG/GS/MPE workstation configuration in XGML v3.0 format with complete multi-engine setup. |
| `simple_piano.xgdsl` | Minimal XG DSL configuration for a simple piano patch. |
| `jazz_combo.xgdsl` | Placeholder file for jazz combo XG DSL configuration. |

### Markdown DSL Examples

| File | Description |
|------|-------------|
| `jazz_combo_example.md` | Complete jazz combo arrangement with full XG parameter control, written in XG DSL YAML format. |
| `electronic_music_example.md` | Electronic music production example with advanced XG modulation and effects, written in XG DSL YAML format. |

### Style Files (`styles/`)

| File | Description |
|------|-------------|
| `styles/edm_pop.yaml` | EDM pop style with driving beats, pulsing bass, and energetic synth patterns. |
| `styles/jazz_swing.yaml` | Jazz swing style with brushed drums and walking bass (Yamaha SFF-style format). |
| `styles/jazz_waltz.yaml` | Classic 3/4 jazz waltz with walking bass and brush drums. |
| `styles/latin_pop.yaml` | Upbeat Latin pop style with percussion and brass sections. |
| `styles/pop_ballad.yaml` | Pop ballad style in Yamaha SFF-style YAML format. |
| `styles/rock_standard.yaml` | Rock style with driving drums and guitar in Yamaha SFF-style format. |
