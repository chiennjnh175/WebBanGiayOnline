from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Product, Category, Profile, Cart, CartItem, Order, OrderItem, Brand, ProductVariant
from .forms import RegistrationForm, UserUpdateForm, ProfileUpdateForm, ProductForm, OrderStatusForm
from django.db.models import Q, Sum, Count, F, Min, Max
from django.core.paginator import Paginator
from django.db.models.functions import TruncMonth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from urllib.parse import urlencode
import json
import os
import math
from django.conf import settings
from django.http import HttpResponse
from django.db import transaction
from django.utils.text import slugify
import csv
import io

def home(request, category_slug=None):
    G = request.GET
 
    cat_slug = category_slug or G.get('category')
    brand_slug = G.get('brand') or None
    sizes_sel = [s for s in G.getlist('size') if s]
    query = G.get('q')
    sort = G.get('sort', '')
 
    def to_number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
 
    min_price = to_number(G.get('min_price'))
    max_price = to_number(G.get('max_price'))
    cur_min = int(min_price) if min_price is not None else None
    cur_max = int(max_price) if max_price is not None else None
 
    selected_category = get_object_or_404(Category, slug=cat_slug) if cat_slug else None
    categories = list(Category.objects.all())
    brands = list(Brand.objects.all())
    selected_brand = next((b for b in brands if b.slug == brand_slug), None)
 
    # ---------- Bộ lọc ----------
    def filtered(skip=()):
        qs = Product.objects.all()
        if selected_category and 'category' not in skip:
            qs = qs.filter(category=selected_category)
        if selected_brand and 'brand' not in skip:
            qs = qs.filter(brand=selected_brand)
        if sizes_sel and 'size' not in skip:
            qs = qs.filter(variants__size__in=sizes_sel)      # chọn nhiều size = "hoặc"
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(category__name__icontains=query) |
                Q(brand__name__icontains=query)
            )
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        return qs.distinct()
 
    sort_map = {'price_asc': 'price', 'price_desc': '-price', 'name': 'name'}
    products = filtered().order_by(sort_map.get(sort, '-id')).prefetch_related('variants')
 
    # ---------- Số đếm theo bộ lọc đang bật (bỏ qua chính nhóm đó) ----------
    def count_by(field, skip):
        ids = filtered(skip).order_by().values('pk')
        return dict(Product.objects.filter(pk__in=ids).order_by()
                    .values_list(field).annotate(n=Count('id')))
 
    cat_counts = count_by('category', {'category'})
    brand_counts = count_by('brand', {'brand'})
    for c in categories:
        c.product_count = cat_counts.get(c.id, 0)
    for b in brands:
        b.product_count = brand_counts.get(b.id, 0)
 
    base_ids = filtered({'size'}).order_by().values('pk')
    size_counts = dict(ProductVariant.objects.filter(product__in=base_ids).order_by()
                       .values_list('size').annotate(n=Count('product', distinct=True)))
 
    def size_key(value):
        try:
            return (0, float(value), '')
        except (TypeError, ValueError):
            return (1, 0, str(value))
 
    all_sizes = sorted(set(ProductVariant.objects.exclude(size__isnull=True)
                           .values_list('size', flat=True)), key=size_key)
    sizes = [{'value': s, 'count': size_counts.get(s, 0), 'checked': str(s) in sizes_sel}
             for s in all_sizes]
 
    # ---------- Các mức giá gợi ý (tự tính theo giá sản phẩm hiện có) ----------
    bounds = Product.objects.aggregate(lo=Min('price'), hi=Max('price'))
    price_min_bound = int(bounds['lo'] or 0)
    price_max_bound = int(math.ceil(bounds['hi'] or 0))
    span = price_max_bound - price_min_bound
    unit = 100 if span >= 1000 else 10
 
    def nice(v):
        return int(round(v / unit) * unit)
 
    cut1 = nice(price_min_bound + span / 3)
    cut2 = nice(price_min_bound + 2 * span / 3)
    presets = [{'label': 'Tất cả mức giá', 'min': None, 'max': None}]
    if cut1 < cut2:
        presets += [
            {'label': f'Dưới ${cut1:,}', 'min': None, 'max': cut1},
            {'label': f'${cut1:,} – ${cut2:,}', 'min': cut1, 'max': cut2},
            {'label': f'Trên ${cut2:,}', 'min': cut2, 'max': None},
        ]
    for p in presets:
        p['active'] = (p['min'] == cur_min and p['max'] == cur_max)
 
    # ---------- Phân trang ----------
    try:
        per_page = int(G.get('show', 9))
    except ValueError:
        per_page = 9
    if per_page not in (9, 12, 24):
        per_page = 9
    paginator = Paginator(products, per_page)
    page_obj = paginator.get_page(G.get('page'))
    page_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1))
    for product in page_obj.object_list:
        product.has_available_variant = any(variant.stock > 0 for variant in product.variants.all())

    # ---------- Link và nhãn bộ lọc đang bật ----------
    def url_minus(*keys, value=None, path=None):
        params = G.copy()
        params.pop('page', None)
        for k in keys:
            if value is None:
                params.pop(k, None)
            else:
                params.setlist(k, [v for v in params.getlist(k) if v != value])
        qs = params.urlencode()
        return (path or request.path) + ('?' + qs if qs else '')
 
    active_filters = []
    if selected_category:
        active_filters.append({'label': selected_category.name,
                               'url': url_minus('category', path=reverse('home'))})
    if selected_brand:
        active_filters.append({'label': selected_brand.name.title(), 'url': url_minus('brand')})
    for s in sizes_sel:
        active_filters.append({'label': f'Size {s}', 'url': url_minus('size', value=s)})
    if cur_min is not None or cur_max is not None:
        if cur_min is not None and cur_max is not None:
            price_label = f'${cur_min:,} – ${cur_max:,}'
        elif cur_min is not None:
            price_label = f'Từ ${cur_min:,}'
        else:
            price_label = f'Đến ${cur_max:,}'
        active_filters.append({'label': price_label, 'url': url_minus('min_price', 'max_price')})
    if query:
        active_filters.append({'label': f'"{query}"', 'url': url_minus('q')})
 
    keep = G.copy()
    keep.pop('page', None)
    keep.pop('category', None)
    keep_qs = keep.urlencode()                      # giữ bộ lọc khi đổi thể loại
 
    clear_all_url = reverse('home')                 # xóa hết bộ lọc nhưng giữ từ khóa tìm kiếm
    if query:
        clear_all_url += '?' + urlencode({'q': query})
 
    page_params = G.copy()
    page_params.pop('page', None)
 
    context = {
        'products': page_obj,
        'is_store_home': not category_slug and not G,
        'categories': categories,
        'brands': brands,
        'sizes': sizes,
        'selected_category': selected_category,
        'selected_brand': selected_brand,
        'current_category_slug': cat_slug,
        'current_brand_slug': brand_slug,
        'sort': sort,
        'per_page': per_page,
        'page_range': page_range,
        'ellipsis': Paginator.ELLIPSIS,
        'query_string': page_params.urlencode(),
        'keep_qs': keep_qs,
        'price_presets': presets,
        'cur_min': '' if cur_min is None else cur_min,
        'cur_max': '' if cur_max is None else cur_max,
        'active_filters': active_filters,
        'clear_all_url': clear_all_url,
    }
    return render(request, 'store/home.html', context)


