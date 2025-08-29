from PyQt5.QtWidgets import QWidget, QLabel, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtCore import Qt, QThreadPool
from pathlib import Path
from ocr import ocr_vi
from translator import translate_vi2en
from threading_utils import CallableWorker
from config import CONFIG
import logging

class TranslateTab(QWidget):
    def __init__(self):
        super().__init__()
        self.img_path: Path | None = None

        self.image_lbl = QLabel("No image", alignment=Qt.AlignCenter)
        self.vi_edit, self.en_edit = QTextEdit(), QTextEdit(readOnly=True)
        self.ocr_btn = QPushButton("Run OCR (Ctrl+O)")
        self.trans_btn = QPushButton("Translate (Ctrl+T)")
        self.save_btn = QPushButton("Save Texts")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.ocr_btn)
        btn_row.addWidget(self.trans_btn)
        btn_row.addWidget(self.save_btn)

        main_lay = QHBoxLayout(self)
        main_lay.addWidget(self.image_lbl, 2)
        right_box = QVBoxLayout()
        right_box.addLayout(btn_row)
        right_box.addWidget(QLabel("Vietnamese OCR:"))
        right_box.addWidget(self.vi_edit, 1)
        right_box.addWidget(QLabel("English Translation:"))
        right_box.addWidget(self.en_edit, 1)
        main_lay.addLayout(right_box, 3)

        self.ocr_btn.clicked.connect(self._run_ocr)
        self.trans_btn.clicked.connect(self._run_translate)
        self.save_btn.clicked.connect(self._save_texts)
        self.ocr_btn.setShortcut(QKeySequence("Ctrl+O"))
        self.trans_btn.setShortcut(QKeySequence("Ctrl+T"))

        self.pool = QThreadPool.globalInstance()

    def load_image(self, path: Path):
        self.img_path = path
        pix = QPixmap(str(path))
        self.image_lbl.setPixmap(pix.scaled(self.image_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.vi_edit.clear()
        self.en_edit.clear()

    def _run_ocr(self):
        if not self.img_path:
            return
        self._set_btns(False)
        w = CallableWorker(ocr_vi, self.img_path)
        w.sig.done.connect(self._on_ocr_done)
        w.sig.error.connect(self._on_error)
        self.pool.start(w)

    def _run_translate(self):
        vi = self.vi_edit.toPlainText().strip()
        if not vi:
            return
        self._set_btns(False)
        w = CallableWorker(translate_vi2en, vi)
        w.sig.done.connect(self._on_translate_done)
        w.sig.error.connect(self._on_error)
        self.pool.start(w)

    def _save_texts(self):
        if not self.img_path:
            return
        base = self.img_path.with_suffix("")
        (base.with_name(base.name + "_" + CONFIG.vi_filename)).write_text(self.vi_edit.toPlainText(), encoding="utf-8")
        (base.with_name(base.name + "_" + CONFIG.en_filename)).write_text(self.en_edit.toPlainText(), encoding="utf-8")
        logging.info("Saved texts alongside image")

    def _on_ocr_done(self, text: str):
        self.vi_edit.setPlainText(text)
        self._set_btns(True)

    def _on_translate_done(self, text: str):
        self.en_edit.setPlainText(text)
        self._set_btns(True)

    def _on_error(self, msg: str):
        self._set_btns(True)
        logging.error(msg)
        QMessageBox.critical(self, "Error", msg)

    def _set_btns(self, en: bool):
        for b in (self.ocr_btn, self.trans_btn, self.save_btn):
            b.setEnabled(en)