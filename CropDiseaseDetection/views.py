from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from payment.quota import check_and_increment_quota

from .models import ScanResult
from .ml_model import is_plant, predict_disease
from .disease_info import get_disease_info

SUPPORTED_CROPS = [
    "Apple",
    "Blueberry",
    "Cherry (including sour)",
    "Corn (maize)",
    "Grape",
    "Orange",
    "Peach",
    "Bell Pepper",
    "Potato",
    "Raspberry",
    "Soybean",
    "Squash",
    "Strawberry",
    "Tomato",
]

CONFIDENCE_THRESHOLD = 60.0

SEVERITY_MAP = {
    "severe": "high",
    "high": "high",
    "moderate": "medium",
    "medium": "medium",
    "mild": "low",
    "low": "low",
    "none": "low",
}

class DiseaseDetectionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        blocked = check_and_increment_quota(request.user, "disease_detection")
        if blocked:
            return blocked
        
        image = request.FILES.get("image")

        if not image:
            return Response(
                {"error": "No image provided. Please upload a leaf image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        image.seek(0)

        try:
            prediction = predict_disease(image)
        except Exception as exc:
            return Response(
                {"error": f"Disease detection failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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

        info = get_disease_info(prediction["raw_label"])

        treatment_list = info.get("treatment", [])
        prevention_list = info.get("prevention", [])

        result = {
            "cropType": prediction["crop_type"],
            "disease": prediction["disease"],
            "confidence": prediction["confidence"],
            "isHealthy": prediction["is_healthy"],
            "severity": info["severity"],
            "description": info["description"],
            "treatment": treatment_list,  
            "prevention": prevention_list,  
        }

        normalized_severity = SEVERITY_MAP.get(
            info.get("severity", "low").lower(), "low"
        )

        image.seek(0)
        ScanResult.objects.create(
            user=request.user, 
            image=image,
            crop_type=prediction["crop_type"],
            disease=prediction["disease"],
            confidence=prediction["confidence"],
            is_healthy=prediction["is_healthy"],
            severity=normalized_severity,
            description=info.get("description", ""),
            treatment="\n".join(treatment_list),  
            prevention="\n".join(prevention_list),  
        )

        return Response(result, status=status.HTTP_200_OK)

class RecentScansAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scans = ScanResult.objects.filter(user=request.user).order_by("-created_at")[:10]
        data = [
            {
                "id": s.id,
                "crop": s.crop_type,
                "disease": s.disease,
                "confidence": s.confidence,
                "severity": s.severity,
                "date": s.created_at.strftime("%d %b %Y"),
                "status": "healthy" if s.disease.lower() == "healthy" else "warning",
                "isHealthy": s.is_healthy,
                "description": s.description,
                "treatment": s.treatment,
                "prevention": s.prevention,
                "image": request.build_absolute_uri(s.image.url) if s.image else None,
            }
            for s in scans
        ]
        return Response(data)


class ScanDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            s = ScanResult.objects.get(pk=pk, user=request.user)
        except ScanResult.DoesNotExist:
            return Response(
                {"error": "Scan not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "id": s.id,
                "crop": s.crop_type,
                "disease": s.disease,
                "confidence": s.confidence,
                "severity": s.severity,
                "date": s.created_at.strftime("%d %b %Y"),
                "status": "healthy" if s.disease.lower() == "healthy" else "warning",
                "isHealthy": s.is_healthy,
                "description": s.description,
                "treatment": s.treatment,
                "prevention": s.prevention,
                "image": request.build_absolute_uri(s.image.url) if s.image else None,
            }
        )