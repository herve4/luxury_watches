# admin_banner.py
from django.utils.html import format_html
from django.contrib import admin
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