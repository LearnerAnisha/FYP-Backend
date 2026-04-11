import os
import json
import numpy as np
from pathlib import Path
import tensorflow as tf

# tf_keras is needed only for the .h5 model
import tf_keras  # noqa: F401  (registers legacy ops)
from tf_keras.models import load_model as legacy_load_model

# Paths  (override via env vars for Docker / production)
_BASE = Path(__file__).resolve().parent

PLANT_DETECTOR_PATH = Path(
    os.getenv("PLANT_DETECTOR_PATH", _BASE / "weights" / "plant_detector.keras")
)
DISEASE_MODEL_PATH = Path(
    os.getenv("DISEASE_MODEL_PATH", _BASE / "weights" / "final_disease_model.h5")
)
CLASS_NAMES_PATH = Path(
    os.getenv("CLASS_NAMES_PATH", _BASE / "weights" / "class_names.json")
)

# Singleton state
_plant_detector = None
_disease_model = None
_class_names = None


def _load_class_names():
    global _class_names
    if _class_names is None:
        with open(CLASS_NAMES_PATH, "r") as f:
            _class_names = json.load(f)
    return _class_names


def get_plant_detector():
    """Return the plant-vs-non-plant binary model (loaded once)."""
    global _plant_detector
    if _plant_detector is None:
        _plant_detector = tf.keras.models.load_model(str(PLANT_DETECTOR_PATH))
    return _plant_detector


def get_disease_model():
    """Return the 38-class disease model (loaded once, via legacy tf_keras)."""
    global _disease_model
    if _disease_model is None:
        _disease_model = legacy_load_model(str(DISEASE_MODEL_PATH))
    return _disease_model


# Image pre-processing
IMG_SIZE = (224, 224)


def preprocess_image(image_file) -> np.ndarray:
    """
    Accept a Django InMemoryUploadedFile / TemporaryUploadedFile and
    return a float32 numpy array shaped (1, 224, 224, 3) with values in [0, 1].
    """
    from PIL import Image as PILImage

    img = PILImage.open(image_file).convert("RGB")
    img = img.resize(IMG_SIZE, PILImage.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)  # (1, 224, 224, 3)


# Prediction helpers

def is_plant(image_file) -> tuple[bool, float]:
    """
    Returns (is_plant: bool, confidence: float 0-100).
    Threshold: sigmoid output > 0.5 → plant.
    """
    model = get_plant_detector()
    arr = preprocess_image(image_file)
    prob = float(model.predict(arr, verbose=0)[0][0])  # sigmoid scalar
    return prob > 0.5, round(prob * 100, 2)


def predict_disease(image_file) -> dict:
    """
    Returns a dict with keys:
        crop_type   str   e.g. "Tomato"
        disease     str   e.g. "Early_blight"  (or "healthy")
        confidence  float 0-100
        is_healthy  bool
        raw_label   str   e.g. "Tomato___Early_blight"
    """
    model = get_disease_model()
    class_names = _load_class_names()

    arr = preprocess_image(image_file)
    probs = model.predict(arr, verbose=0)[0]          # (38,)
    idx = int(np.argmax(probs))
    confidence = round(float(probs[idx]) * 100, 2)

    raw_label = class_names[idx]                      # e.g. "Tomato___Early_blight"
    parts = raw_label.split("___")
    crop_type = parts[0].replace("_", " ")            # "Tomato"
    disease = parts[1].replace("_", " ") if len(parts) > 1 else "Unknown"
    is_healthy = "healthy" in disease.lower()

    return {
        "crop_type": crop_type,
        "disease": disease,
        "confidence": confidence,
        "is_healthy": is_healthy,
        "raw_label": raw_label,
    }