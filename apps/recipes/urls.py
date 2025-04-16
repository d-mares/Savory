from django.urls import path
from . import views

app_name = 'recipes'

urlpatterns = [
    path('', views.home, name='home'),
    path('recipe/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('recipe/<int:recipe_id>/images/', views.recipe_images, name='recipe_images'),
    path('my-recipes/', views.personal_recipes, name='personal_recipes'),
    path('recipe/<int:recipe_id>/add-to-collection/', views.add_to_collection, name='add_to_collection'),
    path('recipe/<int:recipe_id>/remove-from-collection/', views.remove_from_collection, name='remove_from_collection'),
    path('recipe/<int:recipe_id>/toggle-collection/', views.toggle_recipe_collection, name='toggle_recipe_collection'),
    path('search/', views.search_recipes, name='search_recipes'),
]