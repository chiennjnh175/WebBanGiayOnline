from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify # Thêm import này để tự tạo slug

# 1. Danh mục sản phẩm
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

# 2. Sản phẩm
class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, null=True, blank=True) # THÊM DÒNG NÀY
    price = models.IntegerField(default=0)
    description = models.TextField(null=True, blank=True)
    brand = models.CharField(max_length=100)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

    # THÊM HÀM NÀY: Tự động tạo slug nếu để trống
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

# 3. Thông tin người dùng bổ sung
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.user.username