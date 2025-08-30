# ui/translator_tab.py
from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import List, Tuple

from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QGraphicsTextItem,          # ← đúng module
)
from PyQt5.QtCore import QThreadPool, Qt
from PyQt5.QtGui  import QFont
from threading_utils import CallableWorker
from translator      import translate_vi2en
from ui.layout_view  import LayoutView


class TranslatorTab(QWidget):
    """Trái: LayoutView (editable) – Phải: LayoutView (readonly)."""

    # ------------------------------------------------------------------
    def __init__(
        self,
        *,
        blocks: List[dict],
        img_size: Tuple[int, int],
        img_path: Path | str,
    ) -> None:
        super().__init__()

        # canvas Vietnamese
        self.vi_view = LayoutView(editable=True)
        self.vi_view.load_layout(blocks, img_size, Path(img_path))
        self._blocks_orig = blocks          # giữ box gốc
        self._img_size   = img_size

        # canvas English (readonly)
        self.en_view = LayoutView(editable=False)

        # translate button
        self.trans_btn = QPushButton("Translate → English")
        self.trans_btn.setShortcut("Ctrl+T")
        self.trans_btn.clicked.connect(self._translate)

        # layout
        top = QHBoxLayout(); top.addStretch(); top.addWidget(self.trans_btn)

        left  = QVBoxLayout(); left.addWidget(QLabel("Vietnamese OCR:"))
        left.addWidget(self.vi_view, 1)

        right = QVBoxLayout(); right.addWidget(QLabel("English translator:"))
        right.addWidget(self.en_view, 1)

        panes = QHBoxLayout(); panes.addLayout(left, 1); panes.addLayout(right, 1)

        root = QVBoxLayout(self); root.addLayout(top); root.addLayout(panes, 1)

        self.pool = QThreadPool.globalInstance()

    # ------------------------------------------------------------------
    # TRANSLATE: dịch toàn bộ văn bản (sau khi user đã chỉnh)
    # ------------------------------------------------------------------
    def _translate(self) -> None:
        texts = [blk["text"].strip() for blk in self._blocks_orig]
        if not any(texts):
            QMessageBox.warning(self, "Warning", "No Vietnamese text!")
            return

        joined = " ### ".join(texts)

        self._set_busy(True)
        worker = CallableWorker(translate_vi2en, joined)
        worker.sig.done.connect(self._show_en_blocks)
        worker.sig.error.connect(self._show_err)        # slot đã có
        self.pool.start(worker)

    # ------------------------------------------------------------------
    # HIỂN THỊ English theo đúng vị trí box gốc (readonly)
    # ------------------------------------------------------------------
    def _show_en_blocks(self, full_en: str) -> None:
        parts = [p.strip().replace("*", "") for p in full_en.split(" ### ")]
        if len(parts) < len(self._blocks_orig):
            parts += [""] * (len(self._blocks_orig) - len(parts))

        blocks_en = []
        for blk, en_txt in zip(self._blocks_orig, parts):
            new_blk = dict(blk)
            new_blk["text"] = en_txt
            blocks_en.append(new_blk)

        self.en_view.load_layout(
            blocks   = blocks_en,
            img_size = self._img_size,
            img_path = None,            # không cần nền ảnh
        )
        self._set_busy(False)

    # ------------------------------------------------------------------
    # ERROR handler
    # ------------------------------------------------------------------
    def _show_err(self, msg: str) -> None:
        QMessageBox.critical(self, "Error", msg)
        self._set_busy(False)

    # ------------------------------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        self.trans_btn.setEnabled(not busy)
