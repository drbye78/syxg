#!/bin/bash
# Custom git editor that automatically rewrites commit messages based on commit hash

FILE="$1"

declare -A MESSAGES
MESSAGES[d92f415]="Remove docs and refactor FM/SF2 engines"
MESSAGES[ccc4b8c]="Add vibexg module, MIDI infrastructure and tests"
MESSAGES[09de094]="Enhance MPE, sampling, sequencer and style systems"
MESSAGES[dc1b501]="Reorganize project structure and add vibexg workstation"
MESSAGES[b575c70]="Refactor effects, engines, voice and XG arpeggiator"
MESSAGES[9a54fd5]="refactor: update default audio format to MP3 and remove debug output"
MESSAGES[4d93597]="Refactor SF2 engine, channel, effects and add tests"
MESSAGES[ad49d27]="Remove sf2_presets.csv test data files"
MESSAGES[653c8ec]="Remove .qwen config and dependabot.yml"
MESSAGES[82964dc]="Add SF2 region support and envelope tests"

# Read the file and modify lines
while IFS= read -r line; do
  # Check if line starts with "pick" or "reword"
  if [[ "$line" =~ ^(pick|reword)\ ([a-f0-9]+)\ (.+)$ ]]; then
    commit="${BASH_REMATCH[2]}"
    if [[ -n "${MESSAGES[$commit]}" ]]; then
      echo "reword $commit ${MESSAGES[$commit]}"
      continue
    fi
  fi
  echo "$line"
done < "$FILE" > "$FILE.new"

mv "$FILE.new" "$FILE"

# For reword commands, git will call the editor again to edit the message
# We need to handle this by checking if we're being called for a message file
if [[ -f "$1" && ! "$1" =~ ^/tmp/ ]]; then
  # This is the todo file - we already modified it
  exit 0
elif [[ -f "$1" && "$1" =~ /git-rebase-todo/ ]]; then
  # This is also the todo file
  exit 0
fi

# If we get here, git is asking us to edit a commit message
# Check if there's a COMMIT_MSG file or similar
if [[ -f ".git/COMMIT_EDITMSG" ]]; then
  exit 0
fi
