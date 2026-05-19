# # test_ar_overlay.py
# import cv2
# from east_detector import EASTDetector
# from ocr_engine    import OCREngine
# from translator    import Translator
# from ar_overlay    import AROverlay

# detector   = EASTDetector()
# ocr        = OCREngine(languages=['en'])
# translator = Translator(source_lang='en', target_lang='vi')
# overlay    = AROverlay(font_path="fonts/arial.ttf")

# image = cv2.imread("test_image.jpg")
# if image is None:
#     print("❌ Không tìm thấy test_image.jpg!")
#     exit()

# print(f"📐 Kích thước ảnh: {image.shape[1]}x{image.shape[0]}")

# print("\n🔍 Đang detect vùng chữ...")
# boxes = detector.detect(image, min_confidence=0.3)
# print(f"   Raw boxes: {len(boxes)}")

# # ── THAY ĐỔI DUY NHẤT: dùng auto_merge_boxes thay vì merge_boxes ──
# print("\n⚙️  Đang tính thông số tự động...")
# merged = detector.auto_merge_boxes(boxes, image.shape)
# print(f"   Sau merge: {len(merged)} vùng")

# print("\n📖 Đang nhận dạng chữ...")
# ocr_results = ocr.recognize_all(image, merged)
# print(f"   Nhận dạng được {len(ocr_results)} vùng")

# print("\n🌐 Đang dịch thuật...")
# translated_results = translator.translate_all(ocr_results)

# print("\n🎨 Đang vẽ AR overlay...")
# result_image = overlay.draw_all(image, translated_results, shrink=4)

# cv2.imwrite("result_ar.jpg", result_image)
# print("\n💾 Đã lưu kết quả vào result_ar.jpg")

# cv2.imshow("AR Translation Result", result_image)
# cv2.waitKey(0)
# cv2.destroyAllWindows()




# HƯỚNG SỐ 2: EasyOCR quét toàn ảnh

import cv2
from ocr_engine  import OCREngine
from translator  import Translator
from ar_overlay  import AROverlay

# ── HƯỚNG 2: Không cần EASTDetector nữa ──────────────
ocr        = OCREngine(languages=['en'])
translator = Translator(source_lang='en', target_lang='vi')
overlay    = AROverlay(font_path="fonts/arial.ttf")

image = cv2.imread("fh66tgpPTwRVf9KU39k4RmFL2ijf1bsCDXUZrVk2.jpg")
if image is None:
    print("❌ Không tìm thấy fh66tgpPTwRVf9KU39k4RmFL2ijf1bsCDXUZrVk2.jpg!")
    exit()

print(f"📐 Kích thước ảnh: {image.shape[1]}x{image.shape[0]}")

# ── Bước mới: EasyOCR quét toàn ảnh 1 lần ────────────
print("\n📖 Đang OCR toàn bộ ảnh...")
ocr_results = ocr.recognize_full_image(image)
print(f"\n✅ Nhận dạng được {len(ocr_results)} vùng chữ")

# ── Dịch thuật ────────────────────────────────────────
print("\n🌐 Đang dịch thuật...")
translated_results = translator.translate_all(ocr_results)

# ── AR Overlay ────────────────────────────────────────
print("\n🎨 Đang vẽ AR overlay...")
result_image = overlay.draw_all(image, translated_results, shrink=4)

cv2.imwrite("result_ar.jpg", result_image)
print("\n💾 Đã lưu kết quả vào result_ar.jpg")

print("\n--- KẾT QUẢ ---")
for i, r in enumerate(translated_results):
    print(f"[{i+1}] '{r['text']}' → '{r['translated']}'")

cv2.imshow("AR Translation Result", result_image)
cv2.waitKey(0)
cv2.destroyAllWindows()