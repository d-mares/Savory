from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, validators=[validate_email])
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def clean(self):
        super().clean()
        if not self.email:
            raise ValidationError({'email': 'Email is required'})
        self.email = self.email.lower()

    def save(self, *args, **kwargs):
        self.full_clean()  # This will call clean() and validate the model
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
