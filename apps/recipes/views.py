from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import Recipe, RecipeImage, CarouselItem, UserRecipeCollection, Tag, Ingredient
import logging
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.utils import IntegrityError
from django.db import models
from django.db.models import Q, Count

def home(request):
    """Home page view."""
    carousel_items = CarouselItem.objects.select_related('recipe').all()
    user_recipe_collection = None
    
    if request.user.is_authenticated:
        user_recipe_collection = Recipe.objects.filter(
            collected_by__user=request.user
        )
    
    context = {
        'carousel_items': carousel_items,
        'user_recipe_collection': user_recipe_collection,
    }
    return render(request, 'recipes/home.html', context)

def recipe_detail(request, recipe_id):
    """Recipe detail view."""
    recipe = get_object_or_404(Recipe, recipe_id=recipe_id)
    images = recipe.images.all().order_by('order')
    
    # Get user's pantry items if authenticated
    user_pantry = []
    if request.user.is_authenticated:
        from apps.pantry.models import UserPantry
        pantry_items = UserPantry.objects.filter(user=request.user).select_related('ingredient')
        user_pantry = [item.ingredient for item in pantry_items]
        
        # Get related ingredients for each pantry item
        related_ingredients = []
        for item in pantry_items:
            related_ingredients.extend(item.related_ingredients.all())
        
        # Add related ingredients to user_pantry
        user_pantry.extend(related_ingredients)
    
    return render(request, 'recipes/recipe_detail.html', {
        'recipe': recipe,
        'images': images,
        'user_pantry': user_pantry,
    })

