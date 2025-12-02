from django.db import models

class MarketPrice(models.Model):
    """
    Stores daily price data of fruits and vegetables fetched from the Kalimati Market API.
    Historical data will be used later for machine learning predictions.
    """
    commodity_name = models.CharField(max_length=150)
    commodity_unit = models.CharField(max_length=50, null=True, blank=True)
    min_price = models.FloatField()
    max_price = models.FloatField()
    avg_price = models.FloatField()
    date = models.DateField()  # API sends the date for each price list

    class Meta:
        unique_together = ("commodity_name", "date")  # Avoid duplicate entries for same day/item
        ordering = ["-date", "commodity_name"]  # Sort by latest date first

    def __str__(self):
        return f"{self.commodity_name} ({self.date})"
