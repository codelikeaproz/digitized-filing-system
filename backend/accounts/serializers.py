import binascii

from django.conf import settings
from rest_framework import serializers
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import password_changed
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import DjangoUnicodeDecodeError, force_str
from django.utils.http import urlsafe_base64_decode

from config.timezone_utils import format_local_datetime
from documents.permissions import get_accessible_org_unit_ids
from orgunits.models import OrgUnit
from .models import User

ALLOWED_NAME_SUFFIXES = {"", "Jr.", "Sr.", "I", "II", "III", "IV", "V"}
from config.employee_number import (
    is_legacy_numeric_employee_number,
    normalize_employee_number,
    validate_employee_number_value as shared_validate_employee_number,
)


def validate_employee_number_value(value, instance=None):
    employee_number = normalize_employee_number(value)
    if not employee_number:
        return None

    allow_legacy = bool(
        instance is not None
        and instance.employee_number
        and is_legacy_numeric_employee_number(instance.employee_number)
        and is_legacy_numeric_employee_number(employee_number)
    )
    error = shared_validate_employee_number(employee_number, required=True, allow_legacy=allow_legacy)
    if error:
        raise serializers.ValidationError(error)

    queryset = User.objects.filter(employee_number__iexact=employee_number)
    if instance is not None:
        queryset = queryset.exclude(pk=instance.pk)
    if queryset.exists():
        raise serializers.ValidationError("Employee number is already in use.")

    return employee_number


def build_profile_picture_url(user, request=None):
    if not user.profile_picture:
        return None
    if request is not None:
        return request.build_absolute_uri(user.profile_picture.url)
    return user.profile_picture.url


