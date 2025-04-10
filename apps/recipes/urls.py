from django.urls import path
from . import views

app_name = 'recipes'

urlpatterns = [
    path('', views.home, name='home'),
    path('recipe/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('admin/recipe/<int:recipe_id>/images/', views.recipe_images, name='recipe_images'),
]