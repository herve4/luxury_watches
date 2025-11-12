from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import Order, CustomerLead, Product, Review, Comment
from django.core.validators import EmailValidator

class CustomerForm(forms.Form):
    """Formulaire pour les informations client (utilisé pour les utilisateurs non connectés)."""
    first_name = forms.CharField(
        label='Prénom',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
            'placeholder': 'Votre prénom',
            'required': 'required'
        })
    )
    last_name = forms.CharField(
        label='Nom',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
            'placeholder': 'Votre nom',
            'required': 'required'
        })
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
            'placeholder': 'votre@email.com',
            'required': 'required'
        })
    )
    phone = forms.CharField(
        label='Téléphone',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
            'placeholder': 'Votre numéro de téléphone',
            'required': 'required'
        })
    )

User = get_user_model()

class ReviewForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.is_authenticated:
            self.fields['first_name'].widget = forms.HiddenInput()
            self.fields['last_name'].widget = forms.HiddenInput()
            self.fields['email'].widget = forms.HiddenInput()
            self.initial.update({
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'email': self.user.email
            })
    
    class Meta:
        model = Review
        fields = ['first_name', 'last_name', 'email', 'rating', 'comment']
        widgets = {
            'rating': forms.HiddenInput(),
            'comment': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent',
                'placeholder': 'Dites-nous ce que vous pensez de ce produit...'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2 text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent',
                'placeholder': 'Votre prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2 text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent',
                'placeholder': 'Votre nom'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2 text-white focus:ring-2 focus:ring-amber-500 focus:border-transparent',
                'placeholder': 'votre@email.com'
            }),
        }
        labels = {
            'first_name': _('Prénom'),
            'last_name': _('Nom'),
            'email': _('Adresse email'),
            'rating': _('Note'),
            'title': _('Titre de votre avis'),
            'comment': _('Votre avis'),
        }
        help_texts = {
            'email': _('Votre adresse email ne sera pas publiée.'),
            'rating': _('Sélectionnez une note de 1 à 5 étoiles'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Si l'utilisateur est connecté, on pré-remplit les champs
        if self.user and self.user.is_authenticated:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
            
            # On rend les champs en lecture seule
            self.fields['first_name'].widget.attrs['readonly'] = True
            self.fields['last_name'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['readonly'] = True
        
        # Ajout des classes CSS aux champs
        for field in self.fields:
            if field != 'rating':  # On gère le style du rating séparément
                self.fields[field].widget.attrs.update({
                    'class': 'form-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                })


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'w-full bg-slate-700/50 border border-slate-600/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/50',
                'placeholder': 'Ajouter un commentaire...',
            })
        }

# class CheckoutForm(forms.ModelForm):
#     quantity = forms.IntegerField(
#         min_value=1, 
#         initial=1,
#         required=True,
#         widget=forms.NumberInput(attrs={
#             'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
#             'min': '1',
#             'value': '1',
#             'id': 'quantity-input',
#             'required': 'required'
#         })
#     )
    
#     class Meta:
#         model = Order
#         fields = [
#             'shipping_address', 
#             'billing_address', 
#             'notes',
#             'quantity'
#         ]
#         widgets = {
#             'shipping_address': forms.Textarea(attrs={
#                 'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
#                 'rows': 3,
#                 'placeholder': 'Adresse complète de livraison',
#                 'required': 'required'
#             }),
#             'billing_address': forms.Textarea(attrs={
#                 'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
#                 'rows': 3,
#                 'placeholder': 'Adresse de facturation (identique à la livraison si vide)'
#             }),
#             'notes': forms.Textarea(attrs={
#                 'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
#                 'rows': 2,
#                 'placeholder': 'Instructions spéciales pour la commande',
#                 'required': False
#             }),
#         }

#     def __init__(self, *args, **kwargs):
#         self.request = kwargs.pop('request', None)
#         self.product = kwargs.pop('product', None)
#         super().__init__(*args, **kwargs)
        
#         # Si l'utilisateur n'est pas connecté, ajouter les champs d'information client
#         if not (self.request and self.request.user.is_authenticated):
#             self.fields['email'] = forms.EmailField(
#                 label='Email',
#                 widget=forms.EmailInput(attrs={
#                     'class': 'form-control',
#                     'placeholder': 'votre@email.com',
#                     'required': True
#                 })
#             )
#             self.fields['first_name'] = forms.CharField(
#                 label='Prénom',
#                 widget=forms.TextInput(attrs={
#                     'class': 'form-control',
#                     'placeholder': 'Votre prénom',
#                     'required': True
#                 })
#             )
#             self.fields['last_name'] = forms.CharField(
#                 label='Nom',
#                 widget=forms.TextInput(attrs={
#                     'class': 'form-control',
#                     'placeholder': 'Votre nom',
#                     'required': True
#                 })
#             )
#             self.fields['phone'] = forms.CharField(
#                 label='Téléphone',
#                 widget=forms.TextInput(attrs={
#                     'class': 'form-control',
#                     'placeholder': 'Votre numéro de téléphone',
#                     'required': True
#                 })
#             )
            
#             # Déplacer les champs au début du formulaire
#             field_order = ['first_name', 'last_name', 'email', 'phone']
#             self.order_fields(field_order + [f for f in self.fields if f not in field_order])

#     def clean(self):
#         cleaned_data = super().clean()
        
#         # Vérifier la quantité disponible si un produit est spécifié
#         quantity = cleaned_data.get('quantity', 1)
#         if self.product and quantity > self.product.in_stock:
#             raise forms.ValidationError({
#                 'quantity': f'Il ne reste que {self.product.in_stock} exemplaire(s) en stock.'
#             })
            
#         # Si l'adresse de facturation n'est pas renseignée, utiliser celle de livraison
#         if not cleaned_data.get('billing_address') and cleaned_data.get('shipping_address'):
#             cleaned_data['billing_address'] = cleaned_data['shipping_address']
            
#         return cleaned_data

#     def save(self, commit=True):
#         order = super().save(commit=False)
        
#         # Définir le prix unitaire et le total
#         if self.product:
#             order.unit_price = self.product.price
#             order.total_price = order.unit_price * self.cleaned_data.get('quantity', 1)
        
#         # Si l'utilisateur n'est pas connecté, créer ou mettre à jour le lead
#         if not (self.request and self.request.user.is_authenticated):
#             email = self.cleaned_data.get('email')
#             first_name = self.cleaned_data.get('first_name')
#             last_name = self.cleaned_data.get('last_name')
#             phone = self.cleaned_data.get('phone')
            
#             # Créer ou mettre à jour le lead
#             lead, created = CustomerLead.objects.update_or_create(
#                 email=email,
#                 defaults={
#                     'first_name': first_name,
#                     'last_name': last_name,
#                     'phone': phone,
#                     'is_customer': True
#                 }
#             )
#             order.lead = lead
        
#         if commit:
#             order.save()
            
#         return order


class CheckoutForm(forms.ModelForm):
    quantity = forms.IntegerField(
        min_value=1, 
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'id': 'quantity-input'
        })
    )
    
    class Meta:
        model = Order
        fields = [
            'shipping_address', 
            'billing_address', 
            'notes',
            'quantity'
        ]
        widgets = {
            'shipping_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse complète de livraison',
                'required': True
            }),
            'billing_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse de facturation (identique à la livraison si vide)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Instructions spéciales pour la commande',
                'required': False
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        
        # Si l'utilisateur n'est pas connecté, ajouter les champs d'information client
        if not (self.request and self.request.user.is_authenticated):
            self.fields['customer_email'] = forms.EmailField(
                label='Email',
                widget=forms.EmailInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'votre@email.com',
                    'required': True
                })
            )
            self.fields['customer_first_name'] = forms.CharField(
                label='Prénom',
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Votre prénom',
                    'required': True
                })
            )
            self.fields['customer_last_name'] = forms.CharField(
                label='Nom',
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Votre nom',
                    'required': True
                })
            )
            self.fields['customer_phone'] = forms.CharField(
                label='Téléphone',
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Votre numéro de téléphone',
                    'required': True
                })
            )
            
            # Réorganiser l'ordre des champs
            field_order = ['customer_first_name', 'customer_last_name', 'customer_email', 'customer_phone']
            self.order_fields(field_order + [f for f in self.fields if f not in field_order])

    def clean(self):
        cleaned_data = super().clean()
        
        # Vérifier la quantité disponible si un produit est spécifié
        quantity = cleaned_data.get('quantity', 1)
        if self.product and quantity > self.product.in_stock:
            raise forms.ValidationError({
                'quantity': f'Il ne reste que {self.product.in_stock} exemplaire(s) en stock.'
            })
            
        # Si l'adresse de facturation n'est pas renseignée, utiliser celle de livraison
        if not cleaned_data.get('billing_address') and cleaned_data.get('shipping_address'):
            cleaned_data['billing_address'] = cleaned_data['shipping_address']
            
        return cleaned_data

    def save(self, commit=True):
        order = super().save(commit=False)
        
        # Les prix seront calculés automatiquement par le modèle
        if self.product:
            order.unit_price = self.product.price
        
        if commit:
            order.save()
            
        return order
    
    

