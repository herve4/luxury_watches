"""
Middleware pour gérer les fonctionnalités personnalisées de l'application.
"""
from django.http import HttpRequest
from .models import Order


class RecentOrdersMiddleware:
    """
    Middleware pour gérer les commandes récentes des utilisateurs non connectés.
    Stocke les ID des commandes récentes dans la session de l'utilisateur.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Code à exécuter pour chaque requête avant que la vue soit appelée
        response = self.get_response(request)
        
        # Si une commande a été créée lors de cette requête et que l'utilisateur n'est pas connecté
        if hasattr(request, 'order_created') and not request.user.is_authenticated:
            # Initialiser la liste des commandes récentes dans la session si elle n'existe pas
            if 'recent_orders' not in request.session:
                request.session['recent_orders'] = []
            
            # Ajouter l'ID de la commande à la liste des commandes récentes
            recent_orders = request.session['recent_orders']
            if request.order_created.id not in recent_orders:
                recent_orders.append(request.order_created.id)
                # Ne conserver que les 5 commandes les plus récentes
                request.session['recent_orders'] = recent_orders[-5:]
                request.session.modified = True
        
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Appelé juste avant que la vue ne soit appelée.
        """
        # Rien de particulier à faire ici pour l'instant
        return None

    def process_exception(self, request, exception):
        """
        Appelé quand une vue lève une exception.
        """
        # Loguer l'erreur ou effectuer d'autres actions si nécessaire
        return None

    def process_template_response(self, request, response):
        """
        Appelé juste après que la vue a été exécutée, si la réponse est un TemplateResponse.
        """
        return response
