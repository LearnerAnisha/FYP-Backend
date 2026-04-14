from django.db import models

class ScanResult(models.Model):
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