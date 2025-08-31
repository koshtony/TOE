from django.shortcuts import render,get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .forms import ProductForm,BulkStockForm
from .models import Product,Stock,StockHistory
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import csv
from io import StringIO
import uuid
# Create your views here.
@login_required
def home_view(request):
    
    
    
    return render(request, 'sales_process/home.html')

@login_required
def create_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            return HttpResponse("<div class='alert alert-success'>✅ Product created successfully</div>")
        else:
            
            return HttpResponse("<div class='alert alert-danger'>❌❌😔 Product creation failed</div>")
            
    else:
        form = ProductForm()
    return render(request, "sales_process/create_product.html", {"product_form": form})


@login_required 
def list_products(request):
    

    products = Product.objects.all()

   

    return render(request, "sales_process/list_products.html", {"products": products})


@login_required
def filter_products(request):
    query = request.GET.get("q", "").strip()
    products = Product.objects.all()

    if query:
        products = products.filter(
            model_name__icontains=query
        ) | products.filter(
            model_sku__icontains=query
        ) | products.filter(
            item_code__icontains=query
        )

    return render(request, "sales_process/list_products_table.html", {"products": products})

@login_required 
def bulk_add_stock(request):
    if request.method == "POST":
        form = BulkStockForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            imeis = form.cleaned_data['imei_numbers'].splitlines()

            added_imeis = []
            duplicate_imeis = []
        
            for imei in imeis:
                imei = imei.strip()
                if not imei:
                    continue
                if Stock.objects.filter(imei_number=imei).exists():
                    duplicate_imeis.append(imei)
                    continue

                stock = Stock.objects.create(
                    product=product,
                    imei_number=imei,
                    added_by=request.user,
                    serial_number=f"SER-{uuid.uuid4().hex[:8]}",
                    stock_in_date=timezone.now().date()
                )

                StockHistory.objects.create(
                    stock=stock,
                    action="added",
                    performed_by=request.user,
                    details=f"Bulk add for {product.model_name}"
                )

                added_imeis.append(imei)

            # if duplicates found → create downloadable CSV
            duplicate_csv_url = None
        

            return render(request, "sales_process/stock_in_results.html", {
                "product": product,
                "added_imeis": added_imeis,
                "duplicate_imeis": duplicate_imeis,
            })

    else:
        form = BulkStockForm()
    return render(request, "sales_process/add_stocks.html", {"form": form})

User = get_user_model()


def list_stocks(request):
    stocks = Stock.objects.select_related("product").all()
    return render(request, "sales_process/list_stocks.html", {"stocks": stocks})

def filter_stocks(request):
    """HTMX filter endpoint – returns only the table"""
    query = request.GET.get("q", "").strip()
    stocks = Stock.objects.all().select_related("product", "assigned_to")

    if query:
        stocks = stocks.filter(
            Q(imei_number__icontains=query) |
            Q(product__model_name__icontains=query) |
            Q(product__model_sku__icontains=query) |
            Q(product__model_category__icontains=query) |
            Q(assigned_to__username__icontains=query)
        )

    return render(request, "sales_process/list_stocks_table.html", {"stocks": stocks})

@csrf_exempt
def allocate_stock(request, imei_number):
    stock = get_object_or_404(Stock, imei_number=imei_number)

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        
        if not user_id:
            return HttpResponse("<div class='text-danger'>Please select a user.</div>")

        new_user = get_object_or_404(User, id=user_id)
        old_user = stock.assigned_to

        stock.assigned_to = new_user
        stock.last_assigned_date = timezone.now().date()
        stock.save()

        # Log allocation / transfer
        if old_user and old_user != new_user:
            action = f"Transferred from {old_user} to {new_user}"
        else:
            action = f"Allocated to {new_user}"
            
        

        StockHistory.objects.create(
            stock=stock,
            action="allocated",
            performed_by=request.user,
            details=action,
            transferred_to=new_user,
            transferred_from=old_user
        )
       
        # ✅ return updated row HTML so htmx replaces the <tr>
        return HttpResponse(
            f"<div class='alert alert-success'>Stock {stock.imei_number} successfully allocated to {new_user.profile.full_name}</div>"
        )

    history = StockHistory.objects.filter(stock__imei_number=imei_number) \
                .select_related("stock__assigned_to__profile") \
                .order_by("-performed_on")
    # GET request → return form partial
    users = User.objects.all()
    return render(request, "sales_process/allocate_stocks.html", {
        "stock": stock,
        "users": users,
        "history": history
    })

@csrf_exempt
def search_users(request,imei_number):
    
    query = request.GET.get("query", "").strip()
    users = User.objects.all()
    
    print(query)

    if query:
        users = users.filter(
            profile__full_name__icontains=query   # 🔎 Search only in Profile.full_name
        )

    return render(request, "sales_process/user_results.html", {
        "users": users,
        "imei_number": imei_number,
    })

@csrf_exempt
def select_user(request, imei_number, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, "sales_process/selected_user.html", {"user": user, "imei_number": imei_number})


def stock_history(request, stock_id):
    stock = get_object_or_404(Stock, id=stock_id)
    history = StockHistory.objects.filter(stock=stock).order_by("-timestamp")
    return render(request, "partials/stock_history.html", {"stock": stock, "history": history})
