from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import RegistrationForm
from .models import Product, Category, Profile, Cart, CartItem, Order, OrderItem
from .forms import UserUpdateForm, ProfileUpdateForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required 

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


@login_required(login_url='login')
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Thông tin của bạn đã được cập nhật thành công!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'store/profile.html', context)

def menu_categories(request):
    return {
        'categories': Category.objects.all()
    }

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST) 
        if form.is_valid():
            form.save()
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
        else:
            messages.error(request, 'Sai tài khoản hoặc mật khẩu')
    return render(request, 'store/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    
    context = {
        'product': product
    }
    return render(request, 'store/product_detail.html', context)

@login_required(login_url='login') 
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
        
    messages.success(request, f'Đã thêm {product.name} vào giỏ!')
    url_truoc_do = request.META.get('HTTP_REFERER')
    if url_truoc_do:
        return redirect(url_truoc_do)
    return redirect('home')

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
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'items': items,
        'total_cart_price': total_cart_price,
        'orders': orders,
    }
    return render(request, 'store/cart.html', context)

@login_required(login_url='login')
def increase_cart_item(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    # Tìm CartItem dựa trên Product ID thay vì CartItem ID
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    
    cart_item.quantity += 1
    cart_item.save()
    return redirect('cart_detail')

@login_required(login_url='login')
def decrease_cart_item(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    # Tìm CartItem dựa trên Product ID
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
        
    return redirect('cart_detail')


@login_required(login_url='login')
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    
    # Khởi tạo context mặc định với cờ order_completed = False
    context = {
        'order_completed': False
    }
    
    if request.method == 'POST':
        # Đề phòng trường hợp giỏ hàng trống mà vẫn gửi form
        if not cart_items.exists():
            messages.error(request, "Giỏ hàng của bạn đang trống!")
            return redirect('cart_detail')
            
        total_amount = sum(item.total_price for item in cart_items)
        
        customer_name = request.POST.get('customer_name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        # Bước 1: Tạo Đơn hàng mới (Order)
        order = Order.objects.create(
            user=request.user,
            customer_name=customer_name,
            phone=phone,
            address=address,
            total_amount=total_amount,
            status='Pending'
        )
        
        # Bước 2: Chuyển dữ liệu từ CartItem sang OrderItem
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.price, 
                quantity=item.quantity
            )
            
        # Bước 3: Xóa sạch giỏ hàng
        cart_items.delete()
        
        # Trả về chính trang checkout kèm theo thông báo thành công
        context['order_completed'] = True
        context['order'] = order
        return render(request, 'store/checkout.html', context)

    # --- Xử lý GET request (Hiển thị form thanh toán) ---
    # Nếu giỏ hàng trống thì đuổi về trang giỏ hàng
    if not cart_items.exists():
        messages.warning(request, "Giỏ hàng của bạn đang trống, hãy mua sắm thêm nhé!")
        return redirect('cart_detail')
        
    total_amount = sum(item.total_price for item in cart_items)
    profile = Profile.objects.filter(user=request.user).first()
    
    context.update({
        'cart_items': cart_items,
        'total_amount': total_amount,
        'profile': profile,
    })
    return render(request, 'store/checkout.html', context)

