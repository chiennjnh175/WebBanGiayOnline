from django.contrib import admin
from .models import Category, Product, ProductVariant, Profile, OrderItem, Order, Brand, Cart, CartItem

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

class BrandAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    list_editable = ('slug', )
    prepopulated_fields = {'slug': ('name',)}

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'brand')
    list_editable = ('price',)
    list_filter = ('category', 'brand')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'address')
    list_editable = ('phone', 'address')
    search_fields = ('user__username', 'phone')

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['variant', 'price', 'quantity']

class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'phone', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer_name', 'phone']
    list_editable = ['status'] 
    inlines = [OrderItemInline]

admin.site.register(Order, OrderAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(ProductVariant)
admin.site.register(Cart)
admin.site.register(CartItem)