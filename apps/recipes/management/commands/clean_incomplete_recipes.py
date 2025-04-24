from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.recipes.models import Recipe, RecipeIngredient, RecipeStep, RecipeImage

class Command(BaseCommand):
    help = 'Remove recipes that are missing ingredients, steps, or images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        # Get all recipes
        recipes = Recipe.objects.all()
        
        # Find recipes with no ingredients
        no_ingredients = recipes.annotate(
            ingredient_count=Count('recipe_ingredients')
        ).filter(ingredient_count=0)
        
        # Find recipes with no steps
        no_steps = recipes.annotate(
            step_count=Count('steps')
        ).filter(step_count=0)
        
        # Find recipes with no images
        no_images = recipes.annotate(
            image_count=Count('images')
        ).filter(image_count=0)
        
        # Combine all incomplete recipes
        incomplete_recipes = (no_ingredients | no_steps | no_images).distinct()
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN - No recipes will be deleted'))
            self.stdout.write(f'Found {incomplete_recipes.count()} incomplete recipes:')
            
            for recipe in incomplete_recipes:
                self.stdout.write(f'\nRecipe: {recipe.name} (ID: {recipe.recipe_id})')
                if recipe.recipe_ingredients.count() == 0:
                    self.stdout.write('  - No ingredients')
                if recipe.steps.count() == 0:
                    self.stdout.write('  - No steps')
                if recipe.images.count() == 0:
                    self.stdout.write('  - No images')
        else:
            # Delete the incomplete recipes
            count = incomplete_recipes.count()
            incomplete_recipes.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} incomplete recipes')) 