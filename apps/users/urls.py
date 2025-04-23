from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('preview-emails/', views.preview_emails, name='preview_emails'),
    path('update-username/', views.update_username, name='update_username'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification_email'),
]
