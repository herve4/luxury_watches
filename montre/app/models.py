from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
import os
from django.utils import timezone

def get_upload_path(instance, filename):
    """
    Définit le chemin de téléchargement pour les images d'options de produits.
    Format: options/{option_type_slug}/{filename}
    """
    if hasattr(instance, 'option_type'):
        option_type_slug = instance.option_type.slug
    else:
        option_type_slug = 'other'
    
    # S'assure que le nom du fichier est sécurisé
    base_filename, file_extension = os.path.splitext(filename)
    safe_filename = f"{slugify(base_filename)}{file_extension}"
    
    return os.path.join('options', option_type_slug, safe_filename)

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class SubCategory(models.Model):
    category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Sub Categories'
        unique_together = ('category', 'slug')
        ordering = ['name']

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Product(models.Model):
    # Informations de base
    name = models.CharField('Nom', max_length=200)
    slug = models.SlugField('Slug', unique=True, help_text="URL d'accès au produit")
    sku = models.CharField('Référence', max_length=50, unique=True, blank=True, null=True)
    
    # Description et détails
    short_description = models.TextField('Description courte', blank=True)
    description = models.TextField('Description détaillée')
    
    # Prix et réduction
    price = models.DecimalField('Prix de vente', max_digits=10, decimal_places=2)
    old_price = models.DecimalField('Ancien prix', max_digits=10, decimal_places=2, blank=True, null=True,
                                   help_text="Laissez vide si pas de réduction")
    cost_price = models.DecimalField('Prix de revient', max_digits=10, decimal_places=2, blank=True, null=True)
    tax_rate = models.DecimalField('Taux de TVA (%)', max_digits=5, decimal_places=2, default=20.0)
    
    # Catégorisation
    category = models.ForeignKey(Category, related_name='products', on_delete=models.SET_NULL, 
                               null=True, blank=True, verbose_name='Catégorie')
    subcategory = models.ForeignKey(SubCategory, related_name='products', on_delete=models.SET_NULL, 
                                  null=True, blank=True, verbose_name='Sous-catégorie')
    related_products = models.ManyToManyField('self', blank=True, verbose_name='Produits associés')
    
    # Statuts et visibilité
    is_featured = models.BooleanField('Mise en avant', default=False,
                                    help_text="Afficher en page d'accueil")
    is_bestseller = models.BooleanField('Meilleure vente', default=False)
    is_new = models.BooleanField('Nouveauté', default=False)
    is_active = models.BooleanField('Actif', default=True,
                                  help_text="Le produit est visible sur le site")
    
    # Gestion des stocks
    in_stock = models.PositiveIntegerField('Quantité en stock', default=1)
    low_stock_threshold = models.PositiveIntegerField('Seuil d\'alerte de stock', default=5)
    track_inventory = models.BooleanField('Gérer les stocks', default=True)
    
    # Métadonnées
    meta_title = models.CharField('Titre SEO', max_length=70, blank=True,
                                help_text="Titre pour les moteurs de recherche (max 70 caractères)")
    meta_description = models.TextField('Description SEO', blank=True, max_length=160,
                                      help_text="Description pour les moteurs de recherche (max 160 caractères)")
    
    # Données supplémentaires
    specifications = models.JSONField('Spécifications techniques', default=dict, blank=True)
    features = models.JSONField('Caractéristiques', default=list, blank=True)
    
    # Dates
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière mise à jour', auto_now=True)
    available_date = models.DateTimeField('Date de disponibilité', default=timezone.now,
                                        help_text="Date à partir de laquelle le produit est disponible à la vente")
    
    class Meta:
        verbose_name = 'Produit'
        verbose_name_plural = 'Produits'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug'], name='product_slug_idx'),
            models.Index(fields=['is_active'], name='product_active_idx'),
            models.Index(fields=['created_at'], name='product_created_idx'),
            models.Index(fields=['price'], name='product_price_idx'),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Générer un SKU s'il n'existe pas
        if not self.sku:
            prefix = 'PROD-'
            if self.category:
                prefix = f"{self.category.name[:3].upper()}-{self.subcategory.name[:3].upper() if self.subcategory else 'GEN'}-"
            last_product = Product.objects.order_by('-id').first()
            new_id = last_product.id + 1 if last_product else 1
            self.sku = f"{prefix}{new_id:04d}"
        
        # Mettre à jour les métadonnées SEO si vides
        if not self.meta_title:
            self.meta_title = self.name[:70]
        if not self.meta_description and self.short_description:
            self.meta_description = self.short_description[:160]
        
        super().save(*args, **kwargs)
    
    @property
    def has_discount(self):
        """Vérifie si le produit a une réduction"""
        return self.old_price is not None and self.old_price > self.price
    
    @property
    def discount_percentage(self):
        """Calcule le pourcentage de réduction"""
        if not self.has_discount:
            return 0
        return int(((self.old_price - self.price) / self.old_price) * 100)
    
    @property
    def price_with_tax(self):
        """Calcule le prix TTC"""
        return self.price * (1 + (self.tax_rate / 100))
    
    @property
    def main_image(self):
        """Retourne l'image principale du produit"""
        return self.images.filter(is_featured=True).first() or self.images.first()
    
    @property
    def average_rating(self):
        """Calcule la note moyenne des avis"""
        from django.db.models import Avg
        return self.reviews.aggregate(Avg('rating'))['rating__avg']
    
    @property
    def review_count(self):
        """Retourne le nombre d'avis"""
        return self.reviews.count()
    
    @property
    def in_stock_status(self):
        """Retourne le statut du stock"""
        if not self.track_inventory:
            return 'available'
        if self.in_stock <= 0:
            return 'out_of_stock'
        if self.in_stock <= self.low_stock_threshold:
            return 'low_stock'
        return 'in_stock'
    
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})
    
    def get_add_to_cart_url(self):
        return reverse('add_to_cart', kwargs={'slug': self.slug})
    
    def get_remove_from_cart_url(self):
        return reverse('remove_from_cart', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Montre"
        verbose_name_plural = "Montres"

    def __str__(self):
        return self.name
        
    @property
    def average_rating(self):
        """Retourne la note moyenne du produit"""
        from django.db.models import Avg
        return self.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        
    @property
    def review_count(self):
        """Retourne le nombre d'avis"""
        return self.reviews.count()
        
    def is_favorite(self, user):
        """Vérifie si le produit est dans les favoris de l'utilisateur"""
        if not user or not user.is_authenticated:
            return False
        return self.favorited_by.filter(user=user).exists()
        
    @property
    def likes_count(self):
        """Retourne le nombre total de favoris pour ce produit"""
        return self.favorited_by.count()
        
    def get_absolute_url(self):
        return f"/api/products/{self.id}/"


class CustomerLead(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField('Prénom', max_length=100, blank=True,null=True)
    last_name = models.CharField('Nom', max_length=100, blank=True,null=True)
    phone = models.CharField('Téléphone', max_length=20, blank=True,null=True)
    address = models.TextField('Adresse', blank=True,null=True)
    city = models.CharField('Ville', max_length=100, blank=True,null=True)
    postal_code = models.CharField('Code postal', max_length=20, blank=True,null=True)
    country = models.CharField('Pays', max_length=100, blank=True)
    product_interest = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière mise à jour', auto_now=True)
    contacted = models.BooleanField('Contacté', default=False)
    is_customer = models.BooleanField('Client', default=False)
    last_order_date = models.DateTimeField('Dernière commande', null=True, blank=True)
    total_orders = models.PositiveIntegerField('Nombre de commandes', default=0)
    total_spent = models.DecimalField('Montant total dépensé', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Lead client'
        verbose_name_plural = 'Leads clients'
        ordering = ['-created_at']

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return f"{name} ({self.email})" if name else self.email

    def update_customer_stats(self):
        """Met à jour les statistiques du client"""
        from django.db.models import Sum
        orders = self.orders.all()
        self.total_orders = orders.count()
        self.total_spent = orders.aggregate(total=Sum('total_price'))['total'] or 0
        if orders.exists():
            self.last_order_date = orders.latest('created_at').created_at
        self.is_customer = self.total_orders > 0
        self.save(update_fields=['total_orders', 'total_spent', 'last_order_date', 'is_customer'])

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True,blank=True,null=True)
    
    class Meta:
        ordering = ['is_featured', 'created_at']
    
    def __str__(self):
        return f"Image of {self.product.name}"

class Review(models.Model):
    RATING_CHOICES = (
        (1, '1 - Très mauvais'),
        (2, '2 - Mauvais'),
        (3, '3 - Moyen'),
        (4, '4 - Bon'),
        (5, '5 - Excellent'),
    )
    
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField('Prénom', max_length=100, blank=True)
    last_name = models.CharField('Nom', max_length=100, blank=True)
    email = models.EmailField('Email', blank=True)
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, verbose_name='Note')
    title = models.CharField('Titre', max_length=200)
    comment = models.TextField('Commentaire')
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière mise à jour', auto_now=True)
    is_approved = models.BooleanField('Approuvé', default=False)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')
        verbose_name = 'Avis'
        verbose_name_plural = 'Avis'
    
    def __str__(self):
        return f"{self.get_rating_display()} - {self.title}"
    
    def save(self, *args, **kwargs):
        # Si l'utilisateur est connecté, on récupère ses informations
        if self.user and not self.first_name and not self.last_name:
            self.first_name = self.user.first_name
            self.last_name = self.user.last_name
            self.email = self.user.email
        super().save(*args, **kwargs)

class Comment(models.Model):
    review = models.ForeignKey(Review, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.review}"


class LegalPage(models.Model):
    """
    Modèle pour gérer les pages légales (CGU, mentions légales, politique de confidentialité, etc.)
    """
    PAGE_TYPES = (
        ('terms', _('Conditions d\'utilisation')),
        ('privacy', _('Politique de confidentialité')),
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
@receiver(post_migrate)
def create_default_legal_pages(sender, **kwargs):
    if sender.name == 'app':
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

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('processing', 'En traitement'),
        ('shipped', 'Expédiée'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
    )
    
    # Rendre le lead optionnel pour permettre les commandes sans compte
    lead = models.ForeignKey(
        CustomerLead, 
        on_delete=models.SET_NULL, 
        related_name='orders',
        null=True,
        blank=True
    )
    
    # Champs pour les clients non connectés
    customer_email = models.EmailField('Email du client', null=True, blank=True)
    customer_first_name = models.CharField('Prénom', max_length=100, blank=True,null=True)
    customer_last_name = models.CharField('Nom', max_length=100, blank=True,null=True)
    customer_phone = models.CharField('Téléphone', max_length=20, blank=True,null=True)
    
    # Champs existants
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    quantity = models.PositiveIntegerField(default=1,blank=True,null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True)
    shipping_address = models.TextField('Adresse de livraison',blank=True,null=True)
    billing_address = models.TextField('Adresse de facturation', blank=True,null=True)
    notes = models.TextField('Notes', blank=True,null=True)
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière mise à jour', auto_now=True)
    ip_address = models.GenericIPAddressField('Adresse IP', null=True, blank=True)
    user_agent = models.TextField('User Agent', blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Commande'
        verbose_name_plural = 'Commandes'

    def __str__(self):
        if self.lead:
            return f"Commande #{self.id} - {self.lead.email}"
        return f"Commande #{self.id} - {self.customer_email}"

    def save(self, *args, **kwargs):
        if not self.unit_price and self.product:
            self.unit_price = self.product.price
        if not self.total_price and self.unit_price:
            self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
        
    def get_customer_name(self):
        """Retourne le nom complet du client"""
        if self.lead:
            return f"{self.lead.first_name} {self.lead.last_name}".strip()
        return f"{self.customer_first_name} {self.customer_last_name}".strip()


    """Configuration d'une montre avec des options personnalisables"""
    
    # Référence au produit
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='configurations')
    

    
    # Informations supplémentaires
    created_at = models.DateTimeField('Date de création', auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField('Dernière mise à jour', auto_now=True,blank=True,null=True)
    
    class Meta:
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product}"