def build_full_name(user):
    parts = [user.first_name, user.last_name]
    if getattr(user, "suffix", ""):
        parts.append(user.suffix)
    return " ".join(part for part in parts if part).strip()


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    fullName = serializers.SerializerMethodField()
    firstName = serializers.CharField(source="first_name", required=False, allow_blank=True)
    lastName = serializers.CharField(source="last_name", required=False, allow_blank=True)
    suffix = serializers.CharField(required=False, allow_blank=True)
    employeeNumber = serializers.CharField(source="employee_number", required=False, allow_blank=True)
    orgUnitId = serializers.CharField(source="org_unit_id", required=False, allow_blank=True, allow_null=True)
    orgUnitName = serializers.CharField(source="org_unit.name", read_only=True)
    isActive = serializers.BooleanField(source="is_active_status", required=False)
    createdAt = serializers.SerializerMethodField()
    isLastActiveAdmin = serializers.SerializerMethodField()
    hasUsablePassword = serializers.SerializerMethodField()
    activationStatus = serializers.CharField(source="activation_status", read_only=True)
    activationEmailSentAt = serializers.SerializerMethodField()
    activationExpiresAt = serializers.SerializerMethodField()
    profilePictureUrl = serializers.SerializerMethodField()
    canManage = serializers.SerializerMethodField()
    confirmPassword = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "confirmPassword",
            "fullName",
            "firstName",
            "lastName",
            "suffix",
            "employeeNumber",
            "role",
            "orgUnitId",
            "orgUnitName",
            "profilePictureUrl",
            "canManage",
            "isActive",
            "createdAt",
            "isLastActiveAdmin",
            "hasUsablePassword",
            "activationStatus",
            "activationEmailSentAt",
            "activationExpiresAt",
        ]
        extra_kwargs = {"password": {"write_only": True, "required": False, "trim_whitespace": False}}

    def _can_manager_set_password(self):
        request = self.context.get("request")
        if not request or not getattr(request.user, "is_authenticated", False):
            return False
        return getattr(request.user, "role", None) in {"admin", "dept_head"}

    def _validate_manager_password(self, attrs):
        password = attrs.pop("password", None) or None
        confirm_password = attrs.pop("confirmPassword", None) or None

        if password:
            if not self._can_manager_set_password():
                raise serializers.ValidationError(
                    {"password": "Only Admin or Dept Head can set user passwords."}
                )
            if password != confirm_password:
                raise serializers.ValidationError({"message": "Password and confirm password do not match."})

            user_for_validation = self.instance or User(
                email=attrs.get("email", ""),
                first_name=attrs.get("first_name", ""),
                last_name=attrs.get("last_name", ""),
            )
            try:
                validate_password(password, user_for_validation)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    {
                        "message": "Password does not meet security requirements.",
                        "errors": list(exc.messages),
                    }
                ) from exc
            self._manager_password = password
        elif confirm_password:
            raise serializers.ValidationError({"message": "Password is required when confirm password is provided."})
        else:
            self._manager_password = None

        self.password_was_set = bool(password)
        return attrs

    def get_fullName(self, obj):
        return build_full_name(obj) or obj.get_full_name() or obj.email

    def get_createdAt(self, obj):
        return format_local_datetime(obj.date_joined)

    def get_isLastActiveAdmin(self, obj):
        if obj.role != "admin" or not obj.is_active or not obj.is_active_status:
            return False
        return User.objects.filter(role="admin", is_active=True, is_active_status=True).count() == 1

    def get_hasUsablePassword(self, obj):
        return obj.has_usable_password()

    def get_activationEmailSentAt(self, obj):
        if not obj.activation_email_sent_at:
            return None
        return format_local_datetime(obj.activation_email_sent_at)

    def get_activationExpiresAt(self, obj):
        expires_at = obj.activation_expires_at
        if not expires_at:
            return None
        return format_local_datetime(expires_at)

    def get_profilePictureUrl(self, obj):
        return build_profile_picture_url(obj, self.context.get("request"))

    def get_canManage(self, obj):
        request = self.context.get("request")
        if request is None or not getattr(request.user, "is_authenticated", False):
            return False
        actor = request.user
        if actor.role == "admin":
            return True
        if actor.role == "dept_head":
            scope = get_accessible_org_unit_ids(actor)
            return (
                actor.org_unit_id is not None
                and obj.role == "staff"
                and obj.org_unit_id in scope
            )
        return False

    def validate_employeeNumber(self, value):
        return validate_employee_number_value(value, getattr(self, "instance", None))

    def validate_suffix(self, value):
        suffix = (value or "").strip()
        if suffix in ALLOWED_NAME_SUFFIXES:
            return suffix
        # Preserve legacy free-text suffixes already stored on the user.
        instance = getattr(self, "instance", None)
        if instance and instance.suffix == suffix:
            return suffix
        raise serializers.ValidationError("Select a valid name suffix.")

    def validate(self, attrs):
        employee_number = attrs.get("employee_number", serializers.empty)
        if employee_number is serializers.empty:
            employee_number = getattr(self.instance, "employee_number", None)
        if not normalize_employee_number(employee_number or ""):
            raise serializers.ValidationError({"employeeNumber": "Employee number is required."})

        role = attrs.get("role", getattr(self.instance, "role", "staff"))

        if role == "admin":
            attrs["org_unit_id"] = None
            return self._validate_manager_password(attrs)

        org_unit_id = attrs.get("org_unit_id", serializers.empty)
        if org_unit_id is serializers.empty:
            if self.instance and self.instance.org_unit_id:
                return self._validate_manager_password(attrs)
            raise serializers.ValidationError({"message": "Office Unit is required for Dept Head and Staff."})

        if org_unit_id in ("", None):
            raise serializers.ValidationError({"message": "Office Unit is required for Dept Head and Staff."})

        try:
            org_unit = OrgUnit.objects.get(pk=org_unit_id, is_deleted=False)
        except (OrgUnit.DoesNotExist, TypeError, ValueError):
            raise serializers.ValidationError({"message": "Invalid Office Unit."})

        attrs["org_unit_id"] = org_unit.pk
        return self._validate_manager_password(attrs)

    def _apply_name_fields(self, user):
        # Backward compatibility: legacy clients may still send a single fullName string.
        full_name = (self.initial_data.get("fullName") or "").strip()
        if full_name and not (user.first_name or user.last_name):
            parts = full_name.split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""

    def create(self, validated_data):
        password = getattr(self, "_manager_password", None)
        user = User(**validated_data)
        self._apply_name_fields(user)
        if password:
            user.set_password(password)
            user.is_active = True
            user.is_active_status = True
        else:
            user.is_active = False
            user.is_active_status = False
            user.set_unusable_password()
        user.save()
        if password:
            password_changed(password, user)
        return user

    def update(self, instance, validated_data):
        password = getattr(self, "_manager_password", None)
        was_pending = (
            not instance.has_usable_password()
            or not instance.is_active
            or not instance.is_active_status
        )
        for key, value in validated_data.items():
            setattr(instance, key, value)
        self._apply_name_fields(instance)
        if password:
            instance.set_password(password)
            if was_pending:
                instance.is_active = True
                instance.is_active_status = True
            password_changed(password, instance)
        instance.save()
        return instance


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    fullName = serializers.SerializerMethodField()
    firstName = serializers.CharField(source="first_name", required=False, allow_blank=True)
    lastName = serializers.CharField(source="last_name", required=False, allow_blank=True)
    suffix = serializers.CharField(required=False, allow_blank=True)
    employeeNumber = serializers.CharField(source="employee_number", read_only=True)
    orgUnitName = serializers.CharField(source="org_unit.name", read_only=True)
    profilePictureUrl = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "role",
            "firstName",
            "lastName",
            "suffix",
            "employeeNumber",
            "orgUnitName",
            "fullName",
            "profilePictureUrl",
        ]
        read_only_fields = ["id", "email", "role", "employeeNumber", "orgUnitName", "fullName", "profilePictureUrl"]

    def get_fullName(self, obj):
        return build_full_name(obj) or obj.get_full_name() or obj.email

    def get_profilePictureUrl(self, obj):
        return build_profile_picture_url(obj, self.context.get("request"))

    def validate_suffix(self, value):
        suffix = (value or "").strip()
        if suffix in ALLOWED_NAME_SUFFIXES:
            return suffix
        instance = getattr(self, "instance", None)
        if instance and instance.suffix == suffix:
            return suffix
        raise serializers.ValidationError("Select a valid name suffix.")

    def validate(self, attrs):
        blocked = {"email", "role", "employee_number", "org_unit", "org_unit_id", "profile_picture"}
        if self.initial_data:
            for key in self.initial_data.keys():
                normalized = key.replace("employeeNumber", "employee_number").replace("orgUnitName", "org_unit")
                if normalized in blocked or key in {"employeeNumber", "role", "email", "orgUnitName", "orgUnitId"}:
                    raise serializers.ValidationError(
                        {"message": f"{key} cannot be changed from profile settings."}
                    )
        return attrs

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance


