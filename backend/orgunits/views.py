from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.models import User
from config.pagination import StandardResultsSetPagination
from documents.models import Document, Folder
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
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = OrgUnit.objects.filter(is_deleted=False).order_by("name")
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(type__icontains=search))
        return queryset

    def _validate_hierarchy(self, *, instance=None, name=None, parent=None):
        org_unit_name = (name or "").strip()
        if not org_unit_name:
            raise ValidationError({"name": "Org Unit name cannot be empty."})

        if instance and parent:
            if parent.pk == instance.pk:
                raise ValidationError({"parentId": "Org Unit cannot be its own parent."})

            ancestor = parent
            while ancestor:
                if ancestor.pk == instance.pk:
                    raise ValidationError({"parentId": "Circular Org Unit parent relationship is not allowed."})
                ancestor = ancestor.parent

        duplicate_queryset = OrgUnit.objects.filter(
            is_deleted=False,
            parent=parent,
            name__iexact=org_unit_name,
        )
        if instance:
            duplicate_queryset = duplicate_queryset.exclude(pk=instance.pk)
        if duplicate_queryset.exists():
            raise ValidationError({"name": "An Org Unit with this name already exists under the same parent."})

    def _resolve_parent(self, serializer, instance=None):
        fallback_parent_id = instance.parent_id if instance else None
        parent_id = serializer.validated_data.get("parent_id", fallback_parent_id)
        if not parent_id:
            return None

        parent = OrgUnit.objects.filter(pk=parent_id, is_deleted=False).first()
        if not parent:
            raise ValidationError({"parentId": "Parent Org Unit does not exist."})
        return parent

    def perform_create(self, serializer):
        parent = self._resolve_parent(serializer)
        name = serializer.validated_data.get("name")
        self._validate_hierarchy(name=name, parent=parent)
        serializer.save(name=name.strip(), parent=parent)

    def perform_update(self, serializer):
        instance = serializer.instance
        parent = self._resolve_parent(serializer, instance)
        name = serializer.validated_data.get("name", instance.name)
        self._validate_hierarchy(instance=instance, name=name, parent=parent)
        serializer.save(name=name.strip(), parent=parent)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        has_dependencies = (
            User.objects.filter(org_unit=instance).exists()
            or Folder.objects.filter(org_unit=instance, is_deleted=False).exists()
            or Document.objects.filter(folder__org_unit=instance, is_deleted=False).exists()
            or OrgUnit.objects.filter(parent=instance, is_deleted=False).exists()
        )

        if has_dependencies:
            return Response(
                {"message": "Cannot delete OrgUnit. It still contains users, folders, documents, or sub-units."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            instance.is_deleted = True
            instance.save(update_fields=["is_deleted"])

        return Response({"message": "Org Unit deleted successfully"}, status=status.HTTP_200_OK)
