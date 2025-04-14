from django.urls import path
from . import views

app_name = 'shopping'

urlpatterns = [
    path('', views.shopping_list, name='shopping_list'),
    path('add/<int:ingredient_id>/', views.add_to_shopping_list, name='add_to_shopping_list'),
    path('remove/<int:ingredient_id>/', views.remove_from_shopping_list, name='remove_from_shopping_list'),
    path('toggle/<int:ingredient_id>/', views.toggle_item, name='toggle_item'),
    path('search-ingredients/', views.search_ingredients, name='search_ingredients'),
    path('complete-trip/', views.complete_shopping_trip, name='complete_shopping_trip'),
]
