import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, FormView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect, Http404, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_POST
from django.db import models
from django.db.models import Q, Count, Prefetch, Avg
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormMixin
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.auth.mixins import UserPassesTestMixin
from rest_framework import viewsets, status, generics, permissions, filters
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _
from .models import Product, ProductImage, Review, Comment
from .forms import ReviewForm, CommentForm
from .serializers import ProductSerializer, ProductDetailSerializer
from .models_banner import VideoBanner

logger = logging.getLogger(__name__)

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_featured', 'is_bestseller', 'is_new', 'is_active']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrage supplémentaire si nécessaire
        return queryset.filter(is_active=True).order_by('-created_at')


@require_http_methods(["POST"])
@csrf_exempt
def add_comment(request, review_id):
    """Ajoute un commentaire à un avis"""
    if request.method == 'POST':
        review = get_object_or_404(Review, id=review_id)
        form = CommentForm(request.POST)
        
        if form.is_valid() and request.user.is_authenticated:
            comment = form.save(commit=False)
            comment.review = review
            comment.user = request.user
            comment.save()
            
            # Retourner le rendu HTML du commentaire
            return render(request, 'components/comment_item.html', {
                'comment': comment
            })
        
        return JsonResponse({
            'success': False, 
            'errors': form.errors if form.errors else 'Veuillez vous connecter pour commenter'
        }, status=400)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)




def get_watch_image_url(product):
    """Génère l'URL de l'image basée sur la configuration"""
    # Si vous avez des images spécifiques pour chaque combinaison, vous pouvez les générer ici
    # Par exemple: f"{product.id}_{cadran}_{bracelet}_{finition}.jpg"
    # Pour l'instant, nous utilisons l'image de base du produit
    if product.images.exists():
        return product.images.first().image.url
    return ''

def product_detail_page(request, slug):
    """Vue pour afficher les détails d'un produit et gérer les avis"""
    try:
        product = get_object_or_404(Product, slug=slug, is_active=True)
        
        # Récupérer les images du produit
        images = product.images.all()
        
        # Récupérer les produits associés (limité à 4)
        related_products = product.related_products.filter(is_active=True)[:4]
        
        # Si pas assez de produits associés, compléter avec des produits de la même catégorie
        if related_products.count() < 4 and product.category:
            related_from_category = product.category.products.filter(
                is_active=True
            ).exclude(id=product.id).distinct()
            
            # Éviter les doublons
            existing_ids = [p.id for p in related_products]
            related_from_category = related_from_category.exclude(id__in=existing_ids)
            
            # Ajouter jusqu'à avoir 4 produits au total
            related_products = list(related_products) + list(related_from_category[:4 - related_products.count()])
        
        # Gestion du formulaire d'avis
        if request.method == 'POST':
            form = ReviewForm(request.POST, user=request.user)
            if form.is_valid():
                review = form.save(commit=False)
                review.product = product
                if request.user.is_authenticated:
                    review.user = request.user
                review.is_approved = False  # Les avis nécessitent une modération
                review.save()
                messages.success(request, _("Merci pour votre avis ! Il sera publié après modération."))
                return redirect('product_detail', slug=product.slug)
        else:
            form = ReviewForm(user=request.user)
        
        # Récupérer les avis approuvés
        reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
        
        # Calculer la note moyenne
        avg_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        
        context = {
            'product': product,
            'images': images,
            'related_products': related_products,
            'reviews': reviews,
            'review_form': form,
            'review_avg': avg_rating,
        }
        
        return render(request, 'products/product_detail_page.html', context)
        
    except Exception as e:
        # Log l'erreur pour le débogage
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur dans la vue product_detail: {str(e)}")
        
        # Afficher une page d'erreur générique
        return render(request, 'error.html', 
                     {'message': _("Une erreur est survenue lors du chargement du produit.")}, 
                     status=500)

