#!/bin/bash
# Git sequence editor that converts pick to reword

FILE="$1"

# Create a simple mapping file
cat > /tmp/commit_msgs.txt << 'EOF'
d92f415:Remove docs and refactor FM/SF2 engines
ccc4b8c:Add vibexg module, MIDI infrastructure and tests
09de094:Enhance MPE, sampling, sequencer and style systems
dc1b501:Reorganize project structure and add vibexg workstation
b575c70:Refactor effects, engines, voice and XG arpeggiator
9a54fd5:refactor: update default audio format to MP3 and remove debug output
4d93597:Refactor SF2 engine, channel, effects and add tests
ad49d27:Remove sf2_presets.csv test data files
653c8ec:Remove .qwen config and dependabot.yml
82964dc:Add SF2 region support and envelope tests
EOF

# Replace "pick" with "reword" for commits that have new messages
while IFS= read -r line; do
  if [[ "$line" =~ ^pick\ ([a-f0-9]+)\  ]]; then
    commit="${BASH_REMATCH[1]}"
    if grep -q "^$commit:" /tmp/commit_msgs.txt; then
      echo "reword $commit"
      continue
    fi
  fi
  echo "$line"
done < "$FILE" > "$FILE.tmp"
mv "$FILE.tmp" "$FILE"
