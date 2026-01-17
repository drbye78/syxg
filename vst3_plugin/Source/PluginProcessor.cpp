/*
  ==============================================================================

    PluginProcessor.cpp
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

  ==============================================================================
*/

#include "PluginProcessor.h"

//==============================================================================
XGWorkstationVST3AudioProcessor::XGWorkstationVST3AudioProcessor()
#ifndef JucePlugin_PreferredChannelConfigurations
     : AudioProcessor (BusesProperties()
                     #if ! JucePlugin_IsMidiEffect
                      #if ! JucePlugin_IsSynth
                       .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
                      #endif
                       .withOutput ("Output", juce::AudioChannelSet::stereo(), true)
                     #endif
                       )
#endif
{
    // Initialize parameter manager
    parameterManager.initializeParameters(*this);

    // Reserve audio buffer space
    leftChannelBuffer.reserve(8192);
    rightChannelBuffer.reserve(8192);
}

XGWorkstationVST3AudioProcessor::~XGWorkstationVST3AudioProcessor()
{
    shutdownXGWorkstation();
}

//==============================================================================
const juce::String XGWorkstationVST3AudioProcessor::getName() const
{
    return JucePlugin_Name;
}

bool XGWorkstationVST3AudioProcessor::acceptsMidi() const
{
   #if JucePlugin_WantsMidiInput
    return true;
   #else
    return false;
   #endif
}

bool XGWorkstationVST3AudioProcessor::producesMidi() const
{
   #if JucePlugin_ProducesMidiOutput
    return true;
   #else
    return false;
   #endif
}

bool XGWorkstationVST3AudioProcessor::isMidiEffect() const
{
   #if JucePlugin_IsMidiEffect
    return true;
   #else
    return false;
   #endif
}

double XGWorkstationVST3AudioProcessor::getTailLengthSeconds() const
{
    return 0.0;
}

int XGWorkstationVST3AudioProcessor::getNumPrograms()
{
    return 1;   // NB: some hosts don't cope very well if you tell them there are 0 programs,
                // so this should be at least 1, even if you're not really implementing programs.
}

int XGWorkstationVST3AudioProcessor::getCurrentProgram()
{
    return 0;
}

void XGWorkstationVST3AudioProcessor::setCurrentProgram (int index)
{
}

const juce::String XGWorkstationVST3AudioProcessor::getProgramName (int index)
{
    return {};
}

void XGWorkstationVST3AudioProcessor::changeProgramName (int index, const juce::String& newName)
{
}

//==============================================================================
void XGWorkstationVST3AudioProcessor::prepareToPlay (double sampleRate, int samplesPerBlock)
{
    // Store current audio settings
    currentSampleRate = sampleRate;
    currentBlockSize = samplesPerBlock;

    // Initialize XG workstation if not already done
    if (!xgWorkstationReady)
    {
        initializeXGWorkstation();
    }

    // Prepare audio buffers
    leftChannelBuffer.resize(samplesPerBlock);
    rightChannelBuffer.resize(samplesPerBlock);
}

void XGWorkstationVST3AudioProcessor::releaseResources()
{
    // When playback stops, you can use this as an opportunity to free up any
    // spare memory, etc.
}

#ifndef JucePlugin_PreferredChannelConfigurations
bool XGWorkstationVST3AudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
  #if JucePlugin_IsMidiEffect
    juce::ignoreUnused (layouts);
    return true;
  #else
    // This is the place where you check if the layout is supported.
    // In this template code we only support mono or stereo.
    // Some plugin hosts, such as certain GarageBand versions, will only
    // load plugins that support stereo bus layouts.
    if (layouts.getMainOutputChannelSet() != juce::AudioChannelSet::mono()
     && layouts.getMainOutputChannelSet() != juce::AudioChannelSet::stereo())
        return false;

    // This checks if the input layout matches the output layout
   #if ! JucePlugin_IsSynth
    if (layouts.getMainOutputChannelSet() != layouts.getMainInputChannelSet())
        return false;
   #endif

    return true;
  #endif
}
#endif

