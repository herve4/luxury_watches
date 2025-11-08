from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    
    def ready(self):
        # Import des signaux
        import app.signals  # noqa
        
        # Import de la configuration d'administration personnalisée
        try:
            import app.admin_customization
        except ImportError:
            pass
            
        # Les signaux seront importés plus tard s'ils sont nécessaires
