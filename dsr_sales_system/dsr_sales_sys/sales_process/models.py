from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date


class Product(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('discontinued', 'Discontinued'),
    ]
    
    STORAGE_CHOICES = [
        ('16gb', '16GB'),
        ('32gb', '32GB'),
        ('64gb', '64GB'),
        ('128gb', '128GB'),
        ('256gb', '256GB'),
        ('512gb', '512GB'),
        ('1tb', '1TB'),
    ]
    
    RAM_CHOICES = [
        ('4gb', '4GB'),
        ('8gb', '8GB'),
        ('16gb', '16GB'),
        ('32gb', '32GB'),
        ('64gb', '64GB'),
        ('128gb', '128GB'),
        ('256gb', '256GB'),
        ('512gb', '512GB'),
        ('1tb', '1TB'),
    ]
    
    NETWORK_CHOICES = [
        ('2g', '2G'),
        ('3g', '3G'),
        ('4g', '4G'),
        ('5g', '5G'),
    ]
    
    MODEL_CATEGORY_CHOICES = [
        ('phone', 'Phone'),
        ('tablet', 'Tablet'),
        ('laptop', 'Laptop'),
        ('watch', 'Watch'),
    ]

    item_code = models.CharField(max_length=50, unique=True)
    model_name = models.CharField(max_length=100)
    model_sku = models.CharField(max_length=100, unique=True)
    model_category = models.CharField(max_length=100, choices=MODEL_CATEGORY_CHOICES, default='phone')
    model_storage = models.CharField(max_length=50, blank=True, null=True, choices=STORAGE_CHOICES)
    model_ram = models.CharField(max_length=50, blank=True, null=True, choices=RAM_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    network = models.CharField(max_length=100, blank=True, null=True, choices=NETWORK_CHOICES)
    other_specifications = models.TextField(blank=True, null=True)

    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="products_created"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    def __str__(self):
        return f"{self.model_name} {self.network} ({self.model_ram}+{self.model_storage})"


class Stock(models.Model):
    STATUS_CHOICES = [
        ('in_stock', 'In Stock'),
        ('assigned', 'Assigned'),
        ('sold', 'Sold'),
        ('returned', 'Returned'),
    ]

    serial_number = models.CharField(max_length=100, unique=True)
    imei_number = models.CharField(max_length=100, unique=True, blank=True, null=True)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stocks"
    )

    stock_in_date = models.DateField(default=timezone.now)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="stocks_added"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_stock'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stocks_assigned"
    )
    last_assigned_date = models.DateField(null=True, blank=True)

    # 🔑 This is stored for reference but also recomputed when needed
    date_since_stock_in = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Stock: {self.serial_number} ({self.product.model_name})"

    @property
    def days_in_stock(self):
        """Current days in stock = today - stock_in_date"""
        return (date.today() - self.stock_in_date).days


class StockHistory(models.Model):
    ACTION_CHOICES = [
        ('added', 'Added to stock'),
        ('assigned', 'Assigned to user'),
        ('returned', 'Returned to stock'),
        ('sold', 'Sold'),
        ('status_change', 'Status Change'),
    ]

    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="history"
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="stock_history_actions"
    )
    transferred_from = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="transferred_from_allocations",
        null=True, blank=True, on_delete=models.SET_NULL
    )
    transferred_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="transferred_to_allocations",
        null=True, blank=True, on_delete=models.SET_NULL
    )
    performed_on = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.stock.serial_number} - {self.action} on {self.performed_on.strftime('%Y-%m-%d')}"
