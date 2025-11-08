from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.utils.translation import ngettext
from .models import (
    Product,
    Order, CustomerLead, ProductImage, Review, Comment,
    Category, SubCategory
)



class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_featured', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "Aucune image"


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    fields = ['get_user_display', 'rating_stars', 'title', 'comment', 'created_at']
    readonly_fields = ['get_user_display', 'rating_stars', 'title', 'comment', 'created_at']
    can_delete = False
    
    def get_user_display(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name()} <{obj.user.email}>" if obj.user.get_full_name() else obj.user.email
        return f"{obj.first_name} {obj.last_name} <{obj.email}>" if obj.first_name or obj.last_name else obj.email
    get_user_display.short_description = 'Utilisateur'
    
    def rating_stars(self, obj):
        return '★' * obj.rating + '☆' * (5 - obj.rating)
    rating_stars.short_description = 'Note'
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'in_stock', 'is_active', 'created_at', 'category', 'subcategory')
    list_filter = ('is_active', 'is_featured', 'category', 'subcategory')
    search_fields = ('name', 'description')
    list_editable = ('price', 'in_stock', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ReviewInline]
    filter_horizontal = ('related_products',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'price', 'in_stock', 'is_active', 'is_featured')
        }),
        ('Catégorisation', {
            'fields': ('category', 'subcategory', 'related_products'),
        }),
        ('Spécifications', {
            'fields': ('specifications', 'features'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Mettre à jour le cache des produits en vedette
        from django.core.cache import cache
        cache.delete('featured_products')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user_info', 'rating_stars', 'title', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('product__name', 'user__email', 'title', 'comment', 'email', 'first_name', 'last_name')
    list_editable = ('is_approved',)
    readonly_fields = ('created_at', 'updated_at', 'user_info', 'first_name', 'last_name', 'email')
    actions = ['approve_reviews', 'disapprove_reviews']
    
    fieldsets = (
        (None, {
            'fields': ('product', 'user', 'is_approved')
        }),
        ('Avis', {
            'fields': ('title', 'comment', 'rating')
        }),
        ('Informations du commentateur', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_info(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name()} ({obj.user.email})"
        return f"{obj.first_name} {obj.last_name} ({obj.email})"
    user_info.short_description = 'Utilisateur'

    def rating_stars(self, obj):
        return '★' * obj.rating + '☆' * (5 - obj.rating)
    rating_stars.short_description = 'Note'
    rating_stars.admin_order_field = 'rating'

    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(
            request, 
            ngettext(
                '%d avis a été approuvé avec succès.',
                '%d avis ont été approuvés avec succès.',
                updated
            ) % updated,
            messages.SUCCESS
        )
    approve_reviews.short_description = "Approuver les avis sélectionnés"
    
    def disapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(
            request,
            ngettext(
                '%d avis a été désapprouvé avec succès.',
                '%d avis ont été désapprouvés avec succès.',
                updated
            ) % updated,
            messages.SUCCESS
        )
    disapprove_reviews.short_description = "Désapprouver les avis sélectionnés"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'product')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count', 'image_preview')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "Aucune image"
    image_preview.short_description = 'Aperçu'

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Nombre de produits'


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'product_count', 'slug')
    list_filter = ('category',)
    search_fields = ('name', 'category__name')
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Nombre de produits'


