from django.db import models
from django.contrib.auth import get_user_model
from apps.recipes.models import Ingredient

User = get_user_model()

class ShoppingList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_list_items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    is_checked = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'ingredient']
        ordering = ['ingredient__name']  # Order by ingredient name alphabetically

    def __str__(self):
        return f"{self.user.username}'s shopping list: {self.ingredient.name}"
