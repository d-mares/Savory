from django.contrib import admin
from .models import UserPantry

@admin.register(UserPantry)
class UserPantryAdmin(admin.ModelAdmin):
    list_display = ('user', 'ingredient', 'added_at')
    list_filter = ('user', 'ingredient')
    search_fields = ('user__username', 'ingredient__name')
    ordering = ('-added_at',)
