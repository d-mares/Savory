from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import Recipe, RecipeImage
import logging

logger = logging.getLogger(__name__)

# Create your views here.

def home(request):
    return render(request, 'recipes/home.html')

@staff_member_required
def recipe_images(request, recipe_id):
    """Return a list of images for a given recipe."""
    logger.debug(f"Fetching images for recipe_id: {recipe_id}")
    
    try:
        # Use the database ID directly
        recipe = Recipe.objects.get(id=recipe_id)
        logger.debug(f"Found recipe: {recipe.name} (ID: {recipe.id})")
        
        # Get all images for this recipe with their IDs
        images = RecipeImage.objects.filter(recipe=recipe).select_related('recipe')
        logger.debug(f"Found {len(images)} images for recipe {recipe.name}")
        
        # Convert to list with all necessary information
        image_list = []
        for image in images:
            image_data = {
                'id': image.id,
                'url': image.url,
                'order': image.order,
                'recipe_id': recipe.id,  # Use the database ID
                'recipe_name': recipe.name
            }
            image_list.append(image_data)
            logger.debug(f"Added image: {image_data}")
        
        return JsonResponse(image_list, safe=False)
    except Recipe.DoesNotExist:
        logger.error(f"Recipe with id {recipe_id} not found")
        return JsonResponse({'error': 'Recipe not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching images: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
