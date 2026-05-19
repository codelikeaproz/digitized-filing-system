from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone


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
    org_unit = models.ForeignKey(
        "orgunits.OrgUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    is_active_status = models.BooleanField(default=True)
    activation_email_sent_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

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
