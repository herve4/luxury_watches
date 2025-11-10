from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import DetailView, ListView
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from .models import Product, Category, Review
from django.db import models
from .forms import ReviewForm

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
        
        # Filtrage par statut (nouveautés, meilleures ventes, etc.)
        status = self.request.GET.get('status')
        if status == 'new':
            queryset = queryset.filter(is_new=True)
        elif status == 'bestseller':
            queryset = queryset.filter(is_bestseller=True)
        elif status == 'featured':
            queryset = queryset.filter(is_featured=True)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context
