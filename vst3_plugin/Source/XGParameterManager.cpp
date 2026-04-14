/*
  ==============================================================================

    XGParameterManager.cpp
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

  ==============================================================================
*/

#include "XGParameterManager.h"
#include "PythonIntegration.h"

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
    if (!pythonIntegration)
        return;

    for (auto& [index, value] : parameterValues)
    {
        auto it = parameterInfos.find(index);
        if (it != parameterInfos.end())
        {
            pythonIntegration->setParameter(it->second.name, value);
        }
    }
}

void XGParameterManager::syncParameter(int parameterIndex)
{
    if (!pythonIntegration)
        return;

    auto it = parameterInfos.find(parameterIndex);
    if (it != parameterInfos.end())
    {
        auto valueIt = parameterValues.find(parameterIndex);
        if (valueIt != parameterValues.end())
        {
            pythonIntegration->setParameter(it->second.name, valueIt->second);
        }
    }
}

juce::AudioProcessorValueTreeState::ParameterLayout XGParameterManager::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;

    auto addFloat = [&](const juce::String& id, const juce::String& name,
                        float min, float max, float def, const juce::String& label = {}) {
        layout.add(std::make_unique<juce::AudioParameterFloat>(
            juce::ParameterID(id, 1), name,
            juce::NormalisableRange<float>(min, max, 0.01f),
            def, label));
    };

    auto addBool = [&](const juce::String& id, const juce::String& name, float def = 0.0f) {
        layout.add(std::make_unique<juce::AudioParameterBool>(
            juce::ParameterID(id, 1), name, def));
    };

    auto addChoice = [&](const juce::String& id, const juce::String& name,
                         const juce::StringArray& choices, int def = 0) {
        layout.add(std::make_unique<juce::AudioParameterChoice>(
            juce::ParameterID(id, 1), name, choices, def));
    };

    // Master
    addFloat("master_volume", "Master Volume", 0.0f, 1.0f, 0.8f);
    addFloat("master_pan", "Master Pan", 0.0f, 1.0f, 0.5f);
    addFloat("master_tune", "Master Tune", -100.0f, 100.0f, 0.0f, "cents");
    addFloat("master_transpose", "Master Transpose", -24.0f, 24.0f, 0.0f, "semitones");

    // Transport
    addBool("transport_play", "Play");
    addBool("transport_stop", "Stop");
    addBool("transport_record", "Record");
    addBool("transport_pause", "Pause");

    // Pattern
    addFloat("pattern_tempo", "Tempo", 20.0f, 300.0f, 120.0f, "BPM");
    addFloat("pattern_swing", "Swing", 0.0f, 100.0f, 0.0f, "%");
    addFloat("pattern_length", "Length", 1.0f, 16.0f, 4.0f, "bars");
    addFloat("pattern_quantize", "Quantize", 0.0f, 100.0f, 0.0f, "%");
    addChoice("pattern_select", "Pattern",
              {"Init", "Rock 1", "Rock 2", "Ballad", "Jazz", "Latin", "Pop", "Funk"}, 0);

    // Reverb
    addBool("reverb_enable", "Reverb Enable", 1.0f);
    addChoice("reverb_type", "Reverb Type",
              {"Hall 1", "Hall 2", "Room 1", "Room 2", "Stage", "Plate", "Delay", "Pan Delay"}, 0);
    addFloat("reverb_time", "Reverb Time", 0.1f, 20.0f, 2.5f, "s");
    addFloat("reverb_level", "Reverb Level", 0.0f, 127.0f, 64.0f);
    addFloat("reverb_pre_delay", "Reverb Pre-Delay", 0.0f, 127.0f, 0.0f, "ms");
    addFloat("reverb_hf_damp", "Reverb HF Damp", 0.0f, 127.0f, 127.0f);

    // Chorus
    addBool("chorus_enable", "Chorus Enable", 1.0f);
    addChoice("chorus_type", "Chorus Type",
              {"Chorus 1", "Chorus 2", "Chorus 3", "Chorus 4", "Celeste 1", "Celeste 2", "Flanger", "Phaser"}, 0);
    addFloat("chorus_rate", "Chorus Rate", 0.0f, 127.0f, 32.0f, "Hz");
    addFloat("chorus_depth", "Chorus Depth", 0.0f, 127.0f, 64.0f);
    addFloat("chorus_level", "Chorus Level", 0.0f, 127.0f, 64.0f);
    addFloat("chorus_feedback", "Chorus Feedback", 0.0f, 127.0f, 0.0f);
    addFloat("chorus_delay", "Chorus Delay", 0.0f, 127.0f, 20.0f, "ms");

    // Variation
    addBool("variation_enable", "Variation Enable");
    addFloat("variation_type", "Variation Type", 0.0f, 127.0f, 0.0f);
    addFloat("variation_level", "Variation Level", 0.0f, 127.0f, 0.0f);
    addFloat("variation_param1", "Variation Param 1", 0.0f, 127.0f, 64.0f);
    addFloat("variation_param2", "Variation Param 2", 0.0f, 127.0f, 64.0f);

    // 16 Parts
    for (int i = 0; i < 16; ++i)
    {
        addFloat("part_volume_" + juce::String(i), "Part " + juce::String(i + 1) + " Volume", 0.0f, 127.0f, 100.0f);
        addFloat("part_pan_" + juce::String(i), "Part " + juce::String(i + 1) + " Pan", 0.0f, 127.0f, 64.0f);
        addFloat("part_program_" + juce::String(i), "Part " + juce::String(i + 1) + " Program", 0.0f, 127.0f, 0.0f);
        addFloat("part_reverb_" + juce::String(i), "Part " + juce::String(i + 1) + " Reverb Send", 0.0f, 127.0f, 40.0f);
        addFloat("part_chorus_" + juce::String(i), "Part " + juce::String(i + 1) + " Chorus Send", 0.0f, 127.0f, 0.0f);
        addFloat("part_variation_" + juce::String(i), "Part " + juce::String(i + 1) + " Variation Send", 0.0f, 127.0f, 0.0f);
    }

    return layout;
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

    if (pythonIntegration)
    {
        auto it = parameterInfos.find(parameterIndex);
        if (it != parameterInfos.end())
        {
            pythonIntegration->setParameter(it->second.name, newValue);
        }
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
