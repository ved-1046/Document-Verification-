"""
OCR engine wrapper — provides a uniform interface over pytesseract.
Can be swapped to PaddleOCR by implementing the same interface.

TextBlock: one extracted piece of text with its position.
"""
from dataclasses import dataclass
from typing import Optional
import importlib

from PIL import Image


@dataclass
class TextBlock:
    text: str
    page: int = 0
    left: Optional[int] = None
    top: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    confidence: Optional[float] = None
    block_number: Optional[int] = None
    line_number: Optional[int] = None

    @property
    def bbox(self) -> Optional[str]:
        if all(v is not None for v in (self.left, self.top, self.width, self.height)):
            return f"{self.left},{self.top},{self.width},{self.height}"
        return None


class OCREngine:
    """Synchronous OCR engine backed by pytesseract."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self._available = False
        self._engine_name = "unavailable"
        self._unavailable_reason: str | None = None
        try:
            import pytesseract
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            # Check both the executable and the language data used by this app.
            pytesseract.get_tesseract_version()
            languages = pytesseract.get_languages(config="")
            if "eng" not in languages:
                raise RuntimeError(
                    "Tesseract English language data (eng.traineddata) is missing or unavailable."
                )
            self._available = True
            self._engine_name = "tesseract"
        except Exception as exc:
            self._available = False
            self._unavailable_reason = str(exc) or "Tesseract could not be initialized."

    @property
    def engine_name(self) -> str:
        return self._engine_name

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def unavailable_reason(self) -> str | None:
        return self._unavailable_reason

    def extract_blocks(self, image: Image.Image, page: int = 0) -> list[TextBlock]:
        """
        Run OCR on a PIL image.
        Returns list of TextBlock with text, position, and confidence.
        Returns empty list if engine not available (caller handles error state).
        """
        if not self._available:
            return []
        import pytesseract
        data = pytesseract.image_to_data(
            image,
            lang="eng",
            config="--psm 6",
            output_type=pytesseract.Output.DICT,
        )
        blocks: list[TextBlock] = []
        for i, text in enumerate(data["text"]):
            if not text.strip():
                continue
            conf = data["conf"][i]
            if isinstance(conf, str):
                try:
                    conf = float(conf)
                except ValueError:
                    conf = -1
            blocks.append(TextBlock(
                text=text.strip(),
                page=page,
                left=data["left"][i],
                top=data["top"][i],
                width=data["width"][i],
                height=data["height"][i],
                confidence=conf / 100.0 if conf >= 0 else None,
                block_number=data["block_num"][i],
                line_number=data["line_num"][i],
            ))
        return blocks

    @staticmethod
    def reliable_text(blocks: list[TextBlock], min_confidence: float) -> str:
        """Join sufficiently confident OCR words while preserving Tesseract line boundaries."""
        lines: dict[tuple[int, int], list[str]] = {}
        for index, block in enumerate(blocks):
            if block.confidence is None or block.confidence < min_confidence or not block.text.strip():
                continue
            key = (
                block.block_number if block.block_number is not None else 0,
                block.line_number if block.line_number is not None else index,
            )
            lines.setdefault(key, []).append(block.text.strip())
        return "\n".join(" ".join(words) for words in lines.values())

    def full_text(self, image: Image.Image) -> str:
        """Return the full page text as a single string."""
        blocks = self.extract_blocks(image)
        return " ".join(b.text for b in blocks)