@login_required(login_url='login')
@user_passes_test(lambda u: u.is_staff, login_url='home')
def admin_dashboard(request):
    total_products = Product.objects.count()
    total_variants = ProductVariant.objects.count()
    total_users = User.objects.filter(is_staff=False).count()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='Pending').count()
    shipping_orders = Order.objects.filter(status='Shipping').count()
    completed_orders = Order.objects.filter(status='Completed').count()
    canceled_orders = Order.objects.filter(status='Canceled').count()
    completed_revenue = Order.objects.filter(status='Completed').aggregate(total=Sum('total_amount'))['total'] or 0
    pending_revenue = Order.objects.filter(status__in=['Pending', 'Shipping']).aggregate(total=Sum('total_amount'))['total'] or 0
    total_categories = Category.objects.count()
    total_brands = Brand.objects.count()
    low_stock_variants = ProductVariant.objects.filter(stock__lte=5).order_by('stock')[:8]
    recent_orders = Order.objects.order_by('-created_at')[:12]

    revenue_by_category = OrderItem.objects.filter(order__status='Completed') \
        .values('variant__product__category__name') \
        .annotate(total_sales=Sum(F('price') * F('quantity'))) \
        .order_by('-total_sales')
    chart_category_labels = [item['variant__product__category__name'] or "Khác" for item in revenue_by_category]
    chart_category_values = [round(float(item['total_sales']), 2) for item in revenue_by_category]

    revenue_by_brand = OrderItem.objects.filter(order__status='Completed') \
        .values('variant__product__brand__name') \
        .annotate(total_sales=Sum(F('price') * F('quantity'))) \
        .order_by('-total_sales')
    chart_brand_labels = [item['variant__product__brand__name'] or "Khác" for item in revenue_by_brand]
    chart_brand_values = [round(float(item['total_sales']), 2) for item in revenue_by_brand]

    revenue_by_month = Order.objects.filter(status='Completed') \
        .annotate(month=TruncMonth('created_at')) \
        .values('month') \
        .annotate(total=Sum('total_amount')) \
        .order_by('month')

    users_by_month = User.objects.annotate(month=TruncMonth('date_joined')) \
        .values('month') \
        .annotate(count=Count('id')) \
        .order_by('month')

    chart_revenue_labels = [item['month'].strftime("%m/%Y") for item in revenue_by_month]
    chart_revenue_values = [float(item['total']) for item in revenue_by_month]
    
    chart_user_labels = [item['month'].strftime("%m/%Y") for item in users_by_month]
    chart_user_values = [item['count'] for item in users_by_month]
    context = {
        'total_products': total_products,
        'total_variants': total_variants,
        'total_users': total_users,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'shipping_orders': shipping_orders,
        'completed_orders': completed_orders,
        'canceled_orders': canceled_orders,
        'completed_revenue': completed_revenue,
        'low_stock_variants': low_stock_variants,
        'total_categories': total_categories,
        'total_brands': total_brands,
        'recent_orders': recent_orders,
        'chart_revenue_labels': json.dumps(chart_revenue_labels),
        'chart_revenue_values': json.dumps(chart_revenue_values),
        'chart_category_labels': json.dumps(chart_category_labels),
        'chart_category_values': json.dumps(chart_category_values),
        'chart_brand_labels': json.dumps(chart_brand_labels),
        'chart_brand_values': json.dumps(chart_brand_values),
        'chart_user_labels': json.dumps(chart_user_labels),
        'chart_user_values': json.dumps(chart_user_values),
    }
    return render(request, 'store/admin_dashboard.html', context)


