from django.urls import path
from . import views
from .views import home_view,create_product,list_products,filter_products,bulk_add_stock,\
    list_stocks,allocate_stock,stock_history,filter_stocks,search_users,select_user,\
        bulk_allocate_stock,search_users_for_bulk_allocation,download_delivery_note,\
            create_sale,sales_list,return_sale,sales_chart_data,sales_per_model_data,\
                sales_per_product_data,sale_receipt

urlpatterns = [
    path('', home_view, name='home'),
    path('create-product/', create_product, name='create-product'),
    path('list-products/', list_products, name='list-products'),
    path('filter-products/', filter_products, name='filter-products'),
    path('bulk-add-stock/', bulk_add_stock, name='bulk-add-stock'),
    path('list-stocks/', list_stocks, name='list-stocks'),
    path('allocate-stock/<str:imei_number>/', allocate_stock, name='allocate-stock'),
    path('stock-history/<str:imei_number>/', stock_history, name='stock-history'),
    path('filter-stocks/', filter_stocks, name='filter-stocks'),
    path('search-users/<str:imei_number>', search_users, name='search-users'),
    path('select-user/<str:imei_number>/<int:user_id>/', select_user, name='select-user'),
    path('bulk-allocate-stock/', bulk_allocate_stock, name='bulk-allocate-stock'),
    path('search-users-for-bulk-allocation/', search_users_for_bulk_allocation, name='search-users-for-bulk-allocation'),
    path('download-delivery-note/<int:user_id>/', download_delivery_note, name='download-delivery-note'),
    path('create-sale/', create_sale, name='create-sale'),
    path('sales-list/', sales_list, name='sales-list'),
    path('return-sale/', return_sale, name='return-sale'),
    path('sales-chart-data/', sales_chart_data, name='sales-chart-data'),
    path('sales-per-model-data/', sales_per_model_data, name='sales-per-model-data'),
    path('sales-per-product-data/', sales_per_product_data, name='sales-per-product-data'),
    path('sale-receipt/<str:order_id>/', sale_receipt, name='sale-receipt'),
    
    
]