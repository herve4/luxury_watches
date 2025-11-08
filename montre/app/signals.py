from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order, Review

@receiver(post_save, sender=Order)
def send_order_confirmation_email(sender, instance, created, **kwargs):
    """
    Envoie un email de confirmation lorsqu'une commande est créée.
    """
    if created and instance.lead.email:
        subject = f'Confirmation de votre commande #{instance.id}'
        message = f'''
        Bonjour,
        
        Nous avons bien reçu votre commande n°{instance.id} et vous en remercions.
        
        Détails de votre commande :
        - Produit : {instance.product.name}
        - Total : {instance.total_price} FCFA
        
        Vous pouvez suivre l'état de votre commande en vous connectant à votre compte.
        
        Cordialement,
        L'équipe de BOUTILUXE
        '''
        
        html_message = render_to_string('emails/order_confirmation.html', {
            'order': instance,
            'site_name': 'BOUTILUXE',
            'contact_email': 'contact@boutiluxe.com'
        })
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.lead.email],
            html_message=html_message
        )

@receiver(post_save, sender=Review)
def notify_admin_review_submitted(sender, instance, created, **kwargs):
    """
    Notifie l'administrateur lorsqu'un nouvel avis est soumis.
    """
    if created and not instance.is_approved:
        subject = f'Nouvel avis soumis pour {instance.product.name}'
        message = f'''
        Un nouvel avis a été soumis pour le produit {instance.product.name}.
        
        Note : {instance.get_rating_display()}
        Titre : {instance.title}
        Commentaire : {instance.comment}
        
        Connectez-vous à l'administration pour le modérer.
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin[1] for admin in settings.ADMINS],
            fail_silently=True
        )
