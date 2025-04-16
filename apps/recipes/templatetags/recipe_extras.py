from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def get_range(value):
    """Generate a range of numbers from 1 to value."""
    return range(1, value + 1)

@register.filter
def format_time(time_value):
    """Format time to a human-readable format.
    Handles both integer minutes and timedelta objects."""
    if not time_value:
        return "N/A"
    
    # If it's a timedelta, convert to total minutes
    if isinstance(time_value, timedelta):
        total_minutes = int(time_value.total_seconds() / 60)
    else:
        total_minutes = int(time_value)
    
    hours = total_minutes // 60
    mins = total_minutes % 60
    
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m" 