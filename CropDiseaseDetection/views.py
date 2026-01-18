# disease/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ScanResult
from rest_framework.permissions import AllowAny

class DiseaseDetectionAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        
        image = request.FILES.get("image")

        if not image:
            return Response(
                {"error": "Image is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # -----------------------------
        # TODO: Load ML model here
        # prediction = model.predict(image)
        # -----------------------------

        # Temporary dummy response (matches your UI)
        result = {
            "cropType": "Rice",
            "disease": "Leaf Blast",
            "confidence": 92,
            "severity": "Moderate",
            "description": "Rice blast is caused by the fungus Magnaporthe oryzae...",
            "treatment": [
                "Remove and destroy infected plant parts",
                "Apply Tricyclazole fungicide (0.06%)",
                "Ensure proper drainage"
            ],
            "prevention": [
                "Plant resistant varieties",
                "Maintain spacing",
                "Balanced fertilization"
            ]
        }

        # Save history
        ScanResult.objects.create(
            image=image,
            crop_type=result["cropType"],
            disease=result["disease"],
            confidence=result["confidence"],
            severity=result["severity"]
        )

        return Response(result, status=status.HTTP_200_OK)

class RecentScansAPIView(APIView):
    def get(self, request):
        scans = ScanResult.objects.order_by("-created_at")[:5]
        data = [
            {
                "crop": s.crop_type,
                "disease": s.disease,
                "date": s.created_at.strftime("%d %b %Y"),
                "status": "success" if s.disease == "Healthy" else "warning"
            }
            for s in scans
        ]
        return Response(data)
