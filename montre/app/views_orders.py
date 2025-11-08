from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, ListView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST, require_http_methods
from django.http import JsonResponse, HttpResponseRedirect
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import Product, Order, CustomerLead
from .forms import CheckoutForm


from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import HttpResponse

class OrderCreateView(CreateView):
    model = Order
    template_name = 'orders/order_create.html'
    form_class = CheckoutForm
    success_url = reverse_lazy('order_success')
    
    def get_context_data(self, **kwargs):
        """Ajoute le produit et d'autres données au contexte"""
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, slug=self.kwargs['product_slug'], is_active=True)
        context['product'] = product
        context['step'] = 2  # Étape de livraison
        
        return context
    
    def get_form_kwargs(self):
        """Ajoute le produit et la requête aux kwargs du formulaire"""
        kwargs = super().get_form_kwargs()
        product = get_object_or_404(Product, slug=self.kwargs['product_slug'], is_active=True)
        kwargs['product'] = product
        kwargs['request'] = self.request
        return kwargs
    
    def get(self, request, *args, **kwargs):
        """Gère les requêtes GET"""
        product = get_object_or_404(Product, slug=kwargs['product_slug'], is_active=True)
        
        # Vérifier le stock
        if product.in_stock <= 0:
            messages.error(request, "Ce produit est actuellement en rupture de stock.")
            return redirect('product_detail', slug=product.slug)
        
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        """Gère les requêtes POST avec validation personnalisée"""
        self.object = None
        form = self.get_form()
        product = get_object_or_404(Product, slug=kwargs['product_slug'], is_active=True)
        
        # Validation manuelle pour les utilisateurs non authentifiés
        if not request.user.is_authenticated:
            if not self.validate_customer_data(request.POST):
                return self.form_invalid(form)
        
        # Validation de la quantité
        quantity = self.get_quantity_from_post(request.POST)
        if quantity > product.in_stock:
            messages.error(request, f"Stock insuffisant. Il ne reste que {product.in_stock} exemplaire(s).")
            return self.form_invalid(form)
        
        if form.is_valid():
            return self.form_valid(form, product, quantity)
        else:
            return self.form_invalid(form)
    
    def get_quantity_from_post(self, post_data):
        """Extrait et valide la quantité depuis les données POST"""
        try:
            quantity = int(post_data.get('quantity', 1))
            return max(1, quantity)  # Minimum 1
        except (ValueError, TypeError):
            return 1
    
    def validate_customer_data(self, post_data):
        """Valide les données client pour les utilisateurs non authentifiés"""
        required_fields = {
            'customer_first_name': 'Le prénom est obligatoire',
            'customer_last_name': 'Le nom est obligatoire', 
            'customer_email': 'L\'email est obligatoire',
            'customer_phone': 'Le téléphone est obligatoire'
        }
        
        has_errors = False
        
        for field, error_message in required_fields.items():
            if not post_data.get(field, '').strip():
                messages.error(self.request, error_message)
                has_errors = True
        
        # Validation de l'email
        email = post_data.get('customer_email', '').strip()
        if email and '@' not in email:
            messages.error(self.request, 'Veuillez entrer une adresse email valide.')
            has_errors = True
        
        return not has_errors
    
    def form_valid(self, form, product, quantity):
        """Traite le formulaire valide"""
        # Créer la commande avec les données du formulaire
        order = form.save(commit=False)
        order.product = product
        order.quantity = quantity
        
        # Définir les prix (seront calculés automatiquement par save())
        order.unit_price = product.price
        
        # Gérer les données client selon le type d'utilisateur
        if not self.request.user.is_authenticated:
            self.handle_unauthenticated_user(order, self.request.POST)
        else:
            self.handle_authenticated_user(order)
        
        # Métadonnées techniques
        order.ip_address = self.get_client_ip()
        order.user_agent = self.request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Sauvegarder la commande
        order.save()
        
        # Mettre à jour le stock
        self.update_product_stock(product, quantity)
        
        # Préparer la session pour la page de succès
        self.request.session['order_id'] = order.id
        self.request.session['order_email'] = order.customer_email or (order.lead.email if order.lead else '')
        
        from .sms import send_order_confirmation_sms
        from .google_sheets import add_order_to_sheet
        # Envoyer l'email de confirmation
        self.send_confirmation_email(order)
        
        sms_phone = send_order_confirmation_sms(order)
        data_add_order_to_sheet = add_order_to_sheet(order)
        
        if sms_phone:
            messages.success(self.request, f"Un SMS de confirmation a été envoyé à {order.customer_phone}")
        else:
            messages.error(self.request, "Une erreur est survenue lors de l'envoi du SMS de confirmation.")
        
        # if data_add_order_to_sheet:
        #     messages.success(self.request, "La commande a été ajoutée à Google Sheets")
        # else:
        #     messages.error(self.request, "Une erreur est survenue lors de l'ajout de la commande à Google Sheets")
            
        
        messages.success(self.request, f"Votre commande #{order.id} a été confirmée !")
        return super().form_valid(form)
    
    def handle_unauthenticated_user(self, order, post_data):
        """Gère la création du lead et les données client pour les non connectés"""
        email = post_data.get('customer_email', '').strip()
        first_name = post_data.get('customer_first_name', '').strip()
        last_name = post_data.get('customer_last_name', '').strip()
        phone = post_data.get('customer_phone', '').strip()
        
        # Créer ou mettre à jour le CustomerLead
        lead, created = CustomerLead.objects.update_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'is_customer': True
            }
        )
        
        order.lead = lead
        # Garder les informations en double dans la commande pour référence
        order.customer_email = email
        order.customer_first_name = first_name
        order.customer_last_name = last_name
        order.customer_phone = phone
    
    def handle_authenticated_user(self, order):
        """Gère les données pour les utilisateurs connectés"""
        # Si l'utilisateur a un lead associé, l'utiliser
        try:
            lead = CustomerLead.objects.get(email=self.request.user.email)
            order.lead = lead
        except CustomerLead.DoesNotExist:
            # Créer un lead à partir des infos utilisateur
            lead = CustomerLead.objects.create(
                email=self.request.user.email,
                first_name=self.request.user.first_name,
                last_name=self.request.user.last_name,
                is_customer=True
            )
            order.lead = lead
        
        # Garder les informations en double
        order.customer_email = self.request.user.email
        order.customer_first_name = self.request.user.first_name
        order.customer_last_name = self.request.user.last_name
        
        
        self.first_name = self.request.user.first_name
        self.last_name = self.request.user.last_name
    
    def update_product_stock(self, product, quantity):
        """Met à jour le stock du produit"""
        if product.track_inventory:
            product.in_stock = max(0, product.in_stock - quantity)
            product.save(update_fields=['in_stock', 'updated_at'])
    
    def get_client_ip(self):
        """Récupère l'adresse IP du client"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR', '')
        return ip
    
    def send_confirmation_email(self, order):
        """Envoie l'email de confirmation de commande"""
        try:
            subject = f'Confirmation de votre commande #{order.id} - {getattr(settings, "SITE_NAME", "Notre Boutique")}'
            
            context = {
                'order': order,
                'product': order.product,
                'site_name': getattr(settings, "SITE_NAME", "Notre Boutique"),
                'first_name': self.first_name,
                'last_name': self.last_name,
                'protocol': 'https' if self.request.is_secure() else 'http',
                'domain': self.request.get_host(),
                'site_url': settings.SITE_URL,
            }
            
            # Email HTML
            html_message = render_to_string('emails/order_confirmation.html', context)
            plain_message = strip_tags(html_message)
            
            # Déterminer l'email du destinataire
            recipient_email = order.customer_email or (order.lead.email if order.lead else '')
            
            if recipient_email:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
        except Exception as e:
            if settings.DEBUG:
                print(f"DEBUG - Email error: {str(e)}")
            # Log l'erreur mais ne bloque pas le processus de commande
    
    def form_invalid(self, form):
        """Gère les formulaires invalides"""
        # Messages d'erreur généraux
        for field, errors in form.errors.items():
            if field in form.fields:
                field_name = form.fields[field].label
            else:
                field_name = field.replace('_', ' ').title()
            
            for error in errors:
                messages.error(self.request, f"{field_name}: {error}")
        
        return super().form_invalid(form)

