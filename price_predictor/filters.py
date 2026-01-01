import django_filters
from .models import MasterProduct

class MasterProductFilter(django_filters.FilterSet):
    min_price_gte = django_filters.NumberFilter(
        field_name="last_price", lookup_expr="gte"
    )
    min_price_lte = django_filters.NumberFilter(
        field_name="last_price", lookup_expr="lte"
    )

    class Meta:
        model = MasterProduct
        fields = []
