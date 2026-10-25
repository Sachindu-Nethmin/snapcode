#!/usr/bin/env python3
"""SnapCode: drag a box around code on screen -> clean code on your clipboard.

Pipeline (all local, works offline):
  1. macOS `screencapture -i` lets you select a region
  2. Tesseract (open-source OCR) produces a rough draft
  3. Gemma (open-weight, via Ollama) looks at the image + draft and returns
     the exact code with indentation restored and OCR mistakes fixed
  4. Python code is syntax-checked; on error Gemma gets one retry with the error
  5. Result goes to the clipboard (pbcopy) -> just Cmd+V into Colab / your IDE

Usage:
  snapcode.py                 # select a region on screen
  snapcode.py --image a.png   # run on an existing image
  snapcode.py --raw           # skip the LLM, Tesseract only (fastest)
"""
import argparse
import ast
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

OLLAMA_URL = os.environ.get("SNAPCODE_OLLAMA", "http://localhost:11434")
MODEL = os.environ.get("SNAPCODE_MODEL", "gemma4:E4B")

PROMPT = """You are an OCR post-processor for source code.
The image is a screenshot of code (often a Jupyter/Colab cell from a lecture slide).
A rough OCR draft is below. Using the IMAGE as the source of truth:
- Output ONLY the code, exactly as shown. No explanation, no markdown fences.
- Restore indentation (4 spaces per level for Python).
- Fix OCR mistakes: brackets like [[ ]], quotes, colons, underscores, 0/O, 1/l, etc.
- Do NOT add, remove, rename or "improve" anything. Do not include cell numbers
  like [12] or line numbers, and do not include output that is not code.

OCR draft:
---
{draft}
---"""

RETRY = """That code has a syntax error: {error}
Look at the image again and output the corrected code only, exactly as shown."""


def notify(title, msg):
    msg = msg.replace('"', "'")[:180]
    subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "{title}"'],
                   capture_output=True)


def capture_region():
    path = os.path.join(tempfile.gettempdir(), f"snapcode-{int(time.time())}.png")
    # -i interactive selection, -x no shutter sound
    subprocess.run(["screencapture", "-i", "-x", path])
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None  # user pressed Esc
    return path


def tesseract(path):
    # psm 6 = treat the image as one uniform block of text; keep spaces between words
    out = subprocess.run(
        ["tesseract", path, "-", "--psm", "6", "-c", "preserve_interword_spaces=1"],
        capture_output=True, text=True)
    return out.stdout.strip()


def ollama_chat(messages):
    body = json.dumps({
        "model": MODEL, "messages": messages, "stream": False, "think": False,
        "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)["message"]["content"]


def strip_fences(text):
    m = re.search(r"```[\w+-]*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip("\n")


def python_error(code):
    """Return a syntax error message, or None. Notebook magics (!pip, %time) are ignored."""
    lines = ["" if l.lstrip().startswith(("!", "%")) else l for l in code.splitlines()]
    try:
        ast.parse("\n".join(lines))
        return None
    except SyntaxError as e:
        return f"line {e.lineno}: {e.msg}"


def clean_with_llm(path, draft):
    with open(path, "rb") as f:
        img = base64.b64encode(f.read()).decode()
    messages = [{"role": "user", "content": PROMPT.format(draft=draft), "images": [img]}]
    code = strip_fences(ollama_chat(messages))
    err = python_error(code)
    if err:
        messages += [{"role": "assistant", "content": code},
                     {"role": "user", "content": RETRY.format(error=err)}]
        retry = strip_fences(ollama_chat(messages))
        if python_error(retry) is None:
            code = retry
    return code


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", help="use this image instead of selecting a screen region")
    ap.add_argument("--raw", action="store_true", help="Tesseract only, skip Gemma")
    ap.add_argument("--print", action="store_true", help="also print the result")
    args = ap.parse_args()

    path = args.image or capture_region()
    if not path:
        return
    start = time.time()
    draft = tesseract(path)
    code, how = draft, "Tesseract"
    if not args.raw:
        try:
            code, how = clean_with_llm(path, draft), MODEL
        except Exception as e:  # Ollama not running etc. -> still give the user something
            how = f"Tesseract (Gemma unavailable: {e.__class__.__name__})"

    subprocess.run(["pbcopy"], input=code, text=True)
    lines = code.count("\n") + 1 if code else 0
    notify("SnapCode 🦥", f"{lines} lines copied via {how} in {time.time() - start:.1f}s")
    if args.print or args.image:
        print(code)
    if not args.image:
        os.remove(path)


if __name__ == "__main__":
    sys.exit(main())
