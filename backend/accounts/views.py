import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from auditlogs.models import log_audit
from config.pagination import StandardResultsSetPagination

from .models import User
from .serializers import ForgotPasswordSerializer, PasswordChangeSerializer, PasswordResetConfirmSerializer, UserSerializer
from .throttles import LoginRateThrottle

logger = logging.getLogger(__name__)
LAST_ACTIVE_ADMIN_MESSAGE = "At least one active Admin must remain in the system."


def role_label(role):
    return {
        "admin": "Admin",
        "dept_head": "Dept Head",
        "staff": "Staff",
    }.get(role, role)


class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        user = authenticate(
            request,
            email=request.data.get("email"),
            password=request.data.get("password"),
        )
        if not user or not user.is_active_status:
            return Response({"error": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        log_audit(user, "LOGIN", "User logged in from web interface", ip_address=request.META.get("REMOTE_ADDR"))
        return Response(
            {
                "token": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }
        )


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UpdatePasswordView(APIView):
    def post(self, request):
        logger.debug("Password update payload keys: %s", sorted(request.data.keys()))
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            errors = serializer.errors
            if isinstance(errors, dict) and "message" in errors:
                message = errors["message"]
                if isinstance(message, list):
                    message = message[0]
                response_data = {"message": str(message)}
                if "errors" in errors:
                    response_data["errors"] = errors["errors"]
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {
                    "message": "Password does not meet security requirements.",
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        log_audit(request.user, "UPDATE_PASSWORD", "Updated personal account password")
        return Response({"message": "Password updated successfully. Please login again."})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active_status=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
            context = {
                "user": user,
                "user_display_name": user.get_full_name() or user.email,
                "reset_link": reset_link,
            }
            html_message = render_to_string("emails/password_reset_email.html", context)
            text_message = strip_tags(html_message)
            try:
                email_message = EmailMultiAlternatives(
                    subject="Password Reset Request",
                    body=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                email_message.attach_alternative(html_message, "text/html")
                email_message.send(fail_silently=False)
                log_audit(
                    user,
                    "PASSWORD_RESET_REQUEST",
                    f"Password reset email requested for {user.email}",
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
            except Exception:
                logger.exception("Failed to send password reset email for user id %s", user.pk)

        return Response({"message": "If this email exists, a password reset link has been sent."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            message = errors.get("message") if isinstance(errors, dict) else None
            if isinstance(message, list):
                message = message[0]
            response_data = {"message": str(message or "Password reset failed."), "errors": errors}
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        log_audit(
            user,
            "PASSWORD_RESET_SUCCESS",
            f"Password reset completed for {user.email}",
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response({"message": "Password reset successful. Please login."})


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination

    def get_serializer(self, *args, **kwargs):
        data = kwargs.get("data")
        if data is not None:
            normalized = data.copy()
            if "org_unit" in normalized and "orgUnitId" not in normalized:
                normalized["orgUnitId"] = normalized.pop("org_unit")
            if normalized.get("orgUnitId") == "":
                normalized["orgUnitId"] = None
            kwargs["data"] = normalized
        return super().get_serializer(*args, **kwargs)

    def _active_admin_count(self):
        return User.objects.filter(role="admin", is_active_status=True).count()

    def _is_last_active_admin(self, user):
        return user.role == "admin" and user.is_active_status and self._active_admin_count() == 1

    def _as_bool(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def _last_admin_response(self):
        return Response({"message": LAST_ACTIVE_ADMIN_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)

    def _serializer_error_response(self, errors):
        message = errors
        if isinstance(errors, dict):
            message = errors.get("message") or errors.get("non_field_errors") or next(iter(errors.values()), None)
        if isinstance(message, (list, tuple)):
            message = message[0] if message else "Request validation failed."
        return Response(
            {"message": str(message), "errors": errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _would_remove_last_active_admin(self, user, data):
        if not self._is_last_active_admin(user):
            return False

        requested_role = data.get("role")
        if requested_role is not None and requested_role != "admin":
            return True

        requested_active = data.get("isActive", data.get("is_active_status"))
        if requested_active is not None and not self._as_bool(requested_active):
            return True

        return False

    def get_queryset(self):
        queryset = User.objects.select_related("org_unit").order_by("email")
        search = self.request.query_params.get("search")
        role = self.request.query_params.get("role")
        org_unit_id = self.request.query_params.get("orgUnitId")

        if search:
            queryset = queryset.filter(
                models.Q(email__icontains=search)
                | models.Q(first_name__icontains=search)
                | models.Q(last_name__icontains=search)
            )
        if role:
            queryset = queryset.filter(role=role)
        if org_unit_id:
            queryset = queryset.filter(org_unit_id=org_unit_id)
        return queryset

    def perform_create(self, serializer):
        user = serializer.save()
        log_audit(self.request.user, "CREATE_USER", f"Created user: {user.email}")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self._serializer_error_response(serializer.errors)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        old_role = serializer.instance.role
        old_name = serializer.instance.get_full_name() or serializer.instance.email
        old_email = serializer.instance.email
        user = serializer.save()
        new_name = user.get_full_name() or user.email
        if old_role != user.role:
            log_audit(
                self.request.user,
                "UPDATE_USER",
                f"Updated user role: {old_name} from {role_label(old_role)} to {role_label(user.role)}",
            )
        elif old_name != new_name or old_email != user.email:
            log_audit(self.request.user, "UPDATE_USER", f"Updated user: {old_name} to {new_name}")
        else:
            log_audit(self.request.user, "UPDATE_USER", f"Updated user: {user.email}")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        user = self.get_object()
        if self._would_remove_last_active_admin(user, request.data):
            return self._last_admin_response()
        serializer = self.get_serializer(user, data=request.data, partial=partial)
        if not serializer.is_valid():
            return self._serializer_error_response(serializer.errors)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if self._is_last_active_admin(user):
            return self._last_admin_response()
        if user == request.user:
            return Response({"error": "You cannot delete your own account."}, status=status.HTTP_400_BAD_REQUEST)
        email = user.email
        user.delete()
        log_audit(request.user, "DELETE_USER", f"Deleted user: {email}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        if self._would_remove_last_active_admin(user, request.data):
            return self._last_admin_response()
        if "isActive" in request.data:
            user.is_active_status = self._as_bool(request.data["isActive"])
            user.save(update_fields=["is_active_status"])
            return Response(UserSerializer(user).data)
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["patch"], url_path="status")
    def status(self, request, pk=None):
        user = self.get_object()
        requested_active = request.data.get("isActive")
        if requested_active is None:
            return Response({"message": "isActive is required."}, status=status.HTTP_400_BAD_REQUEST)
        if self._is_last_active_admin(user) and requested_active is not None and not self._as_bool(requested_active):
            return self._last_admin_response()
        if user == request.user and requested_active is not None and not self._as_bool(requested_active):
            return Response({"error": "You cannot deactivate your own account."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active_status = self._as_bool(requested_active)
        user.save(update_fields=["is_active_status"])
        return Response(UserSerializer(user).data)
