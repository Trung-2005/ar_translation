# ocr_engine.py
import cv2
import easyocr
import numpy as np
import re

class OCREngine:
    """
    OCR Engine dùng EasyOCR — optimized for speed.

    Mặc định: nhận diện tiếng Anh.
    Có thể đổi sang Nhật (ja) hoặc ngôn ngữ khác bằng set_languages().
    """

    # Map: source_lang (ISO) → EasyOCR codes
    SOURCE_OCR = {
        'en': ['en'],          # English
        'ja': ['ja', 'en'],    # Japanese + English fallback
    }

    DEFAULT_LANGS = ['en']

    # Resize ảnh xuống tối đa cạnh này trước OCR để tăng tốc
    OCR_MAX_DIM = 1000

    # Cache reader để tránh reload tốn thời gian
    _reader_cache = {}

    def __init__(self, languages=None):
        if languages is None:
            languages = list(self.DEFAULT_LANGS)

        self._langs = list(languages)
        self._lang_key = tuple(sorted(self._langs))

        if self._lang_key in self._reader_cache:
            print(f"✅ Dùng EasyOCR cache: {self._langs}")
            self.reader = self._reader_cache[self._lang_key]
            return

        print(f"⏳ Đang load EasyOCR model: {self._langs}")
        self.reader = easyocr.Reader(self._langs, gpu=False)
        self._reader_cache[self._lang_key] = self.reader
        print(f"✅ EasyOCR loaded: {self._langs}")

    @property
    def languages(self):
        return list(self._langs)

    def set_languages(self, languages):
        """Đổi ngôn ngữ OCR (dùng cache nếu đã load)."""
        langs = list(languages)
        key = tuple(sorted(langs))

        if key == self._lang_key:
            return

        self._langs = langs
        self._lang_key = key

        if key in self._reader_cache:
            self.reader = self._reader_cache[key]
            print(f"✅ Đã đổi OCR sang: {langs} (cache)")
        else:
            print(f"⏳ Đang load EasyOCR model: {langs}")
            self.reader = easyocr.Reader(langs, gpu=False)
            self._reader_cache[key] = self.reader
            print(f"✅ EasyOCR loaded: {langs}")

    @staticmethod
    def resize_for_ocr(image, max_dim=OCR_MAX_DIM):
        """
        Resize ảnh xuống max_dim cho cạnh dài nhất.
        Giữ nguyên tỉ lệ. Dùng INTER_AREA khi thu nhỏ.
        """
        h, w = image.shape[:2]
        if max(h, w) <= max_dim:
            return image, 1.0
        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(image, (new_w, new_h),
                             interpolation=cv2.INTER_AREA)
        return resized, scale

    @staticmethod
    def scale_rects(rects, scale):
        """Scale toạ độ rect về ảnh gốc sau khi resize OCR."""
        if scale >= 1.0:
            return rects
        inv = 1.0 / scale
        scaled = []
        for r in rects:
            x, y, w, h = r
            scaled.append((
                int(x * inv), int(y * inv),
                int(w * inv), int(h * inv)
            ))
        return scaled

    def preprocess_full(self, image):
        """Tiền xử lý toàn bộ ảnh trước khi OCR — nhẹ hơn để tăng tốc"""
        # CLAHE nhẹ
        lab   = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        l     = clahe.apply(l)
        lab   = cv2.merge((l, a, b))
        image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        return image

    def is_price_only(self, text):
        """Bỏ qua nếu text chỉ là số/giá tiền"""
        cleaned = re.sub(r'[\s,\.\d+oO]+', '', text)
        return len(cleaned) < 2

    def recognize_full_image(self, image):
        """
        EasyOCR detect + OCR toàn bộ ảnh — optimized for speed.

        1. Resize ảnh xuống OCR_MAX_DIM trước khi xử lý
        2. Preprocess nhẹ
        3. Scale lại toạ độ về ảnh gốc
        """
        # ── 1. Resize để OCR nhanh hơn ────────────────────
        ocr_img, scale = self.resize_for_ocr(image)
        if scale < 1.0:
            print(f"   📐 Resize OCR: {image.shape[1]}x{image.shape[0]}"
                  f" → {ocr_img.shape[1]}x{ocr_img.shape[0]}"
                  f" (scale={scale:.3f})")

        # ── 2. Preprocess ─────────────────────────────────
        processed = self.preprocess_full(ocr_img)

        # ── 3. OCR với params speed-optimized ─────────────
        results = self.reader.readtext(
            processed,
            detail=1,
            paragraph=False,
            text_threshold=0.5,
            low_text=0.3,
            link_threshold=0.3,
            width_ths=0.7,
            # canvas_size thấp hơn = nhanh hơn
            canvas_size=min(1280, self.OCR_MAX_DIM),
            # Không upscale ảnh — ảnh đã resize rồi
            mag_ratio=1.0,
            # Tách dòng nhanh
            slope_ths=0.5,
            ycenter_ths=0.5,
            height_ths=0.5,
            # Bỏ qua text quá nhỏ (< 10px)
            min_size=10,
        )

        # ── 4. Scale toạ độ về ảnh gốc + lọc kết quả ────
        output = []
        for (bbox, text, conf) in results:
            text = text.strip()

            if conf < 0.4:
                print(f"  ⏭️  Bỏ qua (conf thấp {conf:.2f}): '{text}'")
                continue
            if self.is_price_only(text):
                print(f"  ⏭️  Bỏ qua (số/giá): '{text}'")
                continue
            if len(text) < 3:
                print(f"  ⏭️  Bỏ qua (quá ngắn): '{text}'")
                continue

            pts = np.array(bbox).astype(np.int32)

            # Scale toạ độ về ảnh gốc
            if scale < 1.0:
                pts = (pts / scale).astype(np.int32)

            x, y, w, h = cv2.boundingRect(pts)

            # Giới hạn trong ảnh gốc
            H_orig, W_orig = image.shape[:2]
            x = max(0, min(x, W_orig - 1))
            y = max(0, min(y, H_orig - 1))
            w = min(w, W_orig - x)
            h = min(h, H_orig - y)

            output.append({
                "rect":       (x, y, w, h),
                "text":       text,
                "confidence": float(conf)
            })
            print(f"  📝 '{text}' (conf: {conf:.2f})"
                  f" rect=({x},{y},{w},{h})")

        return output

    # ── Các method cũ giữ tương thích ─────────────────
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
