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

# ➕ HÀM MỚI: trả về layout chi tiết
def ocr_vi_layout(image_path: Path) -> tuple[list[dict], tuple[int, int]]:
    with image_path.open("rb") as f:
        img = vision.Image(content=f.read())
    resp = VISION_CLIENT.text_detection(image=img, image_context={"language_hints": ["vi"]})
    if resp.error.message:
        raise RuntimeError(resp.error.message)

    blocks = []
    for anno in resp.text_annotations[1:]:  # Bỏ phần text tổng hợp đầu tiên
        text = anno.description.strip()
        vertices = anno.bounding_poly.vertices
        x_coords = [v.x for v in vertices]
        y_coords = [v.y for v in vertices]
        x, y = min(x_coords), min(y_coords)
        w, h = max(x_coords) - x, max(y_coords) - y
        blocks.append({
            "text": text,
            "box": [x, y, w, h]
        })

    # Trả về (danh sách block, kích thước ảnh gốc)
    from PIL import Image
    with Image.open(image_path) as im:
        width, height = im.size
    return blocks, (width, height)