@login_required(login_url='login')
@user_passes_test(lambda u: u.is_staff, login_url='home')
def product_import_template(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mau-import-giay.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['name', 'price', 'description', 'brand', 'category', 'image_url', 'size', 'color', 'stock'])
    writer.writerow(['Nike Air Max 90', '2500000', 'Giày thể thao chính hãng', 'Nike', 'Sneaker', 'https://example.com/nike-air-max.jpg', '40', 'Trắng', '10'])
    writer.writerow(['Nike Air Max 90', '2500000', 'Giày thể thao chính hãng', 'Nike', 'Sneaker', 'https://example.com/nike-air-max.jpg', '41', 'Trắng', '8'])
    return response


@login_required(login_url='login')
@user_passes_test(lambda u: u.is_staff, login_url='home')
def admin_import_products(request):
    result = None
    errors = []
    if request.method == 'POST':
        upload = request.FILES.get('csv_file')
        if not upload:
            errors.append('Hãy chọn file CSV cần nhập.')
        elif upload.size > 5 * 1024 * 1024:
            errors.append('File CSV không được vượt quá 5 MB.')
        else:
            try:
                raw = upload.read()
                try:
                    decoded = raw.decode('utf-8-sig')
                except UnicodeDecodeError:
                    decoded = raw.decode('cp1258')
                reader = csv.DictReader(io.StringIO(decoded))
                required = {'name', 'price', 'brand', 'category', 'image_url', 'size', 'color', 'stock'}
                headers = {header.strip().lower() for header in (reader.fieldnames or []) if header}
                missing = sorted(required - headers)
                if missing:
                    errors.append('Thiếu cột bắt buộc: ' + ', '.join(missing))
                else:
                    rows = []
                    for line, row in enumerate(reader, start=2):
                        row = {str(k).strip().lower(): (v or '').strip() for k, v in row.items() if k}
                        if not any(row.values()):
                            continue
                        try:
                            name = row['name']
                            price = int(row['price'])
                            stock = int(row['stock'] or 0)
                            if not name or price < 0 or stock < 0:
                                raise ValueError('Tên phải có; giá và tồn kho không được âm.')
                            if row['image_url'] and not row['image_url'].startswith(('https://', 'http://')):
                                raise ValueError('image_url phải là link http:// hoặc https:// trực tiếp tới ảnh.')
                            if not row['category']:
                                raise ValueError('category không được để trống.')
                            rows.append((line, row, price, stock))
                        except (KeyError, ValueError) as exc:
                            errors.append(f'Dòng {line}: dữ liệu không hợp lệ ({exc}).')
                    if not errors and not rows:
                        errors.append('File không có dòng sản phẩm nào.')
                    if not errors:
                        created_products = set()
                        created_variants = 0
                        updated_variants = 0
                        try:
                            with transaction.atomic():
                                for line, row, price, stock in rows:
                                    name = row['name']
                                    brand = None
                                    if row['brand']:
                                        brand_slug = slugify(row['brand'])
                                        brand, _ = Brand.objects.get_or_create(slug=brand_slug, defaults={'name': row['brand']})
                                    category_slug = slugify(row['category'])
                                    category, _ = Category.objects.get_or_create(slug=category_slug, defaults={'name': row['category']})
                                    product_slug = slugify(name + ('-' + row['brand'] if row['brand'] else ''))
                                    product, was_created = Product.objects.get_or_create(
                                        slug=product_slug,
                                        defaults={'name': name, 'price': price, 'description': row.get('description', ''),
                                                  'brand': brand, 'category': category, 'image_url': row['image_url']},
                                    )
                                    if was_created:
                                        created_products.add(product.pk)
                                    else:
                                        product.name = name
                                        product.price = price
                                        product.description = row.get('description', '')
                                        product.brand = brand
                                        product.category = category
                                        product.image_url = row['image_url']
                                        product.save()
                                    if row['size']:
                                        variant, was_created = ProductVariant.objects.update_or_create(
                                            product=product, size=row['size'], color=row['color'],
                                            defaults={'stock': stock},
                                        )
                                        if was_created:
                                            created_variants += 1
                                        else:
                                            updated_variants += 1
                        except Exception as exc:
                            errors.append(f'Nhập thất bại và đã hoàn tác toàn bộ: {exc}')
                        else:
                            result = {
                                'products': len(created_products),
                                'variants_created': created_variants,
                                'variants_updated': updated_variants,
                            }
            except (UnicodeDecodeError, csv.Error) as exc:
                errors.append(f'Không đọc được CSV: {exc}')
    return render(request, 'store/admin_import_products.html', {'result': result, 'errors': errors})

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_staff, login_url='home')
def admin_add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm sản phẩm mới.')
            return redirect('admin_dashboard')
    else:
        form = ProductForm()
    return render(request, 'store/admin_product_form.html', {'form': form, 'title': 'Thêm sản phẩm mới'})

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_staff, login_url='home')
def admin_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật sản phẩm thành công.')
            return redirect('admin_dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'store/admin_product_form.html', {'form': form, 'title': 'Chỉnh sửa sản phẩm'})

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_staff, login_url='home')
def admin_update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật trạng thái đơn hàng #{order.id}.')
    return redirect('admin_dashboard')

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    variants = product.variants.all()
    
    # Chuẩn hóa màu/size để dữ liệu có khoảng trắng hoặc khác kiểu chữ
    # không làm mất liên kết giữa lựa chọn trên trang và tồn kho biến thể.
    def normalize_color(color):
        return (color or 'Mặc định').strip().upper()

    colors = list(dict.fromkeys(
        normalize_color(color)
        for color in product.variants.order_by('color').values_list('color', flat=True).distinct()
    ))
    if not colors:
        colors = ['Mặc định']

    sizes = list(dict.fromkeys(
        str(size).strip()
        for size in product.variants.order_by('size').values_list('size', flat=True).distinct()
    ))

    variant_data = {}
    for variant in variants:
        color = normalize_color(variant.color)
        size = str(variant.size).strip()
        variant_data.setdefault(color, {})[size] = {
            'id': variant.id,
            'stock': variant.stock,
            'url': reverse('add_to_cart', args=[variant.id]),
        }

    default_color = next(
        (color for color in colors if any(item['stock'] > 0 for item in variant_data.get(color, {}).values())),
        colors[0] if colors else None,
    )

    product_images = []
    if product.image:
        product_images.append(product.image.url)
        media_products_dir = os.path.join(settings.MEDIA_ROOT, 'products')
        if os.path.exists(media_products_dir):
            for filename in os.listdir(media_products_dir):
                if filename.startswith(f"{product.slug}_") and filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    product_images.append(f"/media/products/{filename}")
    
    context = {
        'product': product,
        'variants': variants,
        'has_stock': variants.filter(stock__gt=0).exists(),
        'colors': colors,
        'default_color': default_color,
        'sizes': sizes,
        # json_script trong template tự serialize object; không json.dumps ở đây,
        # nếu không phía trình duyệt sẽ nhận chuỗi JSON thay vì object dữ liệu.
        'variant_data': variant_data,
        'product_images': product_images,
    }
    return render(request, 'store/product_detail.html', context)

