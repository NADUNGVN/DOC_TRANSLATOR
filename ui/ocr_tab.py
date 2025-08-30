from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QTabWidget,
)
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtCore import Qt, QThreadPool
from pathlib import Path
from ocr import ocr_vi_layout
from threading_utils import CallableWorker
from config import CONFIG
import logging, json
from ui.layout_view import LayoutView

# -----------------------------------------------------------------------------
# OCRTab – Chỉ OCR tiếng Việt, thêm nút "Xác nhận" để dịch & mở tab mới
# -----------------------------------------------------------------------------

class OCRTab(QWidget):
    """Tab OCR – OCR & xác nhận dịch sang English ở tab mới."""

    def __init__(self):
        super().__init__()
        self.img_path: Path | None = None
        self._ocr_blocks: list[dict] | None = None

        # Widgets trái/phải
        self.image_lbl = QLabel("No image", alignment=Qt.AlignCenter)
        self.image_lbl.setMinimumWidth(480)
        self._img_size: tuple[int, int] | None = None   
        self.layout_view = LayoutView()

        # Buttons
        self.ocr_btn = QPushButton("Run OCR (Ctrl+O)")
        self.confirm_btn = QPushButton("✔ Confirm → Translate")
        self.confirm_btn.setEnabled(False) 

        # Layout
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.ocr_btn)
        btn_row.addWidget(self.confirm_btn)

        right_box = QVBoxLayout()
        right_box.addLayout(btn_row)
        right_box.addWidget(QLabel("Vietnamese OCR:"))
        right_box.addWidget(self.layout_view, 1)

        main_lay = QHBoxLayout(self)
        main_lay.addWidget(self.image_lbl, 2)
        main_lay.addLayout(right_box, 3)

        # Signals
        self.ocr_btn.clicked.connect(self._run_ocr)
        self.confirm_btn.clicked.connect(self._confirm)
        self.ocr_btn.setShortcut(QKeySequence("Ctrl+O"))
        self.pool = QThreadPool.globalInstance()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_image(self, path: Path):
        self.img_path = path
        pix = QPixmap(str(path))
        self.image_lbl.setPixmap(
            pix.scaled(self.image_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.layout_view.scene().clear()
        self._ocr_blocks = None
        self._translated_en = None

    # ------------------------------------------------------------------
    # OCR thread
    # ------------------------------------------------------------------
    def _run_ocr(self):
        if not self.img_path:
            return
        self._set_btns(False)

        def do_ocr():
            blocks, img_size = ocr_vi_layout(self.img_path)
            base = self.img_path.with_suffix("")
            box_path = base.with_name(f"{base.name}_boxes.json")
            box_path.write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"blocks": blocks, "img_size": img_size}

        w = CallableWorker(do_ocr)
        w.sig.done.connect(self._on_ocr_done)
        w.sig.error.connect(self._on_error)
        self.pool.start(w)

    def _on_ocr_done(self, res: dict):
        self._ocr_blocks = res["blocks"]
        self._img_size   = res["img_size"]
        self.layout_view.load_layout(res["blocks"], res["img_size"], self.img_path)
        self._set_btns(True)

    # ---------------- Confirm → open Translator tab ------------------
    def _confirm(self):
        if not self._ocr_blocks:
            QMessageBox.warning(self, "Warning", "Please run OCR first.")
            return

        vi_txt = self.layout_view.gather_text_lines()
        if not vi_txt.strip():
            QMessageBox.warning(self, "Warning", "No OCR text found.")
            return

        tabw = self._find_tab_widget()
        if not tabw:
            return

        from ui.translator_tab import TranslatorTab   # tránh vòng lặp import
        self._save_texts()
        new_tab = TranslatorTab(
            blocks=self._ocr_blocks,
            img_size=self._img_size,
            img_path=self.img_path,
        )
        tabw.addTab(new_tab, "Translator")
        tabw.setCurrentWidget(new_tab)

    def _find_tab_widget(self) -> QTabWidget | None:
        parent = self.parent()
        while parent and not isinstance(parent, QTabWidget):
            parent = parent.parent()
        return parent  # type: ignore

    # ------------------------------------------------------------------
    # Save helper
    # ------------------------------------------------------------------
    def _save_texts(self):
        if not self.img_path or not self._ocr_blocks:
            return
        vi_text = self.layout_view.gather_text_lines()
        base = self.img_path.with_suffix("")
        (base.with_name(base.name + "_" + CONFIG.vi_filename)).write_text(vi_text, encoding="utf-8")
        if self._translated_en:
            (base.with_name(base.name + "_" + CONFIG.en_filename)).write_text(
                self._translated_en, encoding="utf-8"
            )
        logging.info("Saved texts alongside image")

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------
    def _on_error(self, msg: str):
        """Hiển thị dialog và bật lại nút khi worker báo lỗi."""
        logging.error(msg)
        QMessageBox.critical(self, "Error", str(msg))
        self._set_btns(True)

    def _set_btns(self, enabled: bool):
        self.ocr_btn.setEnabled(enabled)
        self.confirm_btn.setEnabled(enabled and self._ocr_blocks is not None)
