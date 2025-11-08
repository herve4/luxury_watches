from django import template

register = template.Library()

@register.filter(name='sub')
def sub(value, arg):
    """Soustrait la valeur de l'argument de la valeur donnée."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Récupère une valeur d'un dictionnaire par sa clé."""
    if not dictionary:
        return 0
    return dictionary.get(str(key), 0)
