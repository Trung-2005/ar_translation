# translator.py
import requests
import time
import re

class Translator:
    def __init__(self, source_lang='en', target_lang='vi'):
        self.source_lang = source_lang
        self.target_lang = target_lang
        # Cache lưu kết quả dịch — tránh gọi API lặp lại
        self._cache = {}

    def clean_text(self, text):
        """Loại bỏ ký tự OCR sai và số giá tiền"""
        text = re.sub(r'\b\d[\d,\.\s]*\d\b', '', text)
        text = re.sub(r'[_@#\|\\\/\*~`]', '', text)
        text = ' '.join(text.split())
        return text.strip()

    def translate(self, text):
        """Dịch 1 text đơn lẻ (dùng cache)"""
        if not text or not text.strip():
            return ""

        cleaned = self.clean_text(text)
        if not cleaned or len(cleaned) < 3:
            return text

        key = cleaned.lower()
        if key in self._cache:
            return self._cache[key]

        result = self._call_mymemory(cleaned)
        result = result.capitalize()
        self._cache[key] = result
        return result

    def translate_batch(self, texts):
        """
        Dịch NHIỀU text trong 1 request API duy nhất.

        Chiến lược:
          - Gộp các text bằng separator ' [§] '
          - MyMemory giữ nguyên separator trong kết quả
          - Tách kết quả ra thành list
          - Cache từng kết quả riêng

        Args:
            texts: list[str] — danh sách text cần dịch

        Returns:
            list[str] — danh sách đã dịch, cùng thứ tự
        """
        if not texts:
            return []

        # ── 1. Làm sạch từng text ─────────────────────────
        cleaned_list = []
        for t in texts:
            c = self.clean_text(t)
            if c and len(c) >= 3:
                cleaned_list.append(c)
            else:
                cleaned_list.append(t)

        # ── 2. Kiểm tra cache ─────────────────────────────
        results = [""] * len(cleaned_list)
        uncached_indices = []
        uncached_texts = []

        for i, t in enumerate(cleaned_list):
            key = t.lower()
            if key in self._cache:
                results[i] = self._cache[key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(t)

        # Nếu tất cả đều đã cache → trả về ngay
        if not uncached_texts:
            return results

        # ── 3. Gộp tất cả vào 1 request ──────────────────
        SEP = " [§] "
        combined = SEP.join(uncached_texts)

        try:
            translated_all = self._call_mymemory(combined)
            # Tách kết quả
            parts = translated_all.split(SEP)

            for idx, i in enumerate(uncached_indices):
                translated_text = parts[idx] if idx < len(parts) else uncached_texts[idx]
                translated_text = translated_text.strip().capitalize()
                self._cache[uncached_texts[idx].lower()] = translated_text
                results[i] = translated_text

            n_new = len(uncached_indices)
            n_cached = len(texts) - n_new
            print(f"   🌐 Batch: {n_new} mới + {n_cached} cache"
                  f" → 1 request")

        except Exception as e:
            print(f"  ⚠️  Batch lỗi ({e}), fallback từng cái...")
            for idx, i in enumerate(uncached_indices):
                try:
                    t = uncached_texts[idx]
                    r = self._call_mymemory(t).capitalize()
                    self._cache[t.lower()] = r
                    results[i] = r
                except:
                    results[i] = uncached_texts[idx]

        return results

    def _call_mymemory(self, text):
        """
        Gọi MyMemory API — miễn phí, không cần API key.

        Hỗ trợ cả text đơn và text đã gộp separator.
        """
        if not text or not text.strip():
            return ""

        try:
            url = "https://api.mymemory.translated.net/get"
            params = {
                "q":        text.strip(),
                "langpair": f"{self.source_lang}|{self.target_lang}",
                "de":       "your_email@gmail.com"
            }
            response = requests.get(url, params=params, timeout=15)
            data     = response.json()

            if data["responseStatus"] == 200:
                return data["responseData"]["translatedText"]
            else:
                print(f"  ⚠️  API lỗi: {data['responseStatus']}")
                return text

        except requests.exceptions.Timeout:
            print("  ⚠️  API timeout!")
            return text
        except Exception as e:
            print(f"  ⚠️  Lỗi: {e}")
            return text

    def translate_all(self, ocr_results):
        """
        Dịch toàn bộ kết quả OCR — dùng batch API.

        Nhận vào list dict từ ocr.recognize_all()
        Trả về list dict bổ sung thêm trường 'translated'
        """
        if not ocr_results:
            return []

        print(f"  🌐 Batch dịch {len(ocr_results)} vùng...")

        # Trích xuất text cần dịch
        texts = [r["text"] for r in ocr_results]

        # Dịch batch 1 lần
        translated_texts = self.translate_batch(texts)

        # Ghép kết quả
        results = []
        for i, r in enumerate(ocr_results):
            translated = translated_texts[i] if i < len(translated_texts) else r["text"]
            print(f"     [{i+1}] '{r['text']}' → '{translated}'")

            results.append({
                "rect":       r["rect"],
                "text":       r["text"],
                "confidence": r["confidence"],
                "translated": translated
            })

        return results

    def translate_all_sequential(self, ocr_results):
        """
        Dịch tuần tự từng cái (giữ lại để backup).
        """
        results = []
        for i, r in enumerate(ocr_results):
            print(f"  🌐 [{i+1}/{len(ocr_results)}] '{r['text']}'", end=" → ")

            translated = self.translate(r["text"])
            print(f"'{translated}'")

            results.append({
                "rect":       r["rect"],
                "text":       r["text"],
                "confidence": r["confidence"],
                "translated": translated
            })

            time.sleep(0.3)

        return results
