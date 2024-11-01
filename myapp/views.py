import csv
from django.db.models import Sum, Max
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from datetime import datetime
from rest_framework.response import Response
from rest_framework.decorators import api_view
import json
from io import TextIOWrapper
from .forms import CSVUploadForm, InvoiceUpdateForm, InvoiceCreateForm, InvoiceForm, InvoiceDetailForm
from .models import Invoice, Store, CustomerGroup, Customer, ProductCategory, Product, InvoiceDetail

def invoice_list(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            decoded_file = TextIOWrapper(csv_file.file, encoding='utf-8', errors='replace')
            reader = csv.reader(decoded_file, delimiter=',')

            next(reader)

            stores_dict = {}
            customer_groups_dict = {}
            customers_dict = {}
            product_categories_dict = {}
            products_dict = {}
            invoices_dict = {}
            invoice_details = []

            for row in reader:
                try:
                    if row[1] not in stores_dict:
                        store = Store(ma_cua_hang=row[1], doanh_nghiep=row[0], dia_chi=row[2])
                        stores_dict[row[1]] = store

                    if row[6] not in customer_groups_dict:
                        customer_group = CustomerGroup(ma_nhom_kh=row[6], thong_tin_nhom_kh=row[7])
                        customer_groups_dict[row[6]] = customer_group

                    if row[8] not in customers_dict:
                        customer = Customer(ma_kh=row[8], ma_nhom_kh=customer_groups_dict[row[6]])
                        customers_dict[row[8]] = customer

                    if row[9] not in product_categories_dict:
                        product_category = ProductCategory(ma_nhom_hang=row[9], nhom_hang=row[9])
                        product_categories_dict[row[9]] = product_category

                    if row[11] not in products_dict:
                        product = Product(
                            ma_hang=row[11],
                            ma_nhom_hang=product_categories_dict[row[9]],
                            mat_hang=row[12],
                            dvt=row[13],
                            don_gia=float(row[15])
                        )
                        products_dict[row[11]] = product

                    if row[5] not in invoices_dict:
                        invoice = Invoice(
                            ma_hoa_don=row[5],
                            ma_cua_hang=stores_dict[row[1]],
                            ma_kh=customers_dict[row[8]],
                            nam=int(row[3]),
                            thang=int(row[4])
                        )
                        invoices_dict[row[5]] = invoice

                    invoice_detail = InvoiceDetail(
                        invoice=invoices_dict[row[5]],
                        ma_hang=products_dict[row[11]],
                        sl_ban=int(row[14]),
                        tam_tinh=float(row[15])
                    )
                    invoice_details.append(invoice_detail)

                except Exception as e:
                    invoices = Invoice.objects.all()
                    messages.error(request, "Import invoice failed, data not match the struct")
                    return render(request, 'myapp/invoice_list.html', {
                        'form': form,
                        'invoices': invoices
                    })

            Store.objects.bulk_create(stores_dict.values(), ignore_conflicts=True)
            CustomerGroup.objects.bulk_create(customer_groups_dict.values(), ignore_conflicts=True)
            Customer.objects.bulk_create(customers_dict.values(), ignore_conflicts=True)
            ProductCategory.objects.bulk_create(product_categories_dict.values(), ignore_conflicts=True)
            Product.objects.bulk_create(products_dict.values(), ignore_conflicts=True)
            Invoice.objects.bulk_create(invoices_dict.values(), ignore_conflicts=True)
            InvoiceDetail.objects.bulk_create(invoice_details, ignore_conflicts=True)
            messages.success(request, "Import invoice successed")

    else:
        form = CSVUploadForm()

    invoices = Invoice.objects.annotate(tong_gia=Sum('invoicedetail__tam_tinh')).order_by("-ma_hoa_don")
    paginator = Paginator(invoices, 10)  # Số lượng hóa đơn mỗi trang
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'myapp/invoice_list.html', {
        'form': form,
        'page_obj': page_obj,
    })

