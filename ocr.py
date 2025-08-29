from pathlib import Path
from google.cloud import vision
from google.oauth2 import service_account
from config import CREDENTIALS

if not CREDENTIALS:
    raise RuntimeError("Missing Google credentials")

VISION_CLIENT = vision.ImageAnnotatorClient(
    credentials=service_account.Credentials.from_service_account_file(CREDENTIALS)
)

def ocr_vi(image_path: Path) -> str:
    with image_path.open("rb") as f:
        img = vision.Image(content=f.read())
    resp = VISION_CLIENT.text_detection(image=img, image_context={"language_hints": ["vi"]})
    if resp.error.message:
        raise RuntimeError(resp.error.message)
    return resp.text_annotations[0].description.strip()
