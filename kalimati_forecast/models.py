from django.db import models


class PriceRecord(models.Model):
    """Stores historical Kalimati market price data."""
    commodity   = models.CharField(max_length=100, db_index=True)
    date        = models.DateField(db_index=True)
    min_price   = models.FloatField()
    max_price   = models.FloatField()
    avg_price   = models.FloatField()
    unit        = models.CharField(max_length=20, default='kg')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('commodity', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.commodity} | {self.date} | avg={self.avg_price}"


class ForecastResult(models.Model):
    """Stores generated forecast predictions."""
    MODEL_CHOICES = [
        ('arima',    'ARIMA'),
        ('sarimax',  'SARIMAX'),
        ('lgbm',     'LightGBM'),
        ('ensemble', 'Ensemble'),
    ]

    commodity    = models.CharField(max_length=100, db_index=True)
    forecast_date = models.DateField()
    predicted_price = models.FloatField()
    lower_bound  = models.FloatField(null=True, blank=True)
    upper_bound  = models.FloatField(null=True, blank=True)
    model_used   = models.CharField(max_length=20, choices=MODEL_CHOICES)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['forecast_date']

    def __str__(self):
        return f"{self.commodity} | {self.forecast_date} | {self.predicted_price}"


class ModelMetric(models.Model):
    """Tracks evaluation metrics per model per commodity."""
    commodity  = models.CharField(max_length=100)
    model_name = models.CharField(max_length=20)
    mae        = models.FloatField()
    rmse       = models.FloatField()
    mape       = models.FloatField()
    trained_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('commodity', 'model_name')

    def __str__(self):
        return f"{self.commodity} | {self.model_name} | MAE={self.mae:.2f}"