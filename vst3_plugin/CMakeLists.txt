cmake_minimum_required(VERSION 3.22)

project(XGWorkstationVST3 VERSION 1.0.0)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# JUCE global settings - required for manual CMake builds
add_compile_definitions(JUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1)

# Disable JUCE features that require additional dependencies
set(JUCE_WEB_BROWSER OFF CACHE BOOL "Disable web browser" FORCE)
set(JUCE_USE_CURL OFF CACHE BOOL "Disable CURL" FORCE)

# Generate compile_commands.json for IDE support
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Find Python and pybind11
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

# Try to find pybind11 via CMake config first, then fallback to pip install
find_package(pybind11 CONFIG QUIET)
if(NOT pybind11_FOUND)
    # Fallback: find pybind11 headers via pip
    execute_process(
        COMMAND ${Python3_EXECUTABLE} -c "import pybind11; print(pybind11.get_include())"
        OUTPUT_VARIABLE PYBIND11_INCLUDE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE PYBIND11_FIND_RESULT
    )
    if(PYBIND11_FIND_RESULT EQUAL 0 AND EXISTS "${PYBIND11_INCLUDE_DIR}")
        add_library(pybind11::embed INTERFACE IMPORTED)
        target_include_directories(pybind11::embed INTERFACE "${PYBIND11_INCLUDE_DIR}")
        target_compile_definitions(pybind11::embed INTERFACE PYBIND11_EMBEDDED_MODULE_IMPL)
        message(STATUS "Found pybind11 via pip: ${PYBIND11_INCLUDE_DIR}")
    else()
        message(FATAL_ERROR "pybind11 not found. Install with: pip install pybind11")
    endif()
else()
    message(STATUS "Found pybind11 via CMake config")
endif()

# Set JUCE modules directory for the embedded JUCE submodule
set(JUCE_MODULES_DIR "${CMAKE_CURRENT_SOURCE_DIR}/JUCE/modules" CACHE PATH "Path to JUCE modules")

# JUCE options - minimal configuration to avoid pkg-config issues
option(JUCE_BUILD_EXTRAS "Build JUCE extras" OFF)
option(JUCE_BUILD_EXAMPLES "Build JUCE examples" OFF)

# Disable all optional JUCE modules to avoid pkg-config dependencies
set(JUCE_USE_ALSA OFF CACHE BOOL "Disable ALSA support")
set(JUCE_USE_JACK OFF CACHE BOOL "Disable JACK support")
set(JUCE_USE_PULSEAUDIO OFF CACHE BOOL "Disable PulseAudio support")
set(JUCE_USE_COREAUDIO OFF CACHE BOOL "Disable CoreAudio support")
set(JUCE_USE_WINRT_MIDI OFF CACHE BOOL "Disable WinRT MIDI support")
set(JUCE_USE_WEBSOCKET OFF CACHE BOOL "Disable WebSocket support")

# Add JUCE - use the embedded submodule
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
        juce::juce_core
        juce::juce_audio_basics
        juce::juce_audio_utils
        juce::juce_audio_processors
        juce::juce_gui_basics
        pybind11::embed
        ${Python3_LIBRARIES}
)

# Disable JUCE features that require additional dependencies
target_compile_definitions(${PROJECT_NAME}
    PRIVATE
        JUCE_WEB_BROWSER=0
        JUCE_USE_CURL=0
        JUCE_VST3_CAN_REPLACE_VST2=0
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
            juce::juce_core
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
