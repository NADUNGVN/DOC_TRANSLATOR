# document_cropper.py
import cv2
import numpy as np
import matplotlib.pyplot as plt

A4_PX_PORTRAIT  = (2480, 3508)   # 210×297 mm @300 dpi  (w, h)
A4_PX_LANDSCAPE = (3508, 2480)   # hoán đổi khi trang xoay ngang

def _order_points(pts: np.ndarray) -> np.ndarray:
    """Trả về 4 điểm theo thứ tự TL, TR, BR, BL."""
    s   = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    return np.array([
        pts[np.argmin(s)],          # TL
        pts[np.argmin(diff)],       # TR
        pts[np.argmax(s)],          # BR
        pts[np.argmax(diff)],       # BL
    ], dtype=np.float32)

def rectify_to_a4(img_bgr, debug=False):
    """
    Tìm khung giấy A4, warp về đúng tỉ lệ.
    Trả về: warped_img (np.ndarray), homography H (3×3)
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blur, 50, 150)

    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_area = img_bgr.shape[0] * img_bgr.shape[1]
    doc_cnt  = None
    max_area = 0

    for c in cnts:
        peri  = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        area   = cv2.contourArea(approx)
        if len(approx) == 4 and area > max_area and area > 0.3 * img_area:
            doc_cnt, max_area = approx, area

    if doc_cnt is None:
        raise RuntimeError("Không tìm được contour 4 góc đủ lớn của trang")

    ordered = _order_points(doc_cnt.reshape(4, 2).astype(np.float32))

    # Xác định trang đang portrait hay landscape
    (tl, tr, br, bl) = ordered
    widthA  = np.linalg.norm(br - bl)
    widthB  = np.linalg.norm(tr - tl)
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)

    avg_w = (widthA + widthB) / 2
    avg_h = (heightA + heightB) / 2

    if avg_w > avg_h:                 # trang xoay ngang
        w, h = A4_PX_LANDSCAPE
    else:
        w, h = A4_PX_PORTRAIT

    dest = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]],
                    dtype=np.float32)

    H = cv2.getPerspectiveTransform(ordered, dest)
    warped = cv2.warpPerspective(img_bgr, H, (w, h))

    if debug:
        dbg = img_bgr.copy()
        cv2.drawContours(dbg, [doc_cnt], -1, (0, 255, 0), 3)
        plt.subplot(1, 2, 1); plt.imshow(cv2.cvtColor(dbg, cv2.COLOR_BGR2RGB)); plt.title("Contour")
        plt.subplot(1, 2, 2); plt.imshow(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)); plt.title("Warped")
        plt.show()

    return warped, H
