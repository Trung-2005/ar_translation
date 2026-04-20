# test_setup.py
import cv2
import easyocr
import fastapi
import numpy as np
from PIL import Image

print(f"✅ OpenCV:   {cv2.__version__}")
print(f"✅ EasyOCR:  {easyocr.__version__}")
print(f"✅ FastAPI:  {fastapi.__version__}")
print(f"✅ NumPy:    {np.__version__}")
print(f"✅ Pillow:   {Image.__version__}")

# Test load model EAST
net = cv2.dnn.readNet("models/frozen_east_text_detection.pb")
print("✅ EAST model: Load thành công!")