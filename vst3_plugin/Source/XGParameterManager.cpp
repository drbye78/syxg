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

    initializeTransportParameters();
    initializePatternParameters();
    initializeSynthesizerParameters();
    initializeEffectsParameters();

    DBG("Parameters initialized: " + juce::String(getNumParameters()));
}

void XGParameterManager::syncWithPython()
{
}

//==============================================================================
void XGParameterManager::parameterChanged(int parameterIndex, float newValue)
{
    parameterValues[parameterIndex] = newValue;

    auto paramId = static_cast<XGParameterID>(parameterIndex);

    switch (paramId)
    {
        case XGParameterID::Transport_Play:
            break;
        case XGParameterID::Transport_Stop:
            break;
        case XGParameterID::Pattern_Tempo:
            break;
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
        if (auto* param = processor->getParameters()[parameterIndex])
        {
            param->setValueNotifyingHost(value);
        }
    }
}

//==============================================================================
void XGParameterManager::registerParameterCallback(XGParameterID paramId,
                                                 std::function<void(float)> callback)
{
    parameterCallbacks[static_cast<int>(paramId)] = callback;
}

void XGParameterManager::registerParameterCallback(int paramIndex,
                                                   std::function<void(float)> callback)
{
    parameterCallbacks[paramIndex] = callback;
}

//==============================================================================
const XGParameterInfo& XGParameterManager::getParameterInfo(int index) const
{
    static XGParameterInfo defaultInfo;
    auto it = parameterInfos.find(index);
    return it != parameterInfos.end() ? it->second : defaultInfo;
}

juce::AudioProcessorParameter* XGParameterManager::getParameter(int index) const
{
    if (processor && index >= 0 && index < processor->getParameters().size())
    {
        return processor->getParameters()[index];
    }
    return nullptr;
}

//==============================================================================
void XGParameterManager::createParameter(int index, const XGParameterInfo& info)
{
    if (!processor)
        return;

    auto* parameter = new juce::AudioParameterFloat(
        juce::ParameterID(info.id, 1),
        info.name,
        juce::NormalisableRange<float>(info.minValue, info.maxValue, info.step),
        info.defaultValue,
        info.label
    );

    processor->addParameter(parameter);
    parameterValues[index] = info.defaultValue;
    parameterInfos[index] = info;
}

//==============================================================================
void XGParameterManager::initializeTransportParameters()
{
    XGParameterInfo info;

    info.id = "TransportPlay"; info.name = "Transport Play"; info.defaultValue = 0.0f;
    createParameter(static_cast<int>(XGParameterID::Transport_Play), info);

    info.id = "TransportStop"; info.name = "Transport Stop"; info.defaultValue = 0.0f;
    createParameter(static_cast<int>(XGParameterID::Transport_Stop), info);

    info.id = "TransportRecord"; info.name = "Transport Record"; info.defaultValue = 0.0f;
    createParameter(static_cast<int>(XGParameterID::Transport_Record), info);

    info.id = "TransportPause"; info.name = "Transport Pause"; info.defaultValue = 0.0f;
    createParameter(static_cast<int>(XGParameterID::Transport_Pause), info);
}

void XGParameterManager::initializePatternParameters()
{
    XGParameterInfo info;

    info.id = "PatternSelect"; info.name = "Pattern Select"; info.minValue = 0.0f; info.maxValue = 127.0f; info.defaultValue = 0.0f;
    createParameter(static_cast<int>(XGParameterID::Pattern_Select), info);

    info.id = "PatternTempo"; info.name = "Pattern Tempo"; info.label = "BPM"; info.minValue = 60.0f; info.maxValue = 200.0f; info.defaultValue = 120.0f;
    createParameter(static_cast<int>(XGParameterID::Pattern_Tempo), info);

    info.id = "PatternSwing"; info.name = "Pattern Swing"; info.label = "%"; info.minValue = 0.0f; info.maxValue = 100.0f; info.defaultValue = 0.0f;
    createParameter(static_cast<int>(XGParameterID::Pattern_Swing), info);

    info.id = "PatternLength"; info.name = "Pattern Length"; info.label = "beats"; info.minValue = 1.0f; info.maxValue = 16.0f; info.defaultValue = 16.0f;
    createParameter(static_cast<int>(XGParameterID::Pattern_Length), info);
}

void XGParameterManager::initializeSynthesizerParameters()
{
    XGParameterInfo info;

    info.id = "MasterVolume"; info.name = "Master Volume"; info.label = "dB"; info.minValue = -60.0f; info.maxValue = 12.0f; info.defaultValue = 0.0f;
    createParameter(static_cast<int>(XGParameterID::Master_Volume), info);

    info.id = "MasterPan"; info.name = "Master Pan"; info.label = ""; info.minValue = -1.0f; info.maxValue = 1.0f; info.defaultValue = 0.0f;
    createParameter(static_cast<int>(XGParameterID::Master_Pan), info);
}

