/*
  ==============================================================================

    PythonIntegration.h
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

    Thread-safe Python interpreter embedding and XG synthesizer integration.
    All Python/GIL operations are designed to be called from non-audio threads.

  ==============================================================================
*/

#pragma once

#include "AppConfig.h"

#include <memory>
#include <vector>
#include <string>
#include <mutex>
#include <atomic>

#include <juce_core/juce_core.h>
#include <pybind11/embed.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

//==============================================================================
class PythonIntegration
{
public:
    PythonIntegration();
    ~PythonIntegration();

    bool initialize(double sampleRate, int blockSize);
    void shutdown();
    bool isReady() const { return pythonReady.load() && synthesizerReady.load(); }

    bool processAudioBlock(const std::vector<float>& leftInput,
                          const std::vector<float>& rightInput,
                          std::vector<float>& leftOutput,
                          std::vector<float>& rightOutput);

    bool sendMidiMessage(int status, int data1, int data2, double timestamp = 0.0);
    juce::String getSynthesizerStatus() const;

    bool setParameter(const juce::String& parameterName, float value);
    float getParameter(const juce::String& parameterName) const;
    bool setPartParameter(int part, const juce::String& parameterName, float value);

    bool loadXGMLConfig(const juce::String& configPath);
    bool saveXGMLConfig(const juce::String& configPath);

    double getSampleRate() const { return currentSampleRate.load(); }
    int getBlockSize() const { return currentBlockSize.load(); }
    int getActiveVoiceCount() const { return activeVoices.load(); }
    juce::String getSynthesizerInfo() const;

    juce::String getLastError() const;
    void clearLastError();

private:
    std::atomic<bool> pythonReady{false};
    std::atomic<bool> synthesizerReady{false};
    std::atomic<double> currentSampleRate{44100.0};
    std::atomic<int> currentBlockSize{512};
    std::atomic<int> activeVoices{0};

    std::unique_ptr<py::scoped_interpreter> pythonInterpreter;
    py::object xgSynthesizer;
    py::object patternSequencer;

    class GilLock
    {
    public:
        GilLock() : state(PyGILState_Ensure()) {}
        ~GilLock() { PyGILState_Release(state); }
        GilLock(const GilLock&) = delete;
        GilLock& operator=(const GilLock&) = delete;
    private:
        PyGILState_STATE state;
    };

    mutable std::mutex operationMutex;
    mutable std::mutex errorMutex;
    juce::String lastError;

    bool setupPythonPath();
    bool createXGSynthesizer(double sampleRate);
    bool createPatternSequencer();
    bool testIntegration();
    void setLastError(const juce::String& error);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (PythonIntegration)
};
