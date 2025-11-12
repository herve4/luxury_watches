"""
Configuration pour l'intégration avec Google Sheets.

Ce fichier contient les informations de configuration pour se connecter à l'API Google Sheets.
"""

# ID de la feuille Google Sheets
SHEET_ID = '1I66Cnc3qCSktYL3bpc5xZKquS8SqubAZfUvOkMvVm1E'
SHEET_NAME = 'contact boutiluxe'

# Informations pour l'authentification du compte de service
# Remplacez ces valeurs par les vôtres
SERVICE_ACCOUNT_FILE = 'path/to/your/service-account.json'  # À mettre à jour avec le chemin vers votre fichier JSON d'identification

# Configuration des colonnes dans la feuille Google Sheets
COLUMNS = {
    'timestamp': 'Horodatage',
    'name': 'Nom',
    'email': 'Email',
    'subject': 'Sujet',
    'message': 'Message'
}
