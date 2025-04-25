from django.urls import path
from . import views

app_name = 'pantry'

urlpatterns = [
    path('', views.pantry_list, name='pantry_list'),
    path('search-ingredients/', views.search_ingredients, name='search_ingredients'),
    path('get-related-ingredients/<int:ingredient_id>/', views.get_related_ingredients, name='get_related_ingredients'),
    path('save-related-ingredients/<int:ingredient_id>/', views.save_related_ingredients, name='save_related_ingredients'),
    path('add/<int:ingredient_id>/', views.add_to_pantry, name='add_to_pantry'),
    path('remove/<int:ingredient_id>/', views.remove_from_pantry, name='remove_from_pantry'),
    path('add-ingredient/', views.add_ingredient, name='add_ingredient'),
    path('suggested-ingredients/', views.suggested_ingredients, name='suggested_ingredients'),
] 