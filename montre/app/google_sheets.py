import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from django.conf import settings
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self, 
                 spreadsheet_id: str = None, 
                 sheet_name: str = "montre",
                 api_key: str = None):
        """
        Initialise le service Google Sheets avec les paramètres fournis.
        
        Args:
            spreadsheet_id: ID de la feuille de calcul Google Sheets
            sheet_name: Nom de l'onglet dans la feuille de calcul
            api_key: Clé API Google (optionnelle)
        """
        self.spreadsheet_id = spreadsheet_id or getattr(settings, 'GOOGLE_SHEETS_SPREADSHEET_ID', '')
        self.sheet_name = sheet_name
        self.api_key = api_key or getattr(settings, 'GOOGLE_API_KEY', '')
        self.creds_path = os.path.join(settings.BASE_DIR, 'credentials.json')
        self.sheet = None
        self._connect()
    
    def _connect(self):
        """Établit la connexion avec Google Sheets"""
        try:
            logger.info(f"Tentative de connexion à Google Sheets...")
            logger.info(f"Chemin du fichier de credentials: {self.creds_path}")
            logger.info(f"ID de la feuille: {self.spreadsheet_id}")
            logger.info(f"Nom de l'onglet: {self.sheet_name}")
            
            if not os.path.exists(self.creds_path):
                error_msg = f"Fichier credentials introuvable: {self.creds_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Vérifier que l'ID de la feuille est défini
            if not self.spreadsheet_id:
                error_msg = "L'ID de la feuille Google Sheets n'est pas défini"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Définir les scopes nécessaires
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
            
            logger.info("Authentification avec le compte de service...")
            
            # S'authentifier
            try:
                creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, scope)
                client = gspread.authorize(creds)
                logger.info("Authentification réussie")
            except Exception as auth_error:
                logger.error(f"Erreur d'authentification: {str(auth_error)}")
                raise
            
            # Ouvrir la feuille de calcul
            logger.info(f"Ouverture de la feuille avec l'ID: {self.spreadsheet_id}")
            try:
                spreadsheet = client.open_by_key(self.spreadsheet_id)
                logger.info("Feuille de calcul ouverte avec succès")
                
                # Obtenir l'onglet
                try:
                    self.sheet = spreadsheet.worksheet(self.sheet_name)
                    logger.info(f"Onglet '{self.sheet_name}' chargé avec succès")
                except gspread.exceptions.WorksheetNotFound:
                    logger.warning(f"L'onglet '{self.sheet_name}' n'existe pas, tentative de création...")
                    self.sheet = spreadsheet.add_worksheet(title=self.sheet_name, rows=100, cols=20)
                    logger.info(f"Nouvel onglet créé: {self.sheet_name}")
                
                logger.info(f"✅ Connecté à Google Sheets - ID: {self.spreadsheet_id}, Feuille: {self.sheet_name}")
                
            except gspread.exceptions.SpreadsheetNotFound:
                error_msg = f"La feuille avec l'ID {self.spreadsheet_id} n'a pas été trouvée ou l'accès est refusé"
                logger.error(error_msg)
                raise Exception(error_msg)
            except Exception as e:
                logger.error(f"Erreur lors de l'ouverture de la feuille: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"❌ Erreur de connexion à Google Sheets: {str(e)}", exc_info=True)
            raise
        
    
    def add_order(self, order) -> bool:
        """Ajoute une commande à la feuille Google Sheets"""
        try:
            if not self.sheet:
                self._connect()
                
            # Préparer les en-têtes si la feuille est vide
            if not self.sheet.get_all_values():
                headers = [
                    'Date', 'ID Commande', 'Nom', 'Prénom', 'Email', 'Téléphone',
                    'Adresse', 'Produit', 'Image Produit', 'Quantité', 'Prix Total', 'Statut'
                ]
                self.sheet.append_row(headers)
            
            # Récupérer le prénom et le nom
            first_name = (getattr(order, 'customer_first_name', '') or "").strip()
            last_name = (getattr(order, 'customer_last_name', '') or "").strip()

            # Récupérer l'image du produit
            image_url = None
            if hasattr(order, 'product') and order.product:
                if hasattr(order.product, 'images') and order.product.images.exists():
                    image_file = order.product.images.first().image
                    image_url = f"{settings.SITE_URL.rstrip('/')}{image_file.url}"
                elif hasattr(order.product, 'image') and order.product.image:
                    image_file = order.product.image
                    image_url = f"{settings.SITE_URL.rstrip('/')}{image_file.url}"

            # Préparer les données de la commande
            row = [
                order.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(order, 'created_at') and order.created_at else "",
                str(getattr(order, 'id', '')),
                last_name,
                first_name,
                getattr(order, 'customer_email', '') or "",
                getattr(order, 'customer_phone', '') or "",
                getattr(order, 'shipping_address', '') or "",
                getattr(order.product, 'name', '') if hasattr(order, 'product') and order.product else "",
                "",  # Laissé vide pour l'image qui sera ajoutée après
                str(getattr(order, 'quantity', 1)),
                str(getattr(order, 'total_price', 0)),
                getattr(order, 'status', 'En attente')
            ]
            
            # Ajouter la ligne
            self.sheet.append_row(row)
            
            # Si une image est disponible, l'ajouter dans la cellule
            if image_url:
                try:
                    from urllib.request import urlopen
                    from io import BytesIO
                    from PIL import Image
                    import requests
                    
                    # Télécharger l'image
                    response = requests.get(image_url, stream=True)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content))
                    
                    # Redimensionner l'image si nécessaire (ex: max 100x100)
                    image.thumbnail((100, 100))
                    
                    # Sauvegarder dans un buffer
                    buffer = BytesIO()
                    image.save(buffer, format='PNG')
                    
                    # Obtenir la dernière ligne ajoutée (celle qu'on vient de créer)
                    all_values = self.sheet.get_all_values()
                    last_row = len(all_values)  # La ligne est la suivante car append_row ajoute à la fin
                    
                    # Mettre à jour la cellule avec l'image
                    self.sheet.update_cell(last_row, 9, '')  # Nettoyer la cellule
                    self.sheet.update_cell(
                        last_row, 9,  # Colonne I (9ème colonne)
                        f'=IMAGE("{image_url}")'  # Formule Google Sheets pour afficher l'image
                    )
                    
                    # Ajuster la hauteur de la ligne pour l'image (formatage conditionnel)
                    self.sheet.format(f'I{last_row}', {
                        'borders': {
                            'top': {'style': 'SOLID'},
                            'bottom': {'style': 'SOLID'},
                            'left': {'style': 'SOLID'},
                            'right': {'style': 'SOLID'}
                        },
                        'verticalAlignment': 'MIDDLE',
                        'horizontalAlignment': 'CENTER'
                    })
                    
                    # Ajuster la largeur de la colonne (en utilisant la méthode update de l'API v4)
                    spreadsheet = self.sheet.spreadsheet
                    body = {
                        'requests': [{
                            'updateDimensionProperties': {
                                'range': {
                                    'sheetId': self.sheet.id,
                                    'dimension': 'COLUMNS',
                                    'startIndex': 8,  # Colonne I (index 8 en base 0)
                                    'endIndex': 9     # Jusqu'à la colonne suivante
                                },
                                'properties': {
                                    'pixelSize': 100
                                },
                                'fields': 'pixelSize'
                            }
                        }]
                    }
                    spreadsheet.batch_update(body)
                    
                except Exception as img_error:
                    logger.error(f"❌ Erreur lors de l'ajout de l'image: {img_error}")
            
            logger.info(f"✅ Commande {getattr(order, 'id', '')} ajoutée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'ajout de la commande: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
# Fonction d'aide pour une utilisation simple
def add_order_to_sheet(order):
    """
    Fonction wrapper pour l'ajout de commande
    """
    try:
        # Récupérer les paramètres depuis les settings Django
        spreadsheet_id = getattr(settings, 'GOOGLE_SHEETS_SPREADSHEET_ID', '')
        api_key = getattr(settings, 'GOOGLE_API_KEY', '')
        
        service = GoogleSheetsService(
            spreadsheet_id=spreadsheet_id,
            sheet_name="montre",
            api_key=api_key
        )
        return service.add_order(order)
    except Exception as e:
        logger.error(f"❌ Erreur globale: {e}")
        return False