@staff_member_required
def recipe_images(request, recipe_id):
    """Return a list of images for a given recipe."""
    
    try:
        # Use the database ID directly
        recipe = Recipe.objects.get(id=recipe_id)
        
        # Get all images for this recipe with their IDs
        images = RecipeImage.objects.filter(recipe=recipe).select_related('recipe')
        
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
        
        return JsonResponse(image_list, safe=False)
    except Recipe.DoesNotExist:
        return JsonResponse({'error': 'Recipe not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def personal_recipes(request):
    """View for user's personal recipe collection."""
    if not request.user.is_authenticated:
        return redirect('account_login')
    
    # Get user's pantry items
    from apps.pantry.models import UserPantry
    pantry_items = UserPantry.objects.filter(user=request.user).select_related('ingredient')
    user_pantry = [item.ingredient for item in pantry_items]
    
    # Get related ingredients for each pantry item
    related_ingredients = []
    for item in pantry_items:
        related_ingredients.extend(item.related_ingredients.all())
    
    # Add related ingredients to user_pantry
    user_pantry.extend(related_ingredients)
    
    # Get all recipes in user's collection
    user_recipes = UserRecipeCollection.objects.filter(user=request.user).select_related('recipe')
    
    # Get unique categories
    categories = set()
    recipes = []
    
    for collection in user_recipes:
        recipe = collection.recipe
        category = collection.category or 'Uncategorized'
        categories.add(category)
        
        # Calculate missing ingredients
        missing_ingredients = []
        for recipe_ingredient in recipe.recipe_ingredients.all():
            if recipe_ingredient.ingredient and recipe_ingredient.ingredient not in user_pantry:
                missing_ingredients.append(recipe_ingredient.ingredient)
        
        recipes.append({
            'recipe': recipe,
            'category': category,
            'missing_ingredients': missing_ingredients,
            'missing_ingredients_count': len(missing_ingredients),
            'total_time': recipe.total_time or (recipe.prep_time + recipe.cook_time if recipe.prep_time and recipe.cook_time else None),
            'rating': recipe.aggregated_rating
        })
    
    # Get sort and direction parameters
    sort_by = request.GET.get('sort', '')
    direction = request.GET.get('direction', 'asc')
    
    if sort_by == 'time':
        recipes.sort(key=lambda x: x['total_time'] or float('inf'), reverse=(direction == 'desc'))
    elif sort_by == 'rating':
        recipes.sort(key=lambda x: x['rating'] or 0, reverse=(direction == 'desc'))
    elif sort_by == 'missing':
        recipes.sort(key=lambda x: x['missing_ingredients_count'], reverse=(direction == 'desc'))
    
    # Get filter parameter
    filter_by = request.GET.get('filter', '')
    if filter_by == 'available':
        recipes = [r for r in recipes if r['missing_ingredients_count'] == 0]
    
    return render(request, 'recipes/personal_recipes.html', {
        'recipes': recipes,
        'categories': sorted(list(categories)),
        'current_sort': sort_by,
        'current_filter': filter_by,
        'current_direction': direction
    })

@login_required
def add_to_collection(request, recipe_id):
    """Add a recipe to user's collection."""
    recipe = get_object_or_404(Recipe, recipe_id=recipe_id)
    
    # Check if recipe is already in collection
    if UserRecipeCollection.objects.filter(user=request.user, recipe=recipe).exists():
        messages.warning(request, 'Recipe is already in your collection.')
    else:
        # Add recipe to collection with its default category
        UserRecipeCollection.objects.create(
            user=request.user,
            recipe=recipe,
            category=recipe.recipe_category
        )
        messages.success(request, 'Recipe added to your collection!')
    
    return redirect('recipes:recipe_detail', recipe_id=recipe_id)

@login_required
def remove_from_collection(request, recipe_id):
    """Remove a recipe from user's collection."""
    recipe = get_object_or_404(Recipe, recipe_id=recipe_id)
    collection = get_object_or_404(UserRecipeCollection, user=request.user, recipe=recipe)
    collection.delete()
    messages.success(request, 'Recipe removed from your collection.')
    return redirect('recipes:personal_recipes')

@login_required
def toggle_recipe_collection(request, recipe_id):
    """Toggle a recipe in user's collection."""
    recipe = get_object_or_404(Recipe, recipe_id=recipe_id)
    
    try:
        # First try to get the collection
        collection = UserRecipeCollection.objects.get(user=request.user, recipe=recipe)
        collection.delete()
        is_in_collection = False
    except UserRecipeCollection.DoesNotExist:
        try:
            # Try to create a new collection
            UserRecipeCollection.objects.create(
                user=request.user,
                recipe=recipe,
                category=recipe.recipe_category
            )
            is_in_collection = True
        except IntegrityError:
            # If we get an integrity error, it means another request created it
            # Just return that it's in the collection
            is_in_collection = True
    
    return JsonResponse({
        'success': True,
        'is_in_collection': is_in_collection
    })

def search_recipes(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 35))
    sort = request.GET.get('sort', '')
    direction = request.GET.get('direction', 'desc')
    filter_type = request.GET.get('filter', '')
    
    # Base queryset
    recipes = Recipe.objects.all()
    
    # Get user's recipe collection if authenticated
    user_recipe_collection = None
    if request.user.is_authenticated:
        user_recipe_collection = Recipe.objects.filter(
            collected_by__user=request.user
        )
    
    # Apply search query
    if query:
        # Search in recipe name, description, and category
        recipes = recipes.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(recipe_category__icontains=query) |
            # Search in ingredients
            Q(recipe_ingredients__ingredient__name__icontains=query) |
            # Search in tags
            Q(recipe_tags__tag__name__icontains=query)
        ).distinct()
    
    # Apply category filter
    if category:
        recipes = recipes.filter(recipe_category=category)
    
    # Apply additional filters
    if filter_type == 'available' and request.user.is_authenticated:
        # Filter recipes where all ingredients are in user's pantry
        recipes = recipes.filter(
            ~Q(recipe_ingredients__ingredient__userpantry__user=request.user)
        ).distinct()
    
    # Get matching ingredients for the sidebar
    matching_ingredients = Ingredient.objects.filter(
        name__icontains=query
    ).distinct()[:10]  # Limit to 10 matching ingredients
    
    # Get unique categories that have matching recipes and sort them alphabetically
    categories = Recipe.objects.filter(
        id__in=recipes.values('id')
    ).values_list('recipe_category', flat=True).distinct().order_by('recipe_category')
    
    # Calculate total recipes and pages
    total_recipes = recipes.count()
    total_pages = (total_recipes + page_size - 1) // page_size
    
    # Apply sorting
    if sort == 'time':
        recipes = recipes.order_by(f"{'-' if direction == 'desc' else ''}total_time")
    elif sort == 'rating':
        recipes = recipes.order_by(f"{'-' if direction == 'desc' else ''}aggregated_rating")
    elif sort == 'date':
        recipes = recipes.order_by(f"{'-' if direction == 'desc' else ''}created_at")
    elif sort == 'missing' and request.user.is_authenticated:
        # Sort by number of missing ingredients
        recipes = recipes.annotate(
            missing_count=Count(
                'recipe_ingredients',
                filter=~Q(recipe_ingredients__ingredient__userpantry__user=request.user)
            )
        ).order_by(f"{'-' if direction == 'desc' else ''}missing_count")
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    recipes = recipes[start:end]
    
    # Prepare recipe data with additional information
    recipe_data = []
    for recipe in recipes:
        data = {
            'recipe': recipe,
            'total_time': recipe.total_time,
            'rating': recipe.aggregated_rating,
        }
        
        if request.user.is_authenticated:
            # Calculate missing ingredients count
            missing_count = recipe.recipe_ingredients.filter(
                ~Q(ingredient__userpantry__user=request.user)
            ).count()
            data['missing_count'] = missing_count
            # Add availability indicator
            data['has_all_ingredients'] = missing_count == 0
        
        recipe_data.append(data)
    
    context = {
        'query': query,
        'recipes': recipe_data,
        'total_recipes': total_recipes,
        'total_pages': total_pages,
        'page': page,
        'page_size': page_size,
        'categories': categories,
        'current_category': category,
        'current_sort': sort,
        'current_direction': direction,
        'current_filter': filter_type,
        'matching_ingredients': matching_ingredients,
        'user_recipe_collection': user_recipe_collection,  # Add user's recipe collection to context
    }
    
    return render(request, 'recipes/search_results.html', context)
