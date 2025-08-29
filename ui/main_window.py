from PyQt5.QtWidgets import QMainWindow, QTabWidget
from ui.capture_tab import CaptureTab
from ui.translate_tab import TranslateTab
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Doc Translator")
        self.resize(1280, 800)

        self.tabs = QTabWidget()
        self.cap_tab = CaptureTab(self._on_captured)
        self.tr_tab = TranslateTab()
        self.tabs.addTab(self.cap_tab, "Capture")
        self.tabs.addTab(self.tr_tab, "Translate")

        self.setCentralWidget(self.tabs)

    def _on_captured(self, path: Path):
        self.tr_tab.load_image(path)
        self.tabs.setCurrentWidget(self.tr_tab)
