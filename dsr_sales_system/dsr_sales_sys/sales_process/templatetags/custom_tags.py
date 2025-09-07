from django import template

register = template.Library()

@register.filter
def get_attr(obj, attr_name):
    """Get attribute value dynamically in templates."""
    return getattr(obj, attr_name, "")
