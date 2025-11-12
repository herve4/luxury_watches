import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView
from django.http import JsonResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings
import os
from datetime import datetime
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
from django.contrib.auth import get_user_model, login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db import transaction

# Import des modèles
from .models import Category, Product
from .models_banner import VideoBanner
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.auth.mixins import UserPassesTestMixin
from rest_framework import viewsets, status, generics, permissions, filters
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
from django.contrib import messages
from .models import Product, ProductImage, Review, Comment
from .forms import ReviewForm, CommentForm, ContactForm
from .serializers import ProductSerializer, ProductDetailSerializer
from .models_banner import VideoBanner
from .models_favorite import Favorite
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

# Vue pour la page À propos
def about_view(request):
    """
    Affiche la page À propos avec des informations sur l'entreprise et l'équipe.
    """
    context = {
        'title': 'À propos - BoutiLuxe',
        'description': 'Découvrez l\'univers d\'exception de BoutiLuxe, où l\'art horloger rencontre l\'élégance intemporelle.',
    }
    return render(request, 'about.html', context)

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
        
        # Récupérer toutes les catégories actives
        categories = Category.objects.all()
        
        # Initialiser le contexte
        context = {
            'featured_products': featured_products,
            'categories': categories,
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

# Vue pour la page de contact
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from .forms import ContactForm
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Configuration Google Sheets
SHEET_ID = '1I66Cnc3qCSktYL3bpc5xZKquS8SqubAZfUvOkMvVm1E'
SHEET_NAME = 'contact boutiluxe'
COLUMNS = {
    'timestamp': 'Horodatage',
    'name': 'Nom',
    'email': 'Email',
    'subject': 'Sujet',
    'message': 'Message'
}

def faq_view(request):
    """
    Affiche la page FAQ avec les questions fréquemment posées.
    """
    faq_categories = [
        {
            'id': 'livraison',
            'title': 'Livraison',
            'icon': 'truck',
            'questions': [
                {
                    'question': 'Quels sont les délais de livraison ?',
                    'answer': 'Les commandes sont expédiées sous 24 à 48h ouvrées. Les délais de livraison varient selon la destination, généralement entre 2 et 5 jours ouvrés.'
                },
                {
                    'question': 'Quels sont les frais de livraison ?',
                    'answer': 'La livraison standard est offerte à partir de 200€ d\'achat. En dessous de ce montant, des frais de 9,90€ s\'appliquent.'
                },
                {
                    'question': 'Livrez-vous à l\'international ?',
                    'answer': 'Oui, nous livrons dans le monde entier. Les délais et frais de livraison varient en fonction de la destination.'
                }
            ]
        },
        {
            'id': 'paiement',
            'title': 'Paiement',
            'icon': 'credit-card',
            'questions': [
                {
                    'question': 'Quels moyens de paiement acceptez-vous ?',
                    'answer': 'Nous acceptons les cartes bancaires (Visa, Mastercard, American Express), PayPal et virements bancaires.'
                },
                {
                    'question': 'Le paiement est-il sécurisé ?',
                    'answer': 'Oui, tous les paiements sont cryptés et sécurisés grâce à notre partenaire de paiement certifié PCI-DSS.'
                },
                {
                    'question': 'Proposez-vous des facilités de paiement ?',
                    'answer': 'Oui, nous proposons le paiement en plusieurs fois sans frais à partir de 300€ d\'achat.'
                }
            ]
        },
        {
            'id': 'retours',
            'title': 'Retours & Échanges',
            'icon': 'exchange-alt',
            'questions': [
                {
                    'question': 'Quelle est votre politique de retour ?',
                    'answer': 'Vous disposez de 14 jours à compter de la réception de votre commande pour effectuer un retour. Les articles doivent être retournés dans leur état d\'origine, non portés et avec leur emballage d\'origine.'
                },
                {
                    'question': 'Comment effectuer un retour ?',
                    'answer': 'Connectez-vous à votre compte, allez dans la section "Mes commandes" et suivez la procédure de retour. Un bon de retour vous sera fourni à imprimer et à joindre à votre colis.'
                }
            ]
        },
        {
            'id': 'garantie',
            'title': 'Garantie',
            'icon': 'shield-alt',
            'questions': [
                {
                    'question': 'Quelle est la durée de la garantie ?',
                    'answer': 'Toutes nos montres bénéficient d\'une garantie constructeur de 2 ans couvrant les défauts de fabrication.'
                },
                {
                    'question': 'Que couvre la garantie ?',
                    'answer': 'La garantie couvre les défauts de matériaux et de fabrication. Elle ne couvre pas les dommages dus à une mauvaise utilisation, un choc ou un manque d\'entretien.'
                }
            ]
        }
    ]
    
    context = {
        'title': 'Foire aux questions',
        'description': 'Trouvez les réponses aux questions les plus fréquemment posées sur nos produits et services.',
        'faq_categories': faq_categories
    }
    return render(request, 'faq.html', context)

@require_http_methods(["POST"])
def toggle_favorite(request, product_id):
    """
    Ajoute ou supprime un produit des favoris de l'utilisateur.
    Gère à la fois les utilisateurs connectés (base de données) et non connectés (session).
    """
    try:
        # Vérification de la requête AJAX
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            logger.warning('Tentative d\'accès non-AJAX à toggle_favorite')
            return JsonResponse({'status': 'error', 'message': 'Requête invalide'}, status=400)

        # Récupération du produit
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            logger.error(f'Produit non trouvé avec l\'ID: {product_id}')
            return JsonResponse({'status': 'error', 'message': 'Produit non trouvé'}, status=404)
        
        # Initialisation de la réponse
        response_data = {'status': 'success'}
        
        if request.user.is_authenticated:
            # Gestion pour les utilisateurs connectés
            try:
                favorite, created = Favorite.objects.get_or_create(
                    user=request.user,
                    product=product
                )

                if not created:
                    favorite.delete()
                    response_data['is_favorite'] = False
                    logger.info(f'Produit {product_id} retiré des favoris de l\'utilisateur {request.user.id}')
                else:
                    response_data['is_favorite'] = True
                    logger.info(f'Produit {product_id} ajouté aux favoris de l\'utilisateur {request.user.id}')
                    
            except Exception as e:
                logger.error(f'Erreur lors de la gestion des favoris: {str(e)}')
                return JsonResponse({
                    'status': 'error',
                    'message': 'Une erreur est survenue lors de la mise à jour des favoris'
                }, status=500)
        else:
            # Gestion pour les utilisateurs non connectés (session)
            try:
                # Initialiser la liste des favoris si elle n'existe pas
                if 'favorites' not in request.session:
                    request.session['favorites'] = []
                
                favorites = request.session['favorites']
                product_id_str = str(product_id)
                
                # Vérifier si le produit est déjà dans les favoris
                if product_id_str in favorites:
                    favorites.remove(product_id_str)
                    response_data['is_favorite'] = False
                    logger.info(f'Produit {product_id} retiré des favoris de session')
                else:
                    favorites.append(product_id_str)
                    response_data['is_favorite'] = True
                    logger.info(f'Produit {product_id} ajouté aux favoris de session')
                
                # Sauvegarder explicitement la session
                request.session.modified = True
                
            except Exception as e:
                logger.error(f'Erreur lors de la gestion des favoris de session: {str(e)}')
                return JsonResponse({
                    'status': 'error',
                    'message': 'Erreur lors de la mise à jour des favoris de session'
                }, status=500)

        # Récupération du nombre total de likes (uniquement pour les utilisateurs connectés)
        try:
            response_data['likes_count'] = product.favorited_by.count()
        except Exception as e:
            logger.error(f'Erreur lors du comptage des favoris: {str(e)}')
            response_data['likes_count'] = 0

        return JsonResponse(response_data)

    except Exception as e:
        # Gestion des erreurs inattendues
        logger.exception('Erreur inattendue dans toggle_favorite')
        return JsonResponse({
            'status': 'error',
            'message': 'Une erreur inattendue est survenue'
        }, status=500)

def terms_view(request):
    """
    Affiche la page des conditions d'utilisation.
    """
    context = {
        'title': 'Conditions d\'utilisation',
        'last_updated': timezone.now(),
    }
    return render(request, 'legal/terms.html', context)

def privacy_view(request):
    """
    Affiche la page de politique de confidentialité.
    """
    return render(request, 'legal/privacy.html')

def register_view(request):
    """
    Vue pour l'inscription des utilisateurs.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Connecter automatiquement l'utilisateur après l'inscription
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Rediriger vers la page d'accueil ou la page précédente
                next_url = request.POST.get('next', '/')
                return redirect(next_url)
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Récupération des données du formulaire
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            # Construction du message
            email_message = f"""
            Nouveau message de contact depuis le site BoutiLuxe
            
            Nom: {name}
            Email: {email}
            
            Sujet: {subject}
            
            Message:
            {message}
            """
            
            try:
                # Envoi de l'email
                send_mail(
                    f"Nouveau message de contact: {subject}",
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,  # Utiliser l'email du serveur comme expéditeur
                    [settings.DEFAULT_FROM_EMAIL],  # À l'administrateur
                    fail_silently=False,
                )
                
                # Ajout des données dans Google Sheets
                try:
                    # Configuration de l'authentification
                    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                    creds = ServiceAccountCredentials.from_json_keyfile_name(settings.GOOGLE_SHEETS_CREDENTIALS, scope)
                    client = gspread.authorize(creds)
                    
                    # Ouverture de la feuille
                    sheet = client.open_by_key('1I66Cnc3qCSktYL3bpc5xZKquS8SqubAZfUvOkMvVm1E').worksheet('contact boutiluxe')
                    
                    # Préparation des données à ajouter
                    row = [
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Horodatage
                        name,
                        email,
                        subject,
                        message
                    ]
                    
                    # Ajout de la nouvelle ligne
                    sheet.append_row(row)
                    
                except Exception as e:
                    # En cas d'erreur avec Google Sheets, on continue car l'email a déjà été envoyé
                    logger.error(f"Erreur Google Sheets: {str(e)}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Votre message a été envoyé avec succès !',
                        'type': 'success'
                    }, status=200)
                    
                messages.success(request, 'Votre message a été envoyé avec succès !')
                return redirect('index')
                
            except Exception as e:
                logger.error(f"Erreur envoi email: {str(e)}")
                error_message = f"Une erreur est survenue lors de l'envoi du message. Veuillez réessayer plus tard."
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': error_message,
                        'type': 'error'
                    }, status=500)
                messages.error(request, error_message)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: [str(error) for error in error_list] for field, error_list in form.errors.items()}
                return JsonResponse({
                    'success': False,
                    'message': 'Veuillez corriger les erreurs dans le formulaire.',
                    'errors': errors,
                    'type': 'error'
                }, status=400)
    else:
        form = ContactForm()
    
    # Si c'est une requête AJAX mais qu'il y a eu une erreur, on renvoie une réponse JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'message': 'Méthode non autorisée ou erreur de requête.',
            'type': 'error'
        }, status=405)
        
    return render(request, 'contact.html', {'form': form})