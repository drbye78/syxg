/*
  ==============================================================================

    PluginEditor.cpp
    Created: 17 Jan 2026
    Author: XG Synthesizer Team

  ==============================================================================
*/

#include "PluginProcessor.h"
#include "PluginEditor.h"

//==============================================================================
XGWorkstationVST3AudioProcessorEditor::XGWorkstationVST3AudioProcessorEditor (XGWorkstationVST3AudioProcessor& p)
    : AudioProcessorEditor (&p),
      audioProcessor (p),
      mainTabs(juce::TabbedButtonBar::TabsAtTop),
      trainingProgressBar(trainingProgress)
{
    setSize (800, 600);

    initializeComponents();
    setupTabs();

    startTimer(500);
}

XGWorkstationVST3AudioProcessorEditor::~XGWorkstationVST3AudioProcessorEditor()
{
    stopTimer();
}

//==============================================================================
void XGWorkstationVST3AudioProcessorEditor::paint (juce::Graphics& g)
{
    // Fill background with professional gradient
    juce::ColourGradient gradient(
        juce::Colours::darkgrey.brighter(0.1f), 0, 0,
        juce::Colours::darkgrey.darker(0.2f), 0, getHeight(),
        false
    );
    g.setGradientFill(gradient);
    g.fillAll();

    // Draw title
    g.setColour (juce::Colours::white);
    g.setFont (24.0f);
    g.drawFittedText ("XG Workstation VST3", getLocalBounds().reduced(20).removeFromTop(40),
                     juce::Justification::centred, 1);

    // Draw version info
    g.setColour (juce::Colours::lightgrey);
    g.setFont (12.0f);
    g.drawFittedText ("Professional XG Synthesis & Pattern Sequencing",
                     getLocalBounds().reduced(20).removeFromTop(60).removeFromTop(15),
                     juce::Justification::centred, 1);
}

void XGWorkstationVST3AudioProcessorEditor::resized()
{
    auto area = getLocalBounds().reduced(10);

    // Title area
    area.removeFromTop(60);

    // Main tabbed interface
    mainTabs.setBounds(area);

    // Layout all tabs (safe to call even for hidden tabs)
    layoutWorkstationTab();
    layoutEffectsTab();
    layoutStatusTab();
    layoutControllersTab();
    layoutPartsTab();
    layoutEffectsRoutingTab();
    layoutAiComposerTab();
}

void XGWorkstationVST3AudioProcessorEditor::layoutWorkstationTab()
{
    auto area = workstationTab.getLocalBounds().reduced(10);

    // Title
    workstationTitleLabel.setBounds(area.removeFromTop(30));

    // Initialize and test buttons
    auto buttonArea = area.removeFromTop(40);
    initializeButton.setBounds(buttonArea.removeFromLeft(150));
    buttonArea.removeFromLeft(10);
    testAudioButton.setBounds(buttonArea.removeFromLeft(100));

    area.removeFromTop(10);

    // Transport controls
    auto transportArea = area.removeFromTop(100);
    transportGroup.setBounds(transportArea);

    auto transportInner = transportArea.reduced(10);
    auto buttonRow = transportInner.removeFromTop(30);
    playButton.setBounds(buttonRow.removeFromLeft(50));
    buttonRow.removeFromLeft(5);
    stopButton.setBounds(buttonRow.removeFromLeft(50));
    buttonRow.removeFromLeft(5);
    recordButton.setBounds(buttonRow.removeFromLeft(60));
    buttonRow.removeFromLeft(5);
    pauseButton.setBounds(buttonRow.removeFromLeft(50));

    transportInner.removeFromTop(5);
    transportStatusLabel.setBounds(transportInner.removeFromTop(20));

    area.removeFromTop(10);

    // Pattern controls
    auto patternArea = area.removeFromTop(120);
    patternGroup.setBounds(patternArea);

    auto patternInner = patternArea.reduced(10);
    patternSelector.setBounds(patternInner.removeFromTop(25));

    patternInner.removeFromTop(5);
    auto patternButtons = patternInner.removeFromTop(25);
    createPatternButton.setBounds(patternButtons.removeFromLeft(100));
    patternButtons.removeFromLeft(10);
    editPatternButton.setBounds(patternButtons.removeFromLeft(100));

    patternInner.removeFromTop(5);
    patternInfoLabel.setBounds(patternInner.removeFromTop(20));

    area.removeFromTop(10);

    // Master controls
    auto masterArea = area.removeFromTop(100);
    masterGroup.setBounds(masterArea);

    auto masterInner = masterArea.reduced(10);
    auto volumeRow = masterInner.removeFromTop(25);
    masterVolumeLabel.setBounds(volumeRow.removeFromLeft(50));
    volumeRow.removeFromLeft(5);
    masterVolumeSlider.setBounds(volumeRow);

    masterInner.removeFromTop(5);
    auto panRow = masterInner.removeFromTop(25);
    masterPanLabel.setBounds(panRow.removeFromLeft(30));
    panRow.removeFromLeft(5);
    masterPanSlider.setBounds(panRow);
}

void XGWorkstationVST3AudioProcessorEditor::layoutEffectsTab()
{
    auto area = effectsTab.getLocalBounds().reduced(10);

    // Title
    effectsTitleLabel.setBounds(area.removeFromTop(30));
    area.removeFromTop(10);

    // System Effects
    auto systemArea = area.removeFromTop(180);
    systemEffectsGroup.setBounds(systemArea);

    auto systemInner = systemArea.reduced(10);

    // Reverb controls
    auto reverbRow = systemInner.removeFromTop(25);
    reverbTypeSelector.setBounds(reverbRow.removeFromLeft(80));
    reverbRow.removeFromLeft(10);
    reverbLevelSlider.setBounds(reverbRow.removeFromLeft(100));
    reverbRow.removeFromLeft(10);
    reverbTimeSlider.setBounds(reverbRow);

    systemInner.removeFromTop(10);

    // Chorus controls
    auto chorusRow = systemInner.removeFromTop(25);
    chorusTypeSelector.setBounds(chorusRow.removeFromLeft(80));
    chorusRow.removeFromLeft(10);
    chorusLevelSlider.setBounds(chorusRow.removeFromLeft(100));
    chorusRow.removeFromLeft(10);
    chorusDepthSlider.setBounds(chorusRow);

    area.removeFromTop(20);

    // Variation Effects
    auto variationArea = area.removeFromTop(140);
    variationEffectsGroup.setBounds(variationArea);

    auto variationInner = variationArea.reduced(10);

    // Variation type selector
    variationTypeSelector.setBounds(variationInner.removeFromTop(25));

    variationInner.removeFromTop(10);

    // Variation parameters
    auto param1Row = variationInner.removeFromTop(25);
    variationLevelSlider.setBounds(param1Row.removeFromLeft(100));
    param1Row.removeFromLeft(10);
    variationParam1Slider.setBounds(param1Row.removeFromLeft(100));
    param1Row.removeFromLeft(10);
    variationParam2Slider.setBounds(param1Row);
}

void XGWorkstationVST3AudioProcessorEditor::layoutStatusTab()
{
    auto area = statusTab.getLocalBounds().reduced(10);

    // Title
    statusTitleLabel.setBounds(area.removeFromTop(30));
    area.removeFromTop(10);

    // Status indicators
    auto statusArea = area.removeFromTop(140);
    statusGroup.setBounds(statusArea);

    auto statusInner = statusArea.reduced(10);
    pythonStatusLabel.setBounds(statusInner.removeFromTop(20));
    synthesizerStatusLabel.setBounds(statusInner.removeFromTop(20));
    sequencerStatusLabel.setBounds(statusInner.removeFromTop(20));
    audioStatusLabel.setBounds(statusInner.removeFromTop(20));
    performanceLabel.setBounds(statusInner.removeFromTop(20));

    area.removeFromTop(20);

    // System info
    auto systemArea = area.removeFromTop(120);
    systemInfoGroup.setBounds(systemArea);

    auto systemInner = systemArea.reduced(10);
    sampleRateLabel.setBounds(systemInner.removeFromTop(20));
    bufferSizeLabel.setBounds(systemInner.removeFromTop(20));
    latencyLabel.setBounds(systemInner.removeFromTop(20));
    activeVoicesLabel.setBounds(systemInner.removeFromTop(20));
}

//==============================================================================
void XGWorkstationVST3AudioProcessorEditor::timerCallback()
{
    updateStatusDisplay();
    updateParameterControls();
    updateXGControls();
}

void XGWorkstationVST3AudioProcessorEditor::buttonClicked(juce::Button* button)
{
    if (button == &initializeButton)
        initializeButtonClicked();
    else if (button == &testAudioButton)
        testAudioButtonClicked();
    else if (button == &playButton || button == &stopButton || button == &recordButton || button == &pauseButton)
        transportButtonClicked(button);
    else if (button == &createPatternButton || button == &editPatternButton)
        patternButtonClicked(button);
    else if (button == &learnModeButton)
        learnModeButtonClicked();
    else if (button == &clearMappingsButton)
        clearMappingsButtonClicked();
    else if (button == &detectControllersButton)
        detectControllersButtonClicked();
    else if (button == &mapPlayButton || button == &mapStopButton || button == &mapRecordButton)
        transportMappingButtonClicked(button);
}

