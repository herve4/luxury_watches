from django.urls import path
from .views import capture_lead, landing_page, product_detail, add_review, add_comment, voir_product
from .views_orders import OrderCreateView, OrderDetailView, OrderListView, OrderSuccessView
from .views_products import ProductListView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Pages principales
    path('', landing_page, name='index'),
    path('contact/', landing_page, name='contact'),  # À implémenter
    path('a-propos/', landing_page, name='about'),  # À implémenter
    
    # Produits
    path('boutique/', ProductListView.as_view(), name='product_list'),
    path('boutique/categorie/<slug:category_slug>/', 
         ProductListView.as_view(), name='product_list_by_category'),
    path('boutique/categorie/<slug:category_slug>/<slug:subcategory_slug>/', 
         ProductListView.as_view(), name='product_list_by_subcategory'),
    path('produit/<slug:slug>/', product_detail, name='product_detail'),
    
    # Panier et commandes
    path('panier/', landing_page, name='cart'),  # À implémenter
    path('voir-produit/<int:product_id>/', voir_product, name='voir_product'),
    path('commande/creer/<slug:product_slug>/', OrderCreateView.as_view(), name='order_create'),
    path('commande/<int:order_id>/', OrderDetailView.as_view(), name='order_detail'),
    path('mes-commandes/', OrderListView.as_view(), name='order_list'),
    path('commande/succes/', OrderSuccessView.as_view(), name='order_success'),
    
    # Capture de leads
    path('leads/', capture_lead, name='capture_lead'),
    
    # Avis
    path('produit/<slug:slug>/avis/', product_detail, name='product_review'),
    path('produit/<slug:product_slug>/ajouter-avis/', add_review, name='add_review'),
    
    # Commentaires
    path('api/reviews/<int:review_id>/comment/', add_comment, name='add_comment'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
