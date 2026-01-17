cmake_minimum_required(VERSION 3.16)

project(XGWorkstationVST3 VERSION 1.0.0)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python and pybind11
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)

# JUCE options - minimal configuration to avoid pkg-config issues
option(JUCE_BUILD_EXTRAS "Build JUCE extras" OFF)
option(JUCE_BUILD_EXAMPLES "Build JUCE examples" OFF)

# Disable all optional JUCE modules to avoid pkg-config dependencies
set(JUCE_USE_ALSA OFF CACHE BOOL "Disable ALSA support")
set(JUCE_USE_JACK OFF CACHE BOOL "Disable JACK support")
set(JUCE_USE_PULSEAUDIO OFF CACHE BOOL "Disable PulseAudio support")
set(JUCE_USE_COREAUDIO OFF CACHE BOOL "Disable CoreAudio support")
set(JUCE_USE_WINRT_MIDI OFF CACHE BOOL "Disable WinRT MIDI support")

# Add JUCE
add_subdirectory(JUCE)

# Create plugin target
juce_add_plugin(${PROJECT_NAME}
    VERSION "1.0.0"
    COMPANY_NAME "XG Synthesizer"
    PLUGIN_MANUFACTURER_CODE "XGSy"
    PLUGIN_CODE "XGWS"
    FORMATS VST3
    PRODUCT_NAME "XG Workstation"
    BUNDLE_ID "com.xg-synthesizer.workstation"
    VST3_CATEGORIES "Instrument" "Synth"
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT TRUE
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
)

# Source files
target_sources(${PROJECT_NAME}
    PRIVATE
        Source/PluginProcessor.cpp
        Source/PluginProcessor.h
        Source/PluginEditor.cpp
        Source/PluginEditor.h
        Source/PythonIntegration.cpp
        Source/PythonIntegration.h
        Source/XGParameterManager.cpp
        Source/XGParameterManager.h
)

# Include directories
target_include_directories(${PROJECT_NAME}
    PRIVATE
        Source
        ${Python3_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(${PROJECT_NAME}
    PRIVATE
        juce::juce_audio_utils
        juce::juce_audio_processors
        juce::juce_gui_basics
        pybind11::embed
        ${Python3_LIBRARIES}
)

# Compiler flags
if(MSVC)
    target_compile_options(${PROJECT_NAME} PRIVATE /W4)
else()
    target_compile_options(${PROJECT_NAME} PRIVATE -Wall -Wextra)
endif()

# Installation
install(TARGETS ${PROJECT_NAME}
    LIBRARY DESTINATION lib/vst3
    RUNTIME DESTINATION bin
)

# ==============================================================================
# AAX BUILD CONFIGURATION (Phase 7.3 - Pro Tools Integration)
# ==============================================================================

option(BUILD_AAX "Build AAX version for Pro Tools" OFF)

if(BUILD_AAX)
    message(STATUS "Building AAX version for Pro Tools")

    # AAX SDK paths (user must set these)
    set(AAX_SDK_ROOT "" CACHE PATH "Path to AAX SDK")
    set(AAX_LIBRARY_PATH "" CACHE PATH "Path to AAX library")

    if(NOT AAX_SDK_ROOT)
        message(FATAL_ERROR "AAX_SDK_ROOT must be set when BUILD_AAX=ON")
    endif()

    # Create AAX-specific target
    set(AAX_PROJECT_NAME "${PROJECT_NAME}_AAX")

    juce_add_plugin(${AAX_PROJECT_NAME}
        VERSION "1.0.0"
        COMPANY_NAME "XG Synthesizer"
        PLUGIN_MANUFACTURER_CODE "XGSy"
        PLUGIN_CODE "XGWA"
        FORMATS AAX
        PRODUCT_NAME "XG Workstation AAX"
        BUNDLE_ID "com.xg-synthesizer.workstation.aax"
        AAX_IDENTIFIER "com.xg-synthesizer.workstation.aax"
        IS_SYNTH TRUE
        NEEDS_MIDI_INPUT TRUE
        NEEDS_MIDI_OUTPUT TRUE
        EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    )

    # AAX-specific source files
    target_sources(${AAX_PROJECT_NAME}
        PRIVATE
            Source/PluginProcessor.cpp
            Source/PluginProcessor.h
            Source/PluginEditor.cpp
            Source/PluginEditor.h
            Source/PythonIntegration.cpp
            Source/PythonIntegration.h
            Source/XGParameterManager.cpp
            Source/XGParameterManager.h
    )

    # AAX-specific include directories
    target_include_directories(${AAX_PROJECT_NAME}
        PRIVATE
            Source
            ${Python3_INCLUDE_DIRS}
            ${AAX_SDK_ROOT}/Interfaces
            ${AAX_SDK_ROOT}/Interfaces/ACF
    )

    # AAX-specific link libraries
    target_link_libraries(${AAX_PROJECT_NAME}
        PRIVATE
            juce::juce_audio_utils
            juce::juce_audio_processors
            juce::juce_gui_basics
            pybind11::embed
            ${Python3_LIBRARIES}
            ${AAX_LIBRARY_PATH}
    )

    # AAX-specific compiler definitions
    target_compile_definitions(${AAX_PROJECT_NAME}
        PRIVATE
            JUCE_PLUGINHOST_AAX=1
            AAX_SDK_BUILD=1
    )

    # AAX installation
    install(TARGETS ${AAX_PROJECT_NAME}
        LIBRARY DESTINATION lib/aax
        RUNTIME DESTINATION bin
    )

    message(STATUS "AAX target ${AAX_PROJECT_NAME} configured")
endif()