void XGWorkstationVST3AudioProcessorEditor::sliderValueChanged(juce::Slider* slider)
{
    // Handle parameter changes and send to processor
    if (slider == &masterVolumeSlider)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Master_Volume), 
            static_cast<float>(masterVolumeSlider.getValue()));
    }
    else if (slider == &masterPanSlider)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Master_Pan), 
            static_cast<float>(masterPanSlider.getValue()));
    }
    else if (slider == &reverbLevelSlider)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Reverb_Level), 
            static_cast<float>(reverbLevelSlider.getValue()));
    }
    else if (slider == &reverbTimeSlider)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Reverb_Time), 
            static_cast<float>(reverbTimeSlider.getValue()));
    }
    else if (slider == &chorusLevelSlider)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Chorus_Level), 
            static_cast<float>(chorusLevelSlider.getValue()));
    }
    else if (slider == &chorusDepthSlider)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Chorus_Depth), 
            static_cast<float>(chorusDepthSlider.getValue()));
    }
    else if (slider == &variationLevelSlider)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Variation_Level), 
            static_cast<float>(variationLevelSlider.getValue()));
    }
    else if (slider == &variationParam1Slider)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Variation_Param1), 
            static_cast<float>(variationParam1Slider.getValue()));
    }
    else if (slider == &variationParam2Slider)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Variation_Param2), 
            static_cast<float>(variationParam2Slider.getValue()));
    }
}

void XGWorkstationVST3AudioProcessorEditor::comboBoxChanged(juce::ComboBox* comboBox)
{
    // Handle combo box changes for effect type selectors
    if (comboBox == &reverbTypeSelector)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Reverb_Type),
            static_cast<float>(reverbTypeSelector.getSelectedId()));
    }
    else if (comboBox == &chorusTypeSelector)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Chorus_Type),
            static_cast<float>(chorusTypeSelector.getSelectedId()));
    }
    else if (comboBox == &variationTypeSelector)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Variation_Type),
            static_cast<float>(variationTypeSelector.getSelectedId()));
    }
    else if (comboBox == &patternSelector)
    {
        audioProcessor.getParameterManager().setParameterValue(
            static_cast<int>(XGParameterID::Pattern_Select),
            static_cast<float>(patternSelector.getSelectedId()));
    }
}

//==============================================================================
void XGWorkstationVST3AudioProcessorEditor::initializeComponents()
{
    // Set up tabbed component - only include functional tabs
    mainTabs.addTab("Workstation", juce::Colours::darkgrey.brighter(0.1f), &workstationTab, false);
    mainTabs.addTab("XG Effects", juce::Colours::darkgrey.brighter(0.1f), &effectsTab, false);
    mainTabs.addTab("Status", juce::Colours::darkgrey.brighter(0.1f), &statusTab, false);
    // TODO: Re-enable when implemented: Controllers, Parts, Effects Routing, AI Composer
    // mainTabs.addTab("Controllers", juce::Colours::darkgrey.brighter(0.1f), &controllersTab, false);
    // mainTabs.addTab("Parts", juce::Colours::darkgrey.brighter(0.1f), &partsTab, false);
    // mainTabs.addTab("Effects Routing", juce::Colours::darkgrey.brighter(0.1f), &effectsRoutingTab, false);
    // mainTabs.addTab("AI Composer", juce::Colours::darkgrey.brighter(0.1f), &aiComposerTab, false);
    addAndMakeVisible(mainTabs);

    // Register listeners for UI controls
    masterVolumeSlider.addListener(this);
    masterPanSlider.addListener(this);
    reverbLevelSlider.addListener(this);
    reverbTimeSlider.addListener(this);
    chorusLevelSlider.addListener(this);
    chorusDepthSlider.addListener(this);
    variationLevelSlider.addListener(this);
    variationParam1Slider.addListener(this);
    variationParam2Slider.addListener(this);
    
    reverbTypeSelector.addListener(this);
    chorusTypeSelector.addListener(this);
    variationTypeSelector.addListener(this);
    patternSelector.addListener(this);

    // Register button listeners
    initializeButton.addListener(this);
    testAudioButton.addListener(this);
    playButton.addListener(this);
    stopButton.addListener(this);
    recordButton.addListener(this);
    pauseButton.addListener(this);
    createPatternButton.addListener(this);
    editPatternButton.addListener(this);

    // Initialize controller database with known controllers
    initializeControllerDatabase();
}

void XGWorkstationVST3AudioProcessorEditor::setupTabs()
{
    setupWorkstationTab();
    setupEffectsTab();
    setupStatusTab();
}

//==============================================================================
// AI Composer Methods (Phase 7 - AI-Assisted Pattern Generation)

void XGWorkstationVST3AudioProcessorEditor::setupAiComposerTab()
{
    // Title
    aiComposerTitleLabel.setText("AI-Assisted Pattern Generation & Composition", juce::dontSendNotification);
    aiComposerTitleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    aiComposerTitleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    aiComposerTab.addAndMakeVisible(aiComposerTitleLabel);

    // AI Pattern Generation
    aiPatternGroup.setText("AI Pattern Generation");
    aiPatternGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    aiPatternGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    aiComposerTab.addAndMakeVisible(aiPatternGroup);

    // Style selector for AI generation
    aiStyleSelector.addItem("Classical", 1);
    aiStyleSelector.addItem("Jazz", 2);
    aiStyleSelector.addItem("Rock", 3);
    aiStyleSelector.addItem("Electronic", 4);
    aiStyleSelector.addItem("World Music", 5);
    aiStyleSelector.addItem("Experimental", 6);
    aiStyleSelector.setSelectedId(1);
    aiPatternGroup.addAndMakeVisible(aiStyleSelector);

    // AI creativity and complexity controls
    aiCreativitySlider.setRange(0.0, 1.0, 0.01);
    aiCreativitySlider.setValue(0.7);
    aiCreativitySlider.setSliderStyle(juce::Slider::LinearHorizontal);
    aiCreativitySlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    aiPatternGroup.addAndMakeVisible(aiCreativitySlider);

    aiComplexitySlider.setRange(0.0, 1.0, 0.01);
    aiComplexitySlider.setValue(0.5);
    aiComplexitySlider.setSliderStyle(juce::Slider::LinearHorizontal);
    aiComplexitySlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    aiPatternGroup.addAndMakeVisible(aiComplexitySlider);

    // Generate pattern button
    generatePatternButton.setButtonText("Generate AI Pattern");
    generatePatternButton.setColour(juce::TextButton::buttonColourId, juce::Colours::purple);
    aiPatternGroup.addAndMakeVisible(generatePatternButton);

    // Analyze current pattern
    analyzePatternButton.setButtonText("Analyze Current Pattern");
    analyzePatternButton.setColour(juce::TextButton::buttonColourId, juce::Colours::blue);
    aiPatternGroup.addAndMakeVisible(analyzePatternButton);

    // AI status display
    aiStatusLabel.setText("AI Model: Ready | Patterns generated: 0", juce::dontSendNotification);
    aiStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    aiPatternGroup.addAndMakeVisible(aiStatusLabel);

    // Pattern Variation
    patternVariationGroup.setText("Pattern Variation & Transformation");
    patternVariationGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    patternVariationGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    aiComposerTab.addAndMakeVisible(patternVariationGroup);

    // Variation buttons for different musical elements
    varyRhythmButton.setButtonText("Vary Rhythm");
    varyRhythmButton.setColour(juce::TextButton::buttonColourId, juce::Colours::orange);
    patternVariationGroup.addAndMakeVisible(varyRhythmButton);

    varyHarmonyButton.setButtonText("Vary Harmony");
    varyHarmonyButton.setColour(juce::TextButton::buttonColourId, juce::Colours::green);
    patternVariationGroup.addAndMakeVisible(varyHarmonyButton);

    varyMelodyButton.setButtonText("Vary Melody");
    varyMelodyButton.setColour(juce::TextButton::buttonColourId, juce::Colours::cyan);
    patternVariationGroup.addAndMakeVisible(varyMelodyButton);

    // Variation amount control
    variationAmountSlider.setRange(0.0, 1.0, 0.01);
    variationAmountSlider.setValue(0.3);
    variationAmountSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    variationAmountSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    patternVariationGroup.addAndMakeVisible(variationAmountSlider);

    // Variation status
    variationStatusLabel.setText("Variation ready - Select pattern to vary", juce::dontSendNotification);
    variationStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    patternVariationGroup.addAndMakeVisible(variationStatusLabel);

    // AI Training Data
    aiTrainingGroup.setText("AI Training & Learning");
    aiTrainingGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    aiTrainingGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    aiComposerTab.addAndMakeVisible(aiTrainingGroup);

    // Record patterns for training
    recordPatternButton.setButtonText("Record Pattern for Training");
    recordPatternButton.setColour(juce::TextButton::buttonColourId, juce::Colours::red);
    aiTrainingGroup.addAndMakeVisible(recordPatternButton);

    // Train model
    trainModelButton.setButtonText("Train AI Model");
    trainModelButton.setColour(juce::TextButton::buttonColourId, juce::Colours::darkred);
    aiTrainingGroup.addAndMakeVisible(trainModelButton);

    // Training status and progress
    trainingStatusLabel.setText("Training data: 0 patterns | Model: Not trained", juce::dontSendNotification);
    trainingStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    aiTrainingGroup.addAndMakeVisible(trainingStatusLabel);

    // Progress bar for training (initially hidden)
    trainingProgressBar.setPercentageDisplay(false);
    trainingProgressBar.setColour(juce::ProgressBar::backgroundColourId, juce::Colours::darkgrey);
    trainingProgressBar.setColour(juce::ProgressBar::foregroundColourId, juce::Colours::green);
    aiTrainingGroup.addAndMakeVisible(trainingProgressBar);

    // Pattern Analysis
    patternAnalysisGroup.setText("Pattern Analysis & Statistics");
    patternAnalysisGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    patternAnalysisGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    aiComposerTab.addAndMakeVisible(patternAnalysisGroup);

    // Analysis results display
    analysisResultsLabel.setText("Analysis: No pattern analyzed yet", juce::dontSendNotification);
    analysisResultsLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    patternAnalysisGroup.addAndMakeVisible(analysisResultsLabel);

    // Analyze current pattern button
    analyzeCurrentPatternButton.setButtonText("Analyze Current Pattern");
    analyzeCurrentPatternButton.setColour(juce::TextButton::buttonColourId, juce::Colours::blue);
    patternAnalysisGroup.addAndMakeVisible(analyzeCurrentPatternButton);

    // Pattern statistics
    patternStatsLabel.setText("Stats: Notes: 0 | Duration: 0s | Complexity: 0", juce::dontSendNotification);
    patternStatsLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    patternAnalysisGroup.addAndMakeVisible(patternStatsLabel);

    // AI Model Management
    aiModelGroup.setText("AI Model Management");
    aiModelGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    aiModelGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    aiComposerTab.addAndMakeVisible(aiModelGroup);

    // Model selector
    aiModelSelector.addItem("Basic Pattern Generator", 1);
    aiModelSelector.addItem("Advanced Style Model", 2);
    aiModelSelector.addItem("Custom Trained Model", 3);
    aiModelSelector.setSelectedId(1);
    aiModelGroup.addAndMakeVisible(aiModelSelector);

    // Model management buttons
    loadModelButton.setButtonText("Load Model");
    loadModelButton.setColour(juce::TextButton::buttonColourId, juce::Colours::blue);
    aiModelGroup.addAndMakeVisible(loadModelButton);

    saveModelButton.setButtonText("Save Model");
    saveModelButton.setColour(juce::TextButton::buttonColourId, juce::Colours::green);
    aiModelGroup.addAndMakeVisible(saveModelButton);

    // Model status
    modelStatusLabel.setText("Model Status: Basic generator loaded", juce::dontSendNotification);
    modelStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    aiModelGroup.addAndMakeVisible(modelStatusLabel);

    DBG("AI Composer tab initialized with pattern generation and analysis controls");
}

