from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

class Recipe(models.Model):
    recipe_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    cook_time = models.DurationField(null=True, blank=True)  # Format: 00:30:00
    prep_time = models.DurationField(null=True, blank=True)  # Format: 00:15:00
    total_time = models.DurationField(null=True, blank=True)  # Format: 00:35:00
    date_published = models.DateTimeField()
    description = models.TextField()
    recipe_category = models.CharField(max_length=100)
    aggregated_rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    review_count = models.IntegerField()
    calories = models.DecimalField(max_digits=6, decimal_places=1)
    fat_content = models.DecimalField(max_digits=6, decimal_places=1)
    saturated_fat_content = models.DecimalField(max_digits=6, decimal_places=1)
    cholesterol_content = models.DecimalField(max_digits=6, decimal_places=1)
    sodium_content = models.DecimalField(max_digits=6, decimal_places=1)
    carbohydrate_content = models.DecimalField(max_digits=6, decimal_places=1)
    fiber_content = models.DecimalField(max_digits=6, decimal_places=1)
    sugar_content = models.DecimalField(max_digits=6, decimal_places=1)
    protein_content = models.DecimalField(max_digits=6, decimal_places=1)
    serving_size = models.CharField(max_length=50)
    servings = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.prep_time and not self.cook_time:
            raise ValidationError({
                'prep_time': 'At least one of prep_time or cook_time must be provided.',
                'cook_time': 'At least one of prep_time or cook_time must be provided.'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class RecipeImage(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='images', on_delete=models.CASCADE)
    url = models.URLField(max_length=500)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.recipe.name} - Image {self.order}"

class RecipeStep(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='steps', on_delete=models.CASCADE)
    step_number = models.IntegerField()
    description = models.TextField()
    order = models.IntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.recipe.name} - Step {self.step_number}"

class Ingredient(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='recipe_ingredients', on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    raw_string = models.TextField()  # Store the original ingredient string with measurements
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.recipe.name} - {self.ingredient.name}"

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class RecipeTag(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='recipe_tags', on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['recipe', 'tag']

    def __str__(self):
        return f"{self.recipe.name} - {self.tag.name}"
