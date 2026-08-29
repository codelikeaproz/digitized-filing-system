"""
Custom user model for DFS.

Uses email as USERNAME_FIELD. Roles: admin, dept_head, staff.
OrgUnit assignment required for non-admin roles (enforced in UserSerializer).

Activation flow: new users start inactive until set-password link is used.
"""
import os
import uuid

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.utils import timezone


def profile_picture_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"profile_pictures/user_{instance.pk}_{uuid.uuid4().hex}{ext}"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("dept_head", "Department Head"),
        ("staff", "Staff"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="staff")
    employee_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    suffix = models.CharField(max_length=20, blank=True, default="")
    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_to,
        blank=True,
        null=True,
    )
    org_unit = models.ForeignKey(
        "orgunits.OrgUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    is_active_status = models.BooleanField(default=True)
    activation_email_sent_at = models.DateTimeField(null=True, blank=True)
    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="user_set",
        related_query_name="user",
        db_table="user_groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="user_set",
        related_query_name="user",
        db_table="user_permissions",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"

    @property
    def activation_expires_at(self):
        if not self.activation_email_sent_at:
            return None
        return self.activation_email_sent_at + timezone.timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)

    @property
    def activation_status(self):
        if self.is_active and self.is_active_status:
            return "active"
        if self.has_usable_password():
            return "inactive"
        expires_at = self.activation_expires_at
        if expires_at and timezone.now() > expires_at:
            return "expired"
        return "pending"

    def __str__(self):
        return self.email
