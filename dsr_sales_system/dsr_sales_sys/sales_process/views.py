from django.shortcuts import render,get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .forms import ProductForm,BulkStockForm
from .models import Product,Stock,StockHistory
from manage_users.models import CompanyProfile
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
import csv
from io import StringIO
import uuid
import datetime
from django.urls import reverse

from .operations import generate_qr_code
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


@transaction.atomic
def bulk_allocate_stock(request):
    
    if request.method == "POST":
        user_id = request.POST.get("user")
        imei_numbers = request.POST.get("imei_numbers", "")

        if not user_id or not imei_numbers:
            return render(request, "sales_process/bulk_allocate_results.html", {
                "error": "Please select a user and enter IMEI numbers."
            })

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return render(request, "sales_process/bulk_allocate_results.html", {
                "error": "Selected user not found."
            })

        imeis = [i.strip() for i in imei_numbers.splitlines() if i.strip()]
        allocated,allocated_items, not_found = [], [],[]

        for imei in imeis:
            try:
                stock = Stock.objects.get(imei_number=imei)
                previous_user = stock.assigned_to
                stock.assigned_to = user
                stock.save()
                
                allocated_items.append(stock)

                StockHistory.objects.create(
                    stock=stock,
                    action="allocated",
                    performed_by=request.user,
                    transferred_to=user,
                    transferred_from=previous_user,
                    details=f"Bulk allocation to {user.profile.full_name}",
                    performed_on=timezone.now()
                )
                allocated.append(imei)
            except Stock.DoesNotExist:
                not_found.append(imei)

        
        

        # ✅ Render HTML receipt with QR
        imei_list = ",".join([s.imei_number for s in allocated_items])
        delivery_note_url = f"/download-delivery-note/{user.id}/?imeis={imei_list}"
        
        download_url = (
            reverse("download-delivery-note", args=[user_id]) +
            f"?imeis={imei_list}"
        )
        
        html_response = f"""
        <div class="p-4 bg-green-100 border border-green-300 rounded-md shadow">
            <p class="text-green-800 font-semibold">✅ Allocation successful!</p>
            <a href="{download_url}" 
               class="btn btn-warning">
               ⬇️ Download Delivery Note
            </a>
        </div>
        """

        return HttpResponse(html_response)

    return render(request, "sales_process/bulk_allocate.html")

def download_delivery_note(request, user_id):
    user = get_object_or_404(User, id=user_id)
    imeis = request.GET.get("imeis", "").split(",")

    company = CompanyProfile.objects.first()

    # ✅ Only the stocks allocated in this action
    allocated_stocks = Stock.objects.filter(imei_number__in=imeis, assigned_to=user)
    
    qr_data = f"Delivery Note\nUser: {user.profile.full_name}\nIMEIs: {', '.join([s.imei_number for s in allocated_stocks])}"
    qr_code_base64 = generate_qr_code(qr_data)
    qr_data_uri = f"data:image/png;base64,{qr_code_base64}"
    
    '''
    html_content = render_to_string("sales_process/delivery_note.html", {
        "company": company,
        "user": user,
        "stocks": allocated_stocks,
        "date": datetime.datetime.now(),
        "qr_code": qr_data_uri,
    })

    #response = HttpResponse(html_content, content_type="text/html")
    #response['Content-Disposition'] = f'attachment; filename="delivery-note-{user.profile.full_name}.html"'
    '''
    
    contxt = {
        "company": company,
        "user": user,
        "stocks": allocated_stocks,
        "date": datetime.datetime.now(),
        "qr_code": qr_data_uri,
    }
    r = render(request, "sales_process/delivery_note.html", contxt)
    
    return r

@csrf_exempt
def search_users_for_bulk_allocation(request):
    
    query = request.GET.get("q", "").strip()
    users = User.objects.all()

    if query:
        users = users.filter(
            Q(profile__full_name__icontains=query)
        )[:5]  # limit results

    return render(request, "sales_process/search_users_for_bulk_allocation.html", {"users": users})


    
    
