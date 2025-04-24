from django.urls import path
from . import views
from allauth.account.views import PasswordResetView, PasswordResetDoneView
from .views import CustomPasswordResetFromKeyView

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('preview-emails/', views.preview_emails, name='preview_emails'),
    path('update-username/', views.update_username, name='update_username'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification_email'),
    path('password/reset/', PasswordResetView.as_view(), name='account_reset_password'),
    path('password/reset/done/', PasswordResetDoneView.as_view(), name='account_reset_password_done'),
    path('password/reset/key/<str:uidb36>-<str:key>/', CustomPasswordResetFromKeyView.as_view(), name='account_reset_password_from_key'),
]
