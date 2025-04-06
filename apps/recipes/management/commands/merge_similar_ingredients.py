import json
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from rapidfuzz import process, fuzz
from ...models import Ingredient, RecipeIngredient
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Merge similar ingredients while preserving recipe relationships'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=85,
            help='Similarity threshold (0-100). Higher values mean stricter matching. Default: 85'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be merged without actually merging'
        )
        parser.add_argument(
            '--min-recipes',
            type=int,
            default=1,
            help='Only consider ingredients used in at least this many recipes. Default: 1'
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        dry_run = options['dry_run']
        min_recipes = options['min_recipes']

        # Get all ingredients with their recipe count
        ingredients = list(Ingredient.objects.annotate(
            recipe_count=Count('recipeingredient')
        ).filter(
            recipe_count__gte=min_recipes
        ).order_by('-recipe_count'))

        if not ingredients:
            self.stdout.write(self.style.WARNING('No ingredients found to process'))
            return

        self.stdout.write(f'Found {len(ingredients)} ingredients to process')
        
        # Track which ingredients have been processed
        processed = set()
        merge_groups = []

        # Process each ingredient
        for base_ingredient in tqdm(ingredients, desc="Finding similar ingredients"):
            if base_ingredient.id in processed:
                continue

            # Get the ingredient name for matching
            base_name = base_ingredient.name.lower()
            
            # Find similar ingredients
            similar_ingredients = []
            
            # Get all other ingredients not yet processed
            remaining_ingredients = [
                ing for ing in ingredients 
                if ing.id not in processed and ing.id != base_ingredient.id
            ]
            
            # Get their names for matching
            remaining_names = [ing.name.lower() for ing in remaining_ingredients]
            
            # Find matches using RapidFuzz
            matches = process.extract(
                base_name,
                remaining_names,
                scorer=fuzz.ratio,
                score_cutoff=threshold
            )
            
            if matches:
                group = [base_ingredient]
                for match_name, score, _ in matches:
                    # Find the matching ingredient object
                    match_ingredient = next(
                        ing for ing in remaining_ingredients 
                        if ing.name.lower() == match_name
                    )
                    group.append(match_ingredient)
                    processed.add(match_ingredient.id)
                
                merge_groups.append(group)
                processed.add(base_ingredient.id)

        if not merge_groups:
            self.stdout.write(self.style.SUCCESS('No similar ingredients found to merge'))
            return

        # Report findings
        self.stdout.write('\nFound the following groups of similar ingredients:')
        for group in merge_groups:
            recipes_count = sum(ing.recipe_count for ing in group)
            ingredients_str = ', '.join(f"{ing.name} ({ing.recipe_count} recipes)" for ing in group)
            self.stdout.write(f"- Group with {recipes_count} total recipes:")
            self.stdout.write(f"  {ingredients_str}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS('\nDry run completed. Use without --dry-run to perform the merges.'))
            return

        # Confirm before proceeding
        if input('\nProceed with merging? (y/n): ').lower() != 'y':
            self.stdout.write(self.style.SUCCESS('Merge cancelled'))
            return

        # Perform the merges
        merged_count = 0
        recipes_updated = 0
        
        for group in tqdm(merge_groups, desc="Merging ingredients"):
            try:
                with transaction.atomic():
                    # Use the most frequently used ingredient as the primary
                    primary = max(group, key=lambda x: x.recipe_count)
                    to_merge = [ing for ing in group if ing.id != primary.id]
                    
                    for ingredient in to_merge:
                        # Update all recipe relationships to point to the primary ingredient
                        updated = RecipeIngredient.objects.filter(
                            ingredient=ingredient
                        ).update(ingredient=primary)
                        
                        recipes_updated += updated
                        
                        # Delete the merged ingredient
                        ingredient.delete()
                        merged_count += 1
                        
                        self.stdout.write(
                            f"Merged '{ingredient.name}' into '{primary.name}', "
                            f"updated {updated} recipes"
                        )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error merging group with primary '{primary.name}': {str(e)}"
                    )
                )
                continue

        self.stdout.write(self.style.SUCCESS(
            f'\nMerged {merged_count} ingredients, updated {recipes_updated} recipe relationships'
        )) 