@login_required(login_url='login') 
def add_to_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    if variant.stock <= 0:
        message = f'Sản phẩm {variant.product.name} size {variant.size} đã hết hàng!'
        if is_ajax:
            return JsonResponse({'ok': False, 'message': message}, status=409)
        messages.error(request, message)
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart, variant=variant, defaults={'product': variant.product},
    )
    
    if not item_created:
        if cart_item.quantity + 1 > variant.stock:
            message = f'Kho chỉ còn {variant.stock} sản phẩm cho size {variant.size}.'
            if is_ajax:
                return JsonResponse({'ok': False, 'message': message}, status=409)
            messages.warning(request, message)
        else:
            cart_item.quantity += 1
            cart_item.save()
            message = f'Đã thêm {variant.product.name} · size {variant.size} vào giỏ.'
            if not is_ajax:
                messages.success(request, 'Đã cập nhật số lượng!')
    else:
        cart_item.quantity = 1
        cart_item.save()
        message = f'Đã thêm {variant.product.name} · size {variant.size} vào giỏ.'
        if not is_ajax:
            messages.success(request, message)
    if is_ajax:
        return JsonResponse({'ok': True, 'message': message})
    if request.GET.get('next') == 'checkout':
        return redirect('checkout')

    url_truoc_do = request.META.get('HTTP_REFERER')
    return redirect(url_truoc_do if url_truoc_do else 'home')

