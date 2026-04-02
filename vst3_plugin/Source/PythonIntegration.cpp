/*
  ==============================================================================

    PythonIntegration.cpp
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

  ==============================================================================
*/

#include "PythonIntegration.h"
#include <filesystem>

//==============================================================================
PythonIntegration::PythonIntegration()
    : pythonReady(false), synthesizerReady(false)
{
}

PythonIntegration::~PythonIntegration()
{
    shutdown();
}

//==============================================================================
bool PythonIntegration::initialize(double sampleRate, int blockSize)
{
    try
    {
        // Initialize Python interpreter
        pythonInterpreter = std::make_unique<py::scoped_interpreter>();

        // Setup Python path
        if (!setupPythonPath())
        {
            DBG("Failed to setup Python path");
            return false;
        }

        // Create XG synthesizer
        if (!createXGSynthesizer(sampleRate))
        {
            DBG("Failed to create XG synthesizer");
            return false;
        }

        // Create pattern sequencer
        if (!createPatternSequencer())
        {
            DBG("Failed to create pattern sequencer");
            return false;
        }

        // Test integration
        if (!testIntegration())
        {
            DBG("Python integration test failed");
            return false;
        }

        pythonReady = true;
        synthesizerReady = true;

        DBG("Python integration initialized successfully");
        return true;
    }
    catch (const std::exception& e)
    {
        DBG("Python integration initialization failed: " + juce::String(e.what()));
        return false;
    }
}

void PythonIntegration::shutdown()
{
    try
    {
        // Clear Python objects
        {
            GilLock gil;
            xgSynthesizer = py::object();
            patternSequencer = py::object();
        }

        // Shutdown interpreter
        pythonInterpreter.reset();
        pythonReady = false;
        synthesizerReady = false;

        DBG("Python integration shutdown");
    }
    catch (const std::exception& e)
    {
        DBG("Python integration shutdown error: " + juce::String(e.what()));
    }
}

//==============================================================================
bool PythonIntegration::processAudioBlock(const std::vector<float>& leftInput,
                                         const std::vector<float>& rightInput,
                                         std::vector<float>& leftOutput,
                                         std::vector<float>& rightOutput)
{
    if (!isReady())
        return false;

    // PERFORMANCE OPTIMIZATION: Minimize GIL scope and avoid unnecessary operations
    try
    {
        GilLock gil;

        // Call XG synthesizer audio generation method with minimal overhead
        // generate_audio_block() returns numpy array with shape (blockSize, 2)
        auto result = xgSynthesizer.attr("generate_audio_block")(leftInput.size());

        // Extract stereo output from numpy array with optimized access
        py::array_t<float> audioArray = result;
        auto buffer = audioArray.unchecked<2>();

        // PERFORMANCE: Pre-allocate output vectors and use direct buffer access
        size_t numSamples = leftInput.size();
        if (leftOutput.size() != numSamples) leftOutput.resize(numSamples);
        if (rightOutput.size() != numSamples) rightOutput.resize(numSamples);

        // PERFORMANCE: Use optimized loop for stereo deinterleaving
        const float* audioData = buffer.data(0, 0);
        for (size_t i = 0; i < numSamples; ++i)
        {
            leftOutput[i] = audioData[i * 2];      // Left channel
            rightOutput[i] = audioData[i * 2 + 1]; // Right channel
        }

        return true;
    }
    catch (const std::exception& e)
    {
        DBG("Audio processing error: " + juce::String(e.what()));
        return false;
    }
}

bool PythonIntegration::sendMidiMessage(int status, int data1, int data2, double timestamp)
{
    if (!isReady())
        return false;

    try
    {
        GilLock gil;

        std::vector<uint8_t> midiBytes;
        midiBytes.push_back(static_cast<uint8_t>(status));

        int msgType = status & 0xF0;
        if (msgType == 0x80 || msgType == 0x90 || msgType == 0xA0 || msgType == 0xB0)
        {
            midiBytes.push_back(static_cast<uint8_t>(data1));
            midiBytes.push_back(static_cast<uint8_t>(data2));
        }
        else if (msgType == 0xC0 || msgType == 0xD0)
        {
            midiBytes.push_back(static_cast<uint8_t>(data1));
        }
        else if (msgType == 0xE0)
        {
            midiBytes.push_back(static_cast<uint8_t>(data1 & 0x7F));
            midiBytes.push_back(static_cast<uint8_t>((data2 >> 7) & 0x7F));
        }

        py::bytes midiData(reinterpret_cast<const char*>(midiBytes.data()), midiBytes.size());
        xgSynthesizer.attr("process_midi_message")(midiData);

        return true;
    }
    catch (const std::exception& e)
    {
        DBG("MIDI message error: " + juce::String(e.what()));
        return false;
    }
}

