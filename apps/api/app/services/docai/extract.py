"""Document extraction (IMPLEMENTATION.md §14 `docai/extract.py`): render
PDF pages to images, OCR them for words + boxes (Tesseract), regex-extract
the per-type fields out of the raw text, then fuzzy-match each extracted
value back to the OCR word box(es) it came from for the DocViewer's
highlight overlay.

This *is* real OCR, not a demo-mode stub — the one deliberate simplification
is the "vision LLM" step §14 describes: instead of a vision model call,
field values come from the regex patterns in `app.services.docai.schemas`,
written to match the sample documents this project generates itself
(`app.seed.docai_seed`). Swapping in a real vision-LLM call behind
`LLMClient` (see `app.services.docai.llm_client`) later only touches this
module's field-matching step, not the OCR/box-matching plumbing around it.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

from app.services.docai.schemas import field_patterns

MAX_PAGES_SCANNED = 3


@dataclass
class OcrWord:
    text: str
    page: int
    x: float
    y: float
    w: float
    h: float
    conf: float


@dataclass
class ExtractionResult:
    fields: dict[str, dict[str, Any]] = field(default_factory=dict)
    boxes: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""
    confidence: float = 0.0
    page_count: int = 1
    preview_png: bytes = b""


def _to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _ocr_image(image: Image.Image, *, page: int) -> tuple[str, list[OcrWord]]:
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    width, height = image.size
    words: list[OcrWord] = []
    texts: list[str] = []
    for i, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
        if not text:
            continue
        texts.append(text)
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = 0.0
        words.append(
            OcrWord(
                text=text,
                page=page,
                x=data["left"][i] / width,
                y=data["top"][i] / height,
                w=data["width"][i] / width,
                h=data["height"][i] / height,
                conf=max(conf, 0.0),
            )
        )
    return " ".join(texts), words


def _find_box(words: list[OcrWord], value: str) -> dict[str, Any] | None:
    needle = value.strip().strip(",.").lower()
    if not needle:
        return None

    for w in words:
        if w.text.strip(",.").lower() == needle:
            return {"page": w.page, "x": w.x, "y": w.y, "w": w.w, "h": w.h}

    tokens = needle.split()
    n = len(tokens)
    if n < 2:
        return None
    for i in range(len(words) - n + 1):
        seq = words[i : i + n]
        seq_text = " ".join(w.text.strip(",.").lower() for w in seq)
        if seq_text == needle:
            x0 = min(w.x for w in seq)
            y0 = min(w.y for w in seq)
            x1 = max(w.x + w.w for w in seq)
            y1 = max(w.y + w.h for w in seq)
            return {"page": seq[0].page, "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}
    return None


def extract_document(pdf_bytes: bytes, *, document_type: str) -> ExtractionResult:
    images = convert_from_bytes(pdf_bytes, dpi=150)
    if not images:
        return ExtractionResult()

    preview_png = _to_png_bytes(images[0])

    raw_text_parts: list[str] = []
    all_words: list[OcrWord] = []
    for idx, image in enumerate(images[:MAX_PAGES_SCANNED], start=1):
        text, words = _ocr_image(image, page=idx)
        raw_text_parts.append(text)
        all_words.extend(words)
    raw_text = "\n".join(raw_text_parts)

    fields: dict[str, dict[str, Any]] = {}
    boxes: list[dict[str, Any]] = []
    confidences: list[float] = []

    for field_name, pattern in field_patterns(document_type).items():
        match = pattern.search(raw_text)
        if not match:
            continue
        value = match.group(1).strip()
        box = _find_box(all_words, value)
        confidence = 92.0 if box else 55.0
        confidences.append(confidence)
        fields[field_name] = {
            "value": value,
            "confidence": confidence,
            "page": box["page"] if box else 1,
        }
        if box:
            boxes.append({**box, "label": field_name, "status": "matched"})

    overall_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    return ExtractionResult(
        fields=fields,
        boxes=boxes,
        raw_text=raw_text,
        confidence=overall_confidence,
        page_count=len(images),
        preview_png=preview_png,
    )
