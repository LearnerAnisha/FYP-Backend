from django.contrib import admin
from .models import MarketPrice

@admin.register(MarketPrice)
class MarketPriceAdmin(admin.ModelAdmin):
    """
    Custom admin configuration to easily view and search market price history.
    """
    list_display = ("commodity_name", "avg_price", "min_price", "max_price", "commodity_unit", "date")
    list_filter = ("date", "commodity_name")
    search_fields = ("commodity_name",)
    ordering = ("-date",)
