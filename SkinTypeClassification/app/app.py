from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware  
import cv2
import numpy as np
from pydantic import BaseModel
import aiofiles
import os
import tensorflow as tf
import json
from app.preprocess_image import preprocess_image

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def validate_image(image_path):
    """Validate if the image contains enough skin area for processing"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Could not load image. Please check the image file.")
        
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        lower_skin_ycrcb = np.array([0, 130, 80], dtype=np.uint8)
        upper_skin_ycrcb = np.array([255, 185, 140], dtype=np.uint8)
        
        lower_skin_hsv = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin_hsv = np.array([50, 255, 255], dtype=np.uint8)
        
        skin_mask_ycrcb = cv2.inRange(ycrcb, lower_skin_ycrcb, upper_skin_ycrcb)
        skin_mask_hsv = cv2.inRange(hsv, lower_skin_hsv, upper_skin_hsv)
        skin_mask = cv2.bitwise_or(skin_mask_ycrcb, skin_mask_hsv)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        skin_mask = cv2.erode(skin_mask, kernel, iterations=1)
        skin_mask = cv2.dilate(skin_mask, kernel, iterations=1)
        
        skin_percentage = (cv2.countNonZero(skin_mask) / (img.shape[0] * img.shape[1])) * 100
        
        if skin_percentage > 5:
            return True
            
        raise ValueError("Please upload a photo showing enough skin area with good lighting.")
        
    except Exception as e:
        raise ValueError(f"Could not process image: {str(e)}. Please ensure good lighting and clear focus.")

class SkinTypeResponse(BaseModel):
    skin_type: str
    short_info: str

    skin_percentage: float  

base_dir = os.path.dirname(os.path.abspath(__file__))
model_dir = os.path.join(base_dir, 'models')
pm_path = os.path.join(model_dir, 'pigmented_nonpigmented_model.h5')
om_path = os.path.join(model_dir, 'oily_dry_model.h5')
sm_path = os.path.join(model_dir, 'sensitive_resistant_model.h5')  # Use the actual filename

os.makedirs(model_dir, exist_ok=True)

try:
    models_to_load = [
        ("pigmentation", pm_path),
        ("oily", om_path),
        ("sensitive", sm_path)
    ]

    loaded_models = {}
    for model_name, model_path in models_to_load:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if os.path.getsize(model_path) == 0:
            raise ValueError(f"Model file is empty: {model_path}")
        loaded_models[model_name] = tf.keras.models.load_model(model_path)

    pigmentation_model = loaded_models["pigmentation"]
    oily_model = loaded_models["oily"]
    sensitive_model = loaded_models["sensitive"]

except Exception as e:
    raise SystemExit(1)

def get_text_info():
    text_info_path = os.path.join(base_dir, 'text_info.json')
    try:
        with open(text_info_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Text info file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading text info: {str(e)}")

text_info = get_text_info()

def calculate_skin_percentage(image_path):
    """Calculate the percentage of skin in the image"""
    img = cv2.imread(image_path)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    lower_skin_ycrcb = np.array([0, 130, 80], dtype=np.uint8)
    upper_skin_ycrcb = np.array([255, 185, 140], dtype=np.uint8)
    
    lower_skin_hsv = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin_hsv = np.array([50, 255, 255], dtype=np.uint8)
    
    skin_mask_ycrcb = cv2.inRange(ycrcb, lower_skin_ycrcb, upper_skin_ycrcb)
    skin_mask_hsv = cv2.inRange(hsv, lower_skin_hsv, upper_skin_hsv)
    skin_mask = cv2.bitwise_or(skin_mask_ycrcb, skin_mask_hsv)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    skin_mask = cv2.erode(skin_mask, kernel, iterations=1)
    skin_mask = cv2.dilate(skin_mask, kernel, iterations=1)
    
    return (cv2.countNonZero(skin_mask) / (img.shape[0] * img.shape[1])) * 100

def skin_color_analysis(image_path):
    """Analyze skin color to detect sensitivity traits"""
    img = cv2.imread(image_path)
    img = cv2.resize(img, (224, 224))
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    
    lower_skin_ycrcb = np.array([0, 130, 80], dtype=np.uint8)
    upper_skin_ycrcb = np.array([255, 185, 140], dtype=np.uint8)
    
    lower_skin_hsv = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin_hsv = np.array([50, 255, 255], dtype=np.uint8)
    
    skin_mask_ycrcb = cv2.inRange(ycrcb, lower_skin_ycrcb, upper_skin_ycrcb)
    skin_mask_hsv = cv2.inRange(hsv, lower_skin_hsv, upper_skin_hsv)
    skin_mask = cv2.bitwise_or(skin_mask_ycrcb, skin_mask_hsv)
    
    hsv_masked = cv2.bitwise_and(hsv, hsv, mask=skin_mask)
    
    if cv2.countNonZero(skin_mask) > 0:
        avg_h = np.sum(hsv_masked[:,:,0]) / cv2.countNonZero(skin_mask)
        avg_s = np.sum(hsv_masked[:,:,1]) / cv2.countNonZero(skin_mask)
        avg_v = np.sum(hsv_masked[:,:,2]) / cv2.countNonZero(skin_mask)
    else:
        avg_h, avg_s, avg_v = 0, 0, 0
    
    bgr = cv2.imread(image_path)
    bgr = cv2.resize(bgr, (224, 224))
    b, g, r = cv2.split(bgr)
    r_masked = cv2.bitwise_and(r, r, mask=skin_mask)
    
    if cv2.countNonZero(skin_mask) > 0:
        avg_r = np.sum(r_masked) / cv2.countNonZero(skin_mask)
    else:
        avg_r = 0
  
    is_sensitive = (avg_r > 150 and avg_s < 100) or (avg_h < 10)
    
    print(f"Skin color analysis: H={avg_h:.1f}, S={avg_s:.1f}, V={avg_v:.1f}, R={avg_r:.1f}")
    print(f"Sensitive based on color: {is_sensitive}")
    
    return is_sensitive

@app.post("/analyze-skin")
async def analyze_skin(file: UploadFile):
    """Analyzes any skin part image and predicts the skin type."""
    temp_image_path = None
    try:
        if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise HTTPException(status_code=400, detail="Only JPG or PNG files are allowed")

        temp_image_path = f'temp_image_{os.urandom(8).hex()}.jpg'

        try:
            async with aiofiles.open(temp_image_path, 'wb') as out_file:
                content = await file.read()
                if not content:
                    raise ValueError("Empty file uploaded")
                await out_file.write(content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error saving file: {str(e)}")

        await validate_image(temp_image_path)
        
        skin_percentage = calculate_skin_percentage(temp_image_path)

        try:
            image = preprocess_image(temp_image_path)
            
            is_oily = oily_model.predict(image, verbose=0)
            is_pigmented = pigmentation_model.predict(image, verbose=0)

            oily_score = float(is_oily[0][0])

            if oily_score > 0.3:
                skin_type = 'O'  
            else:
                skin_type = 'D'  
            
            is_sensitive_skin = skin_color_analysis(temp_image_path)
            
            is_pigmented_skin = float(is_pigmented[0][0]) > 0.2

            print("\n=== Skin Analysis Scores ===")
            print(f"Sensitive Result: {is_sensitive_skin}")
            print(f"Oily Score: {oily_score:.4f}")
            print(f"Pigmented Score: {float(is_pigmented[0][0]):.4f}")
            print(f"Is Pigmented: {is_pigmented_skin}")
            print("==========================\n")

            skin_type += 'S' if is_sensitive_skin else 'R'
            skin_type += 'P' if is_pigmented_skin else 'N'
            skin_type += 'T'

            print(f"Final skin type: {skin_type}")

            if skin_type not in text_info:
                raise ValueError(f"Invalid skin type classification: {skin_type}")

            return SkinTypeResponse(
                skin_type=skin_type,
                short_info=text_info[skin_type],
                skin_percentage=round(skin_percentage, 2)
            )

        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            print(f"Error traceback: {traceback_str}")
            raise HTTPException(status_code=500, detail=f"Error during prediction: {str(e)}")

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Unexpected error traceback: {traceback_str}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except Exception:
                pass

@app.post("/macro")
async def predict_macro(file: UploadFile):
    """Legacy endpoint that redirects to the new analyze-skin endpoint."""
    return await analyze_skin(file)