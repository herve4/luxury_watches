from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import capture_lead, landing_page, product_detail_page, add_review, add_comment, voir_product, contact_view, about_view, faq_view, toggle_favorite, terms_view, privacy_view, register_view
from .views_orders import OrderCreateView, OrderDetailView, OrderListView, OrderSuccessView
from .views_products import ProductListView, product_detail, products_by_category
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Pages principales
    path('', landing_page, name='index'),
    path('contact/', contact_view, name='contact'),
    path('a-propos/', about_view, name='about'),
    path('faq/', faq_view, name='faq'),
    
    # Produits
    path('boutique/', ProductListView.as_view(), name='product_list'),
    path('boutique/categorie/<slug:slug>/', products_by_category, name='products_by_category'),
    path('boutique/sous-categorie/<slug:category_slug>/<slug:subcategory_slug>/', 
         ProductListView.as_view(), name='product_list_by_subcategory'),
    path('produit/<slug:slug>/', product_detail_page, name='product_detail'),
    
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
    
    # Favoris
    path('products/<int:product_id>/toggle-favorite/', toggle_favorite, name='toggle_favorite'),
    
    # Authentification
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('register/', register_view, name='register'),
    
    # Pages légales
    path('conditions-utilisation/', terms_view, name='terms'),
    path('confidentialite/', privacy_view, name='privacy'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