void XGWorkstationVST3AudioProcessorEditor::layoutAiComposerTab()
{
    auto area = aiComposerTab.getLocalBounds().reduced(10);

    // Title
    aiComposerTitleLabel.setBounds(area.removeFromTop(30));
    area.removeFromTop(10);

    // AI Pattern Generation (top section)
    auto patternArea = area.removeFromTop(150);
    aiPatternGroup.setBounds(patternArea);

    auto patternInner = patternArea.reduced(10);
    auto styleRow = patternInner.removeFromTop(25);
    aiStyleSelector.setBounds(styleRow.removeFromLeft(150));

    auto sliderRow1 = patternInner.removeFromTop(25);
    aiCreativitySlider.setBounds(sliderRow1);

    auto sliderRow2 = patternInner.removeFromTop(25);
    aiComplexitySlider.setBounds(sliderRow2);

    auto buttonRow1 = patternInner.removeFromTop(30);
    generatePatternButton.setBounds(buttonRow1.removeFromLeft(140));
    buttonRow1.removeFromLeft(10);
    analyzePatternButton.setBounds(buttonRow1.removeFromLeft(140));

    patternInner.removeFromTop(5);
    aiStatusLabel.setBounds(patternInner.removeFromTop(20));

    area.removeFromTop(10);

    // Pattern Variation (middle section)
    auto variationArea = area.removeFromTop(120);
    patternVariationGroup.setBounds(variationArea);

    auto variationInner = variationArea.reduced(10);
    auto varButtonRow = variationInner.removeFromTop(30);
    varyRhythmButton.setBounds(varButtonRow.removeFromLeft(100));
    varButtonRow.removeFromLeft(5);
    varyHarmonyButton.setBounds(varButtonRow.removeFromLeft(100));
    varButtonRow.removeFromLeft(5);
    varyMelodyButton.setBounds(varButtonRow.removeFromLeft(100));

    variationInner.removeFromTop(5);
    variationAmountSlider.setBounds(variationInner.removeFromTop(25));

    variationInner.removeFromTop(5);
    variationStatusLabel.setBounds(variationInner.removeFromTop(20));

    area.removeFromTop(10);

    // AI Training & Pattern Analysis (bottom sections - side by side)
    auto bottomArea = area.removeFromTop(200);

    // Training section (left)
    auto trainingArea = bottomArea.removeFromLeft(bottomArea.getWidth() / 2 - 5);
    aiTrainingGroup.setBounds(trainingArea);

    auto trainingInner = trainingArea.reduced(10);
    recordPatternButton.setBounds(trainingInner.removeFromTop(30));
    trainingInner.removeFromTop(5);
    trainModelButton.setBounds(trainingInner.removeFromTop(30));
    trainingInner.removeFromTop(5);
    trainingStatusLabel.setBounds(trainingInner.removeFromTop(20));
    trainingInner.removeFromTop(5);
    trainingProgressBar.setBounds(trainingInner.removeFromTop(20));

    bottomArea.removeFromLeft(10);

    // Analysis section (right)
    auto analysisArea = bottomArea;
    patternAnalysisGroup.setBounds(analysisArea);

    auto analysisInner = analysisArea.reduced(10);
    analysisResultsLabel.setBounds(analysisInner.removeFromTop(20));
    analysisInner.removeFromTop(5);
    analyzeCurrentPatternButton.setBounds(analysisInner.removeFromTop(30));
    analysisInner.removeFromTop(5);
    patternStatsLabel.setBounds(analysisInner.removeFromTop(20));

    area.removeFromTop(10);

    // AI Model Management (bottom)
    auto modelArea = area.removeFromTop(100);
    aiModelGroup.setBounds(modelArea);

    auto modelInner = modelArea.reduced(10);
    aiModelSelector.setBounds(modelInner.removeFromTop(25));
    modelInner.removeFromTop(5);

    auto modelButtonRow = modelInner.removeFromTop(30);
    loadModelButton.setBounds(modelButtonRow.removeFromLeft(100));
    modelButtonRow.removeFromLeft(10);
    saveModelButton.setBounds(modelButtonRow.removeFromLeft(100));

    modelInner.removeFromTop(5);
    modelStatusLabel.setBounds(modelInner.removeFromTop(20));
}

void XGWorkstationVST3AudioProcessorEditor::setupWorkstationTab()
{
    // Title
    workstationTitleLabel.setText("XG Workstation Control", juce::dontSendNotification);
    workstationTitleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    workstationTitleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    workstationTab.addAndMakeVisible(workstationTitleLabel);

    // Initialize and test buttons
    initializeButton.setButtonText("Initialize Workstation");
    initializeButton.setColour(juce::TextButton::buttonColourId, juce::Colours::green);
    workstationTab.addAndMakeVisible(initializeButton);

    testAudioButton.setButtonText("Test Audio");
    testAudioButton.setColour(juce::TextButton::buttonColourId, juce::Colours::blue);
    workstationTab.addAndMakeVisible(testAudioButton);

    // Transport controls
    transportGroup.setText("Transport Control");
    transportGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    transportGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    workstationTab.addAndMakeVisible(transportGroup);

    playButton.setButtonText("▶ Play");
    playButton.setColour(juce::TextButton::buttonColourId, juce::Colours::green);
    transportGroup.addAndMakeVisible(playButton);

    stopButton.setButtonText("⏹ Stop");
    stopButton.setColour(juce::TextButton::buttonColourId, juce::Colours::red);
    transportGroup.addAndMakeVisible(stopButton);

    recordButton.setButtonText("⏺ Record");
    recordButton.setColour(juce::TextButton::buttonColourId, juce::Colours::red.brighter());
    transportGroup.addAndMakeVisible(recordButton);

    pauseButton.setButtonText("⏸ Pause");
    pauseButton.setColour(juce::TextButton::buttonColourId, juce::Colours::orange);
    transportGroup.addAndMakeVisible(pauseButton);

    transportStatusLabel.setText("Transport: Stopped", juce::dontSendNotification);
    transportStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    transportGroup.addAndMakeVisible(transportStatusLabel);

    // Pattern controls
    patternGroup.setText("Pattern Sequencer");
    patternGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    patternGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    workstationTab.addAndMakeVisible(patternGroup);

    patternSelector.addItem("Pattern 1 (C Major)", 1);
    patternSelector.addItem("Pattern 2 (D Minor)", 2);
    patternSelector.addItem("Pattern 3 (G Major)", 3);
    patternSelector.setSelectedId(1);
    patternGroup.addAndMakeVisible(patternSelector);

    createPatternButton.setButtonText("Create Pattern");
    patternGroup.addAndMakeVisible(createPatternButton);

    editPatternButton.setButtonText("Edit Pattern");
    patternGroup.addAndMakeVisible(editPatternButton);

    patternInfoLabel.setText("4 notes, 120 BPM, 4 bars", juce::dontSendNotification);
    patternInfoLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    patternGroup.addAndMakeVisible(patternInfoLabel);

    // Master controls
    masterGroup.setText("Master Controls");
    masterGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    masterGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    workstationTab.addAndMakeVisible(masterGroup);

    masterVolumeSlider.setRange(0.0, 1.0, 0.01);
    masterVolumeSlider.setValue(0.8);
    masterVolumeSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    masterVolumeSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    masterGroup.addAndMakeVisible(masterVolumeSlider);

    masterVolumeLabel.setText("Volume", juce::dontSendNotification);
    masterVolumeLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    masterGroup.addAndMakeVisible(masterVolumeLabel);

    masterPanSlider.setRange(-1.0, 1.0, 0.01);
    masterPanSlider.setValue(0.0);
    masterPanSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    masterPanSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    masterGroup.addAndMakeVisible(masterPanSlider);

    masterPanLabel.setText("Pan", juce::dontSendNotification);
    masterPanLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    masterGroup.addAndMakeVisible(masterPanLabel);
}

