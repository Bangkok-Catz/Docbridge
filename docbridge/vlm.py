"""Vision-language OCR using Liquid AI LFM3-VL-2B.

LFM3-VL-2B (Oct 2026) is a ~2B open-weight vision model that lists Thai among
its 16 languages and runs locally (about 1.1 GB at Q4_K_M). docbridge uses it
to turn page images into Markdown when there is no usable text layer: scanned
PDFs, photos, and PDFs whose Thai fonts extract as garbage.

Two ways to run it, picked with DOCBRIDGE_VLM:

  http          any OpenAI-compatible server, e.g. llama.cpp:
                  llama serve -hf LiquidAI/LFM3-VL-2B-GGUF:Q4_K_M
                DOCBRIDGE_VLM_URL   (default http://localhost:8080/v1)
                DOCBRIDGE_VLM_MODEL (default LiquidAI/LFM3-VL-2B)
                DOCBRIDGE_VLM_API_KEY (optional)
  transformers  load the weights in-process (pip install "docbridge[vlm]")

Unset or "off" disables it; docbridge then falls back to Tesseract.
The model weights are under the LFM Open License v1.0 (free for commercial
use under US$10M annual revenue), separate from docbridge's MIT license.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import urllib.request
from functools import lru_cache

DEFAULT_MODEL = "LiquidAI/LFM3-VL-2B"
DEFAULT_URL = "http://localhost:8080/v1"
MAX_SIDE = 1800  # px; caps vision tokens per page (~3-4k) without hurting small Thai marks

PROMPT = (
    "Convert this document page to Markdown. Transcribe every piece of text exactly as written, "
    "in its original language (Thai and/or English). Do not translate, summarize, explain or add anything. "
    "Use # headings for titles, '- ' for list items, and Markdown pipe tables for tables. "
    "Keep the natural reading order. Output only the Markdown."
)
# recommended by Liquid AI for LFM3
SAMPLING = {"temperature": 0.1, "top_k": 50, "top_p": 1.0}

_THINK = re.compile(r"<think>.*?</think>", re.S)
_FENCE = re.compile(r"^```(?:markdown|md)?\s*\n(.*?)\n```\s*$", re.S)


def clean_output(text: str) -> str:
    """Drop the model's <think> reasoning and any wrapping code fence."""
    text = _THINK.sub("", text)
    if "</think>" in text:  # truncated opening tag
        text = text.split("</think>", 1)[1]
    text = text.strip()
    if m := _FENCE.match(text):
        text = m.group(1).strip()
    return text


def _prepare(img):
    img = img.convert("RGB")
    w, h = img.size
    scale = MAX_SIDE / max(w, h)
    if scale < 1:
        img = img.resize((int(w * scale), int(h * scale)))
    return img


class HTTPBackend:
    name = "lfm3-vl (http)"

    def __init__(self, url: str, model: str, api_key: str | None = None, timeout: float = 300):
        self.url = url.rstrip("/") + "/chat/completions"
        self.model, self.api_key, self.timeout = model, api_key, timeout

    def page_to_markdown(self, img) -> str:
        buf = io.BytesIO()
        _prepare(img).save(buf, format="PNG")
        data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": PROMPT},
            ]}],
            "max_tokens": 8192,
            **SAMPLING,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.url, json.dumps(body).encode(), headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            out = json.load(r)
        return clean_output(out["choices"][0]["message"]["content"] or "")


class TransformersBackend:
    name = "lfm3-vl (transformers)"

    def __init__(self, model: str):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.torch = torch
        self.model = AutoModelForImageTextToText.from_pretrained(
            model, dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
        )
        self.processor = AutoProcessor.from_pretrained(model, trust_remote_code=True)

    def page_to_markdown(self, img) -> str:
        messages = [{"role": "user", "content": [
            {"type": "image", "image": _prepare(img)},
            {"type": "text", "text": PROMPT},
        ]}]
        inputs = self.processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
        ).to(self.model.device)
        with self.torch.inference_mode():
            ids = self.model.generate(
                **inputs, do_sample=True, repetition_penalty=1.1, max_new_tokens=8192, **SAMPLING
            )
        new = ids[:, inputs["input_ids"].shape[1]:]
        return clean_output(self.processor.batch_decode(new, skip_special_tokens=True)[0])


@lru_cache(maxsize=1)
def _backend_for(mode: str, url: str, model: str, key: str | None):
    if mode == "http":
        return HTTPBackend(url, model, key)
    if mode == "transformers":
        return TransformersBackend(model)
    return None


def get_backend():
    """Return the configured VLM backend, or None if disabled."""
    mode = os.environ.get("DOCBRIDGE_VLM", "off").strip().lower()
    if mode in ("", "off", "0", "false", "none"):
        return None
    return _backend_for(
        mode,
        os.environ.get("DOCBRIDGE_VLM_URL", DEFAULT_URL),
        os.environ.get("DOCBRIDGE_VLM_MODEL", DEFAULT_MODEL),
        os.environ.get("DOCBRIDGE_VLM_API_KEY"),
    )


def reset_backend():
    _backend_for.cache_clear()
