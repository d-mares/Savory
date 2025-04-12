from django.core.management.base import BaseCommand
from django.db import transaction
from urllib.parse import unquote
from apps.recipes.models import Ingredient, RecipeIngredient
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fixes URL-encoded characters in ingredient names'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Run in test mode (show changes without applying them)',
        )

    def handle(self, *args, **options):
        # Get all ingredients that contain % in their name
        ingredients = Ingredient.objects.filter(name__contains='%')
        total_ingredients = ingredients.count()
        
        self.stdout.write(f'Found {total_ingredients} ingredients with URL-encoded characters')
        
        if options['test']:
            self.stdout.write(self.style.WARNING('Running in TEST MODE - no changes will be made'))
        
        fixed_count = 0
        with transaction.atomic():
            for ingredient in ingredients:
                original_name = ingredient.name
                # Decode the URL-encoded characters
                decoded_name = unquote(original_name)
                
                if decoded_name != original_name:
                    # Check if an ingredient with the decoded name already exists
                    existing_ingredient = Ingredient.objects.filter(name=decoded_name).first()
                    
                    if existing_ingredient:
                        if options['test']:
                            # If it exists, show what would be updated
                            recipe_count = RecipeIngredient.objects.filter(ingredient=ingredient).count()
                            self.stdout.write(f'Would update {recipe_count} recipes from: {original_name} -> {decoded_name}')
                            self.stdout.write(f'Would delete ingredient: {original_name}')
                        else:
                            # If it exists, update all RecipeIngredient references to point to the existing ingredient
                            recipe_count = RecipeIngredient.objects.filter(ingredient=ingredient).count()
                            RecipeIngredient.objects.filter(ingredient=ingredient).update(ingredient=existing_ingredient)
                            # Delete the duplicate ingredient
                            ingredient.delete()
                            self.stdout.write(f'Updated {recipe_count} recipes from: {original_name} -> {decoded_name}')
                            self.stdout.write(f'Deleted ingredient: {original_name}')
                    else:
                        if options['test']:
                            # If it doesn't exist, show what would be updated
                            self.stdout.write(f'Would update: {original_name} -> {decoded_name}')
                        else:
                            # If it doesn't exist, update the ingredient name
                            ingredient.name = decoded_name
                            ingredient.save()
                            self.stdout.write(f'Updated: {original_name} -> {decoded_name}')
                    
                    fixed_count += 1
            
            if options['test']:
                # Rollback the transaction in test mode
                self.stdout.write(self.style.WARNING('\nThis was a test run - no changes were made'))
                self.stdout.write(self.style.SUCCESS(f'Would have fixed {fixed_count} ingredients'))
                return
        
        self.stdout.write(self.style.SUCCESS(f'Successfully fixed {fixed_count} ingredients')) 