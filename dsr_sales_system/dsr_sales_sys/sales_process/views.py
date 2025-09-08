from django.shortcuts import render,get_object_or_404,get_list_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .forms import ProductForm,BulkStockForm,SaleForm,SaleSearchForm
from .models import Product,Stock,StockHistory,Sale,Customer
from manage_users.models import CompanyProfile,Profile, CustomUser
from django.db import transaction
from django.apps import apps
from django.contrib import messages
from django.db.models import Q,Count,F,Min,Sum,ExpressionWrapper, DurationField,Avg
from django.db.models.functions import TruncDay, TruncMonth,TruncWeek
from django.utils.timezone import now
from django.http import HttpResponse, JsonResponse,Http404,FileResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from datetime import date, timedelta
from django.utils.timezone import localdate
from django.core.cache import cache
from .operations import generate_qr_code
from django.utils.timezone import is_aware
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import pandas as pd
import csv
from io import StringIO
import io
import uuid
import datetime
from django.urls import reverse

from .operations import generate_qr_code
# Create your views here.
@login_required
def home_view(request):
    
    # ⚡ quick cache to avoid recomputation
    payload = cache.get("sales_dash_v2")
    if payload:
        return render(request, "sales/dashboard.html", payload)

    today = localdate()
    yesterday = today - timedelta(days=1)

    # Week starts Monday
    start_week = today - timedelta(days=today.weekday())
    prev_week_start = start_week - timedelta(days=7)

    start_month = today.replace(day=1)
    prev_month_end = start_month - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    start_year = today.replace(month=1, day=1)
    prev_year_start = date(start_year.year - 1, 1, 1)

    base = Q(is_returned=False)

    # ---------- SINGLE AGGREGATE BLOCK ----------
    agg = Sale.objects.aggregate(
        # Totals
        sales_today=Count("id", filter=base & Q(sales_date__date=today)),
        sales_yesterday=Count("id", filter=base & Q(sales_date__date=yesterday)),

        sales_week=Count("id", filter=base & Q(sales_date__date__gte=start_week)),
        sales_prev_week=Count(
            "id",
            filter=base & Q(sales_date__date__gte=prev_week_start, sales_date__date__lt=start_week),
        ),

        sales_month=Count("id", filter=base & Q(sales_date__date__gte=start_month)),
        sales_prev_month=Count(
            "id",
            filter=base & Q(sales_date__date__gte=prev_month_start, sales_date__date__lte=prev_month_end),
        ),

        sales_year=Count("id", filter=base & Q(sales_date__date__gte=start_year)),
        sales_prev_year=Count(
            "id",
            filter=base & Q(sales_date__date__gte=prev_year_start, sales_date__date__lt=start_year),
        ),

        # Distinct sellers for averages
        sellers_today=Count("sold_by", filter=base & Q(sales_date__date=today), distinct=True),
        sellers_week=Count("sold_by", filter=base & Q(sales_date__date__gte=start_week), distinct=True),
        sellers_month=Count("sold_by", filter=base & Q(sales_date__date__gte=start_month), distinct=True),
        sellers_year=Count("sold_by", filter=base & Q(sales_date__date__gte=start_year), distinct=True),
    )

    def safe_div(a, b):
        return round(a / b, 2) if b else 0.0

    def growth(curr, prev):
        if prev == 0:
            return 100.0 if curr > 0 else 0.0
        return round(((curr - prev) / prev) * 100, 2)

    # ---------- AVERAGES ----------
    avg_per_agent_today = safe_div(agg["sales_today"], agg["sellers_today"])
    avg_per_agent_week  = safe_div(agg["sales_week"],  agg["sellers_week"])
    avg_per_agent_month = safe_div(agg["sales_month"], agg["sellers_month"])

    days_elapsed_in_week  = (today - start_week).days + 1
    days_elapsed_in_month = today.day
    days_elapsed_in_year  = (today - start_year).days + 1

    avg_daily_week  = safe_div(agg["sales_week"],  days_elapsed_in_week)
    avg_daily_month = safe_div(agg["sales_month"], days_elapsed_in_month)
    avg_daily_year  = safe_div(agg["sales_year"],  days_elapsed_in_year)

    # ---------- GROWTH ----------
    growth_today = growth(agg["sales_today"], agg["sales_yesterday"])
    growth_week  = growth(agg["sales_week"],  agg["sales_prev_week"])
    growth_month = growth(agg["sales_month"], agg["sales_prev_month"])
    growth_year  = growth(agg["sales_year"],  agg["sales_prev_year"])

    # ---------- SERIES (small, indexed) ----------
    last30 = today - timedelta(days=30)
    sales_per_day = (
        Sale.objects.filter(base, sales_date__date__gte=last30)
        .annotate(day=TruncDay("sales_date"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    last12m_start = start_month - timedelta(days=365)
    sales_per_month = (
        Sale.objects.filter(base, sales_date__date__gte=last12m_start)
        .annotate(month=TruncMonth("sales_date"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )

    # ---------- TOP SELLERS (tiny) ----------
    top_sellers = (
    Sale.objects.filter(base)
    .values("sold_by", "sold_by__profile__full_name", "sold_by__profile__photo")
    .annotate(total=Count("id"))
    .order_by("-total")[:5]
    )
    
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    sales = Sale.objects.select_related("stock", "stock__product").order_by("-sales_date")
    monthly_sales = sales.filter(sales_date__date__gte=start_of_month)

    # Total sellout count by product for this month
    monthly_by_product = (
        monthly_sales
        .values("stock__product__model_name")
        .annotate(totals=Count("id"))
      
    )
    context = {
        **agg,
        "growth_today": growth_today,
        "growth_week": growth_week,
        "growth_month": growth_month,
        "growth_year": growth_year,
        "avg_per_agent_today": avg_per_agent_today,
        "avg_per_agent_week": avg_per_agent_week,
        "avg_per_agent_month": avg_per_agent_month,
        "avg_daily_week": avg_daily_week,
        "avg_daily_month": avg_daily_month,
        "avg_daily_year": avg_daily_year,
        "sales_per_day": list(sales_per_day),
        "sales_per_month": list(sales_per_month),
        "top_sellers": list(top_sellers),
        "monthly_by_product": list(monthly_by_product),
    }

    cache.set("sales_dash_v2", payload, 60) 
    return render(request, "sales_process/home.html", context)
@login_required
@csrf_exempt
def sales_chart_data(request):
    period = request.GET.get("period", "day")  # default daily
    base = Sale.objects.filter(is_returned=False)

    if period == "day":
        qs = (
            base.annotate(bucket=TruncDay("sales_date"))
            .values("bucket")
            .annotate(total=Count("id"))
            .order_by("bucket")
        )
    elif period == "week":
        qs = (
            base.annotate(bucket=TruncWeek("sales_date"))
            .values("bucket")
            .annotate(total=Count("id"))
            .order_by("bucket")
        )
    else:  # month
        qs = (
            base.annotate(bucket=TruncMonth("sales_date"))
            .values("bucket")
            .annotate(total=Count("id"))
            .order_by("bucket")
        )

    data = {
        "labels": [row["bucket"].strftime("%Y-%m-%d") for row in qs],
        "values": [row["total"] for row in qs],
    }
    return JsonResponse(data)


@login_required
def sales_per_product_data(request):
    qs = Sale.objects.select_related("stock__product") \
                     .values("stock__product__model_name") \
                     .annotate(total=Count("id")) \
                     .order_by("-total")

    labels = [item["stock__product__model_name"] for item in qs]
    values = [item["total"] for item in qs]
    return JsonResponse({"labels": labels, "values": values})
@login_required
def sales_per_model_data(request):
    qs = Sale.objects.select_related("stock__product") \
                     .values("stock__product__model_name") \
                     .annotate(total=Count("id")) \
                     .order_by("-total")

    labels = [item["stock__product__model_name"] for item in qs]
    values = [item["total"] for item in qs]
    return JsonResponse({"labels": labels, "values": values})

    
    
   

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
@transaction.atomic
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

@login_required
def list_stocks(request):
    
    user = request.user
    
    if user.role == "manager" or user.role == "admin":
        
        stocks = Stock.objects.select_related("product", "assigned_to")
        
    else: 
        
        stocks = Stock.objects.select_related("product", "assigned_to").filter(assigned_to=user)
        
        
    total_stocks = stocks.count()

    # Average age in days
    avg_age_qs = stocks.annotate(
        age=ExpressionWrapper(
            timezone.now() - F("stock_in_date"),  # assuming you have a date_added field
            output_field=DurationField()
        )
    ).aggregate(avg_age=Avg("age"))

    avg_age_days = None
    if avg_age_qs["avg_age"]:
        avg_age_days = avg_age_qs["avg_age"].days

    # Weeks of stock: (total stock) / (avg weekly sales of last 4 weeks)
    four_weeks_ago = timezone.now() - timedelta(weeks=4)
    recent_sales = Sale.objects.filter(
        sales_date__gte=four_weeks_ago,
        stock__in=stocks
    )
    weekly_sales = recent_sales.count() / 4 if recent_sales.exists() else 0
    weeks_of_stock = round(total_stocks / weekly_sales, 1) if weekly_sales else "∞"
    
    return render(request, "sales_process/list_stocks.html", {"stocks": stocks, "total_stocks": total_stocks, "avg_age_days": avg_age_days, "weeks_of_stock": weeks_of_stock})
@login_required
def filter_stocks(request):
    """HTMX filter endpoint – returns only the table"""
    query = request.GET.get("q", "").strip()
    
    user = request.user
    
    if user.role == "manager" or user.role == "admin":
        
        stocks = Stock.objects.all().select_related("product", "assigned_to")
        
    else: 
        
        stocks = Stock.objects.all().select_related("product", "assigned_to").filter(assigned_to=user)
    
  

    if query:
        stocks = stocks.filter(
            Q(imei_number__icontains=query) |
            Q(product__model_name__icontains=query) |
            Q(product__model_sku__icontains=query) |
            Q(product__model_category__icontains=query) |
            Q(assigned_to__username__icontains=query)
        )

    return render(request, "sales_process/list_stocks_table.html", {"stocks": stocks})
@login_required
@csrf_exempt
@transaction.atomic
def allocate_stock(request, imei_number):
    stock = get_object_or_404(Stock, imei_number=imei_number)

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        
        if not user_id:
            return HttpResponse("<div class='text-danger'>Please select a user.</div>")

        new_user = get_object_or_404(User, id=user_id)
        old_user = stock.assigned_to

        stock.assigned_to = new_user
        stock.allocated_by = request.user
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
@login_required
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
@login_required
@csrf_exempt
def select_user(request, imei_number, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, "sales_process/selected_user.html", {"user": user, "imei_number": imei_number})


def stock_history(request, stock_id):
    stock = get_object_or_404(Stock, id=stock_id)
    history = StockHistory.objects.filter(stock=stock).order_by("-timestamp")
    return render(request, "partials/stock_history.html", {"stock": stock, "history": history})

@login_required
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
                stock.allocated_by = request.user
                stock.last_assigned_date = timezone.now().date()
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
@login_required
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
@login_required
@csrf_exempt
def search_users_for_bulk_allocation(request):
    
    query = request.GET.get("q", "").strip()
    users = User.objects.all()

    if query:
        users = users.filter(
            Q(profile__full_name__icontains=query)
        )[:5]  # limit results

    return render(request, "sales_process/search_users_for_bulk_allocation.html", {"users": users})

'''

        sales processing
        
'''
@login_required
@transaction.atomic
def create_sale(request):
    if request.method == "POST":
        form = SaleForm(request.POST)
        if form.is_valid():
        
            sale, results = form.process_sale(sold_by=request.user)
       
            
            if sale and results:
                return render(request, "sales_process/sales_message.html", {
                    "status": "success",
                    "sale": sale,
                    "message": f"✅ Sale created successfully! <a href='{results}' target='_blank'>Download Receipt</a>"
                })

            else:
                return render(request, "sales_process/sales_message.html", {
                    "status": "error",
                    "message": results
                })

           
        # invalid form
        return render(request, "sales_process/sales_message.html", {
            "status": "error",
            "message": form.errors
        })

    # ✅ GET: show form
    form = SaleForm()
    return render(request, "sales_process/create_sales.html", {"form": form})

@login_required
def sales_list(request):
    
    user = request.user
    
    if user.role == "manager" or user.role == "admin":	
        sales = Sale.objects.select_related("stock", "sold_by").order_by("-sales_date")
    
    else:
        sales = Sale.objects.select_related("stock", "sold_by").filter(sold_by=user).order_by("-sales_date")
        
    

    
    form = SaleSearchForm(request.GET or None)
    
    if request.method == "POST":
        imei = request.POST.get("imei")
        product_name = request.POST.get("product_name")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        
        if user.role == "manager" or user.role == "admin":	
            sales = Sale.objects.select_related("stock", "sold_by").order_by("-sales_date")
    
        else:
            sales = Sale.objects.select_related("stock", "sold_by").filter(sold_by=user).order_by("-sales_date")
        
        
        if imei:
            sales = sales.filter(stock__imei_number=imei)
        if product_name:
            sales = sales.filter(stock__product__model_name__icontains=product_name)
        if start_date:
            sales = sales.filter(sales_date__date__gte=start_date)
        if end_date:
            sales = sales.filter(sales_date__date__lte=end_date)
            
   
        
        return render(request, "sales_process/sales_list_table.html", {"sales": sales})
    
    today = now().date()
    month_start = today.replace(day=1)

    today_sales = sales.filter(sales_date__date=today).aggregate(
        qty=Count("id"), amount=Sum("stock__product__price")
    )

    month_sales = sales.filter(sales_date__date__gte=month_start).aggregate(
        qty=Count("id"), amount=Sum("stock__product__price")
    )

    total_sales = sales.aggregate(qty=Count("id"), amount=Sum("stock__product__price"))

    summary = {
        "today_qty": today_sales["qty"] or 0,
        "today_amount": today_sales["amount"] or 0,
        "month_qty": month_sales["qty"] or 0,
        "month_amount": month_sales["amount"] or 0,
        "total_qty": total_sales["qty"] or 0,
        "total_amount": total_sales["amount"] or 0,
    }
    
    sales = sales[:5]
    
    return render(request, "sales_process/sales_list.html", {"sales": sales, "summary": summary})
@login_required
@csrf_exempt
@transaction.atomic
def return_sale(request):
    
    if request.method=="POST":
        
        sale_id = request.POST.get("sale_id")
        action = request.POST.get("action")
        sale = get_object_or_404(Sale, id=sale_id)
        
        stock = sale.stock
        
        if action == "mark":
        # update stock status back to available
            sale.is_returned = True
            sale.save()
            stock.status = "returned"
            stock.save()
            msg = 'has been marked as returned'
           
        elif action == "return":            
            stock.status = "in_stock"
            stock.save()
            sale.delete()
            
            msg = 'has been returned to stock'
        else:
            return HttpResponse("Invalid action", status=400)
            

        # add to history
        StockHistory.objects.create(
            stock=stock,
            action="Returned from customer",
            transferred_to=None,
            transferred_from=sale.sold_by,
            performed_on=timezone.now()
        )

        # delete the sale record (or mark it as returned instead if you prefer)
        
        sales = Sale.objects.select_related("stock").order_by("-sales_date")

        resp = f'<div class="alert alert-success" role="alert">Sale #{sale.stock.imei_number} {msg}.</div>'

        return render(request, "sales_process/sales_list_table.html", {"sales": sales,"resp":resp})

@login_required
def sale_receipt(request, order_id):
    
    sales = get_list_or_404(Sale, order_id=order_id)
    company = CompanyProfile.objects.first()
    
    if not sales:
        raise Http404("<h1>Sale not found</h1>")
    
    customer = sales[0].customer
    
    qr_code_base64 = generate_qr_code(order_id)

    total_amount = sum(sale.stock.product.price for sale in sales)
    total_quantity = len(sales)
    
    sale = sales[0]
    
    return render(request, "sales_process/sales_receipt.html", {
        "sales": sales,
        "company": company,
        "customer": customer,
        "order_id": order_id,
        "total_amount": total_amount,
        "sales_date": sales[0].sales_date,
        "total_quantity": total_quantity,
        "qr_code_base64": qr_code_base64,
        "sale": sale
        
    })
@login_required   
def order_list(request):
    
    user = request.user

    # Base queryset with aggregations
    orders = (
        Sale.objects.values("order_id", "customer__name", "sold_by__profile__full_name")
        .annotate(
            date=Min("sales_date"),
            total_items=Count("id"),
            total_amount=Sum(F("stock__product__price")),
        )
        .order_by("-date")
    )

    # Restrict if user is sales (not manager/admin)
    if user.role not in ["manager", "admin"]:
        orders = orders.filter(sold_by=user)

    return render(
        request,
        "sales_process/order_list.html",
        {"orders": orders},
    )

@login_required
def report_hub(request):
    return render(request, "sales_process/report_hub.html")



def search_reports(request):
    """
    Search across all models dynamically.
    Only searches text-like fields (CharField, TextField).
    """
    if request.method == "POST":
        query = request.POST.get("q", "").strip()
        results = {}

        if query:
            for model in apps.get_models():
                try:
                    # Collect searchable fields
                    text_fields = [
                        f.name for f in model._meta.fields
                        if f.get_internal_type() in ["CharField", "TextField"]
                    ]

                    if not text_fields:
                        continue

                    # Build OR filter across all text fields
                    q_obj = Q()
                    for field in text_fields:
                        q_obj |= Q(**{f"{field}__icontains": query})

                    qs = model.objects.filter(q_obj)[:50]  # cap results per model

                    if qs.exists():
                        results[model.__name__] = {
                            "fields": [f.name for f in model._meta.fields],
                            "objects": qs,
                        }
                except Exception as e:
                    # Skip models that can’t be queried
                    print(f"Skipping {model.__name__}: {e}")
                    continue

        return render(
            request,
            "sales_process/report_search_results.html",
            {"results": results, "query": query},
        )


def download_report(request, model, format):
    """
    Download report in CSV/XLSX
    """
    buffer = io.BytesIO()

    if model == "sales":
        qs = Sale.objects.select_related("customer", "stock", "sold_by")
        data = [{
            "Order ID": s.order_id,
            "IMEI": s.stock.imei_number,
            "Product": s.stock.product.model_name,
            "RAM": s.stock.product.model_ram,
            "Storage": s.stock.product.model_storage,	
            "Price": s.stock.product.price,
            "Agent Name": s.sold_by.profile.full_name if s.sold_by else None,
            "Agent Phone":s.sold_by.profile.phone_number if s.sold_by else None,	
            "Agent Username":s.sold_by.username if s.sold_by else None,
            "Agent Id":s.sold_by.profile.national_id if s.sold_by else None,
            "Region":s.sold_by.profile.region if s.sold_by else None,
            "Group":s.sold_by.profile.group if s.sold_by else None,
            "Customer Name": s.customer.name,
            "Customer ID": s.customer.id_number,
            "Customer Phone": s.customer.phone,
            "Customer Address": s.customer.address,
            "Processed By": request.user.profile.full_name,
            "Date": s.sales_date.replace(tzinfo=None) if s.sales_date else None
        } for s in qs]
    elif model == "stocks":
        qs = Stock.objects.select_related("product")
        data = [{
            "IMEI": s.imei_number,
            "Product": s.product.model_name,
            "RAM": s.product.model_ram,
            "Storage": s.product.model_storage,
            "Price": s.product.price,
            "Allocated Agent": s.assigned_to.profile.full_name if s.assigned_to else None,
            "Allocated Agent Phone": s.assigned_to.profile.phone_number if s.assigned_to else None,
            "Allocated Agent Username": s.assigned_to.username if s.assigned_to else None,
            "Allocated Agent ID": s.assigned_to.profile.national_id if s.assigned_to else None,
            "Allocated Agent Region": s.assigned_to.profile.region if s.assigned_to else None,
            "Allocated Agent Group": s.assigned_to.profile.group if s.assigned_to else None,
            "Latest Allocated Date": s.last_assigned_date.replace(tzinfo=None) if s.last_assigned_date else None,
            "Stock In Date": s.stock_in_date,
            "Allocated By": s.allocated_by.profile.full_name if s.allocated_by else None,
            "Status": s.status,
        } for s in qs]
    elif model == "customers":
        qs = Profile.objects.all()
        data = [{
            "Name": c.full_name,
            "Phone": c.phone_number,
            "ID": c.national_id,
            "Region": c.region,
        } for c in qs]
    elif model == "users":
        qs = CustomUser.objects.all()
        data = [{
            "Username": u.username,
            "Role": u.role,
            "Email": u.email,
            "Active": u.is_active,
        } for u in qs]
    else:
        return HttpResponse("Invalid model", status=400)

    df = pd.DataFrame(data)

    if format == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{model}_report.csv"'
        df.to_csv(path_or_buf=response, index=False)
        return response
    elif format == "xlsx":
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{model}_report.xlsx"'
        df.to_excel(buffer, index=False)
        response.write(buffer.getvalue())
        return response
    else:
        return HttpResponse("Invalid format", status=400)
    
@login_required    
def export_report(request, model, format):
    
    query = request.GET.get("q", "").strip()

    # Resolve model
    try:
        Model = apps.get_model(app_label="sales_process", model_name=model)  # change app_label
    except LookupError:
        raise Http404("Model not found")

    # Collect searchable fields
    text_fields = [
        f.name for f in Model._meta.fields
        if f.get_internal_type() in ["CharField", "TextField"]
    ]

    qs = Model.objects.all()
    if query and text_fields:
        from django.db.models import Q
        q_obj = Q()
        for field in text_fields:
            q_obj |= Q(**{f"{field}__icontains": query})
        qs = qs.filter(q_obj)

    if not qs.exists():
        return HttpResponse("⚠️ No results found.", status=404)

    fields = [f.name for f in Model._meta.fields]
    data = []
    for obj in qs:
        row = {}
        for field in fields:
            val = getattr(obj, field, "")
            if hasattr(val, "isoformat") and is_aware(val):
                val = val.replace(tzinfo=None)
            row[field] = val
        data.append(row)

    df = pd.DataFrame(data)

    # Export formats
    if format == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{model}_report.csv"'
        df.to_csv(path_or_buf=response, index=False)
        return response

    elif format == "excel":
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{model}_report.xlsx"'
        df.to_excel(response, index=False, engine="openpyxl")
        return response

    elif format == "pdf":
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        textobject = p.beginText(40, 800)
        textobject.setFont("Helvetica", 10)

        # Title
        textobject.textLine(f"{model} Report")
        textobject.textLine("")

        # Data rows
        for row in data[:100]:  # limit rows in PDF
            line = ", ".join(f"{k}: {v}" for k, v in row.items())
            textobject.textLine(line[:120])  # truncate long lines
        p.drawText(textobject)
        p.showPage()
        p.save()

        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f"{model}_report.pdf")

    else:
        return HttpResponse("⚠️ Unsupported format", status=400)
    
    
