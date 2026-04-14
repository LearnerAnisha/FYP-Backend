from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import ScanResult
from .ml_model import is_plant, predict_disease
from .disease_info import get_disease_info

# Supported crops extracted from class_names.json
SUPPORTED_CROPS = [
    "Apple", "Blueberry", "Cherry (including sour)", "Corn (maize)",
    "Grape", "Orange", "Peach", "Bell Pepper",
    "Potato", "Raspberry", "Soybean", "Squash",
    "Strawberry", "Tomato",
]

# If the model's top confidence is below this, treat as unsupported crop
CONFIDENCE_THRESHOLD = 60.0

class DiseaseDetectionAPIView(APIView):
    """
    POST /api/disease/detect/

    Pipeline:
      1. Validate image present
      2. Plant gate        → 422 "not_a_plant"
      3. Confidence gate   → 422 "unsupported_crop"
      4. Enrich with static knowledge
      5. Persist + return JSON
    """

    permission_classes = [AllowAny]

    def post(self, request):
        image = request.FILES.get("image")

        if not image:
            return Response(
                {"error": "No image provided. Please upload a leaf image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 1: Plant vs Non-plant
        try:
            plant_detected, plant_confidence = is_plant(image)
        except Exception as exc:
            return Response(
                {"error": f"Plant detection failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not plant_detected:
            return Response(
                {
                    "error": "not_a_plant",
                    "message": (
                        "The uploaded image does not appear to be a plant leaf. "
                        "Please upload a clear photo of a crop leaf."
                    ),
                    "plant_confidence": plant_confidence,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Step 2: Disease detection 
        image.seek(0)

        try:
            prediction = predict_disease(image)
        except Exception as exc:
            return Response(
                {"error": f"Disease detection failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Step 3: Confidence / supported-crop gate 
        if prediction["confidence"] < CONFIDENCE_THRESHOLD:
            return Response(
                {
                    "error": "unsupported_crop",
                    "message": (
                        "This leaf doesn't match any crop in our database. "
                        "Please upload a leaf from one of the supported crops."
                    ),
                    "confidence": prediction["confidence"],
                    "supported_crops": SUPPORTED_CROPS,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Step 4: Enrich
        info = get_disease_info(prediction["raw_label"])

        result = {
            "cropType": prediction["crop_type"],
            "disease": prediction["disease"],
            "confidence": prediction["confidence"],
            "isHealthy": prediction["is_healthy"],
            "severity": info["severity"],
            "description": info["description"],
            "treatment": info["treatment"],
            "prevention": info["prevention"],
        }
        
        SEVERITY_MAP = {
            "severe": "high",
            "high": "high",
            "moderate": "medium",
            "medium": "medium",
            "mild": "low",
            "low": "low",
            "none": "low",
        }

        raw_severity = info.get("severity", "low")
        normalized_severity = SEVERITY_MAP.get(raw_severity.lower(), "low")

        # Step 5: Persist
        image.seek(0)
        ScanResult.objects.create(
            image=image,
            crop_type=prediction["crop_type"],
            disease=prediction["disease"],
            confidence=prediction["confidence"],
            is_healthy=prediction["is_healthy"],
            severity=normalized_severity, 
            description=info.get("description", ""),
            treatment=info.get("treatment", ""),
            prevention=info.get("prevention", ""),
        )

        return Response(result, status=status.HTTP_200_OK)


class RecentScansAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scans = ScanResult.objects.order_by("-created_at")[:5]
        data = [
            {
                "id": s.id,
                "crop": s.crop_type,
                "disease": s.disease,
                "confidence": s.confidence,
                "severity": s.severity,
                "date": s.created_at.strftime("%d %b %Y"),
                "status": "healthy" if s.disease.lower() == "healthy" else "warning",
            }
            for s in scans
        ]
        return Response(data)