from django.db import models
from django.conf import settings

class ScanResult(models.Model):
    user = models.ForeignKey(          
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="scan_results",
    )
    image = models.ImageField(upload_to="scans/")
    crop_type = models.CharField(max_length=100)
    disease = models.CharField(max_length=100)
    confidence = models.FloatField()
    is_healthy = models.BooleanField(default=False)
    severity = models.CharField(max_length=50)
    description = models.TextField(blank=True, default="")
    treatment = models.TextField(blank=True, default="")
    prevention = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop_type} — {self.disease} ({self.severity})"