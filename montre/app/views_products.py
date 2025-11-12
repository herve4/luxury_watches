from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import DetailView, ListView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from .models import Product, Category, Review, SubCategory
from django.db import models
from .forms import ReviewForm
import logging

def product_detail(request, slug):
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
        avg_rating = reviews.aggregate(avg_rating=models.Avg('rating'))['avg_rating']
        
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

# Vue basée sur une classe pour la liste des produits
class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        
        # Récupérer les paramètres de requête
        query = self.request.GET.get('q')
        status = self.request.GET.get('status')
        price = self.request.GET.get('price')
        sort = self.request.GET.get('sort')
        
        # Filtrage par recherche
        if query:
            queryset = queryset.filter(
                models.Q(name__icontains=query) |
                models.Q(description__icontains=query) |
                models.Q(category__name__icontains=query)
            )
        
        # Filtrage par catégorie
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
        
        # Filtrage par sous-catégorie
        subcategory_slug = self.kwargs.get('subcategory_slug')
        if subcategory_slug:
            subcategory = get_object_or_404(SubCategory, slug=subcategory_slug)
            queryset = queryset.filter(subcategory=subcategory)
        
        # Filtrage par statut
        if status == 'new':
            queryset = queryset.filter(is_new=True)
        elif status == 'bestseller':
            queryset = queryset.filter(is_bestseller=True)
        elif status == 'featured':
            queryset = queryset.filter(is_featured=True)
        
        # Filtrage par prix
        if price:
            if price == '0-50000':
                queryset = queryset.filter(price__lte=50000)
            elif price == '50000-100000':
                queryset = queryset.filter(price__gte=50000, price__lte=100000)
            elif price == '100000-200000':
                queryset = queryset.filter(price__gte=100000, price__lte=200000)
            elif price == '200000-500000':
                queryset = queryset.filter(price__gte=200000, price__lte=500000)
            elif price == '500000-':
                queryset = queryset.filter(price__gte=500000)
        
        # Tri des résultats
        if sort == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort == 'popular':
            # Ici, vous pourriez trier par popularité si vous avez ce champ
            queryset = queryset.order_by('?')  # Tri aléatoire en attendant
        
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        
        # Ajouter les paramètres de recherche actuels au contexte
        context['current_query'] = self.request.GET.get('q', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_price'] = self.request.GET.get('price', '')
        context['current_sort'] = self.request.GET.get('sort', '')
        
        # Ajouter les filtres actifs
        active_filters = []
        
        if self.request.GET.get('q'):
            active_filters.append({
                'name': 'recherche',
                'value': self.request.GET.get('q'),
                'url_param': 'q'
            })
            
        if self.request.GET.get('status'):
            status_display = {
                'new': 'Nouveautés',
                'bestseller': 'Meilleures ventes',
                'featured': 'En vedette'
            }
            active_filters.append({
                'name': 'statut',
                'value': status_display.get(self.request.GET.get('status'), self.request.GET.get('status')),
                'url_param': 'status'
            })
            
        if self.request.GET.get('price'):
            price_ranges = {
                '0-50000': 'Moins de 50 000 FCFA',
                '50000-100000': '50 000 - 100 000 FCFA',
                '100000-200000': '100 000 - 200 000 FCFA',
                '200000-500000': '200 000 - 500 000 FCFA',
                '500000-': 'Plus de 500 000 FCFA'
            }
            active_filters.append({
                'name': 'prix',
                'value': price_ranges.get(self.request.GET.get('price'), self.request.GET.get('price')),
                'url_param': 'price'
            })
        
        context['active_filters'] = active_filters
        
        return context
    
    def get(self, request, *args, **kwargs):
        """
        Surcharge de la méthode get pour gérer les requêtes AJAX
        """
        # Appel à la méthode parente pour obtenir le contexte
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        
        # Si c'est une requête AJAX, on ne renvoie que le HTML des produits
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(request, 'products/partials/product_list.html', {
                'products': context['page_obj'],
                'is_paginated': context['is_paginated'],
                'page_obj': context['page_obj'],
                'paginator': context['paginator'],
                'categories': context.get('categories', []),  # Ajout des catégories au contexte
                'category': context.get('category'),  # Ajout de la catégorie actuelle si elle existe
                'current_query': context.get('current_query', ''),
                'current_status': context.get('current_status', ''),
                'current_price': context.get('current_price', ''),
                'current_sort': context.get('current_sort', '')
            })
            
        # Sinon, on renvoie le template complet
        return self.render_to_response(context)

def products_by_category(request, slug):
    """Affiche les produits d'une catégorie spécifique"""
    try:
        category = get_object_or_404(Category, slug=slug)
        products = Product.objects.filter(category=category, is_active=True)
        
        # Pagination
        paginator = Paginator(products, 12)  # 12 produits par page
        page = request.GET.get('page')
        
        try:
            products = paginator.page(page)
        except PageNotAnInteger:
            # Si le paramètre page n'est pas un entier, afficher la première page
            products = paginator.page(1)
        except EmptyPage:
            # Si la page est hors de portée, afficher la dernière page de résultats
            products = paginator.page(paginator.num_pages)
        
        context = {
            'category': category,
            'products': products,
            'title': f"{category.name} - BoutiLuxe",
            'description': category.description[:160] if category.description else f"Découvrez notre sélection de {category.name} - BoutiLuxe",
            'is_paginated': products.has_other_pages(),
            'page_obj': products  # Pour la pagination
        }
        
        # Utiliser le même template que la liste des produits
        return render(request, 'products/product_list.html', context)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur dans la vue products_by_category: {str(e)}", exc_info=True)
        return render(request, 'error.html', 
                     {'message': _("Une erreur est survenue lors du chargement de la catégorie.")}, 
                     status=500)
