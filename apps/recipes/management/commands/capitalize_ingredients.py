from django.core.management.base import BaseCommand
from apps.recipes.models import Ingredient

class Command(BaseCommand):
    help = 'Capitalize all ingredient names'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing anything',
        )

    def handle(self, *args, **options):
        ingredients = Ingredient.objects.all()
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            self.stdout.write('The following ingredients would be capitalized:')
            
            for ingredient in ingredients:
                current_name = ingredient.name
                capitalized_name = ' '.join(word.capitalize() for word in current_name.split())
                if current_name != capitalized_name:
                    self.stdout.write(f'\n{current_name} -> {capitalized_name}')
        else:
            count = 0
            for ingredient in ingredients:
                current_name = ingredient.name
                capitalized_name = ' '.join(word.capitalize() for word in current_name.split())
                if current_name != capitalized_name:
                    ingredient.name = capitalized_name
                    ingredient.save()
                    count += 1
            
            self.stdout.write(self.style.SUCCESS(f'Successfully capitalized {count} ingredients')) 