void XGWorkstationVST3AudioProcessorEditor::setupEffectsTab()
{
    // Title
    effectsTitleLabel.setText("XG Effects Processing", juce::dontSendNotification);
    effectsTitleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    effectsTitleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    effectsTab.addAndMakeVisible(effectsTitleLabel);

    // System Effects
    systemEffectsGroup.setText("System Effects");
    systemEffectsGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    systemEffectsGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    effectsTab.addAndMakeVisible(systemEffectsGroup);

    // Reverb controls
    reverbTypeSelector.addItem("Hall 1", 1);
    reverbTypeSelector.addItem("Hall 2", 2);
    reverbTypeSelector.addItem("Room 1", 3);
    reverbTypeSelector.addItem("Room 2", 4);
    reverbTypeSelector.addItem("Plate", 5);
    reverbTypeSelector.setSelectedId(2);
    systemEffectsGroup.addAndMakeVisible(reverbTypeSelector);

    reverbLevelSlider.setRange(0.0, 1.0, 0.01);
    reverbLevelSlider.setValue(0.6);
    reverbLevelSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    reverbLevelSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    systemEffectsGroup.addAndMakeVisible(reverbLevelSlider);

    reverbTimeSlider.setRange(0.1, 10.0, 0.1);
    reverbTimeSlider.setValue(2.5);
    reverbTimeSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    reverbTimeSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    systemEffectsGroup.addAndMakeVisible(reverbTimeSlider);

    // Chorus controls
    chorusTypeSelector.addItem("Chorus 1", 1);
    chorusTypeSelector.addItem("Chorus 2", 2);
    chorusTypeSelector.addItem("Flanger", 3);
    chorusTypeSelector.addItem("Phaser", 4);
    chorusTypeSelector.setSelectedId(1);
    systemEffectsGroup.addAndMakeVisible(chorusTypeSelector);

    chorusLevelSlider.setRange(0.0, 1.0, 0.01);
    chorusLevelSlider.setValue(0.4);
    chorusLevelSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    chorusLevelSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    systemEffectsGroup.addAndMakeVisible(chorusLevelSlider);

    chorusDepthSlider.setRange(0.0, 1.0, 0.01);
    chorusDepthSlider.setValue(0.5);
    chorusDepthSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    chorusDepthSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    systemEffectsGroup.addAndMakeVisible(chorusDepthSlider);

    // Variation Effects
    variationEffectsGroup.setText("Variation Effects");
    variationEffectsGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    variationEffectsGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    effectsTab.addAndMakeVisible(variationEffectsGroup);

    variationTypeSelector.addItem("Delay LCR", 13);
    variationTypeSelector.addItem("Delay LR", 14);
    variationTypeSelector.addItem("Distortion", 15);
    variationTypeSelector.addItem("Rotary Speaker", 16);
    variationTypeSelector.setSelectedId(13);
    variationEffectsGroup.addAndMakeVisible(variationTypeSelector);

    variationLevelSlider.setRange(0.0, 1.0, 0.01);
    variationLevelSlider.setValue(0.5);
    variationLevelSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    variationLevelSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    variationEffectsGroup.addAndMakeVisible(variationLevelSlider);

    variationParam1Slider.setRange(0.0, 1.0, 0.01);
    variationParam1Slider.setValue(0.3);
    variationParam1Slider.setSliderStyle(juce::Slider::LinearHorizontal);
    variationParam1Slider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    variationEffectsGroup.addAndMakeVisible(variationParam1Slider);

    variationParam2Slider.setRange(0.0, 1.0, 0.01);
    variationParam2Slider.setValue(0.2);
    variationParam2Slider.setSliderStyle(juce::Slider::LinearHorizontal);
    variationParam2Slider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
    variationEffectsGroup.addAndMakeVisible(variationParam2Slider);
}

void XGWorkstationVST3AudioProcessorEditor::setupStatusTab()
{
    // Title
    statusTitleLabel.setText("System Status & Diagnostics", juce::dontSendNotification);
    statusTitleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    statusTitleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    statusTab.addAndMakeVisible(statusTitleLabel);

    // Status indicators
    statusGroup.setText("Component Status");
    statusGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    statusGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    statusTab.addAndMakeVisible(statusGroup);

    pythonStatusLabel.setText("Python: Initializing...", juce::dontSendNotification);
    pythonStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    statusGroup.addAndMakeVisible(pythonStatusLabel);

    synthesizerStatusLabel.setText("Synthesizer: Initializing...", juce::dontSendNotification);
    synthesizerStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    statusGroup.addAndMakeVisible(synthesizerStatusLabel);

    sequencerStatusLabel.setText("Sequencer: Initializing...", juce::dontSendNotification);
    sequencerStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    statusGroup.addAndMakeVisible(sequencerStatusLabel);

    audioStatusLabel.setText("Audio: Ready", juce::dontSendNotification);
    audioStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    statusGroup.addAndMakeVisible(audioStatusLabel);

    performanceLabel.setText("Performance: Good", juce::dontSendNotification);
    performanceLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    statusGroup.addAndMakeVisible(performanceLabel);

    // System info
    systemInfoGroup.setText("System Information");
    systemInfoGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    systemInfoGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    statusTab.addAndMakeVisible(systemInfoGroup);

    sampleRateLabel.setText("Sample Rate: 44100 Hz", juce::dontSendNotification);
    sampleRateLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    systemInfoGroup.addAndMakeVisible(sampleRateLabel);

    bufferSizeLabel.setText("Buffer Size: 512 samples", juce::dontSendNotification);
    bufferSizeLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    systemInfoGroup.addAndMakeVisible(bufferSizeLabel);

    latencyLabel.setText("Latency: ~11.6 ms", juce::dontSendNotification);
    latencyLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    systemInfoGroup.addAndMakeVisible(latencyLabel);

    activeVoicesLabel.setText("Active Voices: 0", juce::dontSendNotification);
    activeVoicesLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    systemInfoGroup.addAndMakeVisible(activeVoicesLabel);
}

//==============================================================================
void XGWorkstationVST3AudioProcessorEditor::updateStatusDisplay()
{
    if (audioProcessor.isXGWorkstationReady())
    {
        pythonStatusLabel.setText("Python: ✓ Ready", juce::dontSendNotification);
        pythonStatusLabel.setColour(juce::Label::textColourId, juce::Colours::green);

        synthesizerStatusLabel.setText("Synthesizer: ✓ " + audioProcessor.getPythonIntegration().getSynthesizerStatus(),
                                      juce::dontSendNotification);
        synthesizerStatusLabel.setColour(juce::Label::textColourId, juce::Colours::green);

        sequencerStatusLabel.setText("Sequencer: ✓ Ready", juce::dontSendNotification);
        sequencerStatusLabel.setColour(juce::Label::textColourId, juce::Colours::green);
    }
    else
    {
        pythonStatusLabel.setText("Python: ⏳ Initializing...", juce::dontSendNotification);
        pythonStatusLabel.setColour(juce::Label::textColourId, juce::Colours::orange);

        synthesizerStatusLabel.setText("Synthesizer: ⏳ Initializing...", juce::dontSendNotification);
        synthesizerStatusLabel.setColour(juce::Label::textColourId, juce::Colours::orange);

        sequencerStatusLabel.setText("Sequencer: ⏳ Initializing...", juce::dontSendNotification);
        sequencerStatusLabel.setColour(juce::Label::textColourId, juce::Colours::orange);
    }

    // Update transport status
    transportStatusLabel.setText("Transport: Stopped", juce::dontSendNotification);
    transportStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);

    // Update performance metrics
    updatePerformanceDisplay();
}

