from django.urls import path
from . import views

app_name = 'recipes'

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/recipe/<int:recipe_id>/images/', views.recipe_images, name='recipe_images'),
]