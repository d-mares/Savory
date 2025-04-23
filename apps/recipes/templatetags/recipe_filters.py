from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def format_time(time_obj):
    if time_obj is None or time_obj == '':
        return 'N/A'
        
    if isinstance(time_obj, timedelta):
        total_seconds = int(time_obj.total_seconds())
    else:
        try:
            total_seconds = int(time_obj)
        except (ValueError, TypeError):
            return 'N/A'
        
    if total_seconds >= 3600:
        return f"{total_seconds // 3600} hrs"
    else:
        return f"{total_seconds // 60} mins"

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0 