@login_required(login_url='login')
def add_product_to_cart(request, product_id):
    """Add a product before the customer chooses its size and color."""
    product = get_object_or_404(Product, id=product_id)
    if not product.variants.filter(stock__gt=0).exists():
        message = f'{product.name} hiện đã hết hàng.'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': message}, status=409)
        messages.error(request, message)
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, variant=None,
    )
    if not created:
        item.quantity += 1
        item.save(update_fields=['quantity'])
    message = f'Đã thêm {product.name} vào giỏ. Chọn màu và size trong giỏ hàng.'
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'message': message})
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required(login_url='login')
def increase_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if cart_item.variant_id and cart_item.quantity + 1 > cart_item.variant.stock:
        messages.warning(request, "Vượt quá số lượng trong kho!")
    else:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('cart_detail')

@login_required(login_url='login')
def decrease_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart_detail')

@login_required(login_url='login')
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Đã xóa khỏi giỏ hàng!')
    return redirect('cart_detail')

@login_required(login_url='login')
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = list(cart.items.select_related('product', 'variant').all())
    for item in items:
        item.available_variants = item.product.variants.filter(stock__gt=0).order_by('color', 'size')
        item.selected_color = (item.variant.color or '__default__') if item.variant_id else ''
        item.color_options = []
        seen_colors = set()
        for variant in item.available_variants:
            color_value = variant.color or '__default__'
            if color_value not in seen_colors:
                seen_colors.add(color_value)
                item.color_options.append({'value': color_value, 'label': color_value or 'Mặc định'})
    has_unselected = any(item.variant_id is None for item in items)
    total_cart_price = sum(item.total_price for item in items)
    cart_count = sum(item.quantity for item in items)
    context = {
        'items': items,
        'total_cart_price': total_cart_price,
        'cart_count': cart_count,
        'has_unselected': has_unselected,
    }
    return render(request, 'store/cart.html', context)

