# # ocr_engine.py
# import cv2
# import easyocr
# import numpy as np
# import re


# class OCREngine:
#     def __init__(self, languages=['en']):
#         print("⏳ Đang load EasyOCR model...")
#         self.reader = easyocr.Reader(languages, gpu=False)
#         print("✅ EasyOCR loaded!")

#     def preprocess(self, region):
#         gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
#         h, w = gray.shape

#         # Phóng to mạnh hơn nếu chữ nhỏ
#         if h < 64 or w < 64:
#             scale = max(64/h, 64/w, 2.0)
#             gray = cv2.resize(gray, None, fx=scale, fy=scale,
#                             interpolation=cv2.INTER_CUBIC)

#         # Tăng độ tương phản (CLAHE)
#         clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#         gray  = clahe.apply(gray)

#         # Làm sắc nét
#         kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
#         gray   = cv2.filter2D(gray, -1, kernel)

#         # Khử nhiễu nhẹ
#         gray = cv2.bilateralFilter(gray, 9, 75, 75)

#         # Nhị phân hóa
#         _, thresh = cv2.threshold(gray, 0, 255,
#                                 cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#         return thresh
    
#     def is_price_only(self, text):
#         """Trả về True nếu text chỉ là số/giá tiền"""
#         cleaned = re.sub(r'[\s,\.\d+oO]+', '', text)
#         return len(cleaned) < 2
    

#     def recognize(self, image, rect):
#         """rect = (x, y, w, h) từ merge_boxes"""
#         x, y, w, h = rect
#         x  = max(0, x);      y  = max(0, y)
#         w  = min(w, image.shape[1] - x)
#         h  = min(h, image.shape[0] - y)
#         region = image[y:y+h, x:x+w]
#         if region.size == 0:
#             return "", 0.0
#         processed = self.preprocess(region)
#         results   = self.reader.readtext(processed)
#         if not results:
#             return "", 0.0
#         texts = [r[1] for r in results if r[2] > 0.3]
#         confs = [r[2] for r in results if r[2] > 0.3]
#         if not texts:
#             return "", 0.0
#         return " ".join(texts).strip(), float(np.mean(confs))
    

#     def recognize_all(self, image, merged_boxes):
#         results = []
#         for rect in merged_boxes:
#             text, conf = self.recognize(image, rect)
#             if text and not self.is_price_only(text):
#                 results.append({
#                     "rect": rect,
#                     "text": text,
#                     "confidence": conf
#                 })
#                 print(f"  📝 '{text}' (conf: {conf:.2f})")
#             else:
#                 print(f"  ⏭️  Bỏ qua (số/giá): '{text}'")
#         return results




# ocr_engine.py
import cv2
import easyocr
import numpy as np
import re

class OCREngine:
    def __init__(self, languages=['en']):
        print("⏳ Đang load EasyOCR model...")
        self.reader = easyocr.Reader(languages, gpu=False)
        print("✅ EasyOCR loaded!")

    def preprocess_full(self, image):
        """Tiền xử lý toàn bộ ảnh trước khi OCR"""
        # Tăng độ tương phản CLAHE
        lab   = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l     = clahe.apply(l)
        lab   = cv2.merge((l, a, b))
        image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Làm sắc nét nhẹ
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        image  = cv2.filter2D(image, -1, kernel)

        return image

    def is_price_only(self, text):
        """Bỏ qua nếu text chỉ là số/giá tiền"""
        cleaned = re.sub(r'[\s,\.\d+oO]+', '', text)
        return len(cleaned) < 2

    def recognize_full_image(self, image):
        """
        EasyOCR tự detect + OCR toàn bộ ảnh 1 lần
        — Không cần EAST, hoạt động tốt với mọi kích thước ảnh
        """
        # Tiền xử lý ảnh
        processed = self.preprocess_full(image)

        # EasyOCR đọc toàn ảnh
        # detail=1 → trả về bbox + text + confidence
        # paragraph=False → giữ từng dòng riêng biệt
        results = self.reader.readtext(
            processed,
            detail=1,
            paragraph=False,
            # Các thông số giúp detect chính xác hơn
            text_threshold=0.6,    # ngưỡng confidence text
            low_text=0.3,          # ngưỡng phát hiện vùng text thấp
            link_threshold=0.3,    # ngưỡng ghép ký tự thành từ
            canvas_size=2560,      # kích thước tối đa xử lý
            mag_ratio=1.5          # phóng to ảnh trước khi detect
        )

        output = []
        for (bbox, text, conf) in results:
            text = text.strip()

            # Lọc confidence thấp
            if conf < 0.4:
                print(f"  ⏭️  Bỏ qua (conf thấp {conf:.2f}): '{text}'")
                continue

            # Lọc text chỉ là số/giá tiền
            if self.is_price_only(text):
                print(f"  ⏭️  Bỏ qua (số/giá): '{text}'")
                continue

            # Lọc text quá ngắn (1-2 ký tự)
            if len(text) < 3:
                print(f"  ⏭️  Bỏ qua (quá ngắn): '{text}'")
                continue

            # bbox = [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            pts      = np.array(bbox).astype(np.int32)
            x, y, w, h = cv2.boundingRect(pts)

            output.append({
                "rect":       (x, y, w, h),
                "text":       text,
                "confidence": float(conf)
            })
            print(f"  📝 '{text}' (conf: {conf:.2f})")

        return output

    # ── Giữ lại các method cũ để tương thích ────────────
    def preprocess(self, region):
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if h < 64 or w < 64:
            scale = max(64/h, 64/w, 2.0)
            gray  = cv2.resize(gray, None, fx=scale, fy=scale,
                               interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray  = clahe.apply(gray)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        gray   = cv2.filter2D(gray, -1, kernel)
        gray   = cv2.bilateralFilter(gray, 9, 75, 75)
        _, thresh = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def recognize(self, image, rect):
        x, y, w, h = rect
        x = max(0, x);      y = max(0, y)
        w = min(w, image.shape[1] - x)
        h = min(h, image.shape[0] - y)
        region = image[y:y+h, x:x+w]
        if region.size == 0:
            return "", 0.0
        processed = self.preprocess(region)
        results   = self.reader.readtext(processed)
        if not results:
            return "", 0.0
        texts = [r[1] for r in results if r[2] > 0.3]
        confs = [r[2] for r in results if r[2] > 0.3]
        if not texts:
            return "", 0.0
        return " ".join(texts).strip(), float(np.mean(confs))

    def recognize_all(self, image, merged_boxes):
        results = []
        for rect in merged_boxes:
            text, conf = self.recognize(image, rect)
            if text and not self.is_price_only(text):
                results.append({
                    "rect": rect,
                    "text": text,
                    "confidence": conf
                })
                print(f"  📝 '{text}' (conf: {conf:.2f})")
            else:
                print(f"  ⏭️  Bỏ qua: '{text}'")
        return results