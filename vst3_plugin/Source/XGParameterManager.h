/*
  ==============================================================================

    XGParameterManager.h
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

    Manages VST3 parameter mapping, automation, and state persistence
    for XG Workstation with thread-safe operations.

  ==============================================================================
*/

#pragma once

#include "AppConfig.h"

#include <map>
#include <string>
#include <functional>
#include <mutex>
#include <atomic>

#include <juce_audio_processors/juce_audio_processors.h>

class PythonIntegration;

//==============================================================================
enum class XGParameterID
{
    Transport_Play = 0,
    Transport_Stop = 1,
    Transport_Record = 2,
    Transport_Pause = 3,

    Pattern_Select = 10,
    Pattern_Tempo = 11,
    Pattern_Swing = 12,
    Pattern_Length = 13,
    Pattern_Quantize = 14,

    Master_Volume = 100,
    Master_Pan = 101,
    Master_Tune = 102,
    Master_Transpose = 103,

    Reverb_Enable = 200,
    Reverb_Type = 201,
    Reverb_Time = 202,
    Reverb_Level = 203,
    Reverb_PreDelay = 204,
    Reverb_HFDamp = 205,

    Chorus_Enable = 220,
    Chorus_Type = 221,
    Chorus_Rate = 222,
    Chorus_Depth = 223,
    Chorus_Level = 224,
    Chorus_Feedback = 225,
    Chorus_Delay = 226,

    Variation_Enable = 240,
    Variation_Type = 241,
    Variation_Level = 242,
    Variation_Param1 = 243,
    Variation_Param2 = 244,

    Part_Volume_Start = 300,
    Part_Pan_Start = 316,
    Part_Program_Start = 332,
    Part_ReverbSend_Start = 348,
    Part_ChorusSend_Start = 364,
    Part_VariationSend_Start = 380,

    Total_Num_Parameters = 500
};

//==============================================================================
struct XGParameterInfo
{
    juce::String id;
    juce::String name;
    juce::String label;
    float minValue = 0.0f;
    float maxValue = 1.0f;
    float defaultValue = 0.0f;
    float step = 0.01f;
    bool automatable = true;
    bool isDiscrete = false;
    int numSteps = 0;
};

//==============================================================================
class XGParameterManager
{
public:
    XGParameterManager();
    ~XGParameterManager();

    void initializeParameters(juce::AudioProcessor& processor);
    void setPythonIntegration(PythonIntegration* integration);

    juce::AudioProcessorValueTreeState::ParameterLayout createParameterLayout();

    void syncWithPython();
    void syncParameter(int parameterIndex);

    void parameterChanged(int parameterIndex, float newValue);
    float getParameterValue(int parameterIndex) const;
    void setParameterValue(int parameterIndex, float value);

    void registerParameterCallback(XGParameterID paramId, std::function<void(float)> callback);
    void registerParameterCallback(int paramIndex, std::function<void(float)> callback);

    const XGParameterInfo& getParameterInfo(int index) const;
    juce::AudioProcessorParameter* getParameter(int index) const;
    int getNumParameters() const { return static_cast<int>(XGParameterID::Total_Num_Parameters); }

    juce::ValueTree saveState() const;
    void loadState(const juce::ValueTree& state);

    std::map<int, float> getAllParameterValues() const;
    void setParameterValues(const std::map<int, float>& values);

    juce::String getParameterName(int index) const;
    juce::String getParameterValueAsText(int index) const;
    float normalizeParameterValue(int index, float value) const;
    float denormalizeParameterValue(int index, float normalized) const;

private:
    juce::AudioProcessor* processor = nullptr;
    PythonIntegration* pythonIntegration = nullptr;

    mutable std::mutex paramMutex;
    std::map<int, float> parameterValues;
    std::map<int, XGParameterInfo> parameterInfos;
    std::map<int, std::function<void(float)>> parameterCallbacks;
    std::map<int, juce::String> parameterNames;
    std::map<int, juce::String> parameterLabels;

    void createParameter(int index, const XGParameterInfo& info);

    void initializeTransportParameters();
    void initializePatternParameters();
    void initializeSynthesizerParameters();
    void initializeEffectsParameters();
    void initializePartParameters();
    void setupParameterMetadata();
    void triggerCallback(int index, float value);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (XGParameterManager)
};
