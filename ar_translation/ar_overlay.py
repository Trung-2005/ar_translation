# ar_overlay.py
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class AROverlay:
    def __init__(self, font_path="fonts/arial.ttf"):
        self.font_path = font_path

    def _get_font(self, size):
        try:
            return ImageFont.truetype(self.font_path, max(8, size))
        except:
            return ImageFont.load_default()

    def _fit_font_size(self, text, max_w, max_h, min_size=10):
        """Tìm font size lớn nhất vừa khít trong box"""
        size  = max(min_size, int(max_h * 0.72))
        dummy = Image.new("RGB", (1, 1))
        draw  = ImageDraw.Draw(dummy)
        while size > min_size:
            font = self._get_font(size)
            bbox = draw.textbbox((0, 0), text, font=font)
            tw   = bbox[2] - bbox[0]
            th   = bbox[3] - bbox[1]
            if tw <= max_w - 10 and th <= max_h - 4:
                break
            size -= 1
        return size

    def _shrink_rect(self, rect, image_shape, shrink=6):
        """Thu nhỏ box vào trong shrink pixel mỗi phía"""
        x, y, w, h = rect
        H, W = image_shape[:2]
        x1 = max(0,     x + shrink)
        y1 = max(0,     y + shrink)
        x2 = min(W,     x + w - shrink)
        y2 = min(H,     y + h - shrink)
        # Nếu sau shrink box quá nhỏ thì giữ nguyên
        if x2 - x1 < 20 or y2 - y1 < 10:
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(W, x + w), min(H, y + h)
        return x1, y1, x2 - x1, y2 - y1

    def draw_one(self, image, rect, translated_text, shrink=6):
        """Vẽ AR overlay cho 1 vùng"""
        # Thu nhỏ box để không chồng lên các box kề
        sx, sy, sw, sh = self._shrink_rect(rect, image.shape, shrink)
        H, W = image.shape[:2]
        x2 = min(W, sx + sw)
        y2 = min(H, sy + sh)

        if x2 <= sx or y2 <= sy:
            return image

        # ── 1. Nền trắng đặc che hoàn toàn chữ gốc ──────────
        cv2.rectangle(image, (sx, sy), (x2, y2),
                      (255, 255, 255), -1)

        # ── 2. Viền xanh mảnh ────────────────────────────────
        cv2.rectangle(image, (sx, sy), (x2, y2),
                      (0, 150, 0), 1)

        # ── 3. Vẽ chữ dịch căn giữa (PIL) ────────────────────
        box_w = x2 - sx
        box_h = y2 - sy
        fs    = self._fit_font_size(translated_text, box_w, box_h)
        font  = self._get_font(fs)

        img_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw    = ImageDraw.Draw(img_pil)

        bbox = draw.textbbox((0, 0), translated_text, font=font)
        tw   = bbox[2] - bbox[0]
        th   = bbox[3] - bbox[1]

        tx = sx + max(4, (box_w - tw) // 2)
        ty = sy + max(2, (box_h - th) // 2)

        # Shadow
        draw.text((tx + 1, ty + 1), translated_text,
                  font=font, fill=(160, 160, 160))
        # Chữ chính
        draw.text((tx, ty), translated_text,
                  font=font, fill=(170, 0, 0))

        image[:] = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        return image

    def draw_all(self, image, translated_results, shrink=6):
        result = image.copy()
        for r in translated_results:
            result = self.draw_one(
                result,
                r["rect"],
                r["translated"],
                shrink=shrink
            )
            print(f"  🖼️  '{r['text']}' → '{r['translated']}'")
        return result