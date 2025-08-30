from PyQt5.QtWidgets import QMainWindow, QTabWidget
from ui.capture_tab   import CaptureTab
from ui.ocr_tab       import OCRTab           # NEW
# Không cần import TranslatorTab; OCRTab sẽ tạo tab đó khi người dùng nhấn “Confirm”

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Doc Translator")
        self.resize(1280,800)

        self.tabs     = QTabWidget()
        self.cap_tab  = CaptureTab(self._on_captured)
        self.ocr_tab  = OCRTab()

        self.tabs.addTab(self.cap_tab,"Capture")   # tab 1
        self.tabs.addTab(self.ocr_tab,"OCR")       # tab 2
        self.setCentralWidget(self.tabs)

    def _on_captured(self, path):
        self.ocr_tab.load_image(path)
        self.tabs.setCurrentWidget(self.ocr_tab)
