#!/bin/bash
# Git message editor that handles rebase

FILE="$1"

# Read the original message - it contains the old "mokka X" text
orig_msg=$(cat "$FILE")

# Use the original message to identify which commit this is
case "$orig_msg" in
  *"mokka 7"*)
    if grep -q "^ccc4b8c:" /tmp/commit_msgs.txt 2>/dev/null; then
      grep "^ccc4b8c:" /tmp/commit_msgs.txt | cut -d':' -f2- > "$FILE"
      exit 0
    fi
    ;;
  *"mokka 7.1"*)
    if grep -q "^09de094:" /tmp/commit_msgs.txt 2>/dev/null; then
      grep "^09de094:" /tmp/commit_msgs.txt | cut -d':' -f2- > "$FILE"
      exit 0
    fi
    ;;
  *"mokka 8"*)
    # Could be dc1b501 or b575c70 - check which one by position in rebase
    if [[ -d .git/rebase-merge ]]; then
      n=$(cat .git/rebase-merge/current 2>/dev/null)
      # In the todo file, position tells us which commit
      # dc1b501 is earlier (position 4), b575c70 is later (position 5)
      if [[ "$n" -eq 3 ]]; then
        grep "^dc1b501:" /tmp/commit_msgs.txt | cut -d':' -f2- > "$FILE"
        exit 0
      elif [[ "$n" -eq 4 ]]; then
        grep "^b575c70:" /tmp/commit_msgs.txt | cut -d':' -f2- > "$FILE"
        exit 0
      fi
    fi
    ;;
  *"mokka 8.2"*)
    if grep -q "^4d93597:" /tmp/commit_msgs.txt 2>/dev/null; then
      grep "^4d93597:" /tmp/commit_msgs.txt | cut -d':' -f2- > "$FILE"
      exit 0
    fi
    ;;
  *"mokka 8.3"*)
    if grep -q "^ad49d27:" /tmp/commit_msgs.txt 2>/dev/null; then
      grep "^ad49d27:" /tmp/commit_msgs.txt | cut -d':' -f2- > "$FILE"
      exit 0
    fi
    ;;
  *"mokka 8.5"*)
    if grep -q "^653c8ec:" /tmp/commit_msgs.txt 2>/dev/null; then
      grep "^653c8ec:" /tmp/commit_msgs.txt | cut -d':' -f2- > "$FILE"
      exit 0
    fi
    ;;
esac
