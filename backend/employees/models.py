from django.db import models


ALLOWED_NAME_SUFFIXES = {"", "Jr.", "Sr.", "I", "II", "III", "IV", "V"}


class Employee(models.Model):
    employee_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name", "employee_number"]

    def get_full_name(self):
        parts = [self.first_name, self.last_name]
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(part for part in parts if part).strip()

    def __str__(self):
        if self.employee_number:
            return f"{self.employee_number} - {self.get_full_name()}"
        return self.get_full_name()