void XGWorkstationVST3AudioProcessorEditor::updatePerformanceDisplay()
{
    // Update performance status based on metrics
    auto& metrics = audioProcessor.performanceMetrics;

    juce::String perfText = "Performance: ";
    juce::Colour perfColor = juce::Colours::green;

    if (metrics.averageCpuUsage > 80.0)
    {
        perfText += "Critical CPU (" + juce::String(metrics.averageCpuUsage, 1) + "%)";
        perfColor = juce::Colours::red;
    }
    else if (metrics.averageCpuUsage > 50.0)
    {
        perfText += "High CPU (" + juce::String(metrics.averageCpuUsage, 1) + "%)";
        perfColor = juce::Colours::orange;
    }
    else
    {
        perfText += "Good (" + juce::String(metrics.averageCpuUsage, 1) + "%)";
        perfColor = juce::Colours::green;
    }

    // Add underrun information
    if (metrics.bufferUnderruns > 0)
    {
        perfText += " | Underruns: " + juce::String(metrics.bufferUnderruns);
        perfColor = juce::Colours::orange;
    }

    performanceLabel.setText(perfText, juce::dontSendNotification);
    performanceLabel.setColour(juce::Label::textColourId, perfColor);

    // Update sample rate and buffer size
    sampleRateLabel.setText("Sample Rate: " + juce::String(audioProcessor.currentSampleRate, 0) + " Hz",
                           juce::dontSendNotification);
    bufferSizeLabel.setText("Buffer Size: " + juce::String(audioProcessor.currentBlockSize) + " samples",
                           juce::dontSendNotification);

    // Calculate and display latency
    double latencyMs = (audioProcessor.currentBlockSize / audioProcessor.currentSampleRate) * 1000.0;
    latencyLabel.setText("Latency: ~" + juce::String(latencyMs, 1) + " ms",
                        juce::dontSendNotification);

    // Update active voices (placeholder - would need to get from synthesizer)
    activeVoicesLabel.setText("Active Voices: 0", juce::dontSendNotification);

    // Update audio status
    audioStatusLabel.setText("Audio: Active", juce::dontSendNotification);
    audioStatusLabel.setColour(juce::Label::textColourId, juce::Colours::green);
}

void XGWorkstationVST3AudioProcessorEditor::updateParameterControls()
{
    // Update parameter values from processor
    // This would sync with the VST3 parameter system
}

void XGWorkstationVST3AudioProcessorEditor::updateXGControls()
{
    // Update XG effect controls based on current parameter values
}

//==============================================================================
void XGWorkstationVST3AudioProcessorEditor::initializeButtonClicked()
{
    DBG("Initialize workstation button clicked");

    if (!audioProcessor.isXGWorkstationReady())
    {
        audioProcessor.initializeXGWorkstation();
        initializeButton.setButtonText("Reinitialize");
    }
    else
    {
        DBG("XG Workstation already initialized");
    }

    updateStatusDisplay();
}

void XGWorkstationVST3AudioProcessorEditor::testAudioButtonClicked()
{
    DBG("Test audio button clicked");

    if (audioProcessor.isXGWorkstationReady())
    {
        DBG("Sending test MIDI note to XG synthesizer");
        // Send a test note-on followed by note-off
        // This will be handled by the Python integration
    }
    else
    {
        DBG("XG Workstation not ready for audio test");
    }
}

void XGWorkstationVST3AudioProcessorEditor::transportButtonClicked(juce::Button* button)
{
    if (button == &playButton)
    {
        DBG("Play button clicked");
        transportStatusLabel.setText("Transport: Playing", juce::dontSendNotification);
        transportStatusLabel.setColour(juce::Label::textColourId, juce::Colours::green);
    }
    else if (button == &stopButton)
    {
        DBG("Stop button clicked");
        transportStatusLabel.setText("Transport: Stopped", juce::dontSendNotification);
        transportStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    }
    else if (button == &recordButton)
    {
        DBG("Record button clicked");
        transportStatusLabel.setText("Transport: Recording", juce::dontSendNotification);
        transportStatusLabel.setColour(juce::Label::textColourId, juce::Colours::red);
    }
    else if (button == &pauseButton)
    {
        DBG("Pause button clicked");
        transportStatusLabel.setText("Transport: Paused", juce::dontSendNotification);
        transportStatusLabel.setColour(juce::Label::textColourId, juce::Colours::orange);
    }
}

void XGWorkstationVST3AudioProcessorEditor::patternButtonClicked(juce::Button* button)
{
    if (button == &createPatternButton)
    {
        DBG("Create pattern button clicked");
        patternInfoLabel.setText("Pattern creation not yet implemented", juce::dontSendNotification);
    }
    else if (button == &editPatternButton)
    {
        DBG("Edit pattern button clicked");
        patternInfoLabel.setText("Pattern editor not yet implemented", juce::dontSendNotification);
    }
}

//==============================================================================
// Controller Button Event Handlers

void XGWorkstationVST3AudioProcessorEditor::learnModeButtonClicked()
{
    learningMode = !learningMode;

    if (learningMode)
    {
        learnModeButton.setButtonText("Learn Mode: ON");
        learnModeButton.setColour(juce::TextButton::buttonColourId, juce::Colours::red);
        learningStatusLabel.setText("Move a parameter to learn its CC mapping", juce::dontSendNotification);
        learningStatusLabel.setColour(juce::Label::textColourId, juce::Colours::yellow);
        DBG("Parameter learning mode activated");
    }
    else
    {
        learnModeButton.setButtonText("Learn Mode: OFF");
        learnModeButton.setColour(juce::TextButton::buttonColourId, juce::Colours::orange);
        learningStatusLabel.setText("Click 'Learn Mode' then move a parameter", juce::dontSendNotification);
        learningStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
        learningParameter = "";
        DBG("Parameter learning mode deactivated");
    }
}

void XGWorkstationVST3AudioProcessorEditor::clearMappingsButtonClicked()
{
    if (!currentController.isEmpty() && controllerDatabase.count(currentController) > 0)
    {
        controllerDatabase[currentController].ccMappings.clear();
        controllerDatabase[currentController].parameterMappings.clear();

        learningStatusLabel.setText("All mappings cleared for " + currentController, juce::dontSendNotification);
        learningStatusLabel.setColour(juce::Label::textColourId, juce::Colours::green);

        DBG("Cleared all mappings for controller: " + currentController);
    }
    else
    {
        learningStatusLabel.setText("No controller selected", juce::dontSendNotification);
        learningStatusLabel.setColour(juce::Label::textColourId, juce::Colours::red);
    }
}

void XGWorkstationVST3AudioProcessorEditor::detectControllersButtonClicked()
{
    // Controller detection not yet implemented
    // Would scan available MIDI devices using JUCE's MidiInput class
    connectedControllerLabel.setText("Controller detection not implemented", juce::dontSendNotification);
    connectedControllerLabel.setColour(juce::Label::textColourId, juce::Colours::orange);
    
    DBG("Controller detection requested - not yet implemented");
}

void XGWorkstationVST3AudioProcessorEditor::transportMappingButtonClicked(juce::Button* button)
{
    if (currentController.isEmpty())
    {
        transportMapStatusLabel.setText("No controller selected", juce::dontSendNotification);
        transportMapStatusLabel.setColour(juce::Label::textColourId, juce::Colours::red);
        return;
    }

    // Enter transport mapping mode for the specific button
    juce::String mappingType;
    if (button == &mapPlayButton)
        mappingType = "Play";
    else if (button == &mapStopButton)
        mappingType = "Stop";
    else if (button == &mapRecordButton)
        mappingType = "Record";

    transportMapStatusLabel.setText("Press a button on " + currentController + " for " + mappingType,
                                   juce::dontSendNotification);
    transportMapStatusLabel.setColour(juce::Label::textColourId, juce::Colours::yellow);

    DBG("Transport mapping mode activated for: " + mappingType + " on " + currentController);
}

//==============================================================================
// Controller Integration Methods (Phase 6 - Hardware Integration)

