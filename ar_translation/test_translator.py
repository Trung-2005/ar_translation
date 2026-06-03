# test_translator.py
import cv2
from east_detector import EASTDetector
from ocr_engine    import OCREngine
from translator    import Translator

# ── Khởi tạo ──────────────────────────────────────────
detector   = EASTDetector()
ocr        = OCREngine()  # Mặc định: Anh + Trung + Nhật + Hàn
translator = Translator(source_lang='en', target_lang='vi')

# ── Đọc ảnh ───────────────────────────────────────────
image = cv2.imread("test_image.jpg")
if image is None:
    print("❌ Không tìm thấy test_image.jpg!")
    exit()

# ── Bước 2: Detect + Merge ────────────────────────────
print("\n🔍 Đang detect vùng chữ...")
boxes = detector.detect(image, min_confidence=0.3)
merged = detector.merge_boxes(
    boxes, image.shape,
    pad_x=50,
    pad_y=10,
    merge_gap=30  # dùng giá trị đã sửa
)
print(f"   Tìm thấy {len(merged)} vùng")

# ── Bước 3: OCR ───────────────────────────────────────
print("\n📖 Đang nhận dạng chữ...")
ocr_results = ocr.recognize_all(image, merged)
print(f"   Nhận dạng được {len(ocr_results)} vùng")

# ── Bước 4: Dịch thuật ────────────────────────────────
print("\n🌐 Đang dịch thuật...")
translated_results = translator.translate_all(ocr_results)

# ── In kết quả tổng hợp ───────────────────────────────
print("\n--- KẾT QUẢ DỊCH THUẬT ---")
for i, r in enumerate(translated_results):
    print(f"[{i+1}] '{r['text']}'")
    print(f"     → '{r['translated']}'")
    print()

# ── Test cache: dịch lại lần 2 (phải dùng cache) ──────
print("Test cache — dịch lại 'Fried shrimp':")
result2 = translator.translate("Fried shrimp")
print(f"   Kết quả: '{result2}'")

print("\nBước 4 hoàn thành!")