from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import ShoppingList
from apps.recipes.models import Ingredient
from apps.pantry.models import UserPantry

@login_required
def shopping_list(request):
    shopping_items = ShoppingList.objects.filter(user=request.user)
    return render(request, 'shopping/shopping_list.html', {
        'shopping_items': shopping_items,
    })

@login_required
@require_POST
def add_to_shopping_list(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    ShoppingList.objects.get_or_create(user=request.user, ingredient=ingredient)
    return JsonResponse({'success': True})

@login_required
@require_POST
def remove_from_shopping_list(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    ShoppingList.objects.filter(user=request.user, ingredient=ingredient).delete()
    return JsonResponse({'success': True})

@login_required
@require_POST
def toggle_item(request, ingredient_id):
    ingredient = get_object_or_404(Ingredient, id=ingredient_id)
    item = get_object_or_404(ShoppingList, user=request.user, ingredient=ingredient)
    item.is_checked = not item.is_checked
    item.save()
    return JsonResponse({'success': True, 'is_checked': item.is_checked})

@login_required
def search_ingredients(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'ingredients': []})
    
    ingredients = Ingredient.objects.filter(name__icontains=query)[:10]
    return JsonResponse({
        'ingredients': [{'id': i.id, 'name': i.name} for i in ingredients]
    })

@login_required
@require_POST
def complete_shopping_trip(request):
    # Get all checked items
    checked_items = ShoppingList.objects.filter(user=request.user, is_checked=True)
    
    # Add checked items to pantry
    for item in checked_items:
        UserPantry.objects.get_or_create(
            user=request.user,
            ingredient=item.ingredient
        )
    
    # Remove checked items from shopping list
    checked_items.delete()
    
    return JsonResponse({'success': True, 'count': checked_items.count()})
