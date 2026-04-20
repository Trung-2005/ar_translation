# test_ar_overlay.py
import cv2
from east_detector import EASTDetector
from ocr_engine    import OCREngine
from translator    import Translator
from ar_overlay    import AROverlay

detector   = EASTDetector()
ocr        = OCREngine(languages=['en'])
translator = Translator(source_lang='en', target_lang='vi')
overlay    = AROverlay(font_path="fonts/arial.ttf")

image = cv2.imread("test_image.jpg")
if image is None:
    print("❌ Không tìm thấy test_image.jpg!")
    exit()

print(f"📐 Kích thước ảnh: {image.shape[1]}x{image.shape[0]}")

# ── Bước 2: Detect + Merge ────────────────────────────
# Dùng 1 bộ box duy nhất — đủ padding để OCR đọc đúng
print("\n🔍 Đang detect vùng chữ...")
boxes  = detector.detect(image, min_confidence=0.3)
merged = detector.merge_boxes(
    boxes, image.shape,
    pad_x=50,
    pad_y=10,
    merge_gap=30
)
print(f"   Tìm thấy {len(merged)} vùng")

# ── Bước 3: OCR ───────────────────────────────────────
print("\n📖 Đang nhận dạng chữ...")
ocr_results = ocr.recognize_all(image, merged)
print(f"   Nhận dạng được {len(ocr_results)} vùng")

# ── Bước 4: Dịch thuật ────────────────────────────────
print("\n🌐 Đang dịch thuật...")
translated_results = translator.translate_all(ocr_results)

# ── Bước 5: AR Overlay ────────────────────────────────
# shrink=10: thu box vào 10px mỗi phía khi vẽ
# → tránh chồng lên box kề, vẫn đúng vị trí
print("\n🎨 Đang vẽ AR overlay...")
result_image = overlay.draw_all(image, translated_results, shrink=4)

cv2.imwrite("result_ar.jpg", result_image)
print("\n💾 Đã lưu kết quả vào result_ar.jpg")

cv2.imshow("AR Translation Result", result_image)
cv2.waitKey(0)
cv2.destroyAllWindows()