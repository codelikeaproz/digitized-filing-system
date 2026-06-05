from decimal import Decimal

from django.db import models


class OrgType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.SlugField(max_length=50, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class OrgUnit(models.Model):
    ORG_TYPES = [
        ("College", "College"),
        ("Department", "Department"),
        ("Office", "Office"),
        ("Unit", "Unit"),
    ]

    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    type = models.CharField(max_length=50, choices=ORG_TYPES, null=True, blank=True)
    org_type = models.ForeignKey(
        OrgType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="org_units",
    )
    is_deleted = models.BooleanField(default=False)
    # Per-unit PDF storage limits (admin-configurable).
    storage_quota_mb = models.PositiveIntegerField(default=1024)
    storage_used_mb = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def type_name(self):
        return self.org_type.name if self.org_type_id else self.type

    def get_all_children(self):
        children = list(self.children.all())
        for child in self.children.all():
            children.extend(child.get_all_children())
        return children