void XGWorkstationVST3AudioProcessorEditor::setupControllersTab()
{
    // Title
    controllersTitleLabel.setText("Hardware Controller Integration", juce::dontSendNotification);
    controllersTitleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    controllersTitleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    controllersTab.addAndMakeVisible(controllersTitleLabel);

    // Controller Selection
    controllerSelectGroup.setText("Controller Selection");
    controllerSelectGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    controllerSelectGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    controllersTab.addAndMakeVisible(controllerSelectGroup);

    // Controller type selector (will be populated by initializeControllerDatabase)
    controllerSelectGroup.addAndMakeVisible(controllerTypeSelector);

    detectControllersButton.setButtonText("Detect Controllers");
    detectControllersButton.setColour(juce::TextButton::buttonColourId, juce::Colours::blue);
    controllerSelectGroup.addAndMakeVisible(detectControllersButton);

    connectedControllerLabel.setText("No controller connected", juce::dontSendNotification);
    connectedControllerLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    controllerSelectGroup.addAndMakeVisible(connectedControllerLabel);

    // Parameter Learning
    learningGroup.setText("Parameter Learning");
    learningGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    learningGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    controllersTab.addAndMakeVisible(learningGroup);

    learnModeButton.setButtonText("Learn Mode: OFF");
    learnModeButton.setColour(juce::TextButton::buttonColourId, juce::Colours::orange);
    learningGroup.addAndMakeVisible(learnModeButton);

    learningStatusLabel.setText("Click 'Learn Mode' then move a parameter", juce::dontSendNotification);
    learningStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    learningGroup.addAndMakeVisible(learningStatusLabel);

    clearMappingsButton.setButtonText("Clear All Mappings");
    clearMappingsButton.setColour(juce::TextButton::buttonColourId, juce::Colours::red);
    learningGroup.addAndMakeVisible(clearMappingsButton);

    // Transport Mapping
    transportMapGroup.setText("Transport Control Mapping");
    transportMapGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    transportMapGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    controllersTab.addAndMakeVisible(transportMapGroup);

    mapPlayButton.setButtonText("Map Play");
    mapPlayButton.setColour(juce::TextButton::buttonColourId, juce::Colours::green);
    transportMapGroup.addAndMakeVisible(mapPlayButton);

    mapStopButton.setButtonText("Map Stop");
    mapStopButton.setColour(juce::TextButton::buttonColourId, juce::Colours::red);
    transportMapGroup.addAndMakeVisible(mapStopButton);

    mapRecordButton.setButtonText("Map Record");
    mapRecordButton.setColour(juce::TextButton::buttonColourId, juce::Colours::red.brighter());
    transportMapGroup.addAndMakeVisible(mapRecordButton);

    transportMapStatusLabel.setText("Transport mapping: Not configured", juce::dontSendNotification);
    transportMapStatusLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    transportMapGroup.addAndMakeVisible(transportMapStatusLabel);
}

void XGWorkstationVST3AudioProcessorEditor::layoutControllersTab()
{
    auto area = controllersTab.getLocalBounds().reduced(10);

    // Title
    controllersTitleLabel.setBounds(area.removeFromTop(30));
    area.removeFromTop(10);

    // Controller Selection
    auto selectArea = area.removeFromTop(100);
    controllerSelectGroup.setBounds(selectArea);

    auto selectInner = selectArea.reduced(10);
    controllerTypeSelector.setBounds(selectInner.removeFromTop(25));
    selectInner.removeFromTop(5);

    auto buttonRow = selectInner.removeFromTop(25);
    detectControllersButton.setBounds(buttonRow.removeFromLeft(120));
    selectInner.removeFromTop(5);

    connectedControllerLabel.setBounds(selectInner.removeFromTop(20));

    area.removeFromTop(10);

    // Parameter Learning
    auto learningArea = area.removeFromTop(100);
    learningGroup.setBounds(learningArea);

    auto learningInner = learningArea.reduced(10);
    learnModeButton.setBounds(learningInner.removeFromTop(25));
    learningInner.removeFromTop(5);
    learningStatusLabel.setBounds(learningInner.removeFromTop(20));
    learningInner.removeFromTop(5);
    clearMappingsButton.setBounds(learningInner.removeFromTop(25));

    area.removeFromTop(10);

    // Transport Mapping
    auto transportArea = area.removeFromTop(100);
    transportMapGroup.setBounds(transportArea);

    auto transportInner = transportArea.reduced(10);
    auto mapButtons = transportInner.removeFromTop(25);
    mapPlayButton.setBounds(mapButtons.removeFromLeft(70));
    mapButtons.removeFromLeft(5);
    mapStopButton.setBounds(mapButtons.removeFromLeft(70));
    mapButtons.removeFromLeft(5);
    mapRecordButton.setBounds(mapButtons.removeFromLeft(80));

    transportInner.removeFromTop(5);
    transportMapStatusLabel.setBounds(transportInner.removeFromTop(20));
}

void XGWorkstationVST3AudioProcessorEditor::initializeControllerDatabase()
{
    // Initialize with known controller configurations
    // Novation Launchpad series
    {
        ControllerMapping novationLP;
        novationLP.controllerName = "Novation Launchpad";
        // Add default mappings for common parameters
        novationLP.ccMappings[21] = "master_volume";    // Knob 1
        novationLP.ccMappings[22] = "reverb_level";     // Knob 2
        novationLP.ccMappings[23] = "chorus_level";     // Knob 3
        novationLP.parameterMappings["master_volume"] = 21;
        novationLP.parameterMappings["reverb_level"] = 22;
        novationLP.parameterMappings["chorus_level"] = 23;
        controllerDatabase["Novation Launchpad"] = novationLP;
    }

    // Akai APC series
    {
        ControllerMapping akaiAPC;
        akaiAPC.controllerName = "Akai APC40";
        akaiAPC.ccMappings[48] = "master_volume";      // Crossfader
        akaiAPC.ccMappings[49] = "reverb_level";       // Cue Level
        akaiAPC.ccMappings[50] = "chorus_level";       // Track Control 1
        akaiAPC.parameterMappings["master_volume"] = 48;
        akaiAPC.parameterMappings["reverb_level"] = 49;
        akaiAPC.parameterMappings["chorus_level"] = 50;
        controllerDatabase["Akai APC40"] = akaiAPC;
    }

    // Korg nanoPAD2
    {
        ControllerMapping korgNano;
        korgNano.controllerName = "Korg nanoPAD2";
        korgNano.ccMappings[12] = "master_volume";     // Slider 1
        korgNano.ccMappings[13] = "reverb_level";      // Slider 2
        korgNano.ccMappings[14] = "chorus_level";      // Slider 3
        korgNano.parameterMappings["master_volume"] = 12;
        korgNano.parameterMappings["reverb_level"] = 13;
        korgNano.parameterMappings["chorus_level"] = 14;
        controllerDatabase["Korg nanoPAD2"] = korgNano;
    }

    // Generic controller
    {
        ControllerMapping generic;
        generic.controllerName = "Generic MIDI Controller";
        controllerDatabase["Generic MIDI Controller"] = generic;
    }

    // Populate controller type selector
    controllerTypeSelector.addItem("Generic MIDI Controller", 1);
    controllerTypeSelector.addItem("Novation Launchpad", 2);
    controllerTypeSelector.addItem("Akai APC40", 3);
    controllerTypeSelector.addItem("Korg nanoPAD2", 4);
    controllerTypeSelector.setSelectedId(1); // Default to generic

    DBG("Controller database initialized with " + juce::String(controllerDatabase.size()) + " controllers");
}

//==============================================================================
// Parts Management Methods (Phase 6 - Multi-timbral Management)

