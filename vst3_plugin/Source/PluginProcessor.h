/*
  ==============================================================================

    PluginProcessor.h
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

    VST3 Audio Processor with thread-safe Python integration.

  ==============================================================================
*/

#pragma once

#include "AppConfig.h"

#include <atomic>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <vector>
#include <memory>

#include <juce_core/juce_core.h>
#include <juce_audio_basics/juce_audio_basics.h>
#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_audio_utils/juce_audio_utils.h>
#include <juce_gui_basics/juce_gui_basics.h>

#include <pybind11/embed.h>
#include <pybind11/stl.h>

#include "PythonIntegration.h"
#include "XGParameterManager.h"

//==============================================================================
template<typename T>
class LockFreeRingBuffer
{
public:
    LockFreeRingBuffer(size_t size)
        : bufferSize(size), writeIndex(0), readIndex(0)
    {
        buffer.resize(size);
    }

    bool push(const T* data, size_t numSamples)
    {
        size_t available = availableToWrite();
        if (available < numSamples)
            return false;

        for (size_t i = 0; i < numSamples; ++i)
        {
            size_t idx = (writeIndex.load(std::memory_order_relaxed) + i) % bufferSize;
            buffer[idx] = data[i];
        }

        writeIndex.store((writeIndex.load(std::memory_order_relaxed) + numSamples) % bufferSize,
                         std::memory_order_release);
        return true;
    }

    bool pop(T* data, size_t numSamples)
    {
        size_t available = availableToRead();
        if (available < numSamples)
            return false;

        for (size_t i = 0; i < numSamples; ++i)
        {
            size_t idx = (readIndex.load(std::memory_order_relaxed) + i) % bufferSize;
            data[i] = buffer[idx];
        }

        readIndex.store((readIndex.load(std::memory_order_relaxed) + numSamples) % bufferSize,
                        std::memory_order_release);
        return true;
    }

    size_t availableToRead() const
    {
        size_t w = writeIndex.load(std::memory_order_acquire);
        size_t r = readIndex.load(std::memory_order_acquire);
        return (w >= r) ? (w - r) : (bufferSize - r + w);
    }

    size_t availableToWrite() const
    {
        return bufferSize - availableToRead() - 1;
    }

    void reset()
    {
        writeIndex.store(0, std::memory_order_release);
        readIndex.store(0, std::memory_order_release);
    }

private:
    std::vector<T> buffer;
    size_t bufferSize;
    std::atomic<size_t> writeIndex;
    std::atomic<size_t> readIndex;
};

//==============================================================================
struct MidiMessageData
{
    uint8_t status;
    uint8_t data1;
    uint8_t data2;
    double timestamp;
};

//==============================================================================
class MidiMessageQueue
{
public:
    static constexpr size_t MAX_MESSAGES = 1024;

    bool push(const MidiMessageData& msg)
    {
        std::lock_guard<std::mutex> lock(mutex);
        if (queue.size() >= MAX_MESSAGES)
            return false;
        queue.push(msg);
        return true;
    }

    bool pop(MidiMessageData& msg)
    {
        std::lock_guard<std::mutex> lock(mutex);
        if (queue.empty())
            return false;
        msg = queue.front();
        queue.pop();
        return true;
    }

    void clear()
    {
        std::lock_guard<std::mutex> lock(mutex);
        while (!queue.empty())
            queue.pop();
    }

    size_t size() const
    {
        std::lock_guard<std::mutex> lock(mutex);
        return queue.size();
    }

private:
    mutable std::mutex mutex;
    std::queue<MidiMessageData> queue;
};

//==============================================================================
class PythonProcessingThread : public juce::Thread
{
public:
    PythonProcessingThread(PythonIntegration& integration);
    ~PythonProcessingThread() override;

    void run() override;

    LockFreeRingBuffer<float> inputBufferLeft{8192};
    LockFreeRingBuffer<float> inputBufferRight{8192};
    LockFreeRingBuffer<float> outputBufferLeft{8192};
    LockFreeRingBuffer<float> outputBufferRight{8192};

    MidiMessageQueue midiQueue;

    std::atomic<bool> isProcessing{false};
    std::atomic<int> currentBlockSize{512};

    void signalNewBlock() { newDataAvailable.notify_one(); }
    void shutdown() { shouldExit = true; newDataAvailable.notify_one(); }

private:
    PythonIntegration& pythonIntegration;
    std::atomic<bool> shouldExit{false};
    std::condition_variable newDataAvailable;
    std::mutex waitMutex;
};

//==============================================================================
class XGWorkstationVST3AudioProcessor;
class XGWorkstationVST3AudioProcessorEditor;

class XGWorkstationVST3AudioProcessor  : public juce::AudioProcessor,
                                          public juce::AudioProcessorValueTreeState::Listener
{
public:
    XGWorkstationVST3AudioProcessor();
    ~XGWorkstationVST3AudioProcessor() override;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;

#ifndef JucePlugin_PreferredChannelConfigurations
    bool isBusesLayoutSupported (const BusesLayout& layouts) const override;
#endif

    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override;

    const juce::String getName() const override;

    bool acceptsMidi() const override;
    bool producesMidi() const override;
    bool isMidiEffect() const override;
    double getTailLengthSeconds() const override;

    int getNumPrograms() override;
    int getCurrentProgram() override;
    void setCurrentProgram (int index) override;
    const juce::String getProgramName (int index) override;
    void changeProgramName (int index, const juce::String& newName) override;

    void getStateInformation (juce::MemoryBlock& destData) override;
    void setStateInformation (const void* data, int sizeInBytes) override;

    void parameterChanged(const juce::String& parameterID, float newValue) override;

    juce::AudioProcessorValueTreeState& getParameterTree() { return apvts; }

    void initializeXGWorkstation();
    void shutdownXGWorkstation();
    bool isXGWorkstationReady() const { return xgWorkstationReady.load(); }

    PythonIntegration& getPythonIntegration() { return pythonIntegration; }
    const PythonIntegration& getPythonIntegration() const { return pythonIntegration; }

    XGParameterManager& getParameterManager() { return parameterManager; }

    struct PerformanceMetrics
    {
        std::atomic<double> averageCpuUsage{0.0};
        std::atomic<double> peakCpuUsage{0.0};
        std::atomic<int64_t> totalProcessedSamples{0};
        std::atomic<double> averageProcessingTime{0.0};
        std::atomic<int> bufferUnderruns{0};
        std::atomic<int> activeVoices{0};
    } performanceMetrics;

    std::atomic<double> currentSampleRate{44100.0};
    std::atomic<int> currentBlockSize{512};

private:
    PythonIntegration pythonIntegration;
    XGParameterManager parameterManager;
    juce::AudioProcessorValueTreeState apvts;

    std::atomic<bool> xgWorkstationReady{false};
    std::atomic<bool> isBypassed{false};

    std::vector<float> leftInputBuffer;
    std::vector<float> rightInputBuffer;
    std::vector<float> leftOutputBuffer;
    std::vector<float> rightOutputBuffer;

    std::unique_ptr<PythonProcessingThread> processingThread;

    std::atomic<juce::int64> lastCpuMeasurement{0};

    void processMidiMessage(const juce::MidiMessage& message);

    void updatePerformanceMetrics(double processingTimeMs, int numSamples);
    double getCurrentCpuUsage();

    juce::String lastError;
    std::mutex errorMutex;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (XGWorkstationVST3AudioProcessor)
};
