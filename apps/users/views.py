from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .forms import CustomUserCreationForm
from django.http import JsonResponse
import json

# Create your views here.

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Please check your email to verify your account.')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/signup.html', {'form': form})

@login_required
def profile(request):
    context = {
        'user': request.user,
        'is_verified': request.user.is_email_verified,
        'verification_message': 'Your email is verified.' if request.user.is_email_verified else 'Please verify your email to access all features.'
    }
    return render(request, 'users/profile.html', context)

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def preview_emails(request):
    # Create a sample user for preview
    sample_user = request.user
    sample_user.username = "JohnDoe"
    sample_user.first_name = "John"
    sample_user.last_name = "Doe"
    
    # Generate preview URLs
    activate_url = "https://savory.com/confirm-email/abc123"
    password_reset_url = "https://savory.com/reset-password/xyz789"
    
    # Render email templates
    confirmation_email = render_to_string('account/email/email_confirmation_message.html', {
        'user': sample_user,
        'activate_url': activate_url,
    })
    
    reset_email = render_to_string('account/email/password_reset_key_message.html', {
        'user': sample_user,
        'password_reset_url': password_reset_url,
    })
    
    context = {
        'confirmation_email': confirmation_email,
        'reset_email': reset_email,
    }
    return render(request, 'users/email_preview.html', context)

@login_required
def update_username(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_username = data.get('username', '').strip()
            if new_username:
                request.user.username = new_username
                request.user.save()
                return JsonResponse({
                    'success': True,
                    'username': new_username
                })
            return JsonResponse({
                'success': False,
                'error': 'Username cannot be empty'
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            })
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })
