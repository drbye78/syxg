/*
  ==============================================================================

    XGParameterManager.cpp
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

  ==============================================================================
*/

#include "XGParameterManager.h"

//==============================================================================
XGParameterManager::XGParameterManager()
    : processor(nullptr)
{
    setupParameterMetadata();
}

XGParameterManager::~XGParameterManager()
{
}

//==============================================================================
void XGParameterManager::initializeParameters(juce::AudioProcessor& audioProcessor)
{
    processor = &audioProcessor;

    // Add parameters to the processor
    initializeTransportParameters();
    initializePatternParameters();
    initializeSynthesizerParameters();
    initializeEffectsParameters();

    DBG("Parameters initialized: " + juce::String(getNumParameters()));
}

void XGParameterManager::syncWithPython()
{
    // This will be called to synchronize parameter values with Python
    // Implementation will be added when Python integration is complete
}

//==============================================================================
void XGParameterManager::parameterChanged(int parameterIndex, float newValue)
{
    parameterValues[parameterIndex] = newValue;

    // Handle parameter changes based on parameter ID
    auto paramId = static_cast<XGParameterID>(parameterIndex);

    switch (paramId)
    {
        case XGParameterID::Transport_Play:
            // Handle play button
            break;
        case XGParameterID::Transport_Stop:
            // Handle stop button
            break;
        case XGParameterID::Pattern_Tempo:
            // Handle tempo change
            break;
        // Add more parameter handling as needed
        default:
            break;
    }
}

float XGParameterManager::getParameterValue(int parameterIndex) const
{
    auto it = parameterValues.find(parameterIndex);
    return it != parameterValues.end() ? it->second : 0.0f;
}

void XGParameterManager::setParameterValue(int parameterIndex, float value)
{
    parameterValues[parameterIndex] = value;

    if (processor)
    {
        processor->setParameterNotifyingHost(parameterIndex, value);
    }
}

//==============================================================================
void XGParameterManager::registerParameterCallback(XGParameterID paramId,
                                                 std::function<void(float)> callback)
{
    parameterCallbacks[static_cast<int>(paramId)] = callback;
}

const juce::AudioProcessorParameter* XGParameterManager::getParameter(int index) const
{
    if (processor)
    {
        return processor->getParameters()[index];
    }
    return nullptr;
}

//==============================================================================
juce::AudioProcessorParameter* XGParameterManager::createParameter(int index,
                                                                  const juce::String& name,
                                                                  const juce::String& label,
                                                                  float minValue,
                                                                  float maxValue,
                                                                  float defaultValue,
                                                                  float step)
{
    if (!processor)
        return nullptr;

    auto* parameter = new juce::AudioParameterFloat(
        juce::String(index),
        name,
        juce::NormalisableRange<float>(minValue, maxValue, step),
        defaultValue,
        label,
        juce::AudioProcessorParameter::genericParameter,
        [](float value, int) { return juce::String(value, 2); },
        [](const juce::String& text) { return text.getFloatValue(); }
    );

    processor->addParameter(parameter);
    parameterValues[index] = defaultValue;

    return parameter;
}

//==============================================================================
void XGParameterManager::initializeTransportParameters()
{
    // Transport control parameters (boolean style)
    createParameter(static_cast<int>(XGParameterID::Transport_Play),
                   "Transport Play", "", 0.0f, 1.0f, 0.0f);

    createParameter(static_cast<int>(XGParameterID::Transport_Stop),
                   "Transport Stop", "", 0.0f, 1.0f, 0.0f);

    createParameter(static_cast<int>(XGParameterID::Transport_Record),
                   "Transport Record", "", 0.0f, 1.0f, 0.0f);

    createParameter(static_cast<int>(XGParameterID::Transport_Pause),
                   "Transport Pause", "", 0.0f, 1.0f, 0.0f);
}

void XGParameterManager::initializePatternParameters()
{
    // Pattern sequencer parameters
    createParameter(static_cast<int>(XGParameterID::Pattern_Select),
                   "Pattern Select", "", 0.0f, 127.0f, 0.0f);

    createParameter(static_cast<int>(XGParameterID::Pattern_Tempo),
                   "Pattern Tempo", "BPM", 60.0f, 200.0f, 120.0f);

    createParameter(static_cast<int>(XGParameterID::Pattern_Swing),
                   "Pattern Swing", "%", 0.0f, 100.0f, 0.0f);

    createParameter(static_cast<int>(XGParameterID::Pattern_Length),
                   "Pattern Length", "beats", 1.0f, 16.0f, 16.0f);
}

