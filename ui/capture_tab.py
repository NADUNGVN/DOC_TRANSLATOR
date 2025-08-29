from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
from PyQt5.QtGui import QPixmap, QImage, QKeySequence
from PyQt5.QtCore import Qt, QTimer, QThreadPool
from PyQt5.QtGui import QGuiApplication
from pathlib import Path
from datetime import datetime
import cv2
import logging
from config import CONFIG
from ui.document_cropper import rectify_to_a4
import numpy as np
from config import CAPTURE_DIR

class CaptureTab(QWidget):
    def __init__(self, on_captured):
        super().__init__()

        # --- Kích thước preview khớp màn hình hiện tại ---
        scr_geo = QGuiApplication.primaryScreen().availableGeometry()
        self.preview_w, self.preview_h = scr_geo.width(), scr_geo.height()

        self.on_captured = on_captured
        self.rotate_deg = 0

        # --- Mở webcam ---
        self.cap = cv2.VideoCapture(CONFIG.webcam_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open webcam {CONFIG.webcam_index}")

        # --- Thiết lập độ phân giải + khóa manual-exposure ---
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CONFIG.capture_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG.capture_height)

        # 1) tắt hoàn toàn auto-exposure
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)     # 1 = Manual (DirectShow)

        # 2) giảm 1 bước exposure (≈ tối đi 1 stop)
        self.cap.set(cv2.CAP_PROP_EXPOSURE, -5)         # gốc thường là –5

        # 3) bù lại ~0,3-0,5 stop bằng gain nhỏ
        self.cap.set(cv2.CAP_PROP_GAIN, 1)

        # (tùy chọn) in log để kiểm chứng
        # print("AutoExp =", self.cap.get(cv2.CAP_PROP_AUTO_EXPOSURE))
        # print("Exposure =", self.cap.get(cv2.CAP_PROP_EXPOSURE))
        # print("Gain     =", self.cap.get(cv2.CAP_PROP_GAIN))

        # --- Phần giao diện hiển thị ---
        self.view = QLabel(alignment=Qt.AlignCenter)
        self.view.setFixedSize(self.preview_w, self.preview_h)
        self.view.setScaledContents(False)

        self.overlay_lbl = QLabel("", self)
        self.overlay_lbl.setStyleSheet(
            "color:white; background-color:rgba(0,0,0,120); padding:4px;"
        )
        self.overlay_lbl.move(10, 10)
        self.overlay_lbl.setFixedWidth(300)

        self.rot_l_btn  = QPushButton("⟲")
        self.rot_r_btn  = QPushButton("⟳")
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

        # --- Kết nối sự kiện ---
        self.rot_l_btn.clicked.connect(lambda: self._rotate(-90))
        self.rot_r_btn.clicked.connect(lambda: self._rotate(90))
        self.capture_btn.clicked.connect(self._capture)
        self.rot_l_btn.setShortcut(QKeySequence("Ctrl+L"))
        self.rot_r_btn.setShortcut(QKeySequence("Ctrl+R"))

        # --- Bắt đầu luồng preview ---
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

        # 1️⃣ áp dụng góc xoay do người dùng chọn
        frame = self._apply_rotation(frame)                # ← thêm dòng này

        # 2️⃣ hiệu chỉnh về A4
        try:
            warped, H = rectify_to_a4(frame)
        except RuntimeError as e:
            QMessageBox.warning(self, "Capture error", str(e))
            return

        # 3️⃣ lưu ảnh + homography như trước
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = CAPTURE_DIR / f"capture_{ts}"
        img_path = base.with_suffix(".jpg")
        npy_path = base.with_name(base.name + "_H.npy")

        cv2.imwrite(str(img_path), warped,
                    [int(cv2.IMWRITE_JPEG_QUALITY), CONFIG.jpeg_quality])
        np.save(npy_path, H)

        self.on_captured(img_path)