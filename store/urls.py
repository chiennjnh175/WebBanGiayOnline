from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('profile/', views.profile_view, name='profile'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('category/<slug:category_slug>/', views.home, name='products_by_category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
]
