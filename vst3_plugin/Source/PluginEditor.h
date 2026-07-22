/*
  ==============================================================================

    PluginEditor.h
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

    Advanced XG Workstation VST3 Plugin Editor with professional UI.
    Thread-safe communication with processor.

  ==============================================================================
*/

#pragma once

#include "AppConfig.h"

#include <array>
#include <map>

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_audio_utils/juce_audio_utils.h>
#include <juce_gui_basics/juce_gui_basics.h>
#include "PluginProcessor.h"

//==============================================================================
class XGWorkstationVST3AudioProcessorEditor  : public juce::AudioProcessorEditor,
                                                public juce::Timer,
                                                public juce::Button::Listener,
                                                public juce::Slider::Listener,
                                                public juce::ComboBox::Listener
{
public:
    XGWorkstationVST3AudioProcessorEditor (XGWorkstationVST3AudioProcessor&);
    ~XGWorkstationVST3AudioProcessorEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

    void timerCallback() override;

    void buttonClicked(juce::Button*) override;
    void sliderValueChanged(juce::Slider*) override;
    void comboBoxChanged(juce::ComboBox*) override;

private:
    XGWorkstationVST3AudioProcessor& audioProcessor;

    juce::TabbedComponent mainTabs;

    juce::Component workstationTab;
    juce::Label workstationTitleLabel;
    juce::TextButton initializeButton;
    juce::TextButton testAudioButton;

    juce::GroupComponent transportGroup;
    juce::TextButton playButton;
    juce::TextButton stopButton;
    juce::TextButton recordButton;
    juce::TextButton pauseButton;
    juce::Label transportStatusLabel;

    juce::GroupComponent patternGroup;
    juce::ComboBox patternSelector;
    juce::TextButton createPatternButton;
    juce::TextButton editPatternButton;
    juce::Label patternInfoLabel;

    juce::GroupComponent masterGroup;
    juce::Slider masterVolumeSlider;
    juce::Label masterVolumeLabel;
    juce::Slider masterPanSlider;
    juce::Label masterPanLabel;

    juce::Component effectsTab;
    juce::Label effectsTitleLabel;

    juce::GroupComponent systemEffectsGroup;
    juce::ComboBox reverbTypeSelector;
    juce::Slider reverbLevelSlider;
    juce::Slider reverbTimeSlider;
    juce::ComboBox chorusTypeSelector;
    juce::Slider chorusLevelSlider;
    juce::Slider chorusDepthSlider;

    juce::GroupComponent variationEffectsGroup;
    juce::ComboBox variationTypeSelector;
    juce::Slider variationLevelSlider;
    juce::Slider variationParam1Slider;
    juce::Slider variationParam2Slider;

    juce::Component statusTab;
    juce::Label statusTitleLabel;

    juce::GroupComponent statusGroup;
    juce::Label pythonStatusLabel;
    juce::Label synthesizerStatusLabel;
    juce::Label sequencerStatusLabel;
    juce::Label audioStatusLabel;
    juce::Label performanceLabel;

    juce::GroupComponent systemInfoGroup;
    juce::Label sampleRateLabel;
    juce::Label bufferSizeLabel;
    juce::Label latencyLabel;
    juce::Label activeVoicesLabel;

    juce::Label errorLabel;

    juce::Component controllersTab;
    juce::Label controllersTitleLabel;

    juce::GroupComponent controllerSelectGroup;
    juce::ComboBox controllerTypeSelector;
    juce::TextButton detectControllersButton;
    juce::Label connectedControllerLabel;

    juce::GroupComponent learningGroup;
    juce::TextButton learnModeButton;
    juce::Label learningStatusLabel;
    juce::TextButton clearMappingsButton;

    juce::GroupComponent transportMapGroup;
    juce::TextButton mapPlayButton;
    juce::TextButton mapStopButton;
    juce::TextButton mapRecordButton;
    juce::Label transportMapStatusLabel;

    juce::Component partsTab;
    juce::Label partsTitleLabel;

    juce::GroupComponent partsGridGroup;
    std::array<juce::TextButton, 16> partButtons;
    std::array<juce::Label, 16> partLabels;
    std::array<juce::Slider, 16> partVolumeSliders;
    std::array<juce::Slider, 16> partPanSliders;
    std::array<juce::ComboBox, 16> partProgramSelectors;
    std::array<juce::Label, 16> partStatusLabels;

    juce::GroupComponent partsControlGroup;
    juce::TextButton selectAllPartsButton;
    juce::TextButton muteAllPartsButton;
    juce::TextButton soloPartButton;
    juce::Slider masterPartsVolumeSlider;
    juce::Label masterPartsVolumeLabel;

    juce::GroupComponent partInfoGroup;
    juce::Label selectedPartInfoLabel;
    juce::Label partVoiceCountLabel;
    juce::Label partMidiChannelLabel;
    juce::TextButton partSettingsButton;

    juce::Component effectsRoutingTab;
    juce::Label effectsRoutingTitleLabel;

    juce::GroupComponent systemEffectsRoutingGroup;
    std::array<juce::Slider, 16> partReverbSendSliders;
    std::array<juce::Slider, 16> partChorusSendSliders;
    juce::Label systemEffectsLabel;
    juce::TextButton systemEffectsBypassButton;

    juce::GroupComponent insertionEffectsGroup;
    std::array<juce::ComboBox, 16> partInsertionEffectSelectors;
    std::array<juce::Slider, 16> partInsertionLevelSliders;
    std::array<juce::TextButton, 16> partInsertionBypassButtons;
    juce::Label insertionEffectsLabel;

    juce::GroupComponent variationEffectsRoutingGroup;
    std::array<juce::ComboBox, 16> partVariationEffectSelectors;
    std::array<juce::Slider, 16> partVariationSendSliders;
    std::array<juce::TextButton, 16> partVariationBypassButtons;
    juce::Label variationEffectsLabel;

    juce::GroupComponent effectsChainGroup;
    juce::TextButton refreshChainButton;
    juce::Label effectsChainDiagramLabel;
    juce::Label totalEffectsLoadLabel;

    juce::Component aiComposerTab;
    juce::Label aiComposerTitleLabel;

    juce::GroupComponent aiPatternGroup;
    juce::ComboBox aiStyleSelector;
    juce::Slider aiCreativitySlider;
    juce::Slider aiComplexitySlider;
    juce::TextButton generatePatternButton;
    juce::TextButton analyzePatternButton;
    juce::Label aiStatusLabel;

    juce::GroupComponent patternVariationGroup;
    juce::TextButton varyRhythmButton;
    juce::TextButton varyHarmonyButton;
    juce::TextButton varyMelodyButton;
    juce::Slider variationAmountSlider;
    juce::Label variationStatusLabel;

    juce::GroupComponent aiTrainingGroup;
    juce::TextButton recordPatternButton;
    juce::TextButton trainModelButton;
    juce::Label trainingStatusLabel;
    juce::ProgressBar trainingProgressBar;
    double trainingProgress = 0.0;

    juce::GroupComponent patternAnalysisGroup;
    juce::Label analysisResultsLabel;
    juce::TextButton analyzeCurrentPatternButton;
    juce::Label patternStatsLabel;

    juce::GroupComponent aiModelGroup;
    juce::ComboBox aiModelSelector;
    juce::TextButton loadModelButton;
    juce::TextButton saveModelButton;
    juce::Label modelStatusLabel;

    struct ControllerMapping
    {
        juce::String controllerName;
        std::map<int, juce::String> ccMappings;
        std::map<juce::String, int> parameterMappings;
    };

    std::map<juce::String, ControllerMapping> controllerDatabase;
    juce::String currentController;
    bool learningMode = false;
    juce::String learningParameter;
    int selectedPart = 0;

    void initializeComponents();
    void setupTabs();
    void setupWorkstationTab();
    void setupEffectsTab();
    void setupStatusTab();
    void setupControllersTab();
    void setupPartsTab();
    void setupEffectsRoutingTab();
    void setupAiComposerTab();

    void layoutWorkstationTab();
    void layoutEffectsTab();
    void layoutStatusTab();
    void layoutControllersTab();
    void layoutPartsTab();
    void layoutEffectsRoutingTab();
    void layoutAiComposerTab();

    void updateStatusDisplay();
    void updateParameterControls();
    void updateXGControls();
    void updatePerformanceDisplay();

    void initializeButtonClicked();
    void testAudioButtonClicked();
    void transportButtonClicked(juce::Button* button);
    void patternButtonClicked(juce::Button* button);
    void effectsControlChanged(juce::Component* control);

    void learnModeButtonClicked();
    void clearMappingsButtonClicked();
    void detectControllersButtonClicked();
    void transportMappingButtonClicked(juce::Button* button);
    void initializeControllerDatabase();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (XGWorkstationVST3AudioProcessorEditor)
};
