# disease/models.py
from django.db import models

class ScanResult(models.Model):
    image = models.ImageField(upload_to="scans/")
    crop_type = models.CharField(max_length=100)
    disease = models.CharField(max_length=100)
    confidence = models.FloatField()
    severity = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
