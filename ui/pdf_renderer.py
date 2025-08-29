from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from pathlib import Path

def export_layout_pdf(blocks: list[dict], image_size: tuple[int, int], output_path: Path):
    pdf_w, pdf_h = A4  # đơn vị point (1 pt = 1/72 inch)

    img_w, img_h = image_size
    scale_x = pdf_w / img_w
    scale_y = pdf_h / img_h

    c = canvas.Canvas(str(output_path), pagesize=A4)
    c.setFont("Helvetica", 10)

    for blk in blocks:
        text = blk.get("text_en", "").strip()
        if not text:
            continue
        x, y, w, h = blk["box"]

        # Scale từ ảnh sang PDF
        px = x * scale_x
        py = pdf_h - (y * scale_y)  # PDF gốc ở bottom-left, nên phải lật y

        # In đoạn text (tạm thời chỉ 1 dòng)
        c.drawString(px, py, text)

    c.save()
