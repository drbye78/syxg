#!/bin/bash

# This script will sequentially amend commit messages

# First, let's do the oldest commit
git rebase -i d92f415~1 << 'EOF'
reword d92f415 Remove docs and refactor FM/SF2 engines
pick ccc4b8c mokka 7
pick 09de094 mokka 7.1
pick dc1b501 mokka 8
pick b575c70 mokka 8
pick 9a54fd5 refactor: update default audio format to MP3 and remove debug output
pick 4d93597 mokka 8.2
pick ad49d27 mokka 8.3
pick 653c8ec mokka 8.5
pick 82964dc Add SF2 region support and envelope tests
EOF
