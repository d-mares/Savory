from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Ingredient, UserPantry
from .forms import IngredientForm
import urllib.parse

# Create your views here.

@login_required
def pantry_list(request):
    user_pantry = UserPantry.objects.filter(user=request.user)
    return render(request, 'pantry/pantry_list.html', {
        'user_pantry': user_pantry,
    })

@login_required
def search_ingredients(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'ingredients': []})
    
    # Decode the query to handle special characters
    query = urllib.parse.unquote(query)
    
    ingredients = Ingredient.objects.filter(name__icontains=query)[:10]
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
@csrf_exempt
def save_related_ingredients(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    pantry_item = get_object_or_404(UserPantry, user=request.user, ingredient=ingredient)
    
    import json
    data = json.loads(request.body)
    related_ingredient_ids = data.get('related_ingredients', [])
    
    # Remove the current ingredient from the list if it's there
    if ingredient_id in related_ingredient_ids:
        related_ingredient_ids.remove(ingredient_id)
    
    # Update related ingredients
    pantry_item.related_ingredients.set(related_ingredient_ids)
    
    return JsonResponse({'status': 'success'})

@login_required
def add_to_pantry(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    UserPantry.objects.get_or_create(user=request.user, ingredient=ingredient)
    messages.success(request, f'Added {ingredient.name} to your pantry')
    return redirect('pantry:pantry_list')

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
