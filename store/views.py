from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm # Form đăng ký có sẵn của Django
from .forms import RegistrationForm
from .models import Product, Category


# Trang chủ
def home(request):
    products = Product.objects.all() # Bắt tất cả sản phẩm
    categories = Category.objects.all() # Bắt tất cả thể loại
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
        form = RegistrationForm(request.POST) # Sử dụng RegistrationForm
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = RegistrationForm() # Sử dụng RegistrationForm
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