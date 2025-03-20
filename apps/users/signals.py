from django.dispatch import receiver
from allauth.account.signals import email_confirmed
from .models import CustomUser

@receiver(email_confirmed)
def update_user_email_verified(sender, request, email_address, **kwargs):
    user = email_address.user
    user.is_email_verified = True
    user.save() 