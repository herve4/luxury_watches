from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum, Avg
from django.http import HttpResponse
import csv
from .models import (
    Category, SubCategory, ProductImage, 
    CustomerLead, Order, Review, Comment
)
from .models_favorite import Favorite
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple



@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image', 'created_at', 'updated_at']
    list_filter = ['product', 'created_at']
    search_fields = ['product__name', 'product__slug']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            queryset |= self.model.objects.filter(
                Q(product__name__icontains=search_term) |
                Q(product__slug__icontains=search_term)
            )
        return queryset, use_distinct

@admin.register(CustomerLead)
class CustomerLeadAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'phone', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product_interest')
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            queryset |= self.model.objects.filter(
                Q(phone__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term)
            )
        return queryset, use_distinct

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'product', 
        'quantity', 
        'unit_price', 
        'total_price', 
        'status', 
        'created_at',
        'get_status_badge'
    ]
    
    list_filter = [
        'status', 
        'created_at',
        ('lead', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = [
        'id',
        'customer_email',
        'customer_phone',
        'customer_first_name',
        'customer_last_name',
        'lead__email',
        'lead__phone',
        'product__name',
        'shipping_address'
    ]
    
    readonly_fields = ('created_at', 'updated_at', 'total_price')
    
    list_per_page = 20
    date_hierarchy = 'created_at'
    list_select_related = ['product', 'lead']
    autocomplete_fields = ['product', 'lead']
    
    fieldsets = (
        ('Informations client', {
            'fields': (
                ('customer_first_name', 'customer_last_name'),
                ('customer_email', 'customer_phone'),
                
                'lead'
            )
        }),
        ('Détails de la commande', {
            'fields': (
                'product',
                'quantity',
                'unit_price',
                'total_price',
                'status',
            )
        }),
        ('Adresses', {
            'classes': ('collapse',),
            'fields': (
                'shipping_address',
                'billing_address'
            )
        }),
        ('Informations complémentaires', {
            'classes': ('collapse',),
            'fields': (
                'notes',
                'created_at',
                'updated_at'
            )
        }),
    )
    
    # Si vous avez une méthode get_readonly_fields, assurez-vous qu'elle retourne un tuple
    def get_readonly_fields(self, request, obj=None):
        # Retourne toujours un tuple, même si c'est vide
        return super().get_readonly_fields(request, obj) or ()
    
    @admin.display(description='Client')
    def get_customer_info(self, obj):
        if obj.lead:
            return f"{obj.lead.get_full_name()} (Utilisateur)"
        return f"{obj.customer_first_name} {obj.customer_last_name} ({obj.customer_email})"
    
    @admin.display(description='Informations client complètes')
    def get_customer_full_info(self, obj):
        if obj.lead:
            return f"""
                <strong>Utilisateur enregistré</strong><br>
                Email: {obj.lead.email}<br>
                Téléphone: {obj.lead.phone or 'Non renseigné'}<br>
                Date d'inscription: {obj.lead.date_joined.strftime('%d/%m/%Y')}
            """
        return f"""
            <strong>Client invité</strong><br>
            Email: {obj.customer_email}<br>
            Téléphone: {obj.customer_phone or 'Non renseigné'}<br>
            Nom complet: {obj.customer_first_name} {obj.customer_last_name}
        """
    get_customer_full_info.allow_tags = True
    
    @admin.display(description='Statut', ordering='status')
    def get_status_badge(self, obj):
        status_colors = {
            'pending': 'orange',
            'paid': 'blue',
            'shipped': 'purple',
            'delivered': 'green',
            'cancelled': 'red',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="padding: 5px 10px; border-radius: 10px; background: {}; color: white;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    # Actions
    @admin.action(description='Exporter les commandes sélectionnées (CSV)')
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="commandes_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Client', 'Email', 'Téléphone', 'Produit', 'Quantité', 
            'Prix unitaire', 'Prix total', 'Statut', 'Date de création'
        ])
        
        for order in queryset:
            writer.writerow([
                order.id,
                order.get_customer_info(),
                order.lead.email if order.lead else order.customer_email,
                order.lead.phone if order.lead else order.customer_phone,
                order.product.name,
                order.quantity,
                order.unit_price,
                order.total_price,
                order.get_status_display(),
                order.created_at.strftime('%d/%m/%Y %H:%M')
            ])
        
        return response
    
    # Actions de statut
    @admin.action(description='Marquer comme payées')
    def mark_as_paid(self, request, queryset):
        updated = queryset.exclude(status='cancelled').update(status='paid')
        self.message_user(request, f'{updated} commande(s) marquée(s) comme payée(s).')
    
    @admin.action(description='Marquer comme expédiées')
    def mark_as_shipped(self, request, queryset):
        updated = queryset.exclude(status='cancelled').update(status='shipped')
        self.message_user(request, f'{updated} commande(s) marquée(s) comme expédiée(s).')
    
    @admin.action(description='Marquer comme livrées')
    def mark_as_delivered(self, request, queryset):
        updated = queryset.exclude(status='cancelled').update(status='delivered')
        self.message_user(request, f'{updated} commande(s) marquée(s) comme livrée(s).')
    
    @admin.action(description='Marquer comme annulées')
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} commande(s) marquée(s) comme annulée(s).')
    
    actions = [
        export_as_csv,
        mark_as_paid,
        mark_as_shipped,
        mark_as_delivered,
        mark_as_cancelled
    ]
    
    # Amélioration des performances
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'lead')
    
    # Personnalisation du formulaire
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'unit_price' in form.base_fields:
            form.base_fields['unit_price'].widget.attrs['readonly'] = True
        if 'total_price' in form.base_fields:
            form.base_fields['total_price'].widget.attrs['readonly'] = True
        return form
    
    # Calcul automatique du prix total
    def save_model(self, request, obj, form, change):
        if not obj.unit_price and obj.product:
            obj.unit_price = obj.product.price
        if not obj.total_price:
            obj.total_price = obj.unit_price * obj.quantity
        super().save_model(request, obj, form, change)
        
        
