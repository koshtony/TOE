from django import forms
from .models import Product

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
