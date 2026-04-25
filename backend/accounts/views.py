from django.contrib.auth import authenticate
from django.db import models
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from auditlogs.models import log_audit
from config.pagination import StandardResultsSetPagination

from .models import User
from .serializers import UserSerializer
from .throttles import LoginRateThrottle


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
        if not request.user.check_password(request.data.get("current_password")):
            return Response({"error": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(request.data.get("new_password"))
        request.user.save()
        log_audit(request.user, "UPDATE_PASSWORD", "Updated personal account password")
        return Response({"message": "Password updated successfully"})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({"message": "If the email exists, password reset instructions will be sent."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({"message": "Password reset endpoint is ready for email-token integration."})


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination

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

    def perform_update(self, serializer):
        user = serializer.save()
        log_audit(self.request.user, "UPDATE_USER", f"Updated user: {user.email}")

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response({"error": "You cannot delete your own account."}, status=status.HTTP_400_BAD_REQUEST)
        email = user.email
        user.delete()
        log_audit(request.user, "DELETE_USER", f"Deleted user: {email}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        if "isActive" in request.data:
            user.is_active_status = bool(request.data["isActive"])
            user.save(update_fields=["is_active_status"])
            return Response(UserSerializer(user).data)
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["patch"], url_path="status")
    def status(self, request, pk=None):
        user = self.get_object()
        if user == request.user and request.data.get("isActive") is False:
            return Response({"error": "You cannot deactivate your own account."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_active_status = bool(request.data.get("isActive"))
        user.save(update_fields=["is_active_status"])
        return Response(UserSerializer(user).data)