# Filtres personnalisés
class FeaturedFilter(admin.SimpleListFilter):
    title = 'Produit en vedette'
    parameter_name = 'is_featured'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'En vedette'),
            ('no', 'Non vedette'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(is_featured=True)
        if self.value() == 'no':
            return queryset.filter(is_featured=False)

class ContactedFilter(admin.SimpleListFilter):
    title = 'Lead contacté'
    parameter_name = 'contacted'

    def lookups(self, request, model_admin):
        return (
            ('contacted', 'Contactés'),
            ('not_contacted', 'Non contactés'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'contacted':
            return queryset.filter(contacted=True)
        if self.value() == 'not_contacted':
            return queryset.filter(contacted=False)

# Inlines
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_featured', 'image_preview']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.image.url)
        return "Aucune image"
    image_preview.short_description = "Aperçu"


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    fields = ['get_user_display', 'rating_stars', 'title', 'comment', 'created_at']
    readonly_fields = ['get_user_display', 'rating_stars', 'title', 'comment', 'created_at']
    can_delete = False
    
    def get_user_display(self, obj):
        if obj.user:
            return f"{obj.user.get_full_name()} <{obj.user.email}>" if obj.user.get_full_name() else obj.user.email
        return "Anonyme"
    get_user_display.short_description = 'Utilisateur'
    get_user_display.admin_order_field = 'user__email'
    
    def rating_stars(self, obj):
        return '★' * obj.rating + '☆' * (5 - obj.rating)
    rating_stars.short_description = 'Note'
    
    def has_add_permission(self, request, obj):
        return False
    


# Actions personnalisées
@admin.action(description="Marquer comme vedette")
def make_featured(modeladmin, request, queryset):
    queryset.update(is_featured=True)

@admin.action(description="Retirer des vedettes")
def remove_featured(modeladmin, request, queryset):
    queryset.update(is_featured=False)

@admin.action(description="Marquer comme contacté")
def mark_contacted(modeladmin, request, queryset):
    queryset.update(contacted=True)

@admin.action(description="Exporter les leads sélectionnés (CSV)")
def export_leads(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leads_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Email', 'Téléphone', 'Produit d\'intérêt', 'Contacté', 'Date de création'])
    
    for lead in queryset:
        product_name = lead.product_interest.name if lead.product_interest else "Non spécifié"
        contacted = "Oui" if lead.contacted else "Non"
        writer.writerow([
            lead.email,
            lead.phone or "",
            product_name,
            contacted,
            lead.created_at.strftime("%d/%m/%Y %H:%M")
        ])
    
    return response

@admin.action(description="Recalculer les prix des configurations")
def recalculate_prices(modeladmin, request, queryset):
    for config in queryset:
        config.calculate_price()
        config.save()
    modeladmin.message_user(
        request, 
        f"Prix recalculés pour {queryset.count()} configuration(s)"
    )

@admin.action(description="Exporter les configurations (CSV)")
def export_configurations(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="configurations_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Produit', 'Cadran', 'Bracelet', 'Finition', 'Prix Total', 'Date de création'])
    
    for config in queryset:
        writer.writerow([
            config.product.name,
            config.get_cadran_display(),
            config.get_bracelet_display(),
            config.get_finition_display(),
            f"{config.prix_total:,.0f} FCFA".replace(",", " "),  # Format avec espace comme séparateur de milliers
            config.created_at.strftime("%d/%m/%Y %H:%M")
        ])
    
    return response

@admin.action(description="Exporter les commandes (CSV)")
def export_orders(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="commandes_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Email Lead', 'Produit', 'Prix Total', 'Date de commande'])
    
    for order in queryset:
        writer.writerow([
            order.id,
            order.lead.email,
            order.product.name,
            f"{order.total_price:,.0f} FCFA".replace(",", " "),  # Format avec espace comme séparateur de milliers
            order.created_at.strftime("%d/%m/%Y %H:%M")
        ])
    
    return response

from .models_banner import VideoBanner

@admin.register(VideoBanner)
class VideoBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'banner_type', 'preview_buttons', 'created_at')
    list_filter = ('is_active', 'banner_type', 'created_at')
    search_fields = ('title', 'subtitle')
    readonly_fields = ('created_at', 'updated_at', 'preview')
    fieldsets = (
        ('Contenu', {
            'fields': (
                'title',
                'subtitle',
                'is_active',
            )
        }),
        ('Boutons d\'action', {
            'fields': (
                ('button_1_text', 'button_1_url'),
                ('button_2_text', 'button_2_url'),
            )
        }),
        ('Affichage', {
            'fields': (
                'show_title',
                'show_subtitle',
                'show_buttons',
                'show_overlay',
                'overlay_opacity',
            )
        }),
        ('Source vidéo', {
            'fields': (
                'banner_type',
                'video_file',
                'video_url',
                'thumbnail',
                'preview'
            )
        }),
        ('Métadonnées', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def preview(self, obj):
        if obj.pk:
            return format_html(
                '<div style="margin-top: 20px; padding: 10px; background: #f8f9fa; border-radius: 5px;">'
                '<h4>Aperçu de la bannière :</h4>'
                '<div style="margin-top: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background: white;">'
                f'<p><strong>Titre :</strong> {obj.title}</p>'
                f'<p><strong>Sous-titre :</strong> {obj.subtitle or "Non défini"}</p>'
                f'<p><strong>Bouton 1 :</strong> {obj.button_1_text or "Non défini"}</p>'
                f'<p><strong>Bouton 2 :</strong> {obj.button_2_text or "Non défini"}</p>'
                '</div>'
                '</div>'
            )
        return "Enregistrez pour voir un aperçu"
    preview.short_description = "Aperçu"

    def preview_buttons(self, obj):
        return format_html(
            '<div style="display: flex; gap: 5px;">'
            f'<span class="button" style="background: {"#4CAF50" if obj.show_title else "#f44336"}" title="Titre">T</span>'
            f'<span class="button" style="background: {"#4CAF50" if obj.show_subtitle else "#f44336"}" title="Sous-titre">ST</span>'
            f'<span class="button" style="background: {"#4CAF50" if obj.show_buttons else "#f44336"}" title="Boutons">B</span>'
            f'<span class="button" style="background: {"#4CAF50" if obj.show_overlay else "#f44336"}" title="Overlay">O</span>'
            '</div>'
        )
    preview_buttons.short_description = "Éléments actifs"

# Personnalisation du header de l'admin
@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name']
    list_select_related = ['user', 'product']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'product')

admin.site.site_header = "Tableau de bord - BoutiLuxe"
admin.site.index_title = "Tableau de bord BoutiLuxe"