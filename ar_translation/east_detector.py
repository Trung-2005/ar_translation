# east_detector.py
import cv2
import numpy as np

class EASTDetector:
    def __init__(self, model_path="models/frozen_east_text_detection.pb"):
        """Khởi tạo EAST text detector"""
        print("⏳ Đang load EAST model...")
        self.net = cv2.dnn.readNet(model_path)
        self.layer_names = [
            "feature_fusion/Conv_7/Sigmoid",
            "feature_fusion/concat_3"
        ]
        print("✅ EAST model loaded!")

    def detect(self, image, min_confidence=0.3):
        orig_H, orig_W = image.shape[:2]
        newW = (orig_W // 32) * 32
        newH = (orig_H // 32) * 32
        rW = orig_W / float(newW)
        rH = orig_H / float(newH)

        resized = cv2.resize(image, (newW, newH))
        blob = cv2.dnn.blobFromImage(
            resized, 1.0, (newW, newH),
            (123.68, 116.78, 103.94),
            swapRB=True, crop=False
        )

        self.net.setInput(blob)
        scores, geometry = self.net.forward(self.layer_names)
        boxes, confidences = self._decode(scores, geometry, min_confidence)

        if len(boxes) == 0:
            return []

        indices = cv2.dnn.NMSBoxesRotated(
            boxes, confidences,
            score_threshold=min_confidence,
            nms_threshold=0.4
        )

        results = []
        for i in indices:
            box = boxes[i]
            cx = box[0][0] * rW
            cy = box[0][1] * rH
            w  = box[1][0] * rW
            h  = box[1][1] * rH
            results.append(((cx, cy), (w, h), box[2]))

        return results

    def _decode(self, scores, geometry, min_confidence):
        """Giải mã output của EAST thành các box và confidence"""
        num_rows, num_cols = scores.shape[2:4]
        boxes, confidences = [], []

        for y in range(num_rows):
            for x in range(num_cols):
                score = float(scores[0, 0, y, x])
                if score < min_confidence:
                    continue

                offsetX = x * 4.0
                offsetY = y * 4.0
                angle   = float(geometry[0, 4, y, x])
                cos_a   = np.cos(angle)
                sin_a   = np.sin(angle)

                h = float(geometry[0, 0, y, x]) + float(geometry[0, 2, y, x])
                w = float(geometry[0, 1, y, x]) + float(geometry[0, 3, y, x])

                cx = offsetX + cos_a * float(geometry[0, 1, y, x]) \
                             + sin_a * float(geometry[0, 2, y, x])
                cy = offsetY - sin_a * float(geometry[0, 1, y, x]) \
                             + cos_a * float(geometry[0, 2, y, x])

                boxes.append(((cx, cy), (w, h), -angle * 180.0 / np.pi))
                confidences.append(score)

        return boxes, confidences

    def merge_boxes(self, boxes, image_shape,
                    pad_x=50, pad_y=10, merge_gap=30):
        if not boxes:
            return []

        H, W = image_shape[:2]
        rects = []
        for box in boxes:
            pts = cv2.boxPoints(box).astype(np.int32)
            x, y, w, h = cv2.boundingRect(pts)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(W, x + w + pad_x)
            y2 = min(H, y + h + pad_y)
            rects.append([x1, y1, x2, y2])

        rects.sort(key=lambda r: (r[1], r[0]))

        merged = []
        used   = [False] * len(rects)

        for i in range(len(rects)):
            if used[i]:
                continue

            x1, y1, x2, y2 = rects[i]
            h_i = y2 - y1

            for j in range(i + 1, len(rects)):
                if used[j]:
                    continue

                ax1, ay1, ax2, ay2 = rects[j]
                h_j = ay2 - ay1

                center_i = (y1 + y2) / 2
                center_j = (ay1 + ay2) / 2
                same_line = abs(center_i - center_j) < max(h_i, h_j) * 0.6
                close_x   = (ax1 - x2) < merge_gap and (x1 - ax2) < merge_gap

                if same_line and close_x:
                    x1 = min(x1, ax1)
                    y1 = min(y1, ay1)
                    x2 = max(x2, ax2)
                    y2 = max(y2, ay2)
                    used[j] = True

            merged.append((x1, y1, x2 - x1, y2 - y1))
            used[i] = True

        return merged

    def auto_merge_boxes(self, boxes, image_shape):
        """
        Tự động tính pad_x, pad_y, merge_gap
        dựa trên kích thước THỰC TẾ của các box detect được
        → Hoạt động tốt với mọi kích thước ảnh/chữ
        """
        if not boxes:
            return []

        # ── Bước 1: Đo chiều cao & rộng thực của từng box ──
        heights = []
        widths  = []
        for box in boxes:
            pts = cv2.boxPoints(box).astype(np.int32)
            _, _, w, h = cv2.boundingRect(pts)
            heights.append(h)
            widths.append(w)

        # Dùng median để tránh bị ảnh hưởng bởi box quá to/nhỏ
        avg_h = float(np.median(heights))
        avg_w = float(np.median(widths))

        # ── Bước 2: Tính thông số tự động ──────────────────
        # pad_x: đủ để ôm trọn 1 từ (~ 1.2x chiều cao chữ)
        pad_x = int(avg_h * 1.2)

        # pad_y: nhỏ thôi để không gộp 2 dòng (~ 0.25x chiều cao)
        pad_y = int(avg_h * 0.25)

        # merge_gap: gộp các box cùng dòng cách nhau < 1 khoảng chữ
        # Khoảng cách ký tự thường ~ 0.5x chiều cao chữ
        merge_gap = int(avg_h * 0.5)

        print(f"  📐 Thống kê box: avg_h={avg_h:.1f}px, avg_w={avg_w:.1f}px")
        print(f"  ⚙️  Auto params: pad_x={pad_x}, pad_y={pad_y}, merge_gap={merge_gap}")

        return self.merge_boxes(
            boxes, image_shape,
            pad_x=pad_x,
            pad_y=pad_y,
            merge_gap=merge_gap
        )

    def draw_merged_boxes(self, image, merged_boxes):
        result = image.copy()
        for (x, y, w, h) in merged_boxes:
            cv2.rectangle(result,
                          (x, y), (x + w, y + h),
                          (0, 255, 0), 2)
        return result