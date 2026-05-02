from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, Product, Order

class RegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'last_name', 'first_name', 'email'] 
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['last_name'].required = True
        self.fields['first_name'].required = True
        self.fields['email'].required = True
        
        self.fields['last_name'].label = "Họ"
        self.fields['first_name'].label = "Tên"
        self.fields['email'].label = "Địa chỉ Email"
        
        if 'username' in self.fields:
            self.fields['username'].label = "Tên đăng nhập"
            self.fields['username'].help_text = "Bắt buộc. 150 ký tự trở xuống. Chỉ chứa chữ cái, số và @/./+/-/_."
            
        if 'password1' in self.fields:
            self.fields['password1'].label = "Mật khẩu"
            self.fields['password1'].help_text = "Mật khẩu phải có ít nhất 8 ký tự, không được quá phổ biến hoặc quá giống tên đăng nhập."
            
        if 'password2' in self.fields:
            self.fields['password2'].label = "Xác nhận mật khẩu"
            self.fields['password2'].help_text = "Vui lòng nhập lại mật khẩu lần nữa để xác nhận."

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'email']
        labels = {
            'last_name': 'Họ',
            'first_name': 'Tên',
            'email': 'Địa chỉ Email',
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone', 'address']
        labels = {
            'phone': 'Số điện thoại',
            'address': 'Địa chỉ',
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'slug', 'price', 'description', 'brand', 'category', 'image']
        labels = {
            'name': 'Tên sản phẩm',
            'slug': 'Slug',
            'price': 'Giá',
            'description': 'Mô tả',
            'brand': 'Hãng',
            'category': 'Thể loại',
            'image': 'Hình ảnh',
        }


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        labels = {
            'status': 'Trạng thái đơn hàng',
        }