void XGParameterManager::initializeEffectsParameters()
{
    XGParameterInfo info;
    info.minValue = 0.0f; info.maxValue = 1.0f;

    info.id = "ReverbEnable"; info.name = "Reverb Enable"; info.defaultValue = 1.0f;
    createParameter(static_cast<int>(XGParameterID::Reverb_Enable), info);

    info.id = "ReverbTime"; info.name = "Reverb Time"; info.label = "s"; info.minValue = 0.1f; info.maxValue = 10.0f; info.defaultValue = 2.5f;
    createParameter(static_cast<int>(XGParameterID::Reverb_Time), info);

    info.id = "ReverbLevel"; info.name = "Reverb Level"; info.label = ""; info.minValue = 0.0f; info.maxValue = 1.0f; info.defaultValue = 0.6f;
    createParameter(static_cast<int>(XGParameterID::Reverb_Level), info);

    info.id = "ChorusEnable"; info.name = "Chorus Enable"; info.defaultValue = 1.0f;
    createParameter(static_cast<int>(XGParameterID::Chorus_Enable), info);

    info.id = "ChorusRate"; info.name = "Chorus Rate"; info.label = "Hz"; info.minValue = 0.1f; info.maxValue = 10.0f; info.defaultValue = 0.8f;
    createParameter(static_cast<int>(XGParameterID::Chorus_Rate), info);

    info.id = "ChorusDepth"; info.name = "Chorus Depth"; info.label = ""; info.minValue = 0.0f; info.maxValue = 1.0f; info.defaultValue = 0.5f;
    createParameter(static_cast<int>(XGParameterID::Chorus_Depth), info);

    info.id = "ChorusLevel"; info.name = "Chorus Level"; info.defaultValue = 0.4f;
    createParameter(static_cast<int>(XGParameterID::Chorus_Level), info);
}

void XGParameterManager::initializePartParameters()
{
}

void XGParameterManager::setupParameterMetadata()
{
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

    parameterLabels[static_cast<int>(XGParameterID::Pattern_Tempo)] = "BPM";
    parameterLabels[static_cast<int>(XGParameterID::Pattern_Swing)] = "%";
    parameterLabels[static_cast<int>(XGParameterID::Pattern_Length)] = "beats";
    parameterLabels[static_cast<int>(XGParameterID::Master_Volume)] = "dB";
    parameterLabels[static_cast<int>(XGParameterID::Reverb_Time)] = "s";
}

void XGParameterManager::triggerCallback(int index, float value)
{
    auto it = parameterCallbacks.find(index);
    if (it != parameterCallbacks.end())
    {
        it->second(value);
    }
}

juce::ValueTree XGParameterManager::saveState() const
{
    juce::ValueTree state("Parameters");
    for (const auto& kv : parameterValues)
    {
        state.setProperty(juce::String(kv.first), kv.second, nullptr);
    }
    return state;
}

void XGParameterManager::loadState(const juce::ValueTree& state)
{
    for (int i = 0; i < state.getNumProperties(); ++i)
    {
        auto propName = state.getPropertyName(i);
        int index = propName.toString().getIntValue();
        float value = static_cast<float>(state.getProperty(propName));
        setParameterValue(index, value);
    }
}

std::map<int, float> XGParameterManager::getAllParameterValues() const
{
    return parameterValues;
}

void XGParameterManager::setParameterValues(const std::map<int, float>& values)
{
    for (const auto& kv : values)
    {
        setParameterValue(kv.first, kv.second);
    }
}

juce::String XGParameterManager::getParameterName(int index) const
{
    auto it = parameterNames.find(index);
    return it != parameterNames.end() ? it->second : juce::String(index);
}

juce::String XGParameterManager::getParameterValueAsText(int index) const
{
    if (auto* param = getParameter(index))
    {
        return param->getCurrentValueAsText();
    }
    return juce::String(getParameterValue(index));
}

float XGParameterManager::normalizeParameterValue(int index, float value) const
{
    const auto& info = getParameterInfo(index);
    if (info.maxValue > info.minValue)
    {
        return (value - info.minValue) / (info.maxValue - info.minValue);
    }
    return 0.0f;
}

float XGParameterManager::denormalizeParameterValue(int index, float normalized) const
{
    const auto& info = getParameterInfo(index);
    return info.minValue + normalized * (info.maxValue - info.minValue);
}

void XGParameterManager::setPythonIntegration(PythonIntegration* integration)
{
    pythonIntegration = integration;
}

void XGParameterManager::syncParameter(int parameterIndex)
{
}
