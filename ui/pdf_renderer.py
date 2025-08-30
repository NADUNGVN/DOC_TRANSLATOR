from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsTextItem, QTabWidget
)
from PyQt5.QtGui  import QPixmap, QKeySequence, QFont, QPainter
from PyQt5.QtCore import Qt, QThreadPool, QSizeF, QRectF
from pathlib      import Path
from statistics   import median
import logging, json

from ocr          import ocr_vi_layout
from translator   import translate_vi2en
from threading_utils import CallableWorker
from config       import CONFIG

# ╭────────────────────────────────────────────────────────────────────╮
# │ LayoutView – canvas hiển thị văn bản đúng toạ độ A4               │
# ╰────────────────────────────────────────────────────────────────────╯
class LayoutView(QGraphicsView):
    A4_SIZE = QSizeF(595, 842)          # pt (210×297 mm @72 dpi)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(0, 0,
                     self.A4_SIZE.width(), self.A4_SIZE.height()))
        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.TextAntialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._bg_item   = None
        self._zoom_level = 0

    # -------- hiển thị layout & gom text lại thành từng dòng ----------
    def load_layout(self, blocks: list[dict], img_size: tuple[int, int],
                    img_path: Path):
        scn = self.scene();  scn.clear()

        # 1) nền ảnh mờ
        try:
            pix = QPixmap(str(img_path)).scaled(
                    self.A4_SIZE.toSize(), Qt.KeepAspectRatio,
                    Qt.SmoothTransformation)
            self._bg_item = scn.addPixmap(pix)
            self._bg_item.setOpacity(0.2)
        except Exception as e:
            logging.warning("Không thể tải background: %s", e)

        # 2) vẽ text
        img_w, img_h = img_size
        sx, sy       = self.A4_SIZE.width()/img_w, self.A4_SIZE.height()/img_h
        h_pts        = [(b["box"][3]-b["box"][1])*sy for b in blocks]
        global_pt    = max(6, min(28, int((median(h_pts) if h_pts else 12)*.7)))

        for blk in blocks:
            x1,y1,x2,y2 = blk["box"]
            txt = blk["text"].strip()
            if not txt: continue
            item = QGraphicsTextItem(txt)
            item.setFont(QFont("Times New Roman", global_pt))
            item.setPos(x1*sx, y1*sy)
            item.setTextWidth((x2-x1)*sx)
            item.setTextInteractionFlags(Qt.TextEditorInteraction)
            item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
            item.setFlag(QGraphicsTextItem.ItemIsMovable,     True)
            item.setFlag(QGraphicsTextItem.ItemIsFocusable,   True)
            scn.addItem(item)

        self.fitInView(QRectF(0,0,*self.A4_SIZE.toTuple()),
                       Qt.KeepAspectRatio)
        self._zoom_level = 0

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.scale(1.2 if e.angleDelta().y()>0 else 1/1.2,
                       1.2 if e.angleDelta().y()>0 else 1/1.2)
        else:
            super().wheelEvent(e)

    def gather_text_lines(self) -> str:
        items = [i for i in self.scene().items()
                 if isinstance(i, QGraphicsTextItem)]
        items.sort(key=lambda it:(it.pos().y(), it.pos().x()))
        lines, cur_y, buf = [], None, []
        for it in items:
            y = it.pos().y()
            if cur_y is None or abs(y-cur_y)<=14:
                buf.append(it.toPlainText().strip()); cur_y=y
            else:
                lines.append(" ".join(buf)); buf=[it.toPlainText().strip()]; cur_y=y
        if buf: lines.append(" ".join(buf))
        return "\n".join(lines)

