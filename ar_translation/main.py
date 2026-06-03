# main.py
import cv2
import numpy as np
import base64
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from east_detector import EASTDetector
from ocr_engine    import OCREngine
from translator    import Translator
from ar_overlay    import AROverlay

# ── Khởi tạo app ──────────────────────────────────────
app = FastAPI(title="AR Translation API")

# Cho phép Flutter gọi API (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load models 1 lần khi server khởi động ────────────
print("⏳ Đang khởi động server...")
# detector   = EASTDetector()
ocr        = OCREngine()  # Mặc định: tiếng Anh
translator = Translator(source_lang='en', target_lang='vi')
overlay    = AROverlay(font_path="fonts/arial.ttf")
print("✅ Server sẵn sàng!")


def _resolve_ocr_langs(source_lang: str):
    """Lấy EasyOCR codes từ source_lang. Mặc định: ['en']"""
    return list(OCREngine.SOURCE_OCR.get(source_lang, OCREngine.DEFAULT_LANGS))


# ══════════════════════════════════════════════════════
# ENDPOINT 1: Health check
# ══════════════════════════════════════════════════════
@app.get("/")
def health_check():
    return {
        "status": "running",
        "message": "AR Translation API đang hoạt động!"
    }


# ══════════════════════════════════════════════════════
# ENDPOINT 2: Dịch ảnh — trả về ảnh AR đã xử lý
# Flutter gửi ảnh lên → nhận lại ảnh đã dịch (base64)
# ══════════════════════════════════════════════════════
@app.post("/translate-image")
async def translate_image(
    file: UploadFile = File(...),
    source_lang: str = "en",
    target_lang: str = "vi"
):
    # ── Kiểm tra định dạng file ────────────────────────
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ ảnh JPG hoặc PNG!"
        )

    try:
        # ── Đọc ảnh từ request ────────────────────────
        contents = await file.read()
        np_arr   = np.frombuffer(contents, np.uint8)
        image    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(
                status_code=400,
                detail="Không đọc được ảnh!"
            )

        print(f"\n📥 Nhận ảnh: {image.shape[1]}x{image.shape[0]}")
        print(f"   source_lang={source_lang} → target_lang={target_lang}")

        # ── Cấu hình OCR theo ngôn ngữ nguồn ───────────
        ocr_langs = _resolve_ocr_langs(source_lang)
        ocr.set_languages(ocr_langs)
        print(f"   🔤 OCR languages: {ocr_langs}")

        # ── OCR toàn ảnh ──────────────────────────────
        print("📖 Đang OCR toàn ảnh...")
        ocr_results = ocr.recognize_full_image(image)
        print(f"✅ Nhận dạng được {len(ocr_results)} vùng")

        if len(ocr_results) == 0:
            _, buffer = cv2.imencode(".jpg", image)
            img_b64   = base64.b64encode(buffer).decode("utf-8")
            return JSONResponse({
                "status":        "no_text",
                "message":       "Không tìm thấy chữ trong ảnh!",
                "regions_found": 0,
                "image_base64":  img_b64
            })

        print(f"📖 OCR: {len(ocr_results)} vùng có chữ")

        # ── Dịch thuật ────────────────────────
        translator.source_lang = source_lang
        translator.target_lang = target_lang
        translated_results = translator.translate_all(ocr_results)
        print(f"🌐 Đã dịch {len(translated_results)} vùng")

        # ── AR Overlay ────────────────────────
        result_image = overlay.draw_all(image, translated_results, shrink=4)

        # ── Encode ảnh kết quả → base64 ───────────────
        _, buffer = cv2.imencode(
            ".jpg", result_image,
            [cv2.IMWRITE_JPEG_QUALITY, 90])
        img_b64 = base64.b64encode(buffer).decode("utf-8")

        # ── Trả về JSON ───────────────────────────────
        return JSONResponse({
            "status":        "success",
            "regions_found": len(ocr_results),
            "regions_translated": len(translated_results),
            "translations": [
                {
                    "original":   r["text"],
                    "translated": r["translated"],
                    "confidence": round(r["confidence"], 2)
                }
                for r in translated_results
            ],
            "image_base64": img_b64
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════
# ENDPOINT 3: Chỉ trả về text dịch (không overlay)
# Dùng khi Flutter tự vẽ UI
# ══════════════════════════════════════════════════════
@app.post("/translate-text-only")
async def translate_text_only(
    file: UploadFile = File(...),
    source_lang: str = "en",
    target_lang: str = "vi"
):
    contents = await file.read()
    np_arr   = np.frombuffer(contents, np.uint8)
    image    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="Không đọc được ảnh!")

    print(f"\n📥 Nhận ảnh: {image.shape[1]}x{image.shape[0]}")
    print(f"   source_lang={source_lang} → target_lang={target_lang}")

    # ── Cấu hình OCR theo ngôn ngữ nguồn ───────────
    ocr_langs = _resolve_ocr_langs(source_lang)
    ocr.set_languages(ocr_langs)
    print(f"   🔤 OCR languages: {ocr_langs}")

    # ── OCR toàn ảnh ──────────────────────────────
    print("📖 Đang OCR toàn ảnh...")
    ocr_results = ocr.recognize_full_image(image)
    print(f"✅ Nhận dạng được {len(ocr_results)} vùng")

    if len(ocr_results) == 0:
        return JSONResponse({
            "status":        "no_text",
            "message":       "Không tìm thấy chữ trong ảnh!"
        })

    # ── Dịch thuật ────────────────────────────────
    translator.source_lang = source_lang
    translator.target_lang = target_lang
    translated_results = translator.translate_all(ocr_results)

    return JSONResponse({
        "status": "success",
        "translations": [
            {
                "original":   r["text"],
                "translated": r["translated"],
                "confidence": round(r["confidence"], 2),
                "rect": {
                    "x": r["rect"][0],
                    "y": r["rect"][1],
                    "w": r["rect"][2],
                    "h": r["rect"][3]
                }
            }
            for r in translated_results
        ]
    })
