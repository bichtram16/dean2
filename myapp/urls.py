from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .views import invoice_list, invoice_detail, delete_invoice_detail, update_invoice_detail, create_invoice, create_invoice1,import_excel_view,export_invoice_data,chart_view,home

urlpatterns = [
    path('', views.home, name='home'), 
    path('invoices/', invoice_list, name='invoice_list'),
    path('invoices/<str:pk>/', invoice_detail, name='invoice_detail'),
    path('invoice/delete_detail/<int:detail_id>/', delete_invoice_detail, name='delete_invoice_detail'),
    path('invoice/detail/update/<int:id>/', update_invoice_detail, name='update_invoice_detail'),
    path('create-invoice/', create_invoice, name='create_invoice'),
    path('create-invoice1/', create_invoice1, name='create_invoice1'),
    path('import_excel/', import_excel_view, name='import_excel'),
    path('export-invoice-data/', views.export_invoice_data, name='export_invoice_data'),
    path('chart/', views.chart_view, name='chart'),
]