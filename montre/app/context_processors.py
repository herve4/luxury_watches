def cart_context(request):
    """Ajoute le contenu du panier au contexte global."""
    cart = {}
    cart_count = 0
    cart_total = 0
    
    if hasattr(request, 'user') and request.user.is_authenticated:
        # Si l'utilisateur est connecté, récupérez le panier depuis la base de données
        from .models import Order, CustomerLead
        
        try:
            # Récupérer le lead associé à l'utilisateur
            lead = CustomerLead.objects.get(email=request.user.email)
            
            # Récupérer les éléments du panier pour ce lead
            cart_items = Order.objects.filter(
                lead=lead,
                status='in_cart'
            )
            
            cart_count = cart_items.count()
            cart_total = sum(item.total_price for item in cart_items if item.total_price is not None)
            
            cart = {
                'items': cart_items,
                'count': cart_count,
                'total': cart_total
            }
        except CustomerLead.DoesNotExist:
            # Si aucun lead n'est trouvé pour cet utilisateur, le panier reste vide
            pass
    
    return {
        'cart': cart,
        'cart_count': cart_count,
        'cart_total': cart_total
    }
    
# from django.conf import settings

# def site_urls(request):
#     return {
#         'absolute_uri': request.build_absolute_uri('/')[:-1],  # Retire le slash final
#         'site_name': getattr(settings, 'SITE_NAME', 'Luxury Watches'),
#         'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
#     }
