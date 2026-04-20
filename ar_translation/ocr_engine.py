# ocr_engine.py
import cv2
import easyocr
import numpy as np

class OCREngine:
    def __init__(self, languages=['en']):
        print("⏳ Đang load EasyOCR model...")
        self.reader = easyocr.Reader(languages, gpu=False)
        print("✅ EasyOCR loaded!")

    def preprocess(self, region):
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if h < 32 or w < 32:
            scale = max(32/h, 32/w)
            gray  = cv2.resize(gray, None, fx=scale, fy=scale,
                               interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        _, thresh = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    def recognize(self, image, rect):
        """rect = (x, y, w, h) từ merge_boxes"""
        x, y, w, h = rect
        x  = max(0, x);      y  = max(0, y)
        w  = min(w, image.shape[1] - x)
        h  = min(h, image.shape[0] - y)
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
            if text:
                results.append({
                    "rect": rect,
                    "text": text,
                    "confidence": conf
                })
                print(f"  📝 '{text}' (conf: {conf:.2f})")
            else:
                print(f"  ⚠️  Bỏ qua vùng {rect}")
        return results