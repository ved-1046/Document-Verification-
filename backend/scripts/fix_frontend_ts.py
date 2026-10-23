from pathlib import Path

rd_path = Path("frontend/src/pages/RequestDetailPage.tsx")
rd_content = rd_path.read_text(encoding="utf-8")

lines = rd_content.splitlines()
new_lines = []
for line in lines:
    if line.strip().startswith("const _openFlags =") or line.strip().startswith("const openFlags ="):
        continue
    if line.strip().startswith("const _receiptPurpose =") or line.strip().startswith("const receiptPurpose ="):
        continue
    new_lines.append(line)

rd_path.write_text("\n".join(new_lines), encoding="utf-8")
print("Removed unused lines from RequestDetailPage.tsx")
