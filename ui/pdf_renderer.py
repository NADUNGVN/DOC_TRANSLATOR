from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from pathlib import Path

# Đăng ký font tiếng Việt hỗ trợ Unicode
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

def export_layout_pdf(blocks: list[dict], image_size: tuple[int, int], output_path: Path):

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

    pdf_w, pdf_h = A4
    img_w, img_h = image_size
    scale_x = pdf_w / img_w
    scale_y = pdf_h / img_h

    c = canvas.Canvas(str(output_path), pagesize=A4)

    style = ParagraphStyle(
        name="TextBlock",
        fontName="HeiseiMin-W3",
        fontSize=8.5,
        leading=10,
        alignment=TA_LEFT,
    )

    for blk in blocks:
        text = blk.get("text_en", "").strip()
        if not text:
            continue
        x, y, w, h = blk["box"]
        px = x * scale_x
        py = pdf_h - (y + h) * scale_y
        pw = w * scale_x
        ph = h * scale_y

        # Nếu block quá nhỏ, tăng padding
        if pw < 30: pw = 40
        if ph < 15: ph = 18

        frame = Frame(px, py, pw, ph, showBoundary=0)
        para = Paragraph(text.replace("\n", "<br />"), style)
        frame.addFromList([para], c)

    c.save()

