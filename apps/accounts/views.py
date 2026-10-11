from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from .forms import SignInForm


class SignInView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = SignInForm
    redirect_authenticated_user = True


class SignOutView(auth_views.LogoutView):
    """POST-only (Django 5 removed GET logout)."""

    next_page = reverse_lazy("accounts:login")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, "You have been signed out.")
        return response


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("studio:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your password has been changed.")
        return response
