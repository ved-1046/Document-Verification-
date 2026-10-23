from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
processor_path = BASE / "app" / "services" / "document_processing" / "processor.py"
content = processor_path.read_text(encoding="utf-8")

# 1. Update _extract_image
old_extract_image = """    def _extract_image(self, path: Path) -> list[tuple[int, str]]:
        from PIL import Image
        self._require_ocr()
        self._raw_ocr_blocks = {}
        with Image.open(str(path)) as source:
            image = source.convert("RGB")
        blocks = self.ocr.extract_blocks(image, page=0)
        self._raw_ocr_blocks[0] = blocks
        reliable_text = self.ocr.reliable_text(blocks, MIN_OCR_CONFIDENCE)
        return [(0, reliable_text)]"""

new_extract_image = """    def _extract_image(self, path: Path) -> list[tuple[int, str]]:
        from PIL import Image, ImageStat
        self._require_ocr()
        self._raw_ocr_blocks = {}
        with Image.open(str(path)) as source:
            image = source.convert("RGB")

        # Blank & resolution assessment
        stat = ImageStat.Stat(image.convert("L"))
        min_v, max_v = stat.extrema[0]
        if (max_v - min_v) < 15 or stat.stddev[0] < 8.0:
            raise RuntimeError("No readable content found. Please upload a document containing the expense details.")
        if image.width < 150 or image.height < 150:
            raise RuntimeError("This document is difficult to read due to low resolution. Please upload a clearer photo or scan.")

        blocks = self.ocr.extract_blocks(image, page=0)
        self._raw_ocr_blocks[0] = blocks
        reliable_text = self.ocr.reliable_text(blocks, MIN_OCR_CONFIDENCE)

        if not reliable_text.strip():
            if not blocks:
                raise RuntimeError("No readable content found. Please upload a document containing the expense details.")
            raise RuntimeError("This document is difficult to read. Please upload a clearer photo or scan.")

        return [(0, reliable_text)]"""

if old_extract_image in content:
    content = content.replace(old_extract_image, new_extract_image)
    print("Replaced _extract_image")
else:
    print("Could not find old_extract_image")

# 2. Update _extract_pdf
old_extract_pdf = """    def _extract_pdf(self, path: Path) -> list[tuple[int, str]]:
        import fitz
        from PIL import Image
        import io

        pdf = fitz.open(str(path))
        pages: list[tuple[int, str]] = []
        self._raw_ocr_blocks = {}
        try:
            for i, page in enumerate(pdf):
                if i >= MAX_PAGES:
                    break
                # Preserve native text extraction; OCR only pages without enough text.
                text = page.get_text("text").strip()
                if len(text) > 50:
                    pages.append((i, text))
                    continue
                self._require_ocr()
                pix = page.get_pixmap(dpi=250, alpha=False)
                with Image.open(io.BytesIO(pix.tobytes("png"))) as source:
                    image = source.convert("RGB")
                blocks = self.ocr.extract_blocks(image, page=i)
                self._raw_ocr_blocks[i] = blocks
                reliable_text = self.ocr.reliable_text(blocks, MIN_OCR_CONFIDENCE)
                pages.append((i, reliable_text))
        finally:
            pdf.close()
        return pages"""

new_extract_pdf = """    def _extract_pdf(self, path: Path) -> list[tuple[int, str]]:
        import fitz
        from PIL import Image, ImageStat
        import io

        pdf = fitz.open(str(path))
        pages: list[tuple[int, str]] = []
        self._raw_ocr_blocks = {}
        had_content_page = False
        try:
            for i, page in enumerate(pdf):
                if i >= MAX_PAGES:
                    break
                # Preserve native text extraction; OCR only pages without enough text.
                text = page.get_text("text").strip()
                if len(text) > 50:
                    pages.append((i, text))
                    had_content_page = True
                    continue
                self._require_ocr()
                pix = page.get_pixmap(dpi=250, alpha=False)
                with Image.open(io.BytesIO(pix.tobytes("png"))) as source:
                    image = source.convert("RGB")
                stat = ImageStat.Stat(image.convert("L"))
                min_v, max_v = stat.extrema[0]
                if (max_v - min_v) < 15 or stat.stddev[0] < 8.0:
                    continue  # Skip blank page in multi-page PDF
                had_content_page = True
                blocks = self.ocr.extract_blocks(image, page=i)
                self._raw_ocr_blocks[i] = blocks
                reliable_text = self.ocr.reliable_text(blocks, MIN_OCR_CONFIDENCE)
                if reliable_text.strip():
                    pages.append((i, reliable_text))
            if not pages:
                if not had_content_page:
                    raise RuntimeError("No readable content found. Please upload a document containing the expense details.")
                raise RuntimeError("This document is difficult to read. Please upload a clearer photo or scan.")
        finally:
            pdf.close()
        return pages"""

if old_extract_pdf in content:
    content = content.replace(old_extract_pdf, new_extract_pdf)
    print("Replaced _extract_pdf")
else:
    print("Could not find old_extract_pdf")

# 3. Add auto-populate request fields
old_event = """            log_event(db, AuditEventType.extraction_completed,
                      request_id=doc.request_id, entity_type="extraction_run",
                      entity_id=run.id, summary=f"OCR completed (engine={self.ocr.engine_name})")

            db.commit()"""

new_event = """            log_event(db, AuditEventType.extraction_completed,
                      request_id=doc.request_id, entity_type="extraction_run",
                      entity_id=run.id, summary=f"OCR completed (engine={self.ocr.engine_name})")

            # Auto-populate request fields from receipt extraction if not already set
            try:
                from app.models.request import Request
                from app.models.document_version import DocType
                from decimal import Decimal
                from datetime import date
                req = db.get(Request, doc.request_id)
                if req and req.status in (RequestStatus.draft, RequestStatus.processing, RequestStatus.submitted):
                    if doc.doc_type == DocType.receipt:
                        if req.claimed_amount is None and "total_amount" in normalized:
                            try:
                                req.claimed_amount = Decimal(normalized["total_amount"])
                            except Exception:
                                pass
                        if req.expense_date is None and "expense_date" in normalized:
                            try:
                                req.expense_date = date.fromisoformat(normalized["expense_date"])
                            except Exception:
                                pass
                        if (not req.currency or req.currency == "INR") and "currency" in normalized:
                            req.currency = normalized["currency"]
                        if "merchant_name" in normalized and normalized["merchant_name"]:
                            merchant = normalized["merchant_name"].strip()
                            if not req.title or any(req.title.lower().startswith(p) for p in ("expense reimbursement", "untitled claim", "new expense claim", "general expense")):
                                req.title = f"{merchant} Reimbursement"
                    db.flush()
            except Exception as e:
                logger.warning("Could not auto-populate request fields from extraction: %s", e)

            db.commit()"""

if old_event in content:
    content = content.replace(old_event, new_event)
    print("Added auto-populate logic")
else:
    print("Could not find old_event")

processor_path.write_text(content, encoding="utf-8")
print("Updated processor.py successfully.")
