from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CreateUserView,
    ForgotPasswordView,
    LoginView,
    MeView,
    ResetPasswordView,
    UpdatePasswordView,
    UserViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("user/register", CreateUserView.as_view(), name="register"),
    path("auth/login", LoginView.as_view(), name="app-login"),
    path("auth/login/", LoginView.as_view(), name="app-login-slash"),
    path("auth/me", MeView.as_view(), name="app-me"),
    path("auth/update-password", UpdatePasswordView.as_view(), name="update-password"),
    path("auth/update-password/", UpdatePasswordView.as_view(), name="update-password-slash"),
    path("auth/forgot-password", ForgotPasswordView.as_view(), name="forgot-password"),
    path("auth/reset-password", ResetPasswordView.as_view(), name="reset-password"),
] + router.urls
