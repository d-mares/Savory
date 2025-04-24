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

logger = logging.getLogger(__name__)

# Create your views here.

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
    page_size = 20
    sort = request.GET.get('sort', '')
    direction = request.GET.get('direction', 'desc')
    filter_type = request.GET.get('filter', '')
    
    # Initialize cache
    from django.core.cache import cache
    
    cache_key = f"recipes:{query}:{category}:{sort}:{direction}:{filter_type}:{page}"
    cache_time = 60 * 15  # 15 minutes
    
    # Try to get results from cache first
    cached_context = cache.get(cache_key)
    if cached_context:
        return render(request, 'recipes/search_results.html', cached_context)
    
    # Build the base queryset with minimal initial loading
    recipes = Recipe.objects.all()
    
    # Apply search query efficiently
    if query:
        # Use Q objects more efficiently by adding terms one by one
        search_terms = query.split()
        search_query = Q()
        
        for term in search_terms:
            term_query = (
                Q(name__icontains=term) |
                Q(description__icontains=term) |
                Q(recipe_category__icontains=term)
            )
            search_query &= term_query
        
        # First get matching recipe IDs
        recipe_ids = set(recipes.filter(search_query).values_list('id', flat=True))
        
        # Then check ingredients (separately to avoid joins in main query)
        ingredient_recipe_ids = Recipe.objects.filter(
            recipe_ingredients__ingredient__name__icontains=query
        ).values_list('id', flat=True)
        recipe_ids.update(ingredient_recipe_ids)
        
        # Then check tags (separately)
        tag_recipe_ids = Recipe.objects.filter(
            recipe_tags__tag__name__icontains=query
        ).values_list('id', flat=True)
        recipe_ids.update(tag_recipe_ids)
        
        # Apply the combined IDs filter
        recipes = recipes.filter(id__in=recipe_ids)
    
    # Apply category filter
    if category:
        recipes = recipes.filter(recipe_category=category)
    
    # Get user's recipe collection if authenticated
    user_recipe_collection = set()
    if request.user.is_authenticated:
        user_recipe_collection = set(Recipe.objects.filter(
            collected_by__user=request.user
        ).values_list('recipe_id', flat=True))
    
    # Apply filter type
    pantry_ingredient_ids = set()
    if request.user.is_authenticated:
        from apps.pantry.models import UserPantry
        
        # Get pantry items once and convert to a set for faster lookups
        pantry_items = UserPantry.objects.filter(user=request.user).select_related('ingredient')
        
        for item in pantry_items:
            pantry_ingredient_ids.add(item.ingredient.id)
            # Add related ingredients 
            related_ids = item.related_ingredients.values_list('id', flat=True)
            pantry_ingredient_ids.update(related_ids)
        
        if filter_type == 'available':
            # Get recipes where all ingredients are in pantry
            recipe_ingredient_map = {}
            ri_queryset = Recipe.objects.filter(
                id__in=recipes.values_list('id', flat=True)
            ).values('id').annotate(
                ingredient_count=Count('recipe_ingredients'),
                pantry_match_count=Count(
                    'recipe_ingredients__ingredient',
                    filter=Q(recipe_ingredients__ingredient__id__in=pantry_ingredient_ids)
                )
            )
            
            matching_recipe_ids = []
            for ri in ri_queryset:
                if ri['ingredient_count'] == ri['pantry_match_count']:
                    matching_recipe_ids.append(ri['id'])
            
            recipes = recipes.filter(id__in=matching_recipe_ids)
    
    # Apply sorting with proper index usage
    order_field = '-review_count'  # Default to review count
    if sort:
        order_prefix = '-' if direction == 'desc' else ''
        if sort == 'time':
            order_field = f'{order_prefix}total_time'
        elif sort == 'rating':
            order_field = f'{order_prefix}aggregated_rating'
        elif sort == 'name':
            order_field = f'{order_prefix}name'
    
    recipes = recipes.order_by(order_field)
    
    # Get total count using an optimized count query
    total_recipes = recipes.count()
    total_pages = (total_recipes + page_size - 1) // page_size
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    
    # Limit results and fetch necessary data in one go
    selected_recipes = list(recipes.select_related()
                           .prefetch_related(
                               'recipe_ingredients__ingredient',
                               'recipe_tags__tag',
                               'images'
                           )[start:end])
    
    # Get unique categories (cached separately for performance)
    categories_cache_key = "recipe_categories"
    categories = cache.get(categories_cache_key)
    if not categories:
        categories = list(Recipe.objects.values_list('recipe_category', flat=True)
                         .distinct().order_by('recipe_category'))
        cache.set(categories_cache_key, categories, 60 * 60)  # Cache for 1 hour
    
    # Prepare recipe data with additional information
    recipe_data = []
    for recipe in selected_recipes:
        data = {
            'recipe': recipe,
            'total_time': recipe.total_time,
            'rating': recipe.aggregated_rating,
        }
        
        if request.user.is_authenticated:
            # For performance: pre-calculate missing ingredients info in bulk
            recipe_ingredient_ids = set(recipe.recipe_ingredients.all()
                                       .values_list('ingredient_id', flat=True))
            # If pantry is empty, all ingredients are missing
            if not pantry_ingredient_ids:
                data['missing_count'] = len(recipe_ingredient_ids)
                data['has_all_ingredients'] = False
            else:
                missing_count = len(recipe_ingredient_ids - pantry_ingredient_ids)
                data['missing_count'] = missing_count
                data['has_all_ingredients'] = missing_count == 0
        
        recipe_data.append(data)
    
    context = {
        'recipes': recipe_data,
        'query': query,
        'category': category,
        'categories': categories,
        'total_recipes': total_recipes,
        'current_page': page,
        'total_pages': total_pages,
        'current_sort': sort,
        'current_direction': direction,
        'current_filter': filter_type,
        'user_recipe_collection': user_recipe_collection,
    }
    
    # Cache the results
    cache.set(cache_key, context, cache_time)
    
    return render(request, 'recipes/search_results.html', context)