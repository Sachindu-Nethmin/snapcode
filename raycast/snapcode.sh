#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title SnapCode
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 🦥
# @raycast.packageName SnapCode
# @raycast.description Select code on screen -> clean code in clipboard (Tesseract + Gemma, offline)

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
/usr/bin/python3 "$(dirname "$0")/../snapcode.py"
