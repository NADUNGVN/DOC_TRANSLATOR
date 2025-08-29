from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPixmap, QImage, QKeySequence
from PyQt5.QtCore import Qt, QTimer, QThreadPool
from PyQt5.QtGui import QGuiApplication
from pathlib import Path
from datetime import datetime
import cv2
import logging
from config import CONFIG
from ui.document_cropper import detect_and_crop_document


class CaptureTab(QWidget):
    def __init__(self, on_captured):
        super().__init__()
        scr_geo = QGuiApplication.primaryScreen().availableGeometry()
        self.preview_w, self.preview_h = scr_geo.width(), scr_geo.height()

        self.on_captured = on_captured
        self.rotate_deg = 0

        self.cap = cv2.VideoCapture(CONFIG.webcam_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open webcam {CONFIG.webcam_index}")

        # Thiết lập độ phân giải và tắt auto exposure (nếu hỗ trợ)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG.capture_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG.capture_height)
        # self.cap.set(cv2.CAP_PROP_FPS, 60)
        # self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
        # self.cap.set(cv2.CAP_PROP_GAIN, 0)  
        # self.cap.set(cv2.CAP_PROP_EXPOSURE, -6)         # Điều chỉnh theo webcam

        # Giao diện hiển thị
        self.view = QLabel(alignment=Qt.AlignCenter)
        self.view.setFixedSize(self.preview_w, self.preview_h)
        self.view.setScaledContents(False)

        # Overlay thông tin góc xoay, độ phân giải
        self.overlay_lbl = QLabel("", self)
        self.overlay_lbl.setStyleSheet("color: white; background-color: rgba(0,0,0,120); padding: 4px;")
        self.overlay_lbl.move(10, 10)
        self.overlay_lbl.setFixedWidth(300)

        self.rot_l_btn = QPushButton("⟲")
        self.rot_r_btn = QPushButton("⟳")
        self.capture_btn = QPushButton("📸 Capture")

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.rot_l_btn)
        btn_row.addWidget(self.rot_r_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.capture_btn)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.view, 1)
        lay.addLayout(btn_row)

        self.rot_l_btn.clicked.connect(lambda: self._rotate(-90))
        self.rot_r_btn.clicked.connect(lambda: self._rotate(90))
        self.capture_btn.clicked.connect(self._capture)
        self.rot_l_btn.setShortcut(QKeySequence("Ctrl+L"))
        self.rot_r_btn.setShortcut(QKeySequence("Ctrl+R"))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)

    def _update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = self._apply_rotation(frame)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)
        self.view.setPixmap(
            pix.scaled(self.view.width(), self.view.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

        # Cập nhật overlay thông tin
        self.overlay_lbl.setText(f"Rotation: {self.rotate_deg}° | Resolution: {w}x{h}")

    def _apply_rotation(self, frame):
        if self.rotate_deg == 0:
            return frame
        rot_map = {
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE
        }
        return cv2.rotate(frame, rot_map[self.rotate_deg])

    def _rotate(self, deg: int):
        self.rotate_deg = (self.rotate_deg + deg) % 360

    def _capture(self):
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = self._apply_rotation(frame)
        # 👉 CROP tự động giấy tờ
        frame = detect_and_crop_document(frame)

        # Tạo thư mục captures nếu chưa tồn tại
        capture_dir = Path.cwd() / "captures"
        capture_dir.mkdir(exist_ok=True)

        fn = f"capture_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        path = capture_dir / fn
        cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, CONFIG.jpeg_quality])
        logging.info("Saved %s", path)
        self.on_captured(path)
        cv2.imwrite("debug_crop.jpg", frame)

    def closeEvent(self, e):
        self.cap.release()
        super().closeEvent(e)
