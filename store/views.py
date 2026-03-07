from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import RegistrationForm
from .models import Product, Category, Profile
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