class ProfileAvatarSerializer(serializers.Serializer):
    avatar = serializers.ImageField()

    def validate_avatar(self, value):
        content_type = getattr(value, "content_type", "")
        if content_type not in settings.PROFILE_PICTURE_ALLOWED_TYPES:
            raise serializers.ValidationError("Upload a JPEG or PNG image.")

        max_size = settings.PROFILE_PICTURE_MAX_SIZE_BYTES
        if value.size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise serializers.ValidationError(f"Image must be {max_mb:g} MB or smaller.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"message": "Current password is incorrect."})

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"message": "New password and confirm password do not match."})

        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"message": "New password must be different from current password."})

        try:
            validate_password(attrs["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {
                    "message": "Password does not meet security requirements.",
                    "errors": list(exc.messages),
                }
            ) from exc
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        password_changed(self.validated_data["new_password"], user)
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class AccountActivationSetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    default_error_messages = {
        "invalid_link": "Invalid or expired activation link.",
    }

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, binascii.Error, DjangoUnicodeDecodeError):
            raise serializers.ValidationError({"message": self.error_messages["invalid_link"]})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"message": self.error_messages["invalid_link"]})

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"message": "Password and confirm password do not match."})

        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {
                    "message": "Password does not meet security requirements.",
                    "errors": list(exc.messages),
                }
            ) from exc

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["password"])
        user.is_active = True
        user.is_active_status = True
        user.save(update_fields=["password", "is_active", "is_active_status"])
        password_changed(self.validated_data["password"], user)
        return user


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    default_error_messages = {
        "invalid_link": "Invalid or expired reset link.",
    }

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id, is_active_status=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, binascii.Error, DjangoUnicodeDecodeError):
            raise serializers.ValidationError({"message": self.error_messages["invalid_link"]})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"message": self.error_messages["invalid_link"]})

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"message": "New password and confirm password do not match."})

        try:
            validate_password(attrs["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {
                    "message": "Password does not meet security requirements.",
                    "errors": list(exc.messages),
                }
            ) from exc

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        password_changed(self.validated_data["new_password"], user)
        return user