@require_POST
def capture_lead(request):
    """Capture les leads depuis le formulaire de contact"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            name = data.get('name', '').split(' ', 1)
            first_name = name[0] if len(name) > 0 else ''
            last_name = name[1] if len(name) > 1 else ''
            
            if not email:
                return JsonResponse({'success': False, 'errors': {'email': 'Email is required'}}, status=400)
                
            # Ici, vous pourriez enregistrer le lead dans votre base de données
            # Par exemple :
            # lead = Lead.objects.create(
            #     email=email,
            #     first_name=first_name,
            #     last_name=last_name
            # )
            
            return JsonResponse({
                'success': True,
                'message': 'Merci pour votre intérêt ! Nous vous contacterons bientôt.'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'errors': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f'Error capturing lead: {str(e)}')
            return JsonResponse({'success': False, 'errors': 'Une erreur est survenue'}, status=500)
    
    return JsonResponse({'success': False, 'errors': 'Méthode non autorisée'}, status=405)


def add_review(request, product_slug):
    """Ajoute un avis pour un produit"""
    if request.method == 'POST':
        product = get_object_or_404(Product, slug=product_slug, is_active=True)
        
        # Vérifier si l'utilisateur connecté a déjà posté un avis pour ce produit
        if request.user.is_authenticated:
            if Review.objects.filter(product=product, user=request.user).exists():
                return JsonResponse({
                    'success': False,
                    'errors': {'__all__': 'Vous avez déjà posté un avis pour ce produit.'}
                }, status=400)
        
        form = ReviewForm(request.POST, user=request.user)
        
        if form.is_valid():
            with transaction.atomic():
                review = form.save(commit=False)
                review.product = product
                
                # Si l'utilisateur est connecté, on l'associe à l'avis
                if request.user.is_authenticated:
                    review.user = request.user
                
                # Marquer l'avis comme approuvé (ou non selon votre politique de modération)
                review.is_approved = True
                review.save()
                
                # Recharger l'objet pour s'assurer que toutes les relations sont chargées
                review.refresh_from_db()
                
                # Préparer la réponse avec le nouvel avis
                from django.template.loader import render_to_string
                
                context = {
                    'review': review,
                    'user': request.user if request.user.is_authenticated else None
                }
                
                # Rendre le template en supprimant les espaces inutiles
                review_html = render_to_string('components/review_item.html', context, request)
                # Nettoyer le HTML généré
                import re
                review_html = re.sub(r'>\s+<', '><', review_html)  # Supprimer les espaces entre les balises
                review_html = review_html.strip()  # Supprimer les espaces au début et à la fin
                
                return JsonResponse({
                    'success': True,
                    'message': 'Merci pour votre avis !',
                    'review': {
                        'id': review.id,
                        'first_name': review.first_name or '',
                        'last_name': review.last_name or '',
                        'rating': review.rating,
                        'rating_display': review.get_rating_display(),
                        'comment': review.comment,
                        'title': review.title or '',
                        'created_at': review.created_at.strftime('%d/%m/%Y %H:%M'),
                        'timestamp': int(review.created_at.timestamp())
                    },
                    'review_html': review_html
                })
        else:
            # Convertir les erreurs de formulaire en un format plus lisible
            from django.forms.utils import ErrorDict
            if isinstance(form.errors, ErrorDict):
                errors = {k: v[0] for k, v in form.errors.items()}
            else:
                errors = {'__all__': 'Une erreur est survenue lors de la validation du formulaire.'}
                
            return JsonResponse({
                'success': False, 
                'errors': errors
            }, status=400)
    
    return JsonResponse({'success': False, 'errors': 'Méthode non autorisée'}, status=405)



def landing_page(request):
    """Page d'accueil avec les produits en vedette et gestion des commandes"""
    try:
        order_started = request.GET.get('order_started') == 'true'
        product_id = request.GET.get('product_id')
        video_banner = VideoBanner.objects.filter(is_active=True).first()
        
        # Récupérer les produits en vedette
        featured_products = Product.objects.filter(is_featured=True)[:4]
        
        # Initialiser le contexte
        context = {
            'featured_products': featured_products,
            'show_order_modal': False,
            'product': None,
            'order_started': order_started,
            'video_banner': video_banner
        }
        
        # Si une commande est en cours et qu'un produit est spécifié
        if order_started and product_id:
            try:
                product = Product.objects.get(id=product_id)
                context.update({
                    'show_order_modal': True,
                    'product': product
                })
                # Ajouter un message de succès
                messages.success(request, 'Veuillez compléter votre commande')
            except Product.DoesNotExist:
                messages.error(request, 'Produit non trouvé')
        
        return render(request, 'index.html', context)
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la page d'accueil: {str(e)}")
        return render(
            request, 
            'error.html',
            {'message': 'Une erreur est survenue lors du chargement de la page d\'accueil'},
            status=500
        )
     
@require_http_methods(["POST"])
@csrf_exempt
def select_model(request, model_id):
    """Sélection d'un modèle produit"""
    product = get_object_or_404(Product, id=model_id)
    
    return JsonResponse({
        'status': 'success',
        'product_id': product.id,
        'product_name': product.name,
        'product_price': str(product.price),
        'product_image': product.image.url if product.image else ''
    })
    
def voir_product(request, product_id):
    """Voir un produit"""
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'components/voir_produit.html', {'product': product})
    