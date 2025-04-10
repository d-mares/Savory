from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def format_time(time_obj):
    if isinstance(time_obj, timedelta):
        total_seconds = int(time_obj.total_seconds())
    else:
        total_seconds = int(time_obj)
        
    if total_seconds >= 3600:
        return f"{total_seconds // 3600} hrs"
    else:
        return f"{total_seconds // 60} mins" 