void XGWorkstationVST3AudioProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;

    // PERFORMANCE: Start CPU usage measurement
    auto processingStartTime = juce::Time::getHighResolutionTicks();

    // Get buffer info
    auto totalNumInputChannels  = getTotalNumInputChannels();
    auto totalNumOutputChannels = getTotalNumOutputChannels();
    auto numSamples = buffer.getNumSamples();

    // PERFORMANCE: Track total processed samples
    performanceMetrics.totalProcessedSamples += numSamples;

    // Clear output channels that don't have input
    for (auto i = totalNumInputChannels; i < totalNumOutputChannels; ++i)
        buffer.clear (i, 0, numSamples);

    // Process MIDI messages
    for (const auto metadata : midiMessages)
    {
        auto message = metadata.getMessage();
        processMidiMessage(message);
    }

    // If XG workstation is not ready, pass through audio or generate silence
    if (!xgWorkstationReady)
    {
        // PERFORMANCE: Still track processing time for inactive state
        auto processingEndTime = juce::Time::getHighResolutionTicks();
        double processingTimeMs = juce::Time::highResolutionTicksToSeconds(processingEndTime - processingStartTime) * 1000.0;
        updatePerformanceMetrics(processingTimeMs, numSamples);

        // For now, just clear the buffer (silence)
        for (int channel = 0; channel < totalNumOutputChannels; ++channel)
            buffer.clear(channel, 0, numSamples);
        return;
    }

    // PERFORMANCE: Prepare input buffers with optimized memory operations
    if (totalNumInputChannels >= 2)
    {
        auto* leftInput = buffer.getReadPointer(0);
        auto* rightInput = buffer.getReadPointer(1);

        // PERFORMANCE: Use resize + memcpy for better performance than assign
        if (leftChannelBuffer.size() != static_cast<size_t>(numSamples))
            leftChannelBuffer.resize(numSamples);
        if (rightChannelBuffer.size() != static_cast<size_t>(numSamples))
            rightChannelBuffer.resize(numSamples);

        std::memcpy(leftChannelBuffer.data(), leftInput, numSamples * sizeof(float));
        std::memcpy(rightChannelBuffer.data(), rightInput, numSamples * sizeof(float));
    }
    else
    {
        // No inputs, use silence - PERFORMANCE: Avoid repeated assignments
        if (leftChannelBuffer.size() != static_cast<size_t>(numSamples))
        {
            leftChannelBuffer.assign(numSamples, 0.0f);
            rightChannelBuffer.assign(numSamples, 0.0f);
        }
    }

    // Process through XG synthesizer
    std::vector<float> leftOutput(numSamples);
    std::vector<float> rightOutput(numSamples);

    if (pythonIntegration.processAudioBlock(leftChannelBuffer, rightChannelBuffer,
                                           leftOutput, rightOutput))
    {
        // Copy results back to JUCE buffer with optimized operations
        if (totalNumOutputChannels >= 1)
        {
            auto* leftOut = buffer.getWritePointer(0);
            std::memcpy(leftOut, leftOutput.data(), numSamples * sizeof(float));
        }

        if (totalNumOutputChannels >= 2)
        {
            auto* rightOut = buffer.getWritePointer(1);
            std::memcpy(rightOut, rightOutput.data(), numSamples * sizeof(float));
        }
    }
    else
    {
        // Processing failed, output silence
        for (int channel = 0; channel < totalNumOutputChannels; ++channel)
            buffer.clear(channel, 0, numSamples);
    }

    // PERFORMANCE: Update performance metrics
    auto processingEndTime = juce::Time::getHighResolutionTicks();
    double processingTimeMs = juce::Time::highResolutionTicksToSeconds(processingEndTime - processingStartTime) * 1000.0;
    updatePerformanceMetrics(processingTimeMs, numSamples);
}

//==============================================================================
bool XGWorkstationVST3AudioProcessor::hasEditor() const
{
    return true; // (change this to false if you choose to not supply an editor)
}

juce::AudioProcessorEditor* XGWorkstationVST3AudioProcessor::createEditor()
{
    return new XGWorkstationVST3AudioProcessorEditor (*this);
}

//==============================================================================
void XGWorkstationVST3AudioProcessor::getStateInformation (juce::MemoryBlock& destData)
{
    // You should use this method to store your parameters in the memory block.
    // You could do that either as raw data, or use the XML or ValueTree classes
    // as intermediaries to make it easy to save and load complex data.
    juce::ignoreUnused (destData);
}

void XGWorkstationVST3AudioProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    // You should use this method to restore your parameters from this memory block,
    // whose contents will have been created by the getStateInformation() method.
    juce::ignoreUnused (data, sizeInBytes);
}

