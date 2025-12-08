from django.contrib import admin
from .models import MasterProduct, DailyPriceHistory
@admin.register(MasterProduct)
class MasterProductAdmin(admin.ModelAdmin):
    list_display = (
        "commodityname", "commodityunit",
        "avg_price", "min_price", "max_price", "last_price",
        "insert_date", "last_update",
    )
    search_fields = ("commodityname",)
    ordering = ("commodityname",)
@admin.register(DailyPriceHistory)
class DailyPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("product", "date", "avg_price", "min_price", "max_price")
    list_filter = ("date", "product")
    search_fields = ("product__commodityname",)
    ordering = ("-date",)