void XGWorkstationVST3AudioProcessorEditor::setupPartsTab()
{
    // Title
    partsTitleLabel.setText("XG Multi-timbral Parts Management", juce::dontSendNotification);
    partsTitleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    partsTitleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    partsTab.addAndMakeVisible(partsTitleLabel);

    // Parts Grid (4x4 layout for 16 parts)
    partsGridGroup.setText("XG Parts (16-part Multi-timbral)");
    partsGridGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    partsGridGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    partsTab.addAndMakeVisible(partsGridGroup);

    // Initialize all 16 parts
    for (int i = 0; i < 16; ++i)
    {
        // Part buttons (enable/disable parts)
        partButtons[i].setButtonText(juce::String(i + 1));
        partButtons[i].setColour(juce::TextButton::buttonColourId,
                                (i % 4 == 0) ? juce::Colours::green : juce::Colours::blue); // Highlight first column
        partsGridGroup.addAndMakeVisible(partButtons[i]);

        // Part labels (program names)
        partLabels[i].setText("Part " + juce::String(i + 1), juce::dontSendNotification);
        partLabels[i].setColour(juce::Label::textColourId, juce::Colours::white);
        partLabels[i].setFont(juce::Font(10.0f));
        partsGridGroup.addAndMakeVisible(partLabels[i]);

        // Volume sliders
        partVolumeSliders[i].setRange(0.0, 1.0, 0.01);
        partVolumeSliders[i].setValue(0.8);
        partVolumeSliders[i].setSliderStyle(juce::Slider::LinearVertical);
        partVolumeSliders[i].setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
        partsGridGroup.addAndMakeVisible(partVolumeSliders[i]);

        // Pan sliders
        partPanSliders[i].setRange(-1.0, 1.0, 0.01);
        partPanSliders[i].setValue(0.0);
        partPanSliders[i].setSliderStyle(juce::Slider::LinearVertical);
        partPanSliders[i].setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
        partsGridGroup.addAndMakeVisible(partPanSliders[i]);

        // Program selectors (simplified - would normally show actual XG program names)
        partProgramSelectors[i].addItem("Piano 1", 1);
        partProgramSelectors[i].addItem("Piano 2", 2);
        partProgramSelectors[i].addItem("E.Piano", 3);
        partProgramSelectors[i].addItem("Organ", 4);
        partProgramSelectors[i].addItem("Strings", 5);
        partProgramSelectors[i].addItem("Brass", 6);
        partProgramSelectors[i].addItem("Drums", 127); // GM Drums
        partProgramSelectors[i].setSelectedId(1);
        partsGridGroup.addAndMakeVisible(partProgramSelectors[i]);

        // Status labels
        partStatusLabels[i].setText("0 voices", juce::dontSendNotification);
        partStatusLabels[i].setColour(juce::Label::textColourId, juce::Colours::lightgrey);
        partStatusLabels[i].setFont(juce::Font(9.0f));
        partsGridGroup.addAndMakeVisible(partStatusLabels[i]);
    }

    // Parts Control Panel
    partsControlGroup.setText("Parts Control");
    partsControlGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    partsControlGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    partsTab.addAndMakeVisible(partsControlGroup);

    selectAllPartsButton.setButtonText("Select All");
    selectAllPartsButton.setColour(juce::TextButton::buttonColourId, juce::Colours::blue);
    partsControlGroup.addAndMakeVisible(selectAllPartsButton);

    muteAllPartsButton.setButtonText("Mute All");
    muteAllPartsButton.setColour(juce::TextButton::buttonColourId, juce::Colours::orange);
    partsControlGroup.addAndMakeVisible(muteAllPartsButton);

    soloPartButton.setButtonText("Solo Selected");
    soloPartButton.setColour(juce::TextButton::buttonColourId, juce::Colours::yellow);
    partsControlGroup.addAndMakeVisible(soloPartButton);

    masterPartsVolumeSlider.setRange(0.0, 1.0, 0.01);
    masterPartsVolumeSlider.setValue(1.0);
    masterPartsVolumeSlider.setSliderStyle(juce::Slider::LinearHorizontal);
    masterPartsVolumeSlider.setTextBoxStyle(juce::Slider::TextBoxRight, false, 60, 20);
    partsControlGroup.addAndMakeVisible(masterPartsVolumeSlider);

    masterPartsVolumeLabel.setText("Master Parts Volume", juce::dontSendNotification);
    masterPartsVolumeLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    partsControlGroup.addAndMakeVisible(masterPartsVolumeLabel);

    // XG Part Information
    partInfoGroup.setText("Selected Part Information");
    partInfoGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    partInfoGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    partsTab.addAndMakeVisible(partInfoGroup);

    selectedPartInfoLabel.setText("Part 1: Piano 1 (Bank 0, Program 0)", juce::dontSendNotification);
    selectedPartInfoLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    partInfoGroup.addAndMakeVisible(selectedPartInfoLabel);

    partVoiceCountLabel.setText("Active Voices: 0", juce::dontSendNotification);
    partVoiceCountLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    partInfoGroup.addAndMakeVisible(partVoiceCountLabel);

    partMidiChannelLabel.setText("MIDI Channel: 1 (Receive: All)", juce::dontSendNotification);
    partMidiChannelLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    partInfoGroup.addAndMakeVisible(partMidiChannelLabel);

    partSettingsButton.setButtonText("Advanced Part Settings");
    partSettingsButton.setColour(juce::TextButton::buttonColourId, juce::Colours::grey);
    partInfoGroup.addAndMakeVisible(partSettingsButton);

    DBG("XG Parts tab initialized with 16-part multi-timbral controls");
}

void XGWorkstationVST3AudioProcessorEditor::layoutPartsTab()
{
    auto area = partsTab.getLocalBounds().reduced(10);

    // Title
    partsTitleLabel.setBounds(area.removeFromTop(30));
    area.removeFromTop(10);

    // Parts Grid (takes up most of the space)
    auto gridArea = area.removeFromTop(300);
    partsGridGroup.setBounds(gridArea);

    auto gridInner = gridArea.reduced(10);

    // Create 4x4 grid layout for 16 parts
    int partWidth = gridInner.getWidth() / 4;
    int partHeight = gridInner.getHeight() / 4;

    for (int row = 0; row < 4; ++row)
    {
        for (int col = 0; col < 4; ++col)
        {
            int partIndex = row * 4 + col;
            if (partIndex >= 16) break;

            juce::Rectangle<int> partRect(
                gridInner.getX() + col * partWidth,
                gridInner.getY() + row * partHeight,
                partWidth - 2,
                partHeight - 2
            );

            // Layout controls within each part cell
            auto partArea = partRect.reduced(2);

            // Part button (top-left corner)
            partButtons[partIndex].setBounds(partArea.removeFromTop(20).removeFromLeft(25));

            // Part label (top, next to button)
            partLabels[partIndex].setBounds(partArea.removeFromTop(15).withTrimmedLeft(30));

            // Volume and Pan sliders (side by side in middle)
            auto sliderArea = partArea.removeFromTop(40);
            partVolumeSliders[partIndex].setBounds(sliderArea.removeFromLeft(sliderArea.getWidth() / 2 - 2));
            sliderArea.removeFromLeft(4);
            partPanSliders[partIndex].setBounds(sliderArea);

            // Program selector (bottom, most of remaining space)
            auto programArea = partArea.removeFromTop(30);
            partProgramSelectors[partIndex].setBounds(programArea);

            // Status label (bottom, small)
            partStatusLabels[partIndex].setBounds(partArea.removeFromTop(12));
        }
    }

    area.removeFromTop(10);

    // Parts Control Panel
    auto controlArea = area.removeFromTop(80);
    partsControlGroup.setBounds(controlArea);

    auto controlInner = controlArea.reduced(10);
    auto buttonRow = controlInner.removeFromTop(25);
    selectAllPartsButton.setBounds(buttonRow.removeFromLeft(80));
    buttonRow.removeFromLeft(5);
    muteAllPartsButton.setBounds(buttonRow.removeFromLeft(80));
    buttonRow.removeFromLeft(5);
    soloPartButton.setBounds(buttonRow.removeFromLeft(100));

    controlInner.removeFromTop(5);
    auto masterRow = controlInner.removeFromTop(25);
    masterPartsVolumeLabel.setBounds(masterRow.removeFromLeft(120));
    masterRow.removeFromLeft(5);
    masterPartsVolumeSlider.setBounds(masterRow);

    area.removeFromTop(10);

    // Part Information Panel
    auto infoArea = area.removeFromTop(120);
    partInfoGroup.setBounds(infoArea);

    auto infoInner = infoArea.reduced(10);
    selectedPartInfoLabel.setBounds(infoInner.removeFromTop(20));
    partVoiceCountLabel.setBounds(infoInner.removeFromTop(20));
    partMidiChannelLabel.setBounds(infoInner.removeFromTop(20));
    partSettingsButton.setBounds(infoInner.removeFromTop(25));
}

//==============================================================================
// Advanced Effects Routing Methods (Phase 6 - Effects Completion)