from .models_banner import VideoBanner

class ContactForm(forms.Form):
    """Formulaire de contact pour la page de contact."""
    name = forms.CharField(
        label='Votre nom',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
            'placeholder': 'Votre nom complet',
            'required': 'required'
        })
    )
    
    email = forms.EmailField(
        label='Votre email',
        validators=[EmailValidator(message="Veuillez entrer une adresse email valide.")],
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
            'placeholder': 'votre@email.com',
            'required': 'required'
        })
    )
    
    subject = forms.CharField(
        label='Sujet',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
            'placeholder': 'Objet de votre message',
            'required': 'required'
        })
    )
    
    message = forms.CharField(
        label='Votre message',
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-gold-500 focus:border-transparent',
            'rows': 5,
            'placeholder': 'Écrivez votre message ici...',
            'required': 'required'
        })
    )

class VideoBannerForm(forms.ModelForm):
    class Meta:
        model = VideoBanner
        fields = [
            'title', 'banner_type', 'video_file', 
            'video_url', 'thumbnail', 'is_active'
        ]
        widgets = {
            'banner_type': forms.RadioSelect(choices=VideoBanner.BannerType.choices),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['video_file'].required = False
        self.fields['video_url'].required = False

    def clean(self):
        cleaned_data = super().clean()
        banner_type = cleaned_data.get('banner_type')
        video_file = cleaned_data.get('video_file')
        video_url = cleaned_data.get('video_url')

        if banner_type == 'upload' and not video_file and not self.instance.video_file:
            self.add_error('video_file', 'Ce champ est requis pour un téléversement de vidéo.')
        elif banner_type == 'url' and not video_url:
            self.add_error('video_url', 'Ce champ est requis pour une URL de vidéo.')

        return cleaned_data