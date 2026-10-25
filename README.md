# SnapCode 🦥

Press a hotkey, drag a box around code on a lecture slide or video, then press Cmd+V. The clean, correctly indented code is already on your clipboard.

Everything runs locally and works without internet:

| Step | Tool | Why |
|---|---|---|
| Select region | macOS `screencapture -i` | built in |
| Rough OCR | [Tesseract](https://github.com/tesseract-ocr/tesseract) (Apache-2.0) | fast first draft |
| Fix + re-indent | **Gemma** (open weights) via [Ollama](https://ollama.com) | reads the image, fixes `[[ ]]`, quotes, underscores, indentation |
| Verify | Python `ast` | on a syntax error, Gemma gets one retry with the error message |
| Paste | `pbcopy` | Cmd+V into Colab or your IDE |

## Setup

```bash
brew install tesseract ollama
ollama pull gemma4:E4B
```

Hotkey (Raycast): Settings → Extensions → Script Commands → **Add Directory** → choose `snapcode/raycast`, then give **SnapCode** a hotkey (for example ⌥⇧C). The first run asks for Screen Recording permission for Raycast.

## CLI

```bash
python3 snapcode.py                 # select a region
python3 snapcode.py --image a.png   # use an existing image
python3 snapcode.py --raw           # Tesseract only, no LLM
SNAPCODE_MODEL=qwen2.5vl python3 snapcode.py   # swap the model
```

If Ollama isn't running, SnapCode still copies the raw Tesseract text.
