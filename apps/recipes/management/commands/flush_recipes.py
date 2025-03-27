from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from ...models import Recipe, RecipeStep, Ingredient, RecipeIngredient, Tag, RecipeTag, RecipeImage

class Command(BaseCommand):
    help = 'Flush all recipe-related data while preserving the superuser'

    def handle(self, *args, **options):
        self.stdout.write('Starting to flush recipe data...')
        
        # Store superuser information
        User = get_user_model()
        superuser = User.objects.filter(is_superuser=True).first()
        if superuser:
            self.stdout.write(f'Found superuser: {superuser.username}')
        else:
            self.stdout.write('No superuser found')
            return

        try:
            with transaction.atomic():
                # Delete all recipe-related data
                RecipeImage.objects.all().delete()
                self.stdout.write('Deleted all recipe images')
                
                RecipeStep.objects.all().delete()
                self.stdout.write('Deleted all recipe steps')
                
                RecipeIngredient.objects.all().delete()
                self.stdout.write('Deleted all recipe ingredients')
                
                RecipeTag.objects.all().delete()
                self.stdout.write('Deleted all recipe tags')
                
                Ingredient.objects.all().delete()
                self.stdout.write('Deleted all ingredients')
                
                Tag.objects.all().delete()
                self.stdout.write('Deleted all tags')
                
                Recipe.objects.all().delete()
                self.stdout.write('Deleted all recipes')
                
                # Verify superuser still exists
                if not User.objects.filter(is_superuser=True).exists():
                    self.stdout.write(self.style.ERROR('Superuser was accidentally deleted!'))
                    raise Exception('Superuser was deleted')
                
                self.stdout.write(self.style.SUCCESS('Successfully flushed all recipe data while preserving superuser'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during flush: {str(e)}'))
            raise 