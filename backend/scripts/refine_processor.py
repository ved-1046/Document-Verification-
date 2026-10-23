from pathlib import Path

path = Path("backend/app/services/document_processing/processor.py")
c = path.read_text(encoding="utf-8")

# In _extract_image, remove the raise and return [(0, reliable_text)]
old_tail = (
    "        if not reliable_text.strip():\n"
    "            if not blocks:\n"
    '                raise RuntimeError("No readable content found. Please upload a document containing the expense details.")\n'
    '            raise RuntimeError("This document is difficult to read. Please upload a clearer photo or scan.")\n\n'
    "        return [(0, reliable_text)]"
)

new_tail = "        return [(0, reliable_text)]"

if old_tail in c:
    c = c.replace(old_tail, new_tail)
    print("Updated _extract_image tail")
else:
    print("Could not match old_tail")

old_empty = (
    '            if not full_text:\n'
    '                raise RuntimeError(\n'
    '                    "No readable text met the OCR confidence threshold. Check the document image and OCR language data."\n'
    '                )'
)

new_empty = (
    '            if not full_text:\n'
    '                # Differentiate blank documents from blurry / unreadable documents\n'
    '                all_blocks = [b for blocks in self._raw_ocr_blocks.values() for b in blocks]\n'
    '                if not all_blocks:\n'
    '                    raise RuntimeError("No readable content found. Please upload a document containing the expense details.")\n'
    '                confs = [b.confidence for b in all_blocks if b.confidence is not None]\n'
    '                avg_conf = sum(confs) / len(confs) if confs else 0.0\n'
    '                if avg_conf < 0.40:\n'
    '                    raise RuntimeError("This document is difficult to read. Please upload a clearer photo or scan.")\n'
    '                raise RuntimeError("No readable content found. Please upload a document containing the expense details.")'
)

if old_empty in c:
    c = c.replace(old_empty, new_empty)
    print("Updated process empty text handling")
else:
    print("Could not match old_empty")

path.write_text(c, encoding="utf-8")
print("Saved processor.py")
