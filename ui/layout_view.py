from PyQt5.QtWidgets import (
    QWidget,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsTextItem,
)
from PyQt5.QtGui import QPixmap, QFont, QPainter
from PyQt5.QtCore import Qt, QSizeF, QRectF
from statistics import median
from pathlib import Path
import logging


class LayoutView(QGraphicsView):
    """Canvas A4:

    * Hiển thị box OCR đúng toạ độ tuyệt đối.
    * Ctrl + Wheel để zoom tuỳ ý.
    * Luôn auto-fit trang bên trong khung view.
    """

    A4_SIZE = QSizeF(595, 842)  # pt (210×297 mm @72 dpi)

    # ------------------------------------------------------------------
    # INIT
    # ------------------------------------------------------------------
    def __init__(self, parent: QWidget | None = None, *, editable: bool = True):
        super().__init__(parent)

        self.setScene(QGraphicsScene(0, 0,
                                     self.A4_SIZE.width(),
                                     self.A4_SIZE.height()))

        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.TextAntialiasing)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Giúp trang luôn ở giữa & giữ tỷ lệ khi resize view
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self._bg_item   = None          # ảnh nền mờ
        self._editable  = editable

    # ------------------------------------------------------------------
    # LOAD LAYOUT
    # ------------------------------------------------------------------
    def load_layout(
        self,
        blocks: list[dict],
        img_size: tuple[int, int],
        img_path: Path,
    ):
        """Vẽ lại toàn bộ trang (nền + text boxes)"""
        scn = self.scene()
        scn.clear()

        # 1. Background (ảnh mờ)
        try:
            pix = QPixmap(str(img_path)).scaled(
                self.A4_SIZE.toSize(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._bg_item = scn.addPixmap(pix)
            self._bg_item.setOpacity(0.2)
        except Exception as e:           # pragma: no cover
            logging.warning("Không thể tải background: %s", e)

        # 2. Box text
        img_w, img_h = img_size
        sx = self.A4_SIZE.width() / img_w
        sy = self.A4_SIZE.height() / img_h

        h_pts = [(b["box"][3] - b["box"][1]) * sy for b in blocks]
        base_pt = max(6, min(28, int((median(h_pts) if h_pts else 12) * 0.7)))
        logging.info("Auto font size ≈ %s pt", base_pt)

        for blk in blocks:
            x1, y1, x2, y2 = blk["box"]
            txt = blk["text"].strip()
            if not txt:
                continue

            item = QGraphicsTextItem(txt)
            item.setFont(QFont("Times New Roman", base_pt))
            item.setPos(x1 * sx, y1 * sy)
            item.setTextWidth((x2 - x1) * sx)

            # Flags
            if self._editable:
                item.setTextInteractionFlags(Qt.TextEditorInteraction)                
                item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
                item.setFlag(QGraphicsTextItem.ItemIsFocusable, True)
                item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
            else:
                item.setTextInteractionFlags(Qt.TextSelectableByMouse)
                item.setFlag(QGraphicsTextItem.ItemIsFocusable, False)
            
            scn.addItem(item)

        # 3. Fit trang vào khung
        self._fit_page()

    # ------------------------------------------------------------------
    # RESIZE EVENT  →  luôn fit lại
    # ------------------------------------------------------------------
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._fit_page()

    # ------------------------------------------------------------------
    # ZOOM (Ctrl + wheel)
    # ------------------------------------------------------------------
    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            factor = 1.2 if e.angleDelta().y() > 0 else 1 / 1.2
            self.scale(factor, factor)
        else:
            super().wheelEvent(e)

    # ------------------------------------------------------------------
    # COLLECT TEXT (trả về plain-text sau khi user chỉnh)
    # ------------------------------------------------------------------
    def gather_text_lines(self) -> str:
        items = [i for i in self.scene().items()
                 if isinstance(i, QGraphicsTextItem)]
        items.sort(key=lambda it: (it.pos().y(), it.pos().x()))

        lines, buf, cur_y = [], [], None
        thresh = 14  # pt – ngưỡng cùng dòng

        for it in items:
            y = it.pos().y()
            if cur_y is None or abs(y - cur_y) <= thresh:
                buf.append(it.toPlainText().strip())
                cur_y = y if cur_y is None else cur_y
            else:
                lines.append(" ".join(buf))
                buf = [it.toPlainText().strip()]
                cur_y = y
        if buf:
            lines.append(" ".join(buf))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # SHOW PLAIN TEXT (dùng cho canvas tiếng Anh readonly)
    # ------------------------------------------------------------------
    def show_plain_text(self, text: str):
        scn = self.scene()
        scn.clear()

        item = QGraphicsTextItem(text)
        item.setFont(QFont("Times New Roman", 12))
        item.setPos(20, 20)
        item.setTextWidth(self.A4_SIZE.width() - 40)
        item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        scn.addItem(item)

        self._fit_page()

    # ------------------------------------------------------------------
    # INTERNAL: fit page helper
    # ------------------------------------------------------------------
    def _fit_page(self):
        """Scale & center trang A4 để vừa khung, giữ tỉ lệ."""
        self.fitInView(QRectF(0, 0,
                              self.A4_SIZE.width(),
                              self.A4_SIZE.height()),
                       Qt.KeepAspectRatio)
        # Về giữa:
        self.centerOn(self.A4_SIZE.width() / 2,
                      self.A4_SIZE.height() / 2)
