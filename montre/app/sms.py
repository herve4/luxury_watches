import os
import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_sms(phone_number, message):
    """
    Envoie un SMS via l'API TextBee
    
    Args:
        phone_number (str): Numéro de téléphone du destinataire (format international, ex: '+2250700000000')
        message (str): Contenu du message à envoyer
    
    Returns:
        dict: Réponse de l'API TextBee ou None en cas d'erreur
    """
    # Configuration de l'API TextBee
    BASE_URL = 'https://api.textbee.dev/api/v1'
    api_key = getattr(settings, 'TEXTBEE_API_KEY', '')
    device_id = getattr(settings, 'TEXTBEE_DEVICE_ID', '')
    api_url = f'{BASE_URL}/gateway/devices/{device_id}/send-sms'
    
    if not api_key or not device_id:
        print("Erreur: Les clés API TextBee ne sont pas configurées.")
        return None
    
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }
    
    data = {
        'recipients': [phone_number],
        'message': message
    }
    
    try:
        response = requests.post(api_url, json=data, headers=headers)
        response.raise_for_status()  # Lève une exception pour les erreurs HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de l'envoi du SMS: {str(e)}")
        return None

def send_order_confirmation_sms(order):
    """
    Envoie un SMS de confirmation de commande au client
    
    Args:
        order: Objet Order contenant les détails de la commande
    
    Returns:
        bool: True si le SMS a été envoyé avec succès, False sinon
    """
    # Récupérer le numéro de téléphone du client
    phone_number = order.customer_phone
    
    # Vérifier que le numéro est valide (ajoutez + si nécessaire)
    if not phone_number:
        print("Erreur: Aucun numéro de téléphone fourni pour la commande.")
        return False
    
    # Formater le numéro si nécessaire (ajouter l'indicatif si absent)
    # if not phone_number.startswith('+'):
    #     # Par défaut, on suppose l'indicatif de la Côte d'Ivoire (+225)
    #     phone_number = f'+225{phone_number.lstrip("0")}'
    
    # Créer le message du SMS
    message = (
        f"Merci pour votre commande #{order.id} sur BOUTILUXE.\n\n"
        f"---------- Informations de la commande ----------\n"
        f"Produit : {order.product.name}. \n"
        f"Commandé le : {order.created_at}. \n"
        f"Montant : {order.total_price} FCFA. \n"
        f"Quantité : {order.quantity}. \n"
        f"Voir la commande : {settings.SITE_URL}/commande/{order.id}/\n\n"
        f"---------- Informations client ----------\n"
        f"Nom : {order.customer_first_name} {order.customer_last_name}. \n"
        f"Email : {order.customer_email}. \n"
        f"Téléphone : {order.customer_phone}. \n"
        f"---------- Informations de livraison ----------\n"
        f"Adresse de livraison : {order.shipping_address}. \n"
        f"Adresse de facturation : {order.billing_address}. \n"
        f"Adresse ip : {order.ip_address}. \n"
        f"---------- Informations de commande ----------\n"
        f"Statut: {order.status}. \n"
    )
    
    # Envoyer le SMS
    result = send_sms(phone_number, message)
    return result