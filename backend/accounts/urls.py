from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CreateUserView,
    ForgotPasswordView,
    LoginView,
    MeView,
    ProfileAvatarView,
    ProfileChangePasswordView,
    ProfileView,
    ResetPasswordView,
    SetPasswordView,
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
    path("auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot-password-slash"),
    path("auth/reset-password", ResetPasswordView.as_view(), name="reset-password"),
    path("auth/reset-password/", ResetPasswordView.as_view(), name="reset-password-slash"),
    path("auth/set-password", SetPasswordView.as_view(), name="set-password"),
    path("auth/set-password/", SetPasswordView.as_view(), name="set-password-slash"),
    path("profile", ProfileView.as_view(), name="profile"),
    path("profile/", ProfileView.as_view(), name="profile-slash"),
    path("profile/avatar", ProfileAvatarView.as_view(), name="profile-avatar"),
    path("profile/avatar/", ProfileAvatarView.as_view(), name="profile-avatar-slash"),
    path("profile/change-password", ProfileChangePasswordView.as_view(), name="profile-change-password"),
    path("profile/change-password/", ProfileChangePasswordView.as_view(), name="profile-change-password-slash"),
] + router.urls