juce::String PythonIntegration::getSynthesizerStatus() const
{
    if (!isReady())
        return "Not initialized";

    try
    {
        GilLock gil;

        // Get status from synthesizer
        // Placeholder - actual method will depend on XG synthesizer API
        auto status = xgSynthesizer.attr("get_status")();
        return juce::String(py::str(status));
    }
    catch (const std::exception& e)
    {
        return "Error: " + juce::String(e.what());
    }
}

//==============================================================================
bool PythonIntegration::setParameter(const juce::String& parameterName, float value)
{
    if (!isReady())
        return false;

    try
    {
        GilLock gil;

        // Map parameter names to XG synthesizer methods
        if (parameterName == "master_volume")
        {
            xgSynthesizer.attr("set_master_volume")(value);
        }
        else if (parameterName == "reverb_type")
        {
            xgSynthesizer.attr("set_xg_reverb_type")(static_cast<int>(value));
        }
        else if (parameterName == "chorus_type")
        {
            xgSynthesizer.attr("set_xg_chorus_type")(static_cast<int>(value));
        }
        else if (parameterName == "variation_type")
        {
            xgSynthesizer.attr("set_xg_variation_type")(static_cast<int>(value));
        }
        else if (parameterName == "drum_kit")
        {
            // drum_kit parameter format: channel.kit (e.g., "9.26" for channel 9, kit 26)
            // For now, just set a default drum kit on channel 9
            xgSynthesizer.attr("set_drum_kit")(9, static_cast<int>(value));
        }
        else if (parameterName == "tempo")
        {
            // Tempo is handled by pattern sequencer
            if (patternSequencer)
            {
                // This would need to be implemented when sequencer integration is added
                // patternSequencer.attr("set_tempo")(value);
            }
        }
        else
        {
            // Unknown parameter - try generic set_parameter if it exists
            try
            {
                xgSynthesizer.attr("set_parameter")(parameterName.toStdString(), value);
            }
            catch (const std::exception&)
            {
                DBG("Unknown parameter: " + parameterName);
                return false;
            }
        }

        return true;
    }
    catch (const std::exception& e)
    {
        DBG("Parameter set error: " + juce::String(e.what()));
        return false;
    }
}

float PythonIntegration::getParameter(const juce::String& parameterName) const
{
    if (!isReady())
        return 0.0f;

    try
    {
        GilLock gil;

        // Get parameter from synthesizer
        // Placeholder - actual method will depend on XG synthesizer API
        auto value = xgSynthesizer.attr("get_parameter")(parameterName.toStdString());
        return py::float_(value);
    }
    catch (const std::exception& e)
    {
        DBG("Parameter get error: " + juce::String(e.what()));
        return 0.0f;
    }
}

//==============================================================================
bool PythonIntegration::loadXGMLConfig(const juce::String& configPath)
{
    if (!isReady())
        return false;

    try
    {
        GilLock gil;

        // Load XGML configuration
        // Placeholder - actual method will depend on XG synthesizer API
        xgSynthesizer.attr("load_xgml_config")(configPath.toStdString());

        return true;
    }
    catch (const std::exception& e)
    {
        DBG("XGML load error: " + juce::String(e.what()));
        return false;
    }
}

bool PythonIntegration::saveXGMLConfig(const juce::String& configPath)
{
    if (!isReady())
        return false;

    try
    {
        GilLock gil;

        // Save XGML configuration
        // Placeholder - actual method will depend on XG synthesizer API
        xgSynthesizer.attr("save_xgml_config")(configPath.toStdString());

        return true;
    }
    catch (const std::exception& e)
    {
        DBG("XGML save error: " + juce::String(e.what()));
        return false;
    }
}