from django.views.generic import TemplateView

class OrderSuccessView(TemplateView):
    """Page de confirmation de commande"""
    template_name = 'orders/order_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_id = self.request.session.get('order_id')
        order_email = self.request.session.get('order_email')
        
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
                context['order'] = order
                # Nettoyer la session
                if 'order_id' in self.request.session:
                    del self.request.session['order_id']
                if 'order_email' in self.request.session:
                    del self.request.session['order_email']
            except Order.DoesNotExist:
                messages.error(self.request, "Commande non trouvée.")
        
        return context
    
    def get(self, request, *args, **kwargs):
        # Rediriger si pas de commande en session
        if not request.session.get('order_id'):
            messages.warning(request, "Aucune commande récente trouvée.")
            return redirect('index')
        return super().get(request, *args, **kwargs)
      
class OrderDetailView(DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'
    pk_url_kwarg = 'order_id'  # Cela correspond à <int:order_id> dans l'URL

    def get(self, request, *args, **kwargs):
            self.object = self.get_object()
            
            # Si c'est une requête HTMX, on retourne uniquement le contenu
            # if request.headers.get('HX-Request'):
            #     context = self.get_context_data(object=self.object)
            #     html = render_to_string('orders/partials/order_detail_content.html', context, request=request)
            #     return HttpResponse(html)
            
            
                
            return super().get(request, *args, **kwargs)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.object
        return context
    
class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10
    
    def get_queryset(self):
        return Order.objects.filter(
            Q(user=self.request.user) | 
            Q(lead__email=self.request.user.email)
        ).order_by('-created_at')

@require_http_methods(["POST"])
def create_order_from_configuration(request, configuration_id):
    """
    Vue pour créer une commande à partir d'une configuration de montre personnalisée.
    Cette vue est appelée en AJAX.
    """
    try:
        configuration = WatchConfiguration.objects.get(id=configuration_id)
        
        # Vérifier la disponibilité du produit
        if configuration.product.in_stock <= 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Ce produit est actuellement en rupture de stock.'
            }, status=400)
        
        # Créer un nouvel ordre
        order = Order.objects.create(
            product=configuration.product,
            status='pending',
            unit_price=configuration.product.price,
            total_price=configuration.product.price,  # Peut être ajusté selon les options
            shipping_address='',  # À remplir par l'utilisateur
            billing_address='',   # À remplir par l'utilisateur
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Si l'utilisateur est connecté, l'associer à la commande
        if request.user.is_authenticated:
            order.user = request.user
            
            # Créer ou mettre à jour le lead pour l'utilisateur connecté
            if hasattr(request.user, 'email'):
                order.lead, _ = CustomerLead.objects.get_or_create(
                    email=request.user.email,
                    defaults={
                        'first_name': request.user.first_name,
                        'last_name': request.user.last_name,
                        'is_customer': True
                    }
                )
            
            order.save()
        else:
            # Pour les utilisateurs non connectés, stocker l'ID de commande dans la session
            request.session['last_order_id'] = order.id
        
        return JsonResponse({
            'status': 'success',
            'order_id': order.id,
            'redirect_url': reverse('order_detail', kwargs={'pk': order.id})
        })
        
    except WatchConfiguration.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Configuration introuvable.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'Une erreur est survenue lors de la création de la commande.'
        }, status=500)
