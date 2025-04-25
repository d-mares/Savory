from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Ingredient, UserPantry
from .forms import IngredientForm
import urllib.parse
from django.db import transaction
from django.db.utils import OperationalError
import time
from django.core.paginator import Paginator
from django.db.models import Count

# Create your views here.

@login_required
def pantry_list(request):
    user_pantry = UserPantry.objects.filter(user=request.user)
    pantry_count = user_pantry.count()
    return render(request, 'pantry/pantry_list.html', {
        'user_pantry': user_pantry,
        'pantry_count': pantry_count,
    })

@login_required
def search_ingredients(request):
    query = request.GET.get('q', '')
    exclude_id = request.GET.get('exclude_id', None)
    if len(query) < 2:
        return JsonResponse({'ingredients': []})
    
    # Decode the query to handle special characters
    query = urllib.parse.unquote(query)
    
    ingredients = Ingredient.objects.filter(name__icontains=query)
    if exclude_id:
        ingredients = ingredients.exclude(id=exclude_id)
    ingredients = ingredients[:10]
    
    return JsonResponse({
        'ingredients': [{'id': i.id, 'name': i.name} for i in ingredients]
    })

@login_required
def get_related_ingredients(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    pantry_item = get_object_or_404(UserPantry, user=request.user, ingredient=ingredient)
    
    # Get current related ingredients
    current_related = list(pantry_item.related_ingredients.values_list('id', flat=True))
    
    # Add the current ingredient to the list to preselect it
    current_related.append(ingredient_id)
    
    return JsonResponse({
        'related_ingredients': current_related
    })

@login_required
@require_POST
def save_related_ingredients(request, ingredient_id):
    try:
        import json
        data = json.loads(request.body)
        related_ingredient_ids = data.get('related_ingredients', [])
        
        # Get the pantry item
        pantry_item = get_object_or_404(UserPantry, user=request.user, ingredient_id=ingredient_id)
        
        # Try to save with retries
        max_retries = 3
        retry_delay = 0.5  # seconds
        
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Convert string IDs to integers
                    related_ingredient_ids = [int(id) for id in related_ingredient_ids]
                    pantry_item.related_ingredients.set(related_ingredient_ids)
                return JsonResponse({'status': 'success'})
            except OperationalError as e:
                if 'database is locked' in str(e) and attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise
            except ValueError as e:
                return JsonResponse({'status': 'error', 'message': 'Invalid ingredient IDs'}, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def add_to_pantry(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    try:
        UserPantry.objects.get_or_create(user=request.user, ingredient=ingredient)
        return JsonResponse({
            'success': True,
            'message': f'Added {ingredient.name} to your pantry'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required
def remove_from_pantry(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    UserPantry.objects.filter(user=request.user, ingredient=ingredient).delete()
    messages.success(request, f'Removed {ingredient.name} from your pantry')
    return redirect('pantry:pantry_list')

@login_required
def add_ingredient(request):
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'New ingredient added successfully')
            return redirect('pantry_list')
    else:
        form = IngredientForm()
    return render(request, 'pantry/add_ingredient.html', {'form': form})

@login_required
def suggested_ingredients(request):
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1
    
    # Get user's pantry ingredients first
    user_pantry_ingredients = UserPantry.objects.filter(
        user=request.user
    ).values_list('ingredient_id', flat=True)
    
    # Get ingredients ordered by number of recipes that use them, excluding user's pantry
    ingredients = Ingredient.objects.annotate(
        recipe_count=Count('recipeingredient__recipe', distinct=True)
    ).exclude(id__in=user_pantry_ingredients).order_by('-recipe_count', 'name')[:100]
    
    # Paginate results
    paginator = Paginator(ingredients, 20)  # Show 20 items per page
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    return JsonResponse({
        'ingredients': [
            {
                'id': ingredient.id,
                'name': ingredient.name,
                'recipe_count': ingredient.recipe_count
            }
            for ingredient in page_obj
        ],
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages
    })
