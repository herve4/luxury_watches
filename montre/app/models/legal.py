from django.db import models
from django.urls import reverse
from django.utils.text import slugify

class LegalPage(models.Model):
    """
    Modèle pour gérer les pages légales (CGU, mentions légales, politique de confidentialité, etc.)
    """
    PAGE_TYPES = (
        ('terms', 'Conditions d\'utilisation'),
        ('privacy', 'Politique de confidentialité'),
    )
    
    title = models.CharField('Titre', max_length=200)
    slug = models.SlugField('Slug', max_length=200, unique=True, blank=True)
    page_type = models.CharField('Type de page', max_length=20, choices=PAGE_TYPES, unique=True)
    content = models.TextField('Contenu')
    last_updated = models.DateTimeField('Dernière mise à jour', auto_now=True)
    is_active = models.BooleanField('Actif', default=True)
    
    class Meta:
        verbose_name = 'Page légale'
        verbose_name_plural = 'Pages légales'
        ordering = ['title']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        if self.page_type == 'terms':
            return reverse('terms')
        return reverse('privacy')

# Signaux pour créer les pages par défaut
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def create_default_legal_pages(sender, **kwargs):
    if sender.name == 'app':
        from django.utils.translation import gettext_lazy as _
        
        # Création des pages par défaut si elles n'existent pas
        default_pages = [
            {
                'title': _("Conditions d'utilisation"),
                'page_type': 'terms',
                'content': _("""
                    <h2>Conditions d'utilisation</h2>
                    <p>Bienvenue sur notre plateforme. En accédant à ce site, vous acceptez d'être lié par ces conditions d'utilisation.</p>
                    
                    <h3>1. Utilisation du site</h3>
                    <p>Ce site est destiné à fournir des informations sur nos produits et services. Vous acceptez d'utiliser ce site uniquement à des fins légales et d'une manière qui ne porte pas atteinte aux droits des autres utilisateurs.</p>
                    
                    <h3>2. Propriété intellectuelle</h3>
                    <p>Tous les contenus présents sur ce site, y compris les textes, images, logos et marques, sont la propriété exclusive de notre entreprise ou de ses concédants de licence.</p>
                    
                    <h3>3. Modifications</h3>
                    <p>Nous nous réservons le droit de modifier ces conditions d'utilisation à tout moment. Les modifications prendront effet dès leur publication sur le site.</p>
                """).strip(),
            },
            {
                'title': _('Politique de confidentialité'),
                'page_type': 'privacy',
                'content': _("""
                    <h2>Politique de confidentialité</h2>
                    <p>Nous nous engageons à protéger votre vie privée. Cette politique explique comment nous collectons, utilisons et protégeons vos informations personnelles.</p>
                    
                    <h3>1. Collecte des informations</h3>
                    <p>Nous pouvons collecter des informations vous concernant lorsque vous utilisez notre site, notamment lorsque vous remplissez un formulaire ou passez une commande.</p>
                    
                    <h3>2. Utilisation des informations</h3>
                    <p>Les informations que nous recueillons peuvent être utilisées pour :</p>
                    <ul>
                        <li>Personnaliser votre expérience utilisateur</li>
                        <li>Améliorer notre site web</li>
                        <li>Traiter vos commandes</li>
                        <li>Vous envoyer des e-mails périodiques</li>
                    </ul>
                    
                    <h3>3. Protection des informations</h3>
                    <p>Nous mettons en œuvre une variété de mesures de sécurité pour préserver la sécurité de vos informations personnelles.</p>
                    
                    <h3>4. Cookies</h3>
                    <p>Notre site utilise des cookies pour améliorer l'expérience utilisateur. Vous pouvez configurer votre navigateur pour refuser tous les cookies ou pour vous avertir lorsqu'un cookie est envoyé.</p>
                """).strip(),
            },
        ]
        
        for page_data in default_pages:
            LegalPage.objects.get_or_create(
                page_type=page_data['page_type'],
                defaults={
                    'title': page_data['title'],
                    'content': page_data['content'],
                    'is_active': True
                }
            )
