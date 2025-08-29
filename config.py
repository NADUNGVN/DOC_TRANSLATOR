from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    webcam_index: int = 0
    capture_width: int = 2048
    capture_height: int = 1536
    max_ocr_side: int = 2048
    jpeg_quality: int = 100
    vi_filename: str = "vi.txt"
    en_filename: str = "en.txt"

CONFIG = Config()

CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL_ID", "openai/gpt-oss-120b")
