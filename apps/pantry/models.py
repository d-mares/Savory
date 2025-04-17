from django.db import models
from django.contrib.auth import get_user_model
from apps.recipes.models import Ingredient

User = get_user_model()

class UserPantry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pantry_items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    related_ingredients = models.ManyToManyField(Ingredient, related_name='related_to', blank=True)

    class Meta:
        unique_together = ['user', 'ingredient']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username}'s {self.ingredient.name}"
