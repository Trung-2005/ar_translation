# test_east.py
import cv2
from east_detector import EASTDetector

detector = EASTDetector()
image    = cv2.imread("test_image.jpg")

if image is None:
    print("❌ Không tìm thấy test_image.jpg!")
    exit()

print(f"📐 Kích thước ảnh: {image.shape[1]}x{image.shape[0]}")

boxes = detector.detect(image, min_confidence=0.3)  # hạ xuống 0.3 để bắt thêm box
print(f"🔍 Raw boxes  : {len(boxes)}")

merged = detector.merge_boxes(
    boxes, image.shape,
    pad_x=50,      # ← tăng từ 20 lên 50
    pad_y=10,      # ← tăng từ 8 lên 10
    merge_gap=30   # ← tăng từ 40 lên 60
)
print(f"📦 Sau merge  : {len(merged)}")

result = detector.draw_merged_boxes(image, merged)
cv2.imwrite("result_east_merged.jpg", result)
print("💾 Đã lưu: result_east_merged.jpg")

print("\n--- Danh sách boxes ---")
for i, (x, y, w, h) in enumerate(merged):
    print(f"  [{i+1}] x={x}, y={y}, w={w}, h={h}")

cv2.imshow("Merged EAST", result)
cv2.waitKey(0)
cv2.destroyAllWindows()