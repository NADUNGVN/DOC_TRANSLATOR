# config.py
from pathlib import Path
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CAPTURE_DIR = BASE_DIR / "captures"
CAPTURE_DIR.mkdir(exist_ok=True)       # tự tạo thư mục nếu chưa có

@dataclass(frozen=True)
class Config:
    webcam_index: int = 1
    capture_width: int = 2048
    capture_height: int = 1536
    max_ocr_side: int = 2048
    jpeg_quality: int = 100
    vi_filename: str = "vi.txt"
    en_filename: str = "en.txt"

CONFIG = Config()

CREDENTIALS  = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME   = os.getenv("GROQ_MODEL_ID", "openai/gpt-oss-120b")
