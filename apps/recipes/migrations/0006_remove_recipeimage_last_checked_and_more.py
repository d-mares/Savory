# Generated by Django 5.1.7 on 2025-03-27 13:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0005_recipeimage_last_checked_recipeimage_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='recipeimage',
            name='last_checked',
        ),
        migrations.RemoveField(
            model_name='recipeimage',
            name='status',
        ),
    ]
