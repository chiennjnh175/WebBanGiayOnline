from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Product, Category, Profile, Cart, CartItem, Order, OrderItem
from .forms import RegistrationForm, UserUpdateForm, ProfileUpdateForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required 

# --- TRANG CHỦ & DANH MỤC ---
def home(request, category_slug=None):
    products = Product.objects.all()
    categories = Category.objects.all()

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(category__name__icontains=query)
        )
        
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/home.html', context)

# --- CHI TIẾT SẢN PHẨM ---
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    context = {'product': product}
    return render(request, 'store/product_detail.html', context)

# --- GIỎ HÀNG (THÊM/XÓA/TĂNG/GIẢM) ---

@login_required(login_url='login') 
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # 1. Kiểm tra sản phẩm còn hàng không
    if product.stock <= 0:
        messages.error(request, f'Sản phẩm {product.name} đã hết hàng!')
        return redirect('home')

    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not item_created:
        # 2. Kiểm tra nếu tăng thêm có vượt quá kho không
        if cart_item.quantity + 1 > product.stock:
            messages.warning(request, f'Bạn đã có {cart_item.quantity} sản phẩm trong giỏ. Kho chỉ còn {product.stock} sản phẩm.')
        else:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f'Đã cập nhật số lượng {product.name}!')
    else:
        messages.success(request, f'Đã thêm {product.name} vào giỏ!')
        
    next_url = request.GET.get('next')
    if next_url == 'checkout':
        return redirect('checkout')
    
    url_truoc_do = request.META.get('HTTP_REFERER')
    return redirect(url_truoc_do if url_truoc_do else 'home')

@login_required(login_url='login')
def increase_cart_item(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    
    # 3. Kiểm tra kho trước khi tăng số lượng trong giỏ
    if cart_item.quantity + 1 > cart_item.product.stock:
        messages.warning(request, f"Không thể tăng thêm. Kho chỉ còn {cart_item.product.stock} sản phẩm.")
    else:
        cart_item.quantity += 1
        cart_item.save()
        
    return redirect('cart_detail')

@login_required(login_url='login')
def decrease_cart_item(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('cart_detail')

@login_required(login_url='login')
def remove_from_cart(request, item_id):
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'Đã xóa {product_name} khỏi giỏ hàng!')
    return redirect('cart_detail')

@login_required(login_url='login')
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all()
    total_cart_price = sum(item.total_price for item in items)
    cart_count = sum(item.quantity for item in items)
    
    context = {
        'items': items,
        'total_cart_price': total_cart_price,
        'cart_count': cart_count,
    }
    return render(request, 'store/cart.html', context)

# --- THANH TOÁN & ĐẶT HÀNG ---

@login_required(login_url='login')
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    
    if request.method == 'POST':
        if not cart_items.exists():
            messages.error(request, "Giỏ hàng trống!")
            return redirect('cart_detail')
            
        # 4. Kiểm tra kho lần cuối trước khi tạo đơn
        for item in cart_items:
            if item.quantity > item.product.stock:
                messages.error(request, f"Sản phẩm {item.product.name} vừa hết hàng hoặc không đủ số lượng trong kho!")
                return redirect('cart_detail')

        total_amount = sum(item.total_price for item in cart_items)
        
        # Tạo đơn hàng
        order = Order.objects.create(
            user=request.user,
            customer_name=request.POST.get('customer_name'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address'),
            total_amount=total_amount,
            status='Pending'
        )
        
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.price, 
                quantity=item.quantity
            )
            # 5. TRỪ KHO sau khi tạo OrderItem thành công
            product = item.product
            product.stock -= item.quantity
            product.save()
            
        cart_items.delete() # Xóa giỏ hàng sau khi đặt thành công
        
        return render(request, 'store/checkout.html', {'order_completed': True, 'order': order})

    # Logic cho phương thức GET
    if not cart_items.exists():
        messages.warning(request, "Giỏ hàng của bạn đang trống")
        return redirect('cart_detail')
        
    total_amount = sum(item.total_price for item in cart_items)
    profile = Profile.objects.filter(user=request.user).first()
    
    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'profile': profile,
    }
    return render(request, 'store/checkout.html', context)

# --- QUẢN LÝ ĐƠN HÀNG ---

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
        
        # 6. HOÀN KHO khi đơn hàng bị hủy
        for item in order.order_items.all():
            if item.product:
                item.product.stock += item.quantity
                item.product.save()

        messages.success(request, f'Đã hủy đơn hàng #{order.id} và hoàn lại số lượng vào kho!')
    else:
        messages.error(request, 'Chỉ có thể hủy đơn hàng đang ở trạng thái Chờ xử lý.')
        
    return redirect('order_history')

# --- USER & PROFILE ---

@login_required(login_url='login')
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
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
            messages.success(request, 'Đăng ký thành công! Hãy đăng nhập.')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'store/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('home')
        messages.error(request, 'Sai tài khoản hoặc mật khẩu')
    return render(request, 'store/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def menu_categories(request):
    return {'categories': Category.objects.all()}