def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Tính tổng giá từ InvoiceDetail
    total_price = invoice.invoicedetail_set.aggregate(Sum('tam_tinh'))['tam_tinh__sum'] or 0

    if request.method == 'POST':
        form = InvoiceUpdateForm(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            messages.success(request, "Invoice updated successfully.")
            return redirect(reverse('invoice_detail', kwargs={'pk': invoice.pk}))
    else:
        form = InvoiceUpdateForm(instance=invoice)

    return render(request, 'myapp/invoice_detail.html', {
        'invoice': invoice,
        'total_price': total_price,
        'form': form,
    })

def delete_invoice_detail(request, detail_id):
    # Lấy đối tượng InvoiceDetail dựa trên ID
    detail = get_object_or_404(InvoiceDetail, pk=detail_id)
    invoice = detail.invoice  # Lấy đối tượng hóa đơn tương ứng
    invoice_id = invoice.ma_hoa_don  # Lưu lại ID của hóa đơn trước khi xóa

    # Xóa đối tượng InvoiceDetail
    detail.delete()

    # Kiểm tra số lượng chi tiết hóa đơn còn lại
    if invoice.invoicedetail_set.count() == 0:
        # Nếu không còn chi tiết nào, xóa hóa đơn
        invoice.delete()
        messages.success(request, "Invoice and product removed successfully.")
        return redirect('invoice_list')
    else:
        messages.success(request, "Product removed from invoice successfully.")
    
    # Chuyển hướng về trang chi tiết hóa đơn
    return redirect(reverse('invoice_detail', kwargs={'pk': invoice_id}))

def update_invoice_detail(request, id):
    # Lấy đối tượng InvoiceDetail dựa trên ID
    invoice_detail = get_object_or_404(InvoiceDetail, id=id)
    
    if request.method == 'POST':
        # Lấy số lượng mới từ form
        new_quantity = request.POST.get('quantity')
        
        if new_quantity.isdigit() and int(new_quantity) > 0:
            # Cập nhật số lượng
            invoice_detail.sl_ban = int(new_quantity)
            invoice_detail.tam_tinh = invoice_detail.ma_hang.don_gia * int(new_quantity)
            invoice_detail.save()
            messages.success(request, 'Quantity updated successfully!')
        else:
            messages.error(request, 'Invalid quantity. Please enter a positive number.')
    
    # Chuyển hướng trở lại trang chi tiết hóa đơn
    # return redirect('invoice_detail', id=invoice_detail.invoice.ma_hoa_don)
    return redirect(reverse('invoice_detail', kwargs={'pk': invoice_detail.invoice.ma_hoa_don}))

@api_view(['POST'])
def create_invoice1(request):
    # Lấy dữ liệu từ JSON
    data = json.loads(request.body)

    ma_cua_hang = data.get('ma_cua_hang')
    ma_kh = data.get('ma_kh')
    nam = datetime.now().year
    thang = datetime.now().month
    product_ids = data.get('product_ids', [])
    quantities = data.get('quantities', [])

    store = get_object_or_404(Store, ma_cua_hang=ma_cua_hang)
    customer = get_object_or_404(Customer, ma_kh=ma_kh)

    # Tạo Invoice
    invoice = Invoice(ma_cua_hang=store, ma_kh=customer, nam=nam, thang=thang)
    invoice.save()

    # Tạo danh sách InvoiceDetail
    invoice_details = []
    for product_id, quantity in zip(product_ids, quantities):
        # Chỉ tạo InvoiceDetail nếu quantity hợp lệ
        if quantity > 0:  # Kiểm tra số lượng phải lớn hơn 0
            invoice_details.append(InvoiceDetail(invoice=invoice, ma_hang_id=product_id, sl_ban=quantity))

    # Sử dụng bulk_create để lưu tất cả InvoiceDetail trong một lần
    if invoice_details:
        InvoiceDetail.objects.bulk_create(invoice_details)

    # Trả về phản hồi JSON
    return JsonResponse({'message': 'Invoice created successfully!', 'redirect_url': 'invoice_success'})

def create_invoice(request):
    if request.method == 'POST':
        # Lấy dữ liệu từ JSON
        data = json.loads(request.body)

        ma_cua_hang = data.get('ma_cua_hang')
        ma_kh = data.get('ma_kh')
        nam = datetime.now().year
        thang = datetime.now().month
        product_ids = data.get('product_ids', [])
        quantities = data.get('quantities', [])

        store = get_object_or_404(Store, ma_cua_hang=ma_cua_hang)
        customer = get_object_or_404(Customer, ma_kh=ma_kh)

        # Tạo Invoice
        invoice = Invoice(ma_cua_hang=store, ma_kh=customer, nam=nam, thang=thang)
        invoice.save()

        # Tạo danh sách InvoiceDetail
        invoice_details = []
        for product_id, quantity in zip(product_ids, quantities):
            # Chỉ tạo InvoiceDetail nếu quantity hợp lệ
            if quantity > 0:  # Kiểm tra số lượng phải lớn hơn 0
                invoice_details.append(InvoiceDetail(invoice=invoice, ma_hang_id=product_id, sl_ban=quantity))

        # Sử dụng bulk_create để lưu tất cả InvoiceDetail trong một lần
        if invoice_details:
            InvoiceDetail.objects.bulk_create(invoice_details)

        # Trả về phản hồi JSON
        return JsonResponse({'message': 'Invoice created successfully!', 'redirect_url': 'invoice_success'})

    # Nếu không phải POST, trả về form như trước
    products = Product.objects.all()
    customer_groups = CustomerGroup.objects.all()
    stores = Store.objects.all()

    context = {
        'products': products,
        'customer_groups': customer_groups,
        'stores': stores,
    }
    return render(request, 'myapp/create_invoice.html', context)