void XGWorkstationVST3AudioProcessorEditor::setupEffectsRoutingTab()
{
    // Title
    effectsRoutingTitleLabel.setText("Advanced Effects Routing & Processing", juce::dontSendNotification);
    effectsRoutingTitleLabel.setFont(juce::Font(16.0f, juce::Font::bold));
    effectsRoutingTitleLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    effectsRoutingTab.addAndMakeVisible(effectsRoutingTitleLabel);

    // System Effects Routing (Reverb & Chorus sends per part)
    systemEffectsRoutingGroup.setText("System Effects Routing (Reverb & Chorus)");
    systemEffectsRoutingGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    systemEffectsRoutingGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    effectsRoutingTab.addAndMakeVisible(systemEffectsRoutingGroup);

    // Initialize system effects routing controls for all 16 parts
    for (int i = 0; i < 16; ++i)
    {
        // Reverb send levels per part
        partReverbSendSliders[i].setRange(0.0, 1.0, 0.01);
        partReverbSendSliders[i].setValue(0.3);
        partReverbSendSliders[i].setSliderStyle(juce::Slider::LinearVertical);
        partReverbSendSliders[i].setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
        systemEffectsRoutingGroup.addAndMakeVisible(partReverbSendSliders[i]);

        // Chorus send levels per part
        partChorusSendSliders[i].setRange(0.0, 1.0, 0.01);
        partChorusSendSliders[i].setValue(0.2);
        partChorusSendSliders[i].setSliderStyle(juce::Slider::LinearVertical);
        partChorusSendSliders[i].setTextBoxStyle(juce::Slider::NoTextBox, false, 0, 0);
        systemEffectsRoutingGroup.addAndMakeVisible(partChorusSendSliders[i]);
    }

    systemEffectsLabel.setText("Reverb/Chorus Send Levels (Parts 1-16)", juce::dontSendNotification);
    systemEffectsLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    systemEffectsRoutingGroup.addAndMakeVisible(systemEffectsLabel);

    systemEffectsBypassButton.setButtonText("System Effects: ON");
    systemEffectsBypassButton.setColour(juce::TextButton::buttonColourId, juce::Colours::green);
    systemEffectsRoutingGroup.addAndMakeVisible(systemEffectsBypassButton);

    // Insertion Effects (Per-part processing)
    insertionEffectsGroup.setText("Insertion Effects (Per-Part Processing)");
    insertionEffectsGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    insertionEffectsGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    effectsRoutingTab.addAndMakeVisible(insertionEffectsGroup);

    // Initialize insertion effects controls for all 16 parts
    for (int i = 0; i < 16; ++i)
    {
        // Insertion effect selectors per part
        partInsertionEffectSelectors[i].addItem("Bypass", 0);
        partInsertionEffectSelectors[i].addItem("Distortion", 1);
        partInsertionEffectSelectors[i].addItem("Compressor", 2);
        partInsertionEffectSelectors[i].addItem("EQ", 3);
        partInsertionEffectSelectors[i].addItem("Phaser", 4);
        partInsertionEffectSelectors[i].setSelectedId(0);
        insertionEffectsGroup.addAndMakeVisible(partInsertionEffectSelectors[i]);

        // Insertion effect level controls per part
        partInsertionLevelSliders[i].setRange(0.0, 1.0, 0.01);
        partInsertionLevelSliders[i].setValue(1.0);
        partInsertionLevelSliders[i].setSliderStyle(juce::Slider::LinearHorizontal);
        partInsertionLevelSliders[i].setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
        insertionEffectsGroup.addAndMakeVisible(partInsertionLevelSliders[i]);

        // Insertion effect bypass buttons per part
        partInsertionBypassButtons[i].setButtonText("Bypass");
        partInsertionBypassButtons[i].setColour(juce::TextButton::buttonColourId, juce::Colours::grey);
        insertionEffectsGroup.addAndMakeVisible(partInsertionBypassButtons[i]);
    }

    insertionEffectsLabel.setText("Per-Part Insertion Effects", juce::dontSendNotification);
    insertionEffectsLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    insertionEffectsGroup.addAndMakeVisible(insertionEffectsLabel);

    // Variation Effects Routing
    variationEffectsRoutingGroup.setText("Variation Effects Routing");
    variationEffectsRoutingGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    variationEffectsRoutingGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    effectsRoutingTab.addAndMakeVisible(variationEffectsRoutingGroup);

    // Initialize variation effects controls for all 16 parts
    for (int i = 0; i < 16; ++i)
    {
        // Variation effect selectors per part
        partVariationEffectSelectors[i].addItem("Off", 0);
        partVariationEffectSelectors[i].addItem("Delay LCR", 13);
        partVariationEffectSelectors[i].addItem("Delay LR", 14);
        partVariationEffectSelectors[i].addItem("Chorus", 15);
        partVariationEffectSelectors[i].addItem("Flanger", 16);
        partVariationEffectSelectors[i].addItem("Rotary Speaker", 17);
        partVariationEffectSelectors[i].setSelectedId(0);
        variationEffectsRoutingGroup.addAndMakeVisible(partVariationEffectSelectors[i]);

        // Variation effect send levels per part
        partVariationSendSliders[i].setRange(0.0, 1.0, 0.01);
        partVariationSendSliders[i].setValue(0.5);
        partVariationSendSliders[i].setSliderStyle(juce::Slider::LinearHorizontal);
        partVariationSendSliders[i].setTextBoxStyle(juce::Slider::TextBoxRight, false, 50, 20);
        variationEffectsRoutingGroup.addAndMakeVisible(partVariationSendSliders[i]);

        // Variation effect bypass buttons per part
        partVariationBypassButtons[i].setButtonText("Bypass");
        partVariationBypassButtons[i].setColour(juce::TextButton::buttonColourId, juce::Colours::grey);
        variationEffectsRoutingGroup.addAndMakeVisible(partVariationBypassButtons[i]);
    }

    variationEffectsLabel.setText("Per-Part Variation Effects Assignment", juce::dontSendNotification);
    variationEffectsLabel.setColour(juce::Label::textColourId, juce::Colours::white);
    variationEffectsRoutingGroup.addAndMakeVisible(variationEffectsLabel);

    // Effects Chain Visualization
    effectsChainGroup.setText("Effects Chain Status");
    effectsChainGroup.setColour(juce::GroupComponent::outlineColourId, juce::Colours::grey);
    effectsChainGroup.setColour(juce::GroupComponent::textColourId, juce::Colours::white);
    effectsRoutingTab.addAndMakeVisible(effectsChainGroup);

    refreshChainButton.setButtonText("Refresh Chain");
    refreshChainButton.setColour(juce::TextButton::buttonColourId, juce::Colours::blue);
    effectsChainGroup.addAndMakeVisible(refreshChainButton);

    effectsChainDiagramLabel.setText("Effects Chain: System(Reverb+Chorus) -> Parts(Inserts) -> Variation -> Output", juce::dontSendNotification);
    effectsChainDiagramLabel.setColour(juce::Label::textColourId, juce::Colours::lightgrey);
    effectsChainGroup.addAndMakeVisible(effectsChainDiagramLabel);

    totalEffectsLoadLabel.setText("Total Effects Load: Low (Estimated CPU: 15%)", juce::dontSendNotification);
    totalEffectsLoadLabel.setColour(juce::Label::textColourId, juce::Colours::green);
    effectsChainGroup.addAndMakeVisible(totalEffectsLoadLabel);

    DBG("Advanced Effects Routing tab initialized with per-part effects controls");
}

void XGWorkstationVST3AudioProcessorEditor::layoutEffectsRoutingTab()
{
    auto area = effectsRoutingTab.getLocalBounds().reduced(10);

    // Title
    effectsRoutingTitleLabel.setBounds(area.removeFromTop(30));
    area.removeFromTop(10);

    // System Effects Routing
    auto systemArea = area.removeFromTop(150);
    systemEffectsRoutingGroup.setBounds(systemArea);

    auto systemInner = systemArea.reduced(10);
    systemEffectsLabel.setBounds(systemInner.removeFromTop(20));

    // Layout reverb and chorus send sliders for all 16 parts
    auto sendArea = systemInner.removeFromTop(80);
    for (int i = 0; i < 16; ++i)
    {
        int sliderWidth = sendArea.getWidth() / 16;
        int xPos = sendArea.getX() + i * sliderWidth;

        // Reverb send (top half)
        partReverbSendSliders[i].setBounds(xPos, sendArea.getY(), sliderWidth - 2, sendArea.getHeight() / 2 - 2);

        // Chorus send (bottom half)
        partChorusSendSliders[i].setBounds(xPos, sendArea.getY() + sendArea.getHeight() / 2 + 2, sliderWidth - 2, sendArea.getHeight() / 2 - 2);
    }

    systemInner.removeFromTop(5);
    systemEffectsBypassButton.setBounds(systemInner.removeFromTop(25));

    area.removeFromTop(10);

    // Insertion Effects
    auto insertionArea = area.removeFromTop(180);
    insertionEffectsGroup.setBounds(insertionArea);

    auto insertionInner = insertionArea.reduced(10);
    insertionEffectsLabel.setBounds(insertionInner.removeFromTop(20));

    // Layout insertion effects controls for all 16 parts
    auto insertArea = insertionInner.removeFromTop(130);
    for (int i = 0; i < 16; ++i)
    {
        int controlWidth = insertArea.getWidth() / 16;
        int xPos = insertArea.getX() + i * controlWidth;

        // Effect selector (top)
        partInsertionEffectSelectors[i].setBounds(xPos, insertArea.getY(), controlWidth - 2, 25);

        // Level slider (middle)
        partInsertionLevelSliders[i].setBounds(xPos, insertArea.getY() + 30, controlWidth - 2, 30);

        // Bypass button (bottom)
        partInsertionBypassButtons[i].setBounds(xPos, insertArea.getY() + 65, controlWidth - 2, 25);
    }

    area.removeFromTop(10);

    // Variation Effects Routing
    auto variationArea = area.removeFromTop(180);
    variationEffectsRoutingGroup.setBounds(variationArea);

    auto variationInner = variationArea.reduced(10);
    variationEffectsLabel.setBounds(variationInner.removeFromTop(20));

    // Layout variation effects controls for all 16 parts
    auto varArea = variationInner.removeFromTop(130);
    for (int i = 0; i < 16; ++i)
    {
        int controlWidth = varArea.getWidth() / 16;
        int xPos = varArea.getX() + i * controlWidth;

        // Effect selector (top)
        partVariationEffectSelectors[i].setBounds(xPos, varArea.getY(), controlWidth - 2, 25);

        // Send level slider (middle)
        partVariationSendSliders[i].setBounds(xPos, varArea.getY() + 30, controlWidth - 2, 30);

        // Bypass button (bottom)
        partVariationBypassButtons[i].setBounds(xPos, varArea.getY() + 65, controlWidth - 2, 25);
    }

    area.removeFromTop(10);

    // Effects Chain Visualization
    auto chainArea = area.removeFromTop(100);
    effectsChainGroup.setBounds(chainArea);

    auto chainInner = chainArea.reduced(10);
    refreshChainButton.setBounds(chainInner.removeFromTop(25));
    chainInner.removeFromTop(5);
    effectsChainDiagramLabel.setBounds(chainInner.removeFromTop(20));
    chainInner.removeFromTop(5);
    totalEffectsLoadLabel.setBounds(chainInner.removeFromTop(20));
}
