from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render
from django.db import models
from django.db.models import Q
from .models import Recipe, RecipeStep, Ingredient, RecipeIngredient, Tag, RecipeTag, RecipeImage, CarouselItem

class RecipeImageInline(admin.TabularInline):
    model = RecipeImage
    extra = 1
    fields = ('url', 'order', 'preview')
    readonly_fields = ('preview',)
    
    def preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.url)
        return "No image"
    preview.short_description = 'Preview'

class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 1
    fields = ('step_number', 'description', 'order')
    ordering = ('order',)

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    fields = ('ingredient', 'amount', 'unit', 'notes')

class RecipeTagInline(admin.TabularInline):
    model = RecipeTag
    extra = 1

class IngredientFilter(admin.SimpleListFilter):
    title = 'Ingredients'
    parameter_name = 'ingredients'

    def lookups(self, request, model_admin):
        ingredients = Ingredient.objects.all().order_by('name')
        return [(str(i.id), i.name) for i in ingredients]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(recipe_ingredients__ingredient_id=self.value()).distinct()
        return queryset

class RecipeCategoryFilter(admin.SimpleListFilter):
    title = 'Recipe Category'
    parameter_name = 'recipe_category'

    def lookups(self, request, model_admin):
        categories = Recipe.objects.values_list('recipe_category', flat=True).distinct().order_by('recipe_category')
        return [(category, category) for category in categories]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(recipe_category=self.value())
        return queryset

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'recipe_id', 'recipe_category', 'cook_time', 'prep_time', 'total_time', 'date_published', 'aggregated_rating', 'review_count')
    list_filter = ('recipe_category', 'date_published', IngredientFilter)
    search_fields = ('name', 'description', 'recipe_category')
    readonly_fields = ('recipe_id', 'created_at', 'updated_at')
    inlines = [RecipeImageInline, RecipeStepInline, RecipeIngredientInline, RecipeTagInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('recipe_id', 'name', 'description', 'recipe_category', 'date_published')
        }),
        ('Timing', {
            'fields': ('cook_time', 'prep_time', 'total_time')
        }),
        ('Nutritional Information', {
            'fields': (
                'calories', 'fat_content', 'saturated_fat_content', 'cholesterol_content',
                'sodium_content', 'carbohydrate_content', 'fiber_content', 'sugar_content',
                'protein_content'
            )
        }),
        ('Ratings and Reviews', {
            'fields': ('aggregated_rating', 'review_count')
        }),
        ('Servings', {
            'fields': ('serving_size', 'servings')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(RecipeImage)
class RecipeImageAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'url', 'order', 'preview', 'created_at')
    list_filter = ('recipe', 'created_at')
    search_fields = ('recipe__name', 'url')
    readonly_fields = ('preview', 'created_at')
    autocomplete_fields = ['recipe']
    
    def get_search_results(self, request, queryset, search_term):
        # If there's a recipe_id in the GET parameters, filter by that recipe
        recipe_id = request.GET.get('recipe_id')
        if recipe_id:
            queryset = queryset.filter(recipe_id=recipe_id)
        return super().get_search_results(request, queryset, search_term)
    
    def preview(self, obj):
        if obj.url:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.url)
        return "No image"
    preview.short_description = 'Preview'

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'recipe_count', 'view_recipes_link')
    search_fields = ('name',)
    show_full_result_count = False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipe_count=models.Count('recipeingredient__recipe', distinct=True)
        ).order_by('-recipe_count', 'name')

    def recipe_count(self, obj):
        return obj.recipe_count
    recipe_count.admin_order_field = 'recipe_count'

    def view_recipes_link(self, obj):
        url = reverse('admin:recipes_recipe_changelist')
        return format_html(
            '<a href="{}?ingredients={}">View Recipes</a>',
            url,
            obj.id
        )
    view_recipes_link.short_description = 'View Recipes'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:ingredient_id>/recipes/',
                self.admin_site.admin_view(self.recipe_list_view),
                name='ingredient-recipe-list',
            ),
        ]
        return custom_urls + urls

    def recipe_list_view(self, request, ingredient_id):
        ingredient = self.get_object(request, ingredient_id)
        recipes = Recipe.objects.filter(recipeingredient__ingredient=ingredient)
        context = {
            'ingredient': ingredient,
            'recipes': recipes,
            'opts': self.model._meta,
        }
        return render(request, 'admin/recipes/ingredient_recipe_list.html', context)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'recipe_count', 'view_recipes_link')
    search_fields = ('name',)
    show_full_result_count = False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipe_count=models.Count('recipetag__recipe', distinct=True)
        ).order_by('-recipe_count', 'name')

    def recipe_count(self, obj):
        return obj.recipe_count
    recipe_count.admin_order_field = 'recipe_count'

    def view_recipes_link(self, obj):
        url = reverse('admin:recipes_recipe_changelist')
        return format_html(
            '<a href="{}?tags={}">View Recipes</a>',
            url,
            obj.id
        )
    view_recipes_link.short_description = 'View Recipes'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:tag_id>/recipes/',
                self.admin_site.admin_view(self.recipe_list_view),
                name='tag-recipe-list',
            ),
        ]
        return custom_urls + urls

    def recipe_list_view(self, request, tag_id):
        tag = self.get_object(request, tag_id)
        recipes = Recipe.objects.filter(recipetag__tag=tag)
        context = {
            'tag': tag,
            'recipes': recipes,
            'opts': self.model._meta,
        }
        return render(request, 'admin/recipes/tag_recipe_list.html', context)

@admin.register(RecipeStep)
class RecipeStepAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'step_number', 'description')
    list_filter = ('recipe',)
    search_fields = ('description', 'recipe__name')
    ordering = ('recipe', 'order')

@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount', 'unit')
    list_filter = ('recipe', 'ingredient')
    search_fields = ('recipe__name', 'ingredient__name', 'raw_string')
    ordering = ('recipe', 'ingredient')

@admin.register(RecipeTag)
class RecipeTagAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'tag')
    list_filter = ('recipe', 'tag')
    search_fields = ('recipe__name', 'tag__name')
    ordering = ('recipe', 'tag')

@admin.register(CarouselItem)
class CarouselItemAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'image_preview', 'order', 'active', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('recipe__name',)
    ordering = ('order',)
    actions = ['delete_selected']
    autocomplete_fields = ['recipe']
    readonly_fields = ('image_preview', 'created_at', 'updated_at')
    fields = ('recipe', 'image', 'order', 'active', 'image_preview')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipe', 'image')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "recipe":
            kwargs["queryset"] = Recipe.objects.order_by('-aggregated_rating')
        elif db_field.name == "image":
            # Start with an empty queryset
            kwargs["queryset"] = RecipeImage.objects.none()
            
            # If we have a recipe_id (either from existing object or POST data)
            recipe_id = None
            if request.resolver_match.kwargs.get('object_id'):
                carousel_item = self.get_object(request, request.resolver_match.kwargs['object_id'])
                if carousel_item:
                    recipe_id = carousel_item.recipe_id
                    kwargs["queryset"] = RecipeImage.objects.filter(recipe_id=recipe_id)
            elif request.method == 'POST':
                recipe_id = request.POST.get('recipe')
                if recipe_id:
                    kwargs["queryset"] = RecipeImage.objects.filter(recipe_id=recipe_id)
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def image_preview(self, obj):
        if obj.image and obj.image.url:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" alt="Preview of {}" />',
                obj.image.url,
                obj.recipe.name if obj.recipe else "selected image"
            )
        return "No image"
    image_preview.short_description = 'Preview'

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'admin/js/core.js',
            'admin/js/carousel_item_admin.js',
        )
