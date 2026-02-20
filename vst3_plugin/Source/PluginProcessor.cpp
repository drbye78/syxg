/*
  ==============================================================================

    PluginProcessor.cpp
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

  ==============================================================================
*/

#include "PluginProcessor.h"
#include "PluginEditor.h"
#include <chrono>
#include <algorithm>

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
    leftInputBuffer.reserve(8192);
    rightInputBuffer.reserve(8192);
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
    leftInputBuffer.resize(samplesPerBlock);
    rightInputBuffer.resize(samplesPerBlock);
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
        if (leftInputBuffer.size() != static_cast<size_t>(numSamples))
            leftInputBuffer.resize(numSamples);
        if (rightInputBuffer.size() != static_cast<size_t>(numSamples))
            rightInputBuffer.resize(numSamples);

        std::memcpy(leftInputBuffer.data(), leftInput, numSamples * sizeof(float));
        std::memcpy(rightInputBuffer.data(), rightInput, numSamples * sizeof(float));
    }
    else
    {
        // No inputs, use silence - PERFORMANCE: Avoid repeated assignments
        if (leftInputBuffer.size() != static_cast<size_t>(numSamples))
        {
            leftInputBuffer.assign(numSamples, 0.0f);
            rightInputBuffer.assign(numSamples, 0.0f);
        }
    }

    // Pre-allocate output buffers (reuse to avoid per-block allocations)
    static std::vector<float> leftOutput;
    static std::vector<float> rightOutput;
    if (leftOutput.size() != static_cast<size_t>(numSamples))
    {
        leftOutput.resize(numSamples);
        rightOutput.resize(numSamples);
    }

    // Process through XG synthesizer with timeout protection
    // NOTE: For true real-time safety, this should be moved to a separate thread
    // with ring buffers. This is a simplified fallback mechanism.
    bool processingSuccess = false;
    auto processStartTime = std::chrono::high_resolution_clock::now();
    
    if (pythonIntegration.processAudioBlock(leftInputBuffer, rightInputBuffer,
                                           leftOutput, rightOutput))
    {
        // Check if processing took too long (超过可用时间的80%表示可能阻塞)
        auto processEndTime = std::chrono::high_resolution_clock::now();
        double processTimeMs = std::chrono::duration<double, std::milli>(processEndTime - processStartTime).count();
        double availableTimeMs = (numSamples / currentSampleRate) * 1000.0;
        
        if (processTimeMs < availableTimeMs * 0.8) // Only use if under 80% of available time
        {
            processingSuccess = true;
        }
        else
        {
            // Processing took too long, increment underrun counter
            performanceMetrics.bufferUnderruns++;
        }
    }
    
    if (processingSuccess)
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
        // Processing failed or took too long, output silence
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
    juce::ValueTree state("XGWorkstationState");
    
    state.setProperty("masterVolume", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Master_Volume)), nullptr);
    state.setProperty("masterPan", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Master_Pan)), nullptr);
    
    state.setProperty("reverbEnable", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Reverb_Enable)), nullptr);
    state.setProperty("reverbTime", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Reverb_Time)), nullptr);
    state.setProperty("reverbLevel", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Reverb_Level)), nullptr);
    
    state.setProperty("chorusEnable", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Chorus_Enable)), nullptr);
    state.setProperty("chorusRate", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Chorus_Rate)), nullptr);
    state.setProperty("chorusDepth", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Chorus_Depth)), nullptr);
    state.setProperty("chorusLevel", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Chorus_Level)), nullptr);
    
    state.setProperty("patternTempo", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Pattern_Tempo)), nullptr);
    state.setProperty("patternSwing", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Pattern_Swing)), nullptr);
    state.setProperty("patternLength", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Pattern_Length)), nullptr);
    
    state.setProperty("variationEnable", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Variation_Enable)), nullptr);
    state.setProperty("variationType", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Variation_Type)), nullptr);
    state.setProperty("variationLevel", parameterManager.getParameterValue(static_cast<int>(XGParameterID::Variation_Level)), nullptr);
    
    std::unique_ptr<juce::XmlElement> xml(state.createXml());
    if (xml != nullptr)
    {
        juce::MemoryOutputStream stream;
        xml->writeToStream(stream, {}, true);
        destData.append(stream.getData(), stream.getDataSize());
    }
}

