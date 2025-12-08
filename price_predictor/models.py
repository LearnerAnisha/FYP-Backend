from django.db import models
class MasterProduct(models.Model):
    """
    Stores each commodity exactly once.
    This table always holds the latest known price snapshot.
    If today's data is missing, min/max/avg become NULL 
    but last_price keeps the previous known value.
    """
    commodityname = models.CharField(max_length=200, unique=True)
    commodityunit = models.CharField(max_length=50, null=True, blank=True)

    insert_date = models.DateField(auto_now_add=True)
    last_update = models.DateField(auto_now=True)

    # Latest values (set to NULL if no data for today)
    min_price = models.FloatField(null=True, blank=True)
    max_price = models.FloatField(null=True, blank=True)
    avg_price = models.FloatField(null=True, blank=True)

    # Always stores last known price (never set to NULL)
    last_price = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["commodityname"]

    def __str__(self):
        return self.commodityname
class DailyPriceHistory(models.Model):
    """
    Stores daily snapshot records for price trend analysis.
    A row exists only if the commodity appeared in that day's API.
    """
    product = models.ForeignKey(MasterProduct, on_delete=models.CASCADE)
    date = models.DateField()

    min_price = models.FloatField()
    max_price = models.FloatField()
    avg_price = models.FloatField()
    class Meta:
        unique_together = ("product", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.product.commodityname} - {self.date}"
