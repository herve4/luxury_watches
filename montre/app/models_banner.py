# models_banner.py
from django.db import models
from django.core.validators import (
    URLValidator, 
    FileExtensionValidator, 
    MinValueValidator, 
    MaxValueValidator
)
from django.utils.translation import gettext_lazy as _

class VideoBanner(models.Model):
    class BannerType(models.TextChoices):
        UPLOAD = 'upload', _('Téléversement de vidéo')
        URL = 'url', _('Lien vidéo')

    # Informations générales
    title = models.CharField(_('titre principal'), max_length=200)
    subtitle = models.CharField(_('sous-titre'), max_length=300, blank=True)
    is_active = models.BooleanField(_('actif'), default=True)
    
    # Boutons
    button_1_text = models.CharField(_('texte du bouton 1'), max_length=50, blank=True)
    button_1_url = models.CharField(_('lien du bouton 1'), max_length=200, blank=True)
    button_2_text = models.CharField(_('texte du bouton 2'), max_length=50, blank=True)
    button_2_url = models.CharField(_('lien du bouton 2'), max_length=200, blank=True)
    
    # Contrôles d'affichage
    show_title = models.BooleanField(_('afficher le titre'), default=True)
    show_subtitle = models.BooleanField(_('afficher le sous-titre'), default=True)
    show_buttons = models.BooleanField(_('afficher les boutons'), default=True)
    show_overlay = models.BooleanField(_('afficher l\'overlay'), default=True)
    overlay_opacity = models.PositiveSmallIntegerField(
        _('opacité de l\'overlay (%)'), 
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Source vidéo
    banner_type = models.CharField(
        _('type de bannière'),
        max_length=10,
        choices=BannerType.choices,
        default=BannerType.UPLOAD
    )
    video_file = models.FileField(
        _('fichier vidéo'),
        upload_to='banners/videos/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'webm', 'ogg'])]
    )
    video_url = models.URLField(
        _('URL de la vidéo'),
        blank=True,
        null=True,
        validators=[URLValidator()]
    )
    
    # Médias
    thumbnail = models.ImageField(
        _('image de prévisualisation'),
        upload_to='banners/thumbnails/',
        null=True,
        blank=True
    )
    
    # Métadonnées
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    class Meta:
        verbose_name = _('bannière vidéo')
        verbose_name_plural = _('bannières vidéo')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Vérification des sources vidéo
        if not self.video_file and not self.video_url:
            raise ValidationError(_('Veuillez fournir soit un fichier vidéo, soit une URL de vidéo.'))
            
        if self.banner_type == self.BannerType.URL and self.video_file:
            raise ValidationError(_('Veuillez fournir uniquement une URL pour ce type de bannière.'))
            
        if self.banner_type == self.BannerType.UPLOAD and self.video_url:
            raise ValidationError(_('Veuillez fournir uniquement un fichier pour ce type de bannière.'))

    @property
    def video_source(self):
        """Retourne la source vidéo appropriée selon le type de bannière"""
        if self.banner_type == self.BannerType.UPLOAD and self.video_file:
            return self.video_file.url
        return self.video_url

    @property
    def overlay_style(self):
        """Retourne le style CSS pour l'overlay"""
        if not self.show_overlay:
            return 'display: none;'
        return f'opacity: {self.overlay_opacity / 100};'