void XGWorkstationVST3AudioProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    if (data == nullptr || sizeInBytes == 0)
        return;
    
    std::unique_ptr<juce::XmlElement> xml(juce::XmlDocument::parse(juce::String::createStringFromData(data, sizeInBytes)));
    if (xml == nullptr)
        return;
    
    juce::ValueTree state = juce::ValueTree::fromXml(*xml);
    if (!state.isValid() || state.getType() != juce::Identifier("XGWorkstationState"))
        return;
    
    if (state.hasProperty("masterVolume"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Master_Volume), static_cast<float>(state.getProperty("masterVolume")));
    if (state.hasProperty("masterPan"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Master_Pan), static_cast<float>(state.getProperty("masterPan")));
    
    if (state.hasProperty("reverbEnable"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Reverb_Enable), static_cast<float>(state.getProperty("reverbEnable")));
    if (state.hasProperty("reverbTime"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Reverb_Time), static_cast<float>(state.getProperty("reverbTime")));
    if (state.hasProperty("reverbLevel"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Reverb_Level), static_cast<float>(state.getProperty("reverbLevel")));
    
    if (state.hasProperty("chorusEnable"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Chorus_Enable), static_cast<float>(state.getProperty("chorusEnable")));
    if (state.hasProperty("chorusRate"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Chorus_Rate), static_cast<float>(state.getProperty("chorusRate")));
    if (state.hasProperty("chorusDepth"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Chorus_Depth), static_cast<float>(state.getProperty("chorusDepth")));
    if (state.hasProperty("chorusLevel"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Chorus_Level), static_cast<float>(state.getProperty("chorusLevel")));
    
    if (state.hasProperty("patternTempo"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Pattern_Tempo), static_cast<float>(state.getProperty("patternTempo")));
    if (state.hasProperty("patternSwing"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Pattern_Swing), static_cast<float>(state.getProperty("patternSwing")));
    if (state.hasProperty("patternLength"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Pattern_Length), static_cast<float>(state.getProperty("patternLength")));
    
    if (state.hasProperty("variationEnable"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Variation_Enable), static_cast<float>(state.getProperty("variationEnable")));
    if (state.hasProperty("variationType"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Variation_Type), static_cast<float>(state.getProperty("variationType")));
    if (state.hasProperty("variationLevel"))
        parameterManager.setParameterValue(static_cast<int>(XGParameterID::Variation_Level), static_cast<float>(state.getProperty("variationLevel")));
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
    const double alpha = 0.1;
    double currentAvg = performanceMetrics.averageProcessingTime.load();
    performanceMetrics.averageProcessingTime = alpha * processingTimeMs + (1.0 - alpha) * currentAvg;

    auto currentTime = juce::Time::currentTimeMillis();
    auto lastCpu = lastCpuMeasurement.load();
    if (currentTime - lastCpu > 100)
    {
        double cpuUsage = getCurrentCpuUsage();
        double currentPeak = performanceMetrics.peakCpuUsage.load();
        performanceMetrics.averageCpuUsage = alpha * cpuUsage + (1.0 - alpha) * performanceMetrics.averageCpuUsage.load();
        
        double newPeak = std::max(currentPeak, cpuUsage);
        performanceMetrics.peakCpuUsage = newPeak;
        lastCpuMeasurement = static_cast<juce::int64>(currentTime);
    }

    double availableTimeMs = (numSamples / currentSampleRate.load()) * 1000.0;
    if (processingTimeMs > availableTimeMs * 0.9)
    {
        performanceMetrics.bufferUnderruns++;
    }
}

double XGWorkstationVST3AudioProcessor::getCurrentCpuUsage()
{
    // Measure CPU usage based on processing time vs available time
    // This is a simplified implementation - in a real plugin you might want more sophisticated measurement
    auto currentTime = juce::Time::getHighResolutionTicks();
    static auto lastMeasurementTime = currentTime;
    static int measurementCount = 0;
    static double cumulativeUsage = 0.0;
    
    // Get the average processing time from our metrics
    double avgProcessingTime = performanceMetrics.averageProcessingTime.load();
    double sampleRate = currentSampleRate.load();
    int blockSize = currentBlockSize.load();
    
    // Calculate expected processing time for this block
    double availableTimeMs = (blockSize / sampleRate) * 1000.0;
    
    if (availableTimeMs > 0.0 && avgProcessingTime > 0.0)
    {
        // CPU usage = processing time / available time * 100
        double cpuUsage = (avgProcessingTime / availableTimeMs) * 100.0;
        
        // Smooth with exponential moving average
        measurementCount++;
        cumulativeUsage = cumulativeUsage * 0.95 + cpuUsage * 0.05;
        
        return std::max(0.0, std::min(100.0, cumulativeUsage));
    }
    
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

        leftInputBuffer.reserve(optimalSize);
        rightInputBuffer.reserve(optimalSize);

        // Notify Python integration of buffer size change for optimization
        if (xgWorkstationReady)
        {
            pythonIntegration.initialize(currentSampleRate, newBlockSize);
        }

        DBG("Optimized buffer sizes for block size: " + juce::String(newBlockSize));
    }
}

//==============================================================================
// This creates new instances of the plugin for VST3
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new XGWorkstationVST3AudioProcessor();
}
