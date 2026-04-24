from rest_framework import viewsets

from .models import OrgUnit
from .serializers import OrgUnitSerializer


def ensure_default_org_unit():
    org_unit, _ = OrgUnit.objects.get_or_create(
        name="Headquarters",
        defaults={"type": "Office"},
    )
    return org_unit


class OrgUnitViewSet(viewsets.ModelViewSet):
    serializer_class = OrgUnitSerializer

    def get_queryset(self):
        return OrgUnit.objects.filter(is_deleted=False).order_by("name")
