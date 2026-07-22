/*
  ==============================================================================
    AppConfig.h
  
    Global configuration header for JUCE VST3 plugin.
    This file is included before any JUCE module headers.
  ==============================================================================
*/

#pragma once

#define JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED 1

// Disable optional JUCE features to reduce dependencies
#define JUCE_ALSA 0
#define JUCE_JACK 0
#define JUCE_PULSEAUDIO 0
#define JUCE_COREAUDIO 0
#define JUCE_WINRT_MIDI 0
#define JUCE_WEBSOCKET 0
#define JUCE_CURL 0
#define JUCE_WEB_BROWSER 0
