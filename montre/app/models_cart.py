from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from .models import Product

class Cart(models.Model):
    """
    Modèle représentant le panier d'achat d'un utilisateur.
    Un panier est lié à une session ou à un utilisateur connecté.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart'
    )
    session_key = models.CharField(max_length=40, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Panier'
        verbose_name_plural = 'Paniers'
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.user:
            return f"Panier de {self.user.email}"
        return f"Panier (session: {self.session_key})"
    
    @property
    def total_items(self):
        """Retourne le nombre total d'articles dans le panier"""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def subtotal(self):
        """Calcule le sous-total du panier (sans les frais de livraison)"""
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total(self):
        """Calcule le total du panier (sous-total + frais de livraison)"""
        return self.subtotal + self.shipping_cost
    
    @property
    def shipping_cost(self):
        """Calcule les frais de livraison"""
        # Logique de calcul des frais de livraison à implémenter
        # Pour l'instant, retourne 0 ou un montant fixe
        return 0
    
    def add_item(self, product, quantity=1, update_quantity=False):
        """
        Ajoute un produit au panier ou met à jour sa quantité.
        """
        # Vérifier si le produit est déjà dans le panier
        cart_item, created = self.items.get_or_create(
            product=product,
            defaults={'quantity': 0}
        )
        
        if update_quantity:
            cart_item.quantity = quantity
        else:
            cart_item.quantity += quantity
        
        # Vérifier que la quantité ne dépasse pas le stock disponible
        if cart_item.quantity > product.in_stock and product.track_inventory:
            cart_item.quantity = product.in_stock
        
        cart_item.save()
        return cart_item
    
    def remove_item(self, product):
        """Supprime un produit du panier"""
        self.items.filter(product=product).delete()
    
    def clear(self):
        """Vide complètement le panier"""
        self.items.all().delete()
    
    def merge_cart(self, session_cart):
        """Fusionne le panier de session avec le panier utilisateur"""
        if session_cart and session_cart != self:
            for item in session_cart.items.all():
                self.add_item(item.product, item.quantity)
            session_cart.delete()


class CartItem(models.Model):
    """
    Modèle représentant un article dans le panier.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Panier'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='Produit'
    )
    quantity = models.PositiveIntegerField(
        'Quantité',
        default=1,
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        'Prix unitaire',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    created_at = models.DateTimeField('Date d\'ajout', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière mise à jour', auto_now=True)
    
    class Meta:
        verbose_name = 'Article du panier'
        verbose_name_plural = 'Articles du panier'
        unique_together = ('cart', 'product')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    def save(self, *args, **kwargs):
        # Mettre à jour le prix à chaque sauvegarde
        self.price = self.product.price
        super().save(*args, **kwargs)
    
    @property
    def total_price(self):
        """Calcule le prix total pour cette ligne (prix unitaire * quantité)"""
        return self.price * self.quantity
    
    @property
    def has_stock(self):
        """Vérifie si la quantité demandée est disponible en stock"""
        if not self.product.track_inventory:
            return True
        return self.quantity <= self.product.in_stock
    
    def increase_quantity(self, quantity=1):
        """Augmente la quantité de l'article"""
        self.quantity += quantity
        if self.product.track_inventory and self.quantity > self.product.in_stock:
            self.quantity = self.product.in_stock
        self.save()
    
    def decrease_quantity(self, quantity=1):
        """Diminue la quantité de l'article"""
        self.quantity = max(1, self.quantity - quantity)
        self.save()
