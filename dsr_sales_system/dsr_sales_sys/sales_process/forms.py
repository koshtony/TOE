from django import forms
from .models import Product, Stock, StockHistory,Customer,Sale
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
import uuid

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "item_code",
            "model_name",
            "model_sku",
            "model_category",
            "model_storage",
            "model_ram",
            "network",
            "other_specifications",
            "price",
            "status",
        ]
        widgets = {
           "other_specifications": forms.Textarea(
    attrs={
        "rows": 4,
        "class": "form-control",
        "placeholder": "Enter product details...",
        "style": "height:150px;resize: vertical;"  # 👈 only vertical resize
    })
    
        }
        
        
# forms.py
class BulkStockForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    imei_numbers = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 16,
             'style': 'height:150px;resize: vertical;',
            'placeholder': 'Enter one IMEI per line'
        })
    )

class SaleForm(forms.Form):
    imei_number = forms.CharField(
        label="IMEI Numbers",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 16,
             'style': 'height:150px;resize: vertical;',
            "placeholder": "Enter one IMEI per line"}),
    )
    customer_name = forms.CharField(label="Customer Name", max_length=255)
    phone = forms.CharField(label="Phone", max_length=50, required=False)
    email = forms.EmailField(label="Email", required=False)
    address = forms.CharField(label="Address", widget=forms.Textarea, required=False)
    id_number = forms.CharField(label="ID Number", max_length=50, required=False)

    def process_sale(self, sold_by):
        """
        Process the sale:
        - Accept multiple IMEIs
        - Create/reuse customer
        - Create a single Sale with multiple SaleItems
        - Update stocks + history
        """
        imeis = [
            imei.strip()
            for imei in self.cleaned_data["imei_number"].splitlines()
            if imei.strip()
        ]
        if not imeis:
            raise ValidationError("❌ No IMEIs provided.")
        with transaction.atomic():
            # 1. Get/Create Customer
            customer, created = Customer.objects.get_or_create(
                id_number=self.cleaned_data.get("id_number") or None,
                defaults={
                    "name": self.cleaned_data["customer_name"],
                    "phone": self.cleaned_data.get("phone"),
                    "email": self.cleaned_data.get("email"),
                    "address": self.cleaned_data.get("address", ""),
                },
            )

            # 2. Create the Sale
            
            order_id = f"ORD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
            
            #sale = Sale.objects.create(customer=customer, sold_by=sold_by)
            # 3. Process each IMEI
            errors = []
            for imei in imeis:
                try:
                    stock = Stock.objects.get(imei_number=imei, status="in_stock")
                    
                    if not stock.assigned_to:
                        
                        errors.append(f"❌ IMEI {imei} not assigned to any user.")
                        continue
                    
                    if stock.assigned_to != sold_by:
                        errors.append(f"❌ IMEI {imei} not assigned to {sold_by}.")
                        continue

                    # Create SaleItem
                    sale = Sale.objects.create(customer=customer, sold_by=sold_by,stock=stock,order_id=order_id)
                    
                    print(sale)
                    # Update stock
                    stock.status = "sold"
                    stock.assigned_to = None
                    stock.last_assigned_date = None
                    stock.save()

                    # History log
                    StockHistory.objects.create(
                        stock=stock,
                        action="sold",
                        performed_by=sold_by,
                        details=f"✅ Sold in Sale #{sale.id} to {customer.name}",
                    )
                except Stock.DoesNotExist:
                    errors.append(f"❌ IMEI {imei} not found or not in stock.")
            print(errors)
            if errors:
                # If some failed, still return sale but raise warning
                return None, errors
            
            receipt_url = reverse("sale-receipt", args=[sale.order_id])

            return sale,receipt_url
        

class SaleSearchForm(forms.Form):
    
    imei = forms.CharField(label="IMEI", max_length=100, required=False)
    product_name = forms.CharField(label="Product Name", max_length=100, required=False)
    start_date = forms.DateField(
        label="Start Date", 
        required=False, 
        widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        label="End Date", 
        required=False, 
        widget=forms.DateInput(attrs={"type": "date"})
    )
        

