# test_api.py
import requests
import base64
import cv2
import numpy as np

API_URL = "http://127.0.0.1:8000"

def test_health():
    print("── Test Health Check ──────────────────")
    res = requests.get(f"{API_URL}/")
    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()}")

def test_translate_image(image_path="test_image.jpg"):
    print("\n── Test /translate-image ──────────────")
    with open(image_path, "rb") as f:
        files  = {"file": ("test_image.jpg", f, "image/jpeg")}
        params = {"source_lang": "en", "target_lang": "vi", "ocr_langs": "en,ch_sim"}
        res    = requests.post(
            f"{API_URL}/translate-image",
            files=files,
            params=params
        )

    data = res.json()
    print(f"Status       : {data['status']}")
    print(f"Regions found: {data['regions_found']}")
    print(f"Translated   : {data['regions_translated']}")

    print("\n📋 Danh sách dịch:")
    for i, t in enumerate(data["translations"]):
        print(f"  [{i+1}] '{t['original']}' → '{t['translated']}'")

    # Decode ảnh base64 → lưu file
    img_bytes = base64.b64decode(data["image_base64"])
    np_arr    = np.frombuffer(img_bytes, np.uint8)
    result    = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    cv2.imwrite("result-test_image.jpg", result)
    print("\n💾 Đã lưu ảnh kết quả: result-test_image.jpg")

    cv2.imshow("API Result", result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_health()
    test_translate_image()