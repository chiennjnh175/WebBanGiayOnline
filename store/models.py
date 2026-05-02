from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, null=True, blank=True)
    price = models.IntegerField(default=0)
    description = models.TextField(null=True, blank=True)
    
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=20, verbose_name="Kích cỡ")
    color = models.CharField(max_length=50, verbose_name="Màu sắc", null=True, blank=True)
    stock = models.PositiveIntegerField(default=10, verbose_name="Số lượng tồn kho")

    @property
    def is_available(self):
        return self.stock > 0

    def __str__(self):
        return f"{self.product.name} - Size: {self.size} - Màu: {self.color}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.user.username

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Giỏ hàng của {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.variant}"
    
    @property
    def total_price(self):
        return self.variant.product.price * self.quantity
    
class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Đang chờ xử lý'),
        ('Shipping', 'Đang giao hàng'),
        ('Completed', 'Đã hoàn thành'),
        ('Canceled', 'Đã hủy'),
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    total_amount = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Đơn hàng #{self.id} - {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    
    price = models.IntegerField(default=0) 
    quantity = models.IntegerField(default=1)

    def __str__(self):
        if self.variant:
            return f"{self.quantity} x {self.variant} (Đơn #{self.order.id})"
        return f"{self.quantity} x Sản phẩm đã bị xóa (Đơn #{self.order.id})"