//==============================================================================
bool PythonIntegration::setupPythonPath()
{
    try
    {
        GilLock gil;

        auto exePath = juce::File::getSpecialLocation(juce::File::currentExecutableFile);
        auto pluginDir = exePath.getParentDirectory();

        juce::Array<juce::File> searchPaths;
        searchPaths.add(pluginDir);
        searchPaths.add(pluginDir.getParentDirectory());
        searchPaths.add(pluginDir.getParentDirectory().getParentDirectory());

        juce::File synthDir;
        for (auto& basePath : searchPaths)
        {
            auto candidate = basePath.getChildFile("synth");
            if (candidate.isDirectory())
            {
                synthDir = candidate;
                break;
            }
        }

        if (synthDir.isDirectory())
        {
            auto projectRoot = synthDir.getParentDirectory();
            py::module::import("sys").attr("path").attr("insert")(0, projectRoot.getFullPathName().toStdString());
            DBG("Added project root to Python path: " + projectRoot.getFullPathName());
            return true;
        }

        DBG("Synth directory not found in any search path");
        return false;
    }
    catch (const std::exception& e)
    {
        DBG("Python path setup error: " + juce::String(e.what()));
        return false;
    }
}

bool PythonIntegration::createXGSynthesizer(double sampleRate)
{
    try
    {
        GilLock gil;

        py::module xgModule = py::module::import("engine.modern_xg_synthesizer");
        auto synthesizerClass = xgModule.attr("ModernXGSynthesizer");

        xgSynthesizer = synthesizerClass(
            py::arg("sample_rate") = sampleRate,
            py::arg("max_channels") = 16,
            py::arg("xg_enabled") = true,
            py::arg("gs_enabled") = true,
            py::arg("mpe_enabled") = true
        );

        DBG("XG synthesizer created successfully");
        return true;
    }
    catch (const std::exception& e)
    {
        DBG("XG synthesizer creation error: " + juce::String(e.what()));
        return false;
    }
}

bool PythonIntegration::createPatternSequencer()
{
    try
    {
        GilLock gil;

        // Import and create pattern sequencer
        py::module sequencerModule = py::module::import("sequencer.pattern_sequencer");
        auto sequencerClass = sequencerModule.attr("PatternSequencer");

        // Create sequencer instance
        patternSequencer = sequencerClass();

        DBG("Pattern sequencer created successfully");
        return true;
    }
    catch (const std::exception& e)
    {
        DBG("Pattern sequencer creation error: " + juce::String(e.what()));
        return false;
    }
}

bool PythonIntegration::testIntegration()
{
    try
    {
        GilLock gil;

        // Test basic functionality
        if (xgSynthesizer)
        {
            // Try to call a basic method
            auto info = xgSynthesizer.attr("get_synthesizer_info")();
            DBG("Synthesizer info retrieved successfully");
        }

        if (patternSequencer)
        {
            // Try to call a basic method
            auto status = patternSequencer.attr("get_playback_status")();
            DBG("Sequencer status retrieved successfully");
        }

        return true;
    }
    catch (const std::exception& e)
    {
        DBG("Integration test error: " + juce::String(e.what()));
        return false;
    }
}

bool PythonIntegration::setPartParameter(int part, const juce::String& parameterName, float value)
{
    if (!isReady())
        return false;

    try
    {
        GilLock gil;
        xgSynthesizer.attr("set_channel_parameter")(part, parameterName.toStdString(), value);
        return true;
    }
    catch (const std::exception& e)
    {
        DBG("Part parameter error: " + juce::String(e.what()));
        return false;
    }
}

juce::String PythonIntegration::getSynthesizerInfo() const
{
    if (!isReady())
        return "Not initialized";

    try
    {
        GilLock gil;
        auto info = xgSynthesizer.attr("get_synthesizer_info")();
        return juce::String(py::str(info));
    }
    catch (const std::exception& e)
    {
        return "Error: " + juce::String(e.what());
    }
}

juce::String PythonIntegration::getLastError() const
{
    std::lock_guard<std::mutex> lock(errorMutex);
    return lastError;
}

void PythonIntegration::clearLastError()
{
    std::lock_guard<std::mutex> lock(errorMutex);
    lastError = juce::String();
}

void PythonIntegration::setLastError(const juce::String& error)
{
    std::lock_guard<std::mutex> lock(errorMutex);
    lastError = error;
}