//==============================================================================
// XG Workstation specific methods
void XGWorkstationVST3AudioProcessor::initializeXGWorkstation()
{
    if (xgWorkstationReady)
        return;

    DBG("Initializing XG Workstation...");

    // Initialize Python integration
    if (pythonIntegration.initialize(currentSampleRate, currentBlockSize))
    {
        xgWorkstationReady = true;
        DBG("XG Workstation initialized successfully");
    }
    else
    {
        DBG("Failed to initialize XG Workstation");
    }
}

void XGWorkstationVST3AudioProcessor::shutdownXGWorkstation()
{
    if (!xgWorkstationReady)
        return;

    DBG("Shutting down XG Workstation...");
    pythonIntegration.shutdown();
    xgWorkstationReady = false;
}

void XGWorkstationVST3AudioProcessor::processMidiMessage(const juce::MidiMessage& message)
{
    if (!xgWorkstationReady)
        return;

    // Convert JUCE MIDI message to raw bytes
    auto rawData = message.getRawData();
    int status = rawData[0];
    int data1 = message.getRawDataSize() > 1 ? rawData[1] : 0;
    int data2 = message.getRawDataSize() > 2 ? rawData[2] : 0;

    // Send to Python synthesizer
    pythonIntegration.sendMidiMessage(status, data1, data2, message.getTimeStamp());
}

//==============================================================================
// Performance optimization methods
void XGWorkstationVST3AudioProcessor::updatePerformanceMetrics(double processingTimeMs, int numSamples)
{
    // Update average processing time (exponential moving average)
    const double alpha = 0.1; // Smoothing factor
    performanceMetrics.averageProcessingTime =
        alpha * processingTimeMs + (1.0 - alpha) * performanceMetrics.averageProcessingTime;

    // Update CPU usage measurement (every 100ms)
    auto currentTime = juce::Time::currentTimeMillis();
    if (currentTime - lastCpuMeasurement.toMilliseconds() > 100)
    {
        double cpuUsage = getCurrentCpuUsage();
        performanceMetrics.averageCpuUsage = alpha * cpuUsage + (1.0 - alpha) * performanceMetrics.averageCpuUsage;
        performanceMetrics.peakCpuUsage = std::max(performanceMetrics.peakCpuUsage, cpuUsage);
        lastCpuMeasurement = juce::Time(currentTime);
    }

    // Check for buffer underruns (processing time > available time per block)
    double availableTimeMs = (numSamples / currentSampleRate) * 1000.0;
    if (processingTimeMs > availableTimeMs * 0.9) // 90% of available time
    {
        performanceMetrics.bufferUnderruns++;
    }
}

double XGWorkstationVST3AudioProcessor::getCurrentCpuUsage()
{
    // Use JUCE's PerformanceCounter to measure CPU usage
    // This is a simplified implementation - in a real plugin you might want more sophisticated measurement
    static double lastCpuTime = 0.0;
    double currentCpuTime = cpuCounter.getCPUUsage() * 100.0; // Convert to percentage

    if (lastCpuTime > 0.0)
    {
        double cpuUsage = currentCpuTime - lastCpuTime;
        lastCpuTime = currentCpuTime;
        return std::max(0.0, std::min(100.0, cpuUsage));
    }

    lastCpuTime = currentCpuTime;
    return 0.0;
}

void XGWorkstationVST3AudioProcessor::optimizeBufferSizes(int newBlockSize)
{
    // PERFORMANCE: Optimize buffer sizes based on actual usage patterns
    if (newBlockSize != currentBlockSize)
    {
        currentBlockSize = newBlockSize;

        // Resize buffers with some headroom for performance
        size_t optimalSize = static_cast<size_t>(newBlockSize * 1.5); // 50% headroom

        leftChannelBuffer.reserve(optimalSize);
        rightChannelBuffer.reserve(optimalSize);

        // Notify Python integration of buffer size change for optimization
        if (xgWorkstationReady)
        {
            pythonIntegration.initialize(currentSampleRate, newBlockSize);
        }

        DBG("Optimized buffer sizes for block size: " + juce::String(newBlockSize));
    }
}

//==============================================================================
// This creates new instances of the plugin..
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new XGWorkstationVST3AudioProcessor();
}
