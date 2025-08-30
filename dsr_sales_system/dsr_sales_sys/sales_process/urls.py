from django.urls import path
from . import views
from .views import home_view,create_product,list_products,filter_products,bulk_add_stock,\
    list_stocks,allocate_stock,stock_history,filter_stocks

urlpatterns = [
    path('', home_view, name='home'),
    path('create-product/', create_product, name='create-product'),
    path('list-products/', list_products, name='list-products'),
    path('filter-products/', filter_products, name='filter-products'),
    path('bulk-add-stock/', bulk_add_stock, name='bulk-add-stock'),
    path('list-stocks/', list_stocks, name='list-stocks'),
    path('allocate-stock/<int:stock_id>/', allocate_stock, name='allocate-stock'),
    path('stock-history/<int:stock_id>/', stock_history, name='stock-history'),
    path('filter-stocks/', filter_stocks, name='filter-stocks'),
]