# translator.py
import requests
import time

class Translator:
    def __init__(self, source_lang='en', target_lang='vi'):
        self.source_lang = source_lang
        self.target_lang = target_lang
        # Cache lưu kết quả dịch — tránh gọi API lặp lại
        self._cache = {}

    def translate(self, text):
        """Dịch 1 đoạn text, có cache"""
        if not text or not text.strip():
            return ""

        # Kiểm tra cache trước
        key = text.strip().lower()
        if key in self._cache:
            print(f"  💾 [cache] '{text}' → '{self._cache[key]}'")
            return self._cache[key]

        result = self._call_mymemory(text)

        # Lưu vào cache
        # Normalize: chỉ viết hoa chữ cái đầu câu
        result = result.capitalize()
        self._cache[key] = result
        return result

    def _call_mymemory(self, text):
        """
        Gọi MyMemory API — miễn phí, không cần API key
        Giới hạn: 1000 request/ngày
        """
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {
                "q":        text.strip(),
                "langpair": f"{self.source_lang}|{self.target_lang}",
                "de":       "your_email@gmail.com"  # tuỳ chọn, tăng giới hạn lên 10k/ngày
            }
            response = requests.get(url, params=params, timeout=10)
            data     = response.json()

            if data["responseStatus"] == 200:
                translated = data["responseData"]["translatedText"]
                return translated
            else:
                print(f"  ⚠️  API lỗi: {data['responseStatus']}")
                return text  # fallback: trả nguyên bản

        except requests.exceptions.Timeout:
            print("  ⚠️  API timeout!")
            return text
        except Exception as e:
            print(f"  ⚠️  Lỗi: {e}")
            return text

    def translate_all(self, ocr_results):
        """
        Dịch toàn bộ kết quả OCR
        — nhận vào list dict từ ocr.recognize_all()
        — trả về list dict bổ sung thêm trường 'translated'
        """
        results = []
        for i, r in enumerate(ocr_results):
            print(f"  🌐 [{i+1}/{len(ocr_results)}] '{r['text']}'", end=" → ")

            translated = self.translate(r["text"])
            print(f"'{translated}'")

            # Thêm trường translated vào dict
            results.append({
                "rect":       r["rect"],
                "text":       r["text"],
                "confidence": r["confidence"],
                "translated": translated
            })

            # Delay nhỏ tránh spam API
            time.sleep(0.3)

        return results