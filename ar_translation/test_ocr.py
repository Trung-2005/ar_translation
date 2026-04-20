# test_ocr.py
import cv2
import numpy as np
from east_detector import EASTDetector
from ocr_engine    import OCREngine

# ── Khởi tạo ──────────────────────────────────────────
detector = EASTDetector()
ocr      = OCREngine(languages=['en'])

# ── Đọc ảnh ───────────────────────────────────────────
image = cv2.imread("test_image.jpg")
if image is None:
    print("❌ Không tìm thấy test_image.jpg!")
    exit()

print(f"📐 Kích thước ảnh: {image.shape[1]}x{image.shape[0]}")

# ── Bước 2: Detect + Merge (dùng đúng thông số bạn đang dùng) ──
print("\n🔍 Đang detect vùng chữ...")
boxes = detector.detect(image, min_confidence=0.3)
print(f"   Raw boxes  : {len(boxes)}")

merged = detector.merge_boxes(
    boxes, image.shape,
    pad_x=50,
    pad_y=10,
    merge_gap=60
)
print(f"   Sau merge  : {len(merged)} vùng")

# ── Bước 3: OCR từng vùng ─────────────────────────────
print("\n📖 Đang nhận dạng chữ...")
ocr_results = ocr.recognize_all(image, merged)

# ── Tổng kết ──────────────────────────────────────────
print(f"\n✅ Nhận dạng được {len(ocr_results)}/{len(merged)} vùng có chữ")
print("\n--- KẾT QUẢ ---")
for i, r in enumerate(ocr_results):
    print(f"[{i+1}] '{r['text']}' | conf: {r['confidence']:.2f}")

# ── Vẽ kết quả lên ảnh ────────────────────────────────
result_img = image.copy()
for r in ocr_results:
    x, y, w, h = r["rect"]

    # Box xanh lá ôm vùng chữ
    cv2.rectangle(result_img,
                  (x, y), (x + w, y + h),
                  (0, 255, 0), 2)

    # Nền đen phía trên để dễ đọc label
    label = r["text"][:35]
    (tw, th), _ = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1
    )
    cv2.rectangle(result_img,
                  (x, y - th - 8), (x + tw + 4, y),
                  (0, 0, 0), -1)
    cv2.putText(result_img, label,
                (x + 2, y - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (0, 255, 0), 1)

cv2.imwrite("result_ocr.jpg", result_img)
print("\n💾 Đã lưu kết quả vào result_ocr.jpg")

cv2.imshow("OCR Result", result_img)
cv2.waitKey(0)
cv2.destroyAllWindows()