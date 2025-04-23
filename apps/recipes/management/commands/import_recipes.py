import json
import os
from datetime import timedelta, datetime
import pandas as pd
import re
import warnings
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import requests
from tqdm import tqdm

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from ...models import Recipe, RecipeStep, Ingredient, RecipeIngredient, Tag, RecipeTag, RecipeImage

# Suppress all naive datetime warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, message='DateTimeField.*received a naive datetime')
warnings.filterwarnings('ignore', category=RuntimeWarning, module='django.db.models.fields')

class Command(BaseCommand):
    help = 'Import recipes from an Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Excel file')
        parser.add_argument('--batch-size', type=int, default=1000, help='Number of recipes to process in each batch')
        parser.add_argument('--chunk-size', type=int, default=10000, help='Number of rows to read from Excel at once')

    def parse_duration(self, duration_str):
        """
        Parse duration string to timedelta.
        Handles both PT20M format and 00:30:00 format.
        """
        if pd.isna(duration_str):
            return None

        try:
            # If it's already a datetime, return None
            if isinstance(duration_str, (pd.Timestamp, datetime)):
                return None

            # Convert to string if it's not already
            duration_str = str(duration_str)

            if duration_str.startswith('PT'):
                # Handle ISO 8601 duration format
                import re
                match = re.match(r'PT(\d+)H?(\d+)?M?', duration_str)
                if match:
                    hours = int(match.group(1)) if match.group(1) else 0
                    minutes = int(match.group(2)) if match.group(2) else 0
                    return timedelta(hours=hours, minutes=minutes)
            else:
                # Handle HH:MM:SS format
                hours, minutes, seconds = map(int, duration_str.split(':'))
                return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not parse duration {duration_str}: {e}'))
            return None

    def parse_ingredient(self, raw_str):
        """
        Parse ingredient string into amount, unit, and name
        """
        import re
        
        # Strip any leading/trailing whitespace
        raw_str = raw_str.strip()
        
        # Regex to match amount, optional unit, and ingredient name
        pattern = r'^(\d*\.?\d*)\s*(-?\d*\.?\d*)?\s*(\w+)?\s*(.+)?$'
        match = re.match(pattern, raw_str)
        
        if match:
            amount = match.group(1) or match.group(2)
            unit = match.group(3)
            name = (match.group(4) or '').strip()
            
            # If no name found, use the whole match
            if not name and match.group(2):
                name = match.group(2)
        else:
            amount = None
            unit = None
            name = raw_str

        return {
            'amount': float(amount) if amount else None,
            'unit': unit,
            'name': name
        }

    def check_image_accessibility(self, url):
        """Check if an image URL is accessible"""
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def parse_images(self, value):
        """
        Parse image URLs from R-style list format while preserving full URLs
        
        Args:
            value (str): String containing a list of URLs
        
        Returns:
            list: List of cleaned full URLs, limited to 10 items
        """
        if pd.isna(value):
            return []
        
        if isinstance(value, str):
            try:
                # First try to parse as JSON if it's a JSON string
                try:
                    urls = json.loads(value)
                    if isinstance(urls, list):
                        return [url for url in urls if isinstance(url, str) and url.startswith('http')][:10]
                except json.JSONDecodeError:
                    pass
                
                # Remove the c() wrapper if present
                value = value.strip()
                if value.startswith('c(') and value.endswith(')'):
                    value = value[2:-1]
                
                # Use a regex that matches complete URLs, including those with commas
                url_pattern = r'"([^"]+)"'
                found_urls = re.findall(url_pattern, value)
                
                # Clean and filter URLs
                urls = [url for url in found_urls if url.startswith('http')]
                
                # Limit to 10 images
                urls = urls[:10]
                
                if not urls:
                    self.stdout.write(self.style.WARNING(f'No valid URLs found in: {value[:100]}...'))
                elif len(urls) > 10:
                    self.stdout.write(self.style.WARNING(f'Limited recipe images to 10 (had {len(urls)} images)'))
                
                return urls
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error parsing image URLs: {str(e)}'))
                return []
        
        return []

    def safe_decimal(self, value, default=Decimal('0.0')):
        """
        Safely convert a value to a Decimal.
        """
        if pd.isna(value) or value == 'nan':
            return default

        try:
            # Handle different types of input
            if isinstance(value, (int, float)):
                # Convert float to string with fixed precision to avoid scientific notation
                value = f"{value:.10f}"
            elif isinstance(value, str):
                # Clean up the string
                value = value.strip()
                # Remove any scientific notation
                if 'e' in value.lower():
                    value = f"{float(value):.10f}"
            else:
                value = str(value)

            # Try to convert to Decimal
            try:
                decimal_value = Decimal(value)
            except InvalidOperation:
                # If direct conversion fails, try to clean the string
                cleaned_value = re.sub(r'[^\d.-]', '', value)
                if not cleaned_value:
                    return default
                decimal_value = Decimal(cleaned_value)

            # Handle infinity and NaN
            if decimal_value in (Decimal('Infinity'), Decimal('-Infinity'), Decimal('NaN')):
                return default

            # Ensure the value is within valid range for database
            if decimal_value > Decimal('999999.9'):
                return Decimal('999999.9')
            if decimal_value < Decimal('-999999.9'):
                return Decimal('-999999.9')

            # Round to 1 decimal place
            return decimal_value.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error converting value to decimal: {value} ({type(value)}): {str(e)}'))
            return default

    def safe_int(self, value, default=0):
        """
        Safely convert a value to an integer.
        """
        if pd.isna(value) or value == 'nan':
            return default
        try:
            # Convert to float first to handle decimal strings
            float_val = float(value)
            # Round to nearest integer
            return round(float_val)
        except (ValueError, TypeError):
            return default

    def handle(self, *args, **options):
        file_path = options['file_path']
        batch_size = options['batch_size']
        
        self.stdout.write(f'Importing recipes from {file_path}...')
        self.stdout.write(f'Using batch size: {batch_size}')

        # Check if file exists
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        try:
            # Read the entire Excel file at once
            self.stdout.write('Reading Excel file...')
            df = pd.read_excel(file_path)
            
            if df.empty:
                self.stdout.write(self.style.ERROR('No data found in the Excel file'))
                return

            total_rows = len(df)
            self.stdout.write(f'Total rows to process: {total_rows}')

            # Get all existing recipe IDs upfront
            existing_recipe_ids = set(Recipe.objects.values_list('recipe_id', flat=True))
            self.stdout.write(f'Found {len(existing_recipe_ids)} existing recipes')

            # Process recipes in batches
            for i in range(0, len(df), batch_size):
                batch_df = df.iloc[i:i + batch_size]
                try:
                    self._process_batch(batch_df, existing_recipe_ids)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing batch: {str(e)}'))
                    continue

            self.stdout.write(self.style.SUCCESS('Recipe import completed'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading file: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())

    def _process_batch(self, batch_df, existing_recipe_ids):
        # Prepare bulk create/update data
        recipes_to_create = []
        
        for _, row in batch_df.iterrows():
            try:
                # Skip if recipe already exists
                if row['RecipeId'] in existing_recipe_ids:
                    self.stdout.write(self.style.WARNING(f'Skipping existing recipe {row.get("Name", "Unknown")} (ID: {row["RecipeId"]})'))
                    continue
                    
                # Skip recipes with invalid values
                for field in ['AggregatedRating', 'Calories', 'FatContent', 'SaturatedFatContent', 
                            'CholesterolContent', 'SodiumContent', 'CarbohydrateContent', 
                            'FiberContent', 'SugarContent', 'ProteinContent']:
                    if pd.notna(row[field]):
                        try:
                            decimal_value = self.safe_decimal(row[field])
                            if decimal_value in (Decimal('Infinity'), Decimal('-Infinity'), Decimal('NaN')):
                                self.stdout.write(self.style.WARNING(f'Skipping recipe {row.get("Name", "Unknown")} - invalid value for {field}'))
                                continue
                        except Exception:
                            self.stdout.write(self.style.WARNING(f'Skipping recipe {row.get("Name", "Unknown")} - invalid value for {field}'))
                            continue

                recipe_data = {
                    'recipe_id': row['RecipeId'],
                    'name': row['Name'],
                    'cook_time': self.parse_duration(row['CookTime']),
                    'prep_time': self.parse_duration(row['PrepTime']),
                    'total_time': self.parse_duration(row['TotalTime']),
                    'date_published': timezone.make_aware(pd.to_datetime(row['DatePublished'])),
                    'description': row['description'],
                    'recipe_category': row['RecipeCategory'],
                    'aggregated_rating': self.safe_decimal(row['AggregatedRating'], Decimal('0.0')),
                    'review_count': self.safe_int(row['ReviewCount'], 0),
                    'calories': self.safe_decimal(row['Calories'], Decimal('0.0')),
                    'fat_content': self.safe_decimal(row['FatContent'], Decimal('0.0')),
                    'saturated_fat_content': self.safe_decimal(row['SaturatedFatContent'], Decimal('0.0')),
                    'cholesterol_content': self.safe_decimal(row['CholesterolContent'], Decimal('0.0')),
                    'sodium_content': self.safe_decimal(row['SodiumContent'], Decimal('0.0')),
                    'carbohydrate_content': self.safe_decimal(row['CarbohydrateContent'], Decimal('0.0')),
                    'fiber_content': self.safe_decimal(row['FiberContent'], Decimal('0.0')),
                    'sugar_content': self.safe_decimal(row['SugarContent'], Decimal('0.0')),
                    'protein_content': self.safe_decimal(row['ProteinContent'], Decimal('0.0')),
                    'serving_size': row['serving_size'],
                    'servings': self.safe_int(row['servings'], 1),
                }
                
                # Skip recipes that don't have either prep_time or cook_time
                if not recipe_data['prep_time'] and not recipe_data['cook_time']:
                    self.stdout.write(self.style.WARNING(f'Skipping recipe {row.get("Name", "Unknown")} - missing both prep_time and cook_time'))
                    continue
                
                recipes_to_create.append(Recipe(**recipe_data))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Skipping recipe {row.get("Name", "Unknown")} - error: {str(e)}'))
                continue
        
        # Bulk create new recipes
        if recipes_to_create:
            try:
                with transaction.atomic():
                    Recipe.objects.bulk_create(recipes_to_create)
                    self.stdout.write(self.style.SUCCESS(f'Created {len(recipes_to_create)} new recipes'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error during bulk create: {str(e)}'))
                # Try creating recipes one by one
                for recipe in recipes_to_create:
                    try:
                        with transaction.atomic():
                            recipe.save()
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Error creating recipe {recipe.name}: {str(e)}'))
        
        # Process steps, ingredients, tags, and images for each recipe
        for _, row in batch_df.iterrows():
            try:
                recipe = Recipe.objects.filter(recipe_id=row['RecipeId']).first()
                if not recipe:
                    continue
                
                # Process steps
                def parse_list(value):
                    if isinstance(value, str):
                        try:
                            return json.loads(value)
                        except json.JSONDecodeError:
                            # If it's not valid JSON, try to evaluate it as a Python literal
                            try:
                                return eval(value)
                            except:
                                return []
                    return value

                # Process steps
                try:
                    with transaction.atomic():
                        steps = parse_list(row['steps'])
                        RecipeStep.objects.filter(recipe=recipe).delete()
                        steps_to_create = [
                            RecipeStep(
                                recipe=recipe,
                                step_number=i,
                                description=step,
                                order=i
                            )
                            for i, step in enumerate(steps, 1)
                        ]
                        RecipeStep.objects.bulk_create(steps_to_create)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error processing steps for recipe {recipe.name}: {str(e)}'))
                
                # Process ingredients
                try:
                    with transaction.atomic():
                        ingredients = parse_list(row['ingredients'])
                        raw_ingredients = parse_list(row['ingredients_raw_str'])
                        
                        # Get or create ingredients in bulk
                        ingredient_names = [name.lower() for name in ingredients]
                        existing_ingredients = {
                            ing.name: ing 
                            for ing in Ingredient.objects.filter(name__in=ingredient_names)
                        }
                        
                        # Create ingredients one by one to handle duplicates
                        for name in ingredient_names:
                            if name not in existing_ingredients:
                                try:
                                    ingredient = Ingredient.objects.create(name=name)
                                    existing_ingredients[name] = ingredient
                                except Exception as e:
                                    self.stdout.write(self.style.WARNING(f'Error creating ingredient {name}: {e}'))
                                    continue
                        
                        # Create recipe ingredients
                        RecipeIngredient.objects.filter(recipe=recipe).delete()
                        recipe_ingredients_to_create = []
                        for ingredient_name, raw_string in zip(ingredients, raw_ingredients):
                            try:
                                ingredient = existing_ingredients[ingredient_name.lower()]
                                parsed = self.parse_ingredient(raw_string)
                                
                                recipe_ingredients_to_create.append(
                                    RecipeIngredient(
                                        recipe=recipe,
                                        ingredient=ingredient,
                                        raw_string=raw_string,
                                        amount=parsed['amount'],
                                        unit=parsed['unit'],
                                        notes=parsed['name']
                                    )
                                )
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f'Error processing ingredient {ingredient_name}: {e}'))
                                continue
                        
                        RecipeIngredient.objects.bulk_create(recipe_ingredients_to_create)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error processing ingredients for recipe {recipe.name}: {str(e)}'))
                
                # Process tags
                try:
                    with transaction.atomic():
                        tags = parse_list(row['tags'])
                        tag_names = [name.lower() for name in tags]
                        
                        # Get or create tags in bulk
                        existing_tags = {
                            tag.name: tag 
                            for tag in Tag.objects.filter(name__in=tag_names)
                        }
                        
                        # Create tags one by one to handle duplicates
                        for name in tag_names:
                            if name not in existing_tags:
                                try:
                                    tag = Tag.objects.create(name=name)
                                    existing_tags[name] = tag
                                except Exception as e:
                                    self.stdout.write(self.style.WARNING(f'Error creating tag {name}: {e}'))
                                    continue
                        
                        # Create recipe tags
                        RecipeTag.objects.filter(recipe=recipe).delete()
                        recipe_tags_to_create = [
                            RecipeTag(recipe=recipe, tag=existing_tags[name.lower()])
                            for name in tags
                        ]
                        RecipeTag.objects.bulk_create(recipe_tags_to_create)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error processing tags for recipe {recipe.name}: {str(e)}'))
                
                # Process images
                try:
                    with transaction.atomic():
                        RecipeImage.objects.filter(recipe=recipe).delete()
                        image_urls = self.parse_images(row['Images'])
                        images_to_create = [
                            RecipeImage(
                                recipe=recipe,
                                url=url,
                                order=i
                            )
                            for i, url in enumerate(image_urls)
                        ]
                        RecipeImage.objects.bulk_create(images_to_create)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error processing images for recipe {recipe.name}: {str(e)}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing related data for recipe {row.get("Name", "Unknown")}: {str(e)}'))
                continue