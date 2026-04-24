from django.db import models


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
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_all_children(self):
        children = list(self.children.all())
        for child in self.children.all():
            children.extend(child.get_all_children())
        return children
