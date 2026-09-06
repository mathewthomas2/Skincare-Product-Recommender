import logging
import traceback
import os
import json

import aiofiles
import cv2
import numpy as np
import tensorflow as tf
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.preprocess_image import preprocess_image

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

app = FastAPI()

_allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
allowed_origins = (
    [origin.strip() for origin in _allowed_origins_env.split(",")]
    if _allowed_origins_env
    else ["*"]  # open for local dev only — restrict this before deploying
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Skin-mask helper — single source of truth, used by both validation and
# percentage calculation to avoid copy-pasting the same colour ranges.
# ---------------------------------------------------------------------------

_LOWER_YCRCB = np.array([0, 130, 80], dtype=np.uint8)
_UPPER_YCRCB = np.array([255, 185, 140], dtype=np.uint8)
_LOWER_HSV   = np.array([0, 20, 70], dtype=np.uint8)
_UPPER_HSV   = np.array([50, 255, 255], dtype=np.uint8)
_MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))


def _compute_skin_mask(img: np.ndarray) -> np.ndarray:
    """Return a binary skin mask for a BGR image."""
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    hsv   = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    mask_ycrcb = cv2.inRange(ycrcb, _LOWER_YCRCB, _UPPER_YCRCB)
    mask_hsv   = cv2.inRange(hsv,   _LOWER_HSV,   _UPPER_HSV)
    mask = cv2.bitwise_or(mask_ycrcb, mask_hsv)

    mask = cv2.erode(mask,  _MORPH_KERNEL, iterations=1)
    mask = cv2.dilate(mask, _MORPH_KERNEL, iterations=1)
    return mask


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

async def validate_image(image_path: str) -> None:
    """Raise ValueError if the image contains insufficient skin area."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not load image. Please check the image file.")

    mask = _compute_skin_mask(img)
    skin_pct = (cv2.countNonZero(mask) / (img.shape[0] * img.shape[1])) * 100

    if skin_pct <= 5:
        raise ValueError("Please upload a photo showing enough skin area with good lighting.")


def calculate_skin_percentage(image_path: str) -> float:
    """Return the percentage of skin pixels in the image."""
    img  = cv2.imread(image_path)
    mask = _compute_skin_mask(img)
    return (cv2.countNonZero(mask) / (img.shape[0] * img.shape[1])) * 100


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class SkinTypeResponse(BaseModel):
    skin_type: str
    short_info: str
    skin_percentage: float


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

base_dir  = os.path.dirname(os.path.abspath(__file__))
model_dir = os.path.join(base_dir, "models")
pm_path   = os.path.join(model_dir, "pigmented_nonpigmented_model.h5")
om_path   = os.path.join(model_dir, "oily_dry_model.h5")
sm_path   = os.path.join(model_dir, "sensitive_resistant_model.h5")

os.makedirs(model_dir, exist_ok=True)


def _is_git_lfs_pointer(path: str) -> bool:
    """Git LFS pointer files are tiny text files, not real binary models."""
    try:
        if os.path.getsize(path) > 1024:
            return False
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(200).startswith("version https://git-lfs.github.com/spec/v1")
    except Exception:
        return False


try:
    models_to_load = [
        ("pigmentation", pm_path),
        ("oily",         om_path),
        ("sensitive",    sm_path),
    ]

    loaded_models: dict = {}
    for model_name, model_path in models_to_load:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if os.path.getsize(model_path) == 0:
            raise ValueError(f"Model file is empty: {model_path}")
        if _is_git_lfs_pointer(model_path):
            raise ValueError(
                f"'{model_path}' is a Git LFS pointer file, not the real model. "
                "Run `git lfs install && git lfs pull` (or download the models manually "
                "per the README) before starting the server."
            )
        logger.info("Loading model '%s' from %s", model_name, model_path)
        loaded_models[model_name] = tf.keras.models.load_model(model_path)

    pigmentation_model = loaded_models["pigmentation"]
    oily_model         = loaded_models["oily"]
    sensitive_model    = loaded_models["sensitive"]

except Exception as e:
    logger.critical("Could not load ML models: %s", e)
    raise SystemExit(1)


# Load model configuration & calibrated thresholds
def load_model_config() -> dict:
    cfg_path = os.path.join(model_dir, "model_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not read model_config.json: %s. Using default thresholds.", e)
    return {
        "oily_threshold": 0.3,
        "sensitive_threshold": 0.3,
        "pigmented_threshold": 0.2
    }


model_config = load_model_config()


# ---------------------------------------------------------------------------
# Text info
# ---------------------------------------------------------------------------

def get_text_info() -> dict:
    text_info_path = os.path.join(base_dir, "text_info.json")
    try:
        with open(text_info_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Text info file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading text info: {str(e)}")


text_info = get_text_info()


# ---------------------------------------------------------------------------
# Prediction endpoint
# ---------------------------------------------------------------------------

@app.post("/analyze-skin")
async def analyze_skin(file: UploadFile):
    """Analyzes any skin part image and predicts the skin type."""
    temp_image_path = None
    try:
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            raise HTTPException(status_code=400, detail="Only JPG or PNG files are allowed")

        temp_image_path = f"temp_image_{os.urandom(8).hex()}.jpg"

        try:
            async with aiofiles.open(temp_image_path, "wb") as out_file:
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

            # Run all three models
            oily_score        = float(oily_model.predict(image, verbose=0)[0][0])
            pigmented_score   = float(pigmentation_model.predict(image, verbose=0)[0][0])
            sensitive_score   = float(sensitive_model.predict(image, verbose=0)[0][0])

            # Classify using calibrated thresholds
            oily_thresh      = float(model_config.get("oily_threshold", 0.3))
            sensitive_thresh = float(model_config.get("sensitive_threshold", 0.3))
            pigmented_thresh = float(model_config.get("pigmented_threshold", 0.2))

            skin_type  = "O" if oily_score      > oily_thresh else "D"
            skin_type += "S" if sensitive_score  > sensitive_thresh else "R"
            skin_type += "P" if pigmented_score  > pigmented_thresh else "N"
            skin_type += "T"   # Wrinkle dimension not yet modelled — always Tight

            logger.info(
                "Skin analysis — oily=%.4f (th=%.2f) sensitive=%.4f (th=%.2f) pigmented=%.4f (th=%.2f) → %s",
                oily_score, oily_thresh, sensitive_score, sensitive_thresh, pigmented_score, pigmented_thresh, skin_type,
            )

            if skin_type not in text_info:
                raise ValueError(f"Invalid skin type classification: {skin_type}")

            return SkinTypeResponse(
                skin_type=skin_type,
                short_info=text_info[skin_type],
                skin_percentage=round(skin_percentage, 2),
            )

        except Exception as e:
            logger.error("Prediction error:\n%s", traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Error during prediction: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except Exception:
                pass