void XGParameterManager::initializeSynthesizerParameters()
{
    // Master synthesizer parameters
    createParameter(static_cast<int>(XGParameterID::Master_Volume),
                   "Master Volume", "dB", -60.0f, 12.0f, 0.0f);

    createParameter(static_cast<int>(XGParameterID::Master_Pan),
                   "Master Pan", "", -1.0f, 1.0f, 0.0f);
}

void XGParameterManager::initializeEffectsParameters()
{
    // XG Effects parameters
    createParameter(static_cast<int>(XGParameterID::Reverb_Enable),
                   "Reverb Enable", "", 0.0f, 1.0f, 1.0f);

    createParameter(static_cast<int>(XGParameterID::Reverb_Time),
                   "Reverb Time", "s", 0.1f, 10.0f, 2.5f);

    createParameter(static_cast<int>(XGParameterID::Reverb_Level),
                   "Reverb Level", "", 0.0f, 1.0f, 0.6f);

    createParameter(static_cast<int>(XGParameterID::Chorus_Enable),
                   "Chorus Enable", "", 0.0f, 1.0f, 1.0f);

    createParameter(static_cast<int>(XGParameterID::Chorus_Rate),
                   "Chorus Rate", "Hz", 0.1f, 10.0f, 0.8f);

    createParameter(static_cast<int>(XGParameterID::Chorus_Depth),
                   "Chorus Depth", "", 0.0f, 1.0f, 0.5f);

    createParameter(static_cast<int>(XGParameterID::Chorus_Level),
                   "Chorus Level", "", 0.0f, 1.0f, 0.4f);
}

void XGParameterManager::setupParameterMetadata()
{
    // Set up parameter names and labels for display
    parameterNames[static_cast<int>(XGParameterID::Transport_Play)] = "Play";
    parameterNames[static_cast<int>(XGParameterID::Transport_Stop)] = "Stop";
    parameterNames[static_cast<int>(XGParameterID::Transport_Record)] = "Record";
    parameterNames[static_cast<int>(XGParameterID::Transport_Pause)] = "Pause";

    parameterNames[static_cast<int>(XGParameterID::Pattern_Select)] = "Pattern";
    parameterNames[static_cast<int>(XGParameterID::Pattern_Tempo)] = "Tempo";
    parameterNames[static_cast<int>(XGParameterID::Pattern_Swing)] = "Swing";
    parameterNames[static_cast<int>(XGParameterID::Pattern_Length)] = "Length";

    parameterNames[static_cast<int>(XGParameterID::Master_Volume)] = "Volume";
    parameterNames[static_cast<int>(XGParameterID::Master_Pan)] = "Pan";

    parameterNames[static_cast<int>(XGParameterID::Reverb_Enable)] = "Reverb On";
    parameterNames[static_cast<int>(XGParameterID::Reverb_Time)] = "Reverb Time";
    parameterNames[static_cast<int>(XGParameterID::Reverb_Level)] = "Reverb Level";
    parameterNames[static_cast<int>(XGParameterID::Chorus_Enable)] = "Chorus On";
    parameterNames[static_cast<int>(XGParameterID::Chorus_Rate)] = "Chorus Rate";
    parameterNames[static_cast<int>(XGParameterID::Chorus_Depth)] = "Chorus Depth";
    parameterNames[static_cast<int>(XGParameterID::Chorus_Level)] = "Chorus Level";

    // Set labels
    parameterLabels[static_cast<int>(XGParameterID::Pattern_Tempo)] = "BPM";
    parameterLabels[static_cast<int>(XGParameterID::Pattern_Swing)] = "%";
    parameterLabels[static_cast<int>(XGParameterID::Pattern_Length)] = "beats";
    parameterLabels[static_cast<int>(XGParameterID::Master_Volume)] = "dB";
    parameterLabels[static_cast<int>(XGParameterID::Reverb_Time)] = "s";
}
