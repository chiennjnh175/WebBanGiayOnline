from django.contrib import admin
from .models import Category, Product, Profile, OrderItem, Order

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    list_editable = ('slug', )
    prepopulated_fields = {'slug': ('name',)}

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'category', 'brand')
    list_editable = ('stock', 'price')
    list_filter = ('category', 'brand', 'stock')
    prepopulated_fields = {'slug': ('name',)}

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'address')
    list_editable = ('phone', 'address')
    search_fields = ('user__username', 'phone')

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'price', 'quantity']

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