@login_required(login_url='login')
def select_cart_variant(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method != 'POST':
        return redirect('cart_detail')
    selected_color = request.POST.get('color')
    variant = get_object_or_404(
        ProductVariant,
        product=item.product,
        color=None if selected_color == '__default__' else selected_color,
        size=request.POST.get('size'),
        stock__gt=0,
    )
    if variant.stock < item.quantity:
        messages.error(request, f'Size {variant.size} · {variant.color or "Mặc định"} hiện không đủ tồn kho.')
        return redirect('cart_detail')

    duplicate = CartItem.objects.filter(cart=item.cart, variant=variant).exclude(id=item.id).first()
    if duplicate:
        if duplicate.quantity + item.quantity > variant.stock:
            messages.error(request, f'Size {variant.size} · {variant.color or "Mặc định"} hiện không đủ tồn kho.')
            return redirect('cart_detail')
        duplicate.quantity += item.quantity
        duplicate.save(update_fields=['quantity'])
        item.delete()
    else:
        item.variant = variant
        item.save(update_fields=['variant'])
    messages.success(request, f'Đã chọn size {variant.size} · {variant.color or "Mặc định"} cho {item.product.name}.')
    return redirect('cart_detail')

@login_required(login_url='login')
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.select_related('product', 'variant')
    if cart_items.filter(variant__isnull=True).exists():
        messages.error(request, 'Vui lòng chọn màu và size cho các sản phẩm trong giỏ trước khi đặt hàng.')
        return redirect('cart_detail')
    
    if request.method == 'POST':
        if not cart_items.exists():
            return redirect('cart_detail')
            
        for item in cart_items:
            if item.quantity > item.variant.stock:
                messages.error(request, f"Sản phẩm {item.variant} không đủ hàng!")
                return redirect('cart_detail')

        order = Order.objects.create(
            user=request.user,
            customer_name=request.POST.get('customer_name'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address'),
            total_amount=sum(i.total_price for i in cart_items),
            status='Pending'
        )
        
        for item in cart_items:
            OrderItem.objects.create(
                order=order, variant=item.variant,
                price=item.variant.product.price, quantity=item.quantity
            )
            v = item.variant
            v.stock -= item.quantity
            v.save()
            
        cart_items.delete()
        return render(request, 'store/checkout.html', {'order_completed': True, 'order': order})

    profile = Profile.objects.filter(user=request.user).first()
    context = {'cart_items': cart_items, 'total_amount': sum(i.total_price for i in cart_items), 'profile': profile}
    return render(request, 'store/checkout.html', context)

@login_required(login_url='login')
def order_history(request):
    orders = Order.objects.filter(user=request.user).annotate(item_count=Count('order_items')).order_by('-created_at')
    status_counts = {
        status: orders.filter(status=status).count()
        for status, _label in Order.STATUS_CHOICES
    }
    return render(request, 'store/order_history.html', {
        'orders': orders,
        'status_counts': status_counts,
        'total_order_count': orders.count(),
    })

@login_required(login_url='login')
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'Pending':
        order.status = 'Canceled'
        order.save()
        for item in order.order_items.all():
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()
        messages.success(request, 'Đã hủy đơn hàng thành công!')
    return redirect('order_history')

@login_required(login_url='login')
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save(); profile_form.save()
            messages.success(request, 'Cập nhật thành công!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    return render(request, 'store/profile.html', {'user_form': user_form, 'profile_form': profile_form})

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST) 
        if form.is_valid():
            form.save()
            messages.success(request, 'Đăng ký thành công!')
            return redirect('login')
    else: form = RegistrationForm()
    return render(request, 'store/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username'); p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user: login(request, user); return redirect('home')
        messages.error(request, 'Sai tài khoản hoặc mật khẩu')
    return render(request, 'store/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def menu_categories(request):
    return {'categories': Category.objects.all()}

@login_required(login_url='login')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    order_items = OrderItem.objects.filter(order=order).select_related('variant__product')
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'store/order_detail.html', context)
