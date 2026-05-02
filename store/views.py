from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Product, Category, Profile, Cart, CartItem, Order, OrderItem, Brand, ProductVariant
from .forms import RegistrationForm, UserUpdateForm, ProfileUpdateForm, ProductForm, OrderStatusForm
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
import json
import os
from django.conf import settings

def home(request, category_slug=None):
    products = Product.objects.all()
    categories = Category.objects.all()
    brands = Brand.objects.all() 

    cat_slug = category_slug or request.GET.get('category')
    brand_slug = request.GET.get('brand')

    selected_category = None
    selected_brand = None

    if cat_slug:
        selected_category = get_object_or_404(Category, slug=cat_slug)
        products = products.filter(category=selected_category)

    if brand_slug:
        selected_brand = get_object_or_404(Brand, slug=brand_slug)
        products = products.filter(brand=selected_brand)

    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(category__name__icontains=query) |
            Q(brand__name__icontains=query)
        ).distinct()
        
    context = {
        'products': products,
        'categories': categories,
        'brands': brands,
        'selected_category': selected_category,
        'selected_brand': selected_brand,
        # Trả về các slug hiện tại để Template có thể giữ lại trạng thái khi chuyển đổi
        'current_category_slug': cat_slug,
        'current_brand_slug': brand_slug,
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
    }
    return render(request, 'store/admin_dashboard.html', context)

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
    
    colors = [color for color in product.variants.order_by('color').values_list('color', flat=True).distinct() if color]
    if not colors:
        colors = ['Mặc định']

    sizes = list(product.variants.order_by('size').values_list('size', flat=True).distinct())

    variant_data = {}
    for variant in variants:
        color = variant.color or 'Mặc định'
        size = variant.size
        variant_data.setdefault(color, {})[size] = {
            'id': variant.id,
            'stock': variant.stock,
            'url': reverse('add_to_cart', args=[variant.id]),
        }

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
        'colors': colors,
        'sizes': sizes,
        'variant_data': json.dumps(variant_data, ensure_ascii=False),
        'product_images': product_images,
    }
    return render(request, 'store/product_detail.html', context)

@login_required(login_url='login') 
def add_to_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    if variant.stock <= 0:
        messages.error(request, f'Sản phẩm {variant.product.name} size {variant.size} đã hết hàng!')
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, variant=variant)
    
    if not item_created:
        if cart_item.quantity + 1 > variant.stock:
            messages.warning(request, f'Kho chỉ còn {variant.stock} sản phẩm cho lựa chọn này.')
        else:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f'Đã cập nhật số lượng!')
    else:
        cart_item.quantity = 1
        cart_item.save()
        messages.success(request, f'Đã thêm {variant.product.name} - Size {variant.size} vào giỏ!')
    if request.GET.get('next') == 'checkout':
        return redirect('checkout')

    url_truoc_do = request.META.get('HTTP_REFERER')
    return redirect(url_truoc_do if url_truoc_do else 'home')

@login_required(login_url='login')
def increase_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if cart_item.quantity + 1 > cart_item.variant.stock:
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
    items = cart.items.all()
    total_cart_price = sum(item.total_price for item in items)
    cart_count = sum(item.quantity for item in items)
    context = {'items': items, 'total_cart_price': total_cart_price, 'cart_count': cart_count}
    return render(request, 'store/cart.html', context)

@login_required(login_url='login')
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    
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
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_history.html', {'orders': orders})

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
        messages.success(request, 'Đã hủy đơn hàng và hoàn kho.')
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
    
    order_items = OrderItem.objects.filter(order=order)
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'store/order_detail.html', context)