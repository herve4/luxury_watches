from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Product
from .models_cart import Cart, CartItem

def get_cart(request):
    """
    Récupère le panier de l'utilisateur ou en crée un nouveau.
    Gère à la fois les utilisateurs connectés et les invités.
    """
    if request.user.is_authenticated:
        # Pour les utilisateurs connectés, on utilise leur panier
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # Pour les invités, on utilise le panier de session
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
    
    return cart

@require_POST
def add_to_cart(request, product_id):
    """Ajoute un produit au panier ou met à jour sa quantité."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    
    # Vérifier la disponibilité du stock
    if product.track_inventory and quantity > product.in_stock:
        messages.warning(request, f"Stock insuffisant. Il ne reste que {product.in_stock} pièce(s) disponible(s).")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f"Stock insuffisant. Il ne reste que {product.in_stock} pièce(s) disponible(s)."
            })
        return redirect('product_detail', slug=product.slug)
    
    # Ajouter au panier
    cart = get_cart(request)
    cart_item = cart.add_item(product, quantity)
    
    # Réponse pour les requêtes AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_total_items': cart.total_items,
            'message': 'Produit ajouté au panier avec succès!'
        })
    
    messages.success(request, 'Produit ajouté au panier avec succès!')
    return redirect('cart_detail')

@require_POST
def remove_from_cart(request, item_id):
    """Supprime un article du panier."""
    cart = get_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = cart_item.product.name
    cart_item.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_total_items': cart.total_items - 1,
            'message': f'"{product_name}" a été retiré de votre panier.'
        })
    
    messages.info(request, f'"{product_name}" a été retiré de votre panier.')
    return redirect('cart_detail')

@require_POST
def update_cart_item(request, item_id):
    """Met à jour la quantité d'un article dans le panier."""
    cart_item = get_object_or_404(CartItem, id=item_id, cart=get_cart(request))
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity < 1:
        return remove_from_cart(request, item_id)
    
    if cart_item.product.track_inventory and quantity > cart_item.product.in_stock:
        messages.warning(request, f"Stock insuffisant. Il ne reste que {cart_item.product.in_stock} pièce(s) disponible(s).")
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, 'Quantité mise à jour avec succès!')
    
    return redirect('cart_detail')

def cart_detail(request):
    """Affiche le détail du panier."""
    cart = get_cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})

@login_required
def checkout(request):
    """Affiche la page de paiement."""
    cart = get_cart(request)
    
    if cart.total_items == 0:
        messages.warning(request, 'Votre panier est vide.')
        return redirect('product_list')
    
    return render(request, 'cart/checkout.html', {'cart': cart})