# ╭────────────────────────────────────────────────────────────────────╮
# │ OCRTab – thao tác OCR + “✔ Confirm → Translate”                   │
# ╰────────────────────────────────────────────────────────────────────╯
class OCRTab(QWidget):
    def __init__(self):
        super().__init__()
        self.img_path:        Path|None = None
        self._ocr_blocks:     list[dict] | None = None

        # widgets ------------------------------------------------------
        self.image_lbl    = QLabel("No image", alignment=Qt.AlignCenter)
        self.image_lbl.setMinimumWidth(480)
        self.layout_view  = LayoutView()

        self.ocr_btn      = QPushButton("Run OCR (Ctrl+O)")
        self.save_btn     = QPushButton("Save Texts")
        self.confirm_btn  = QPushButton("✔ Confirm → Translate")

        # layout -------------------------------------------------------
        btn_row = QHBoxLayout(); btn_row.addStretch()
        for b in (self.ocr_btn, self.save_btn, self.confirm_btn):
            btn_row.addWidget(b)

        right = QVBoxLayout()
        right.addLayout(btn_row)
        right.addWidget(QLabel("Vietnamese OCR:"))
        right.addWidget(self.layout_view, 1)

        main = QHBoxLayout(self); main.addWidget(self.image_lbl,2); main.addLayout(right,3)

        # signals ------------------------------------------------------
        self.pool = QThreadPool.globalInstance()
        self.ocr_btn.clicked.connect(self._run_ocr)
        self.save_btn.clicked.connect(self._save_texts)
        self.confirm_btn.clicked.connect(self._confirm)
        self.ocr_btn.setShortcut(QKeySequence("Ctrl+O"))

    # ---------------- public API -------------------------------------
    def load_image(self, path: Path):
        self.img_path = path
        pix = QPixmap(str(path)).scaled(self.image_lbl.size(),
              Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_lbl.setPixmap(pix)
        self.layout_view.scene().clear()
        self._ocr_blocks = None

    # ---------------- OCR --------------------------------------------
    def _run_ocr(self):
        if not self.img_path: return
        self._set_btns(False)

        def do():
            blks, sz = ocr_vi_layout(self.img_path)
            (self.img_path.with_suffix("").with_name(
                self.img_path.stem+"_boxes.json")
            ).write_text(json.dumps(blks,ensure_ascii=False,indent=2),
                         encoding="utf-8")
            return {"b":blks,"s":sz}

        w=CallableWorker(do); w.sig.done.connect(self._done); w.sig.error.connect(self._err)
        self.pool.start(w)

    def _done(self,res):
        self._ocr_blocks=res["b"]
        self.layout_view.load_layout(res["b"],res["s"],self.img_path)
        self._set_btns(True)

    # ---------------- Confirm → translate ----------------------------
    def _confirm(self):
        if not self._ocr_blocks:
            QMessageBox.warning(self,"Warning","Please run OCR first."); return
        vi_txt=self.layout_view.gather_text_lines()
        if not vi_txt.strip():
            QMessageBox.warning(self,"Warning","No OCR text found."); return
        self._set_btns(False)
        w=CallableWorker(translate_vi2en,vi_txt)
        w.sig.done.connect(lambda en:self._open_trans_tab(vi_txt,en))
        w.sig.error.connect(self._err); self.pool.start(w)

    def _open_trans_tab(self,vi,en):
        self._set_btns(True)
        tabw=self._find_tab_widget()
        if not tabw: return
        from ui.translator_tab import TranslatorTab    # tránh vòng lặp import
        new=TranslatorTab(vi,en)
        tabw.addTab(new,"Translator"); tabw.setCurrentWidget(new)

    def _find_tab_widget(self)->QTabWidget|None:
        p=self.parent()
        while p and not isinstance(p,QTabWidget): p=p.parent()
        return p

    # ---------------- Save -------------------------------------------
    def _save_texts(self):
        if not (self.img_path and self._ocr_blocks): return
        vi_txt=self.layout_view.gather_text_lines()
        base=self.img_path.with_suffix("")
        (base.with_name(base.name+"_"+CONFIG.vi_filename)).write_text(
            vi_txt,encoding="utf-8")
        logging.info("Saved Vietnamese OCR text")

    # ---------------- helpers ----------------------------------------
    def _err(self,msg:str):
        logging.error(msg); QMessageBox.critical(self,"Error",msg); self._set_btns(True)

    def _set_btns(self,en:bool):
        for b in (self.ocr_btn,self.save_btn,self.confirm_btn): b.setEnabled(en)
