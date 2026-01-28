from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import RegistrationForm
from .models import Product, Category


# Trang chủ
def home(request, category_slug=None):
    products = Product.objects.all()
    categories = Category.objects.all()
    # Nếu người dùng nhấn vào một danh mục cụ thể
    if category_slug:
        # Lấy danh mục dựa trên slug, nếu không có trả về lỗi 404
        category = get_object_or_404(Category, slug=category_slug)
        # Lọc sản phẩm thuộc danh mục đó
        products = products.filter(category=category)
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/home.html', {
        'products': products, 
        'categories': categories
    })

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