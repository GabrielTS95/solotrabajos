from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "ia_agent_8_etapas_detallado.md"
OUTPUT = ROOT / "docs" / "ia_agent_8_etapas_detallado.pdf"

PAGE_W = 595.28
PAGE_H = 841.89
MARGIN_X = 52
MARGIN_TOP = 54
MARGIN_BOTTOM = 48
LINE_GAP = 4


def escape_pdf_text(text: str) -> bytes:
    raw = text.encode("cp1252", errors="replace")
    out = bytearray()
    for b in raw:
        if b in (40, 41, 92):
            out.append(92)
            out.append(b)
        elif b in (10, 13):
            out.append(32)
        else:
            out.append(b)
    return bytes(out)


def wrap_text(text: str, font_size: int, max_width: float) -> list[str]:
    if not text:
        return [""]
    avg_width = font_size * 0.48
    max_chars = max(20, int(max_width / avg_width))
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            lines.append(current)
        while len(word) > max_chars:
            lines.append(word[: max_chars - 1] + "-")
            word = word[max_chars - 1 :]
        current = word
    if current:
        lines.append(current)
    return lines or [""]


class PdfWriter:
    def __init__(self) -> None:
        self.pages: list[list[bytes]] = []
        self.current: list[bytes] = []
        self.y = PAGE_H - MARGIN_TOP
        self.page_number = 0
        self.new_page()

    def new_page(self) -> None:
        if self.current:
            self._footer()
            self.pages.append(self.current)
        self.page_number += 1
        self.current = []
        self.y = PAGE_H - MARGIN_TOP
        self._header()

    def _header(self) -> None:
        self.rect(0, PAGE_H - 32, PAGE_W, 32, fill=(0.04, 0.12, 0.30))
        self.text("IA-AGENT - Guia detallada por etapas", 52, PAGE_H - 22, 10, "F2", color=(1, 1, 1))

    def _footer(self) -> None:
        self.line(52, 38, PAGE_W - 52, 38, color=(0.78, 0.82, 0.88), width=0.7)
        self.text(f"Pagina {self.page_number}", PAGE_W - 112, 24, 8, "F1", color=(0.35, 0.42, 0.52))

    def ensure_space(self, needed: float) -> None:
        if self.y - needed < MARGIN_BOTTOM:
            self.new_page()

    def line(self, x1: float, y1: float, x2: float, y2: float, color=(0, 0, 0), width=1) -> None:
        r, g, b = color
        self.current.append(f"{r:.3f} {g:.3f} {b:.3f} RG {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S".encode())

    def rect(self, x: float, y: float, w: float, h: float, fill=(1, 1, 1), stroke=None, width=1) -> None:
        r, g, b = fill
        if stroke is None:
            self.current.append(f"{r:.3f} {g:.3f} {b:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f".encode())
        else:
            sr, sg, sb = stroke
            self.current.append(
                f"{r:.3f} {g:.3f} {b:.3f} rg {sr:.3f} {sg:.3f} {sb:.3f} RG {width:.2f} w "
                f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re B".encode()
            )

    def text(self, text: str, x: float, y: float, size: int, font: str = "F1", color=(0.05, 0.10, 0.20)) -> None:
        r, g, b = color
        payload = escape_pdf_text(text)
        self.current.append(
            b"BT "
            + f"{r:.3f} {g:.3f} {b:.3f} rg /{font} {size} Tf {x:.2f} {y:.2f} Td ".encode()
            + b"("
            + payload
            + b") Tj ET"
        )

    def add_heading(self, text: str, level: int) -> None:
        if level == 1:
            self.ensure_space(70)
            self.y -= 8
            self.text(text, MARGIN_X, self.y, 22, "F2", color=(0.04, 0.12, 0.30))
            self.y -= 24
            self.line(MARGIN_X, self.y, PAGE_W - MARGIN_X, self.y, color=(0.14, 0.33, 0.78), width=1.2)
            self.y -= 18
        elif level == 2:
            if self.page_number > 1 or self.y < PAGE_H - 120:
                self.new_page()
            self.ensure_space(54)
            self.rect(MARGIN_X - 8, self.y - 28, PAGE_W - (2 * MARGIN_X) + 16, 34, fill=(0.91, 0.96, 1.0), stroke=(0.37, 0.58, 0.86), width=0.8)
            self.text(text, MARGIN_X, self.y - 18, 16, "F2", color=(0.04, 0.18, 0.46))
            self.y -= 48
        else:
            self.ensure_space(34)
            self.y -= 2
            self.text(text, MARGIN_X, self.y, 12, "F2", color=(0.07, 0.22, 0.47))
            self.y -= 18

    def add_paragraph(self, text: str, font_size: int = 10, indent: float = 0, bullet: bool = False) -> None:
        max_width = PAGE_W - (2 * MARGIN_X) - indent
        prefix = "- " if bullet else ""
        wrapped = wrap_text(text, font_size, max_width - (12 if bullet else 0))
        needed = len(wrapped) * (font_size + LINE_GAP) + 4
        self.ensure_space(needed)
        for index, line in enumerate(wrapped):
            x = MARGIN_X + indent
            if bullet and index == 0:
                self.text(prefix + line, x, self.y, font_size, "F1")
            elif bullet:
                self.text("  " + line, x, self.y, font_size, "F1")
            else:
                self.text(line, x, self.y, font_size, "F1")
            self.y -= font_size + LINE_GAP
        self.y -= 2

    def add_code(self, text: str) -> None:
        for line in wrap_text(text, 8, PAGE_W - (2 * MARGIN_X)):
            self.ensure_space(13)
            self.text(line, MARGIN_X + 8, self.y, 8, "F3", color=(0.18, 0.24, 0.32))
            self.y -= 12

    def finish(self) -> bytes:
        if self.current:
            self._footer()
            self.pages.append(self.current)
            self.current = []
        return build_pdf(self.pages)


def render_markdown(markdown: str) -> bytes:
    pdf = PdfWriter()
    in_code = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            pdf.add_code(line)
            continue
        if not line.strip():
            pdf.y -= 5
            continue
        if line.startswith("# "):
            pdf.add_heading(line[2:].strip(), 1)
        elif line.startswith("## "):
            pdf.add_heading(line[3:].strip(), 2)
        elif line.startswith("### "):
            pdf.add_heading(line[4:].strip(), 3)
        elif line.startswith("- "):
            pdf.add_paragraph(line[2:].strip(), bullet=True)
        else:
            cleaned = re.sub(r"`([^`]+)`", r"\1", line)
            pdf.add_paragraph(cleaned)
    return pdf.finish()


def build_pdf(pages: list[list[bytes]]) -> bytes:
    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    catalog_id = add(b"")
    pages_id = add(b"")
    font_regular_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_bold_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    font_mono_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")

    page_ids: list[int] = []
    for commands in pages:
        stream = b"\n".join(commands)
        content_id = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_obj = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W:.2f} {PAGE_H:.2f}] "
            f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R /F3 {font_mono_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode()
        page_ids.append(add(page_obj))

    kids = b" ".join(f"{page_id} 0 R".encode() for page_id in page_ids)
    objects[pages_id - 1] = b"<< /Type /Pages /Kids [ " + kids + b" ] /Count " + str(len(page_ids)).encode() + b" >>"
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()

    out = bytearray(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = [0]
    for obj_id, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{obj_id} 0 obj\n".encode())
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


def main() -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(render_markdown(markdown))
    print(OUTPUT)


if __name__ == "__main__":
    main()
