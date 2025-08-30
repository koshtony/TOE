from django.contrib import admin
from .models import Product, Stock, StockHistory


class StockHistoryInline(admin.TabularInline):
    model = StockHistory
    extra = 0
    readonly_fields = ("action", "performed_by", "details", "performed_on")
    can_delete = False
    verbose_name = "Stock Movement"
    verbose_name_plural = "Stock History"

    def has_add_permission(self, request, obj=None):
        return False  # Prevent adding manually from admin


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("item_code", "model_name", "model_sku", "model_category", "created_on", "status")
    search_fields = ("item_code", "model_name", "model_sku", "model_category")
    list_filter = ("status", "created_on")


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "serial_number",
        "imei_number",
        "product",
        "stock_in_date",
        "days_in_stock",
        "assigned_to",
        "last_assigned_date",
        "status",
    )
    search_fields = ("serial_number", "imei_number", "product__model_name")
    list_filter = ("status", "stock_in_date", "assigned_to")
    inlines = [StockHistoryInline]

    def days_in_stock(self, obj):
        return obj.days_in_stock
    days_in_stock.short_description = "Days in Stock"


@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    list_display = ("stock", "action", "performed_by", "performed_on", "details")
    search_fields = ("stock__serial_number", "stock__imei_number", "details")
    list_filter = ("action", "performed_on")
    readonly_fields = ("stock", "action", "performed_by", "details", "performed_on")
