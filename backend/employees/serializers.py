from rest_framework import serializers

from config.employee_number import (
    normalize_employee_number,
    validate_employee_number_value,
)
from config.timezone_utils import serialize_api_datetime
from documents.permissions import get_accessible_org_unit_ids

from .models import ALLOWED_NAME_SUFFIXES, Employee
from .references import (
    can_delete_requisitioner,
    get_delete_block_reason,
    get_reference_count_for_employee,
)
from .sync import upsert_employee_and_cascade
from .duplicate_detection import EMPLOYEE_NUMBER_EXISTS_MESSAGE
from .permissions import assert_can_manage_requisitioners
from .validation import (
    assert_can_update_employee_number,
    employee_number_changed,
    get_employee_number_edit_state,
)


class EmployeeSearchSerializer(serializers.ModelSerializer):
    """Minimal fields for document upload/edit directory search (non-admin)."""

    id = serializers.CharField(read_only=True)
    employeeNumber = serializers.CharField(source="employee_number", required=False, allow_blank=True)
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    suffix = serializers.CharField(required=False, allow_blank=True)
    fullName = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "employeeNumber",
            "firstName",
            "lastName",
            "suffix",
            "fullName",
        ]

    def get_fullName(self, obj):
        return obj.get_full_name()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get("employeeNumber"):
            data["employeeNumber"] = ""
        return data


class EmployeeSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    employeeNumber = serializers.CharField(source="employee_number", required=False, allow_blank=True)
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    suffix = serializers.CharField(required=False, allow_blank=True)
    isActive = serializers.BooleanField(source="is_active", required=False)
    fullName = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()
    referencedDocumentCount = serializers.SerializerMethodField()
    scopedReferencedDocumentCount = serializers.SerializerMethodField()
    canDelete = serializers.SerializerMethodField()
    deleteBlockReason = serializers.SerializerMethodField()
    canChangeEmployeeNumber = serializers.SerializerMethodField()
    employeeNumberBlockReason = serializers.SerializerMethodField()
    employeeNumberOverrideReason = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "employeeNumber",
            "firstName",
            "lastName",
            "suffix",
            "fullName",
            "isActive",
            "createdAt",
            "referencedDocumentCount",
            "scopedReferencedDocumentCount",
            "canDelete",
            "deleteBlockReason",
            "canChangeEmployeeNumber",
            "employeeNumberBlockReason",
            "employeeNumberOverrideReason",
        ]

    def get_fullName(self, obj):
        return obj.get_full_name()

    def get_createdAt(self, obj):
        return serialize_api_datetime(obj.created_at)

    def get_referencedDocumentCount(self, obj):
        if hasattr(obj, "referenced_document_count"):
            return obj.referenced_document_count
        return get_reference_count_for_employee(obj)

    def get_scopedReferencedDocumentCount(self, obj):
        if hasattr(obj, "scoped_referenced_document_count"):
            return obj.scoped_referenced_document_count

        request = self.context.get("request")
        if request and getattr(request.user, "role", None) != "admin":
            scope_ids = get_accessible_org_unit_ids(request.user)
            return get_reference_count_for_employee(obj, scope_org_unit_ids=scope_ids)
        return self.get_referencedDocumentCount(obj)

    def get_canDelete(self, obj):
        return can_delete_requisitioner(self.get_referencedDocumentCount(obj))

    def get_deleteBlockReason(self, obj):
        return get_delete_block_reason(self.get_referencedDocumentCount(obj))

    def get_canChangeEmployeeNumber(self, obj):
        return get_employee_number_edit_state(obj).get("can_change", True)

    def get_employeeNumberBlockReason(self, obj):
        return get_employee_number_edit_state(obj).get("block_reason")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get("employeeNumber"):
            data["employeeNumber"] = ""
        return data

    def validate_employeeNumber(self, value):
        cleaned = normalize_employee_number(value or "")
        if not cleaned:
            return None
        error = validate_employee_number_value(cleaned, required=True, allow_legacy=False)
        if error:
            raise serializers.ValidationError(error)
        return cleaned

    def validate_firstName(self, value):
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("First name is required.")
        return cleaned

    def validate_lastName(self, value):
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("Last name is required.")
        return cleaned

    def validate_suffix(self, value):
        suffix = (value or "").strip()
        if suffix not in ALLOWED_NAME_SUFFIXES:
            raise serializers.ValidationError("Invalid suffix.")
        return suffix

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user:
            assert_can_manage_requisitioners(user)

        employee_number = attrs.get("employee_number")
        if employee_number is None and self.instance:
            employee_number = self.instance.employee_number

        if employee_number:
            queryset = Employee.objects.filter(employee_number__iexact=employee_number)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({"employeeNumber": EMPLOYEE_NUMBER_EXISTS_MESSAGE})

        if self.instance and user:
            incoming_number = attrs.get("employee_number")
            if incoming_number is None and "employee_number" not in attrs:
                incoming_number = self.instance.employee_number
            override_reason = attrs.get("employeeNumberOverrideReason")
            assert_can_update_employee_number(
                user,
                self.instance,
                incoming_number,
                override_reason=override_reason,
            )

        return attrs

    def create(self, validated_data):
        validated_data.pop("employeeNumberOverrideReason", None)
        employee_number = validated_data.get("employee_number")
        return upsert_employee_and_cascade(
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            suffix=validated_data.get("suffix", ""),
            employee_number=employee_number,
        )

    def update(self, instance, validated_data):
        override_reason = validated_data.pop("employeeNumberOverrideReason", None)
        employee_number = validated_data.get("employee_number")
        if employee_number is None:
            employee_number = instance.employee_number
        employee = upsert_employee_and_cascade(
            first_name=validated_data.get("first_name", instance.first_name),
            last_name=validated_data.get("last_name", instance.last_name),
            suffix=validated_data.get("suffix", instance.suffix),
            employee_number=employee_number,
            employee_instance=instance,
        )
        if override_reason:
            employee._employee_number_override_reason = override_reason.strip()
        return employee


class EmployeeUpsertSerializer(serializers.Serializer):
    employeeNumber = serializers.CharField(required=False, allow_blank=True)
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    suffix = serializers.CharField(required=False, allow_blank=True)
    employeeNumberOverrideReason = serializers.CharField(required=False, allow_blank=True)

    def validate_employeeNumber(self, value):
        cleaned = normalize_employee_number(value or "")
        if not cleaned:
            return None
        error = validate_employee_number_value(cleaned, required=True, allow_legacy=False)
        if error:
            raise serializers.ValidationError(error)
        return cleaned

    def validate_firstName(self, value):
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("First name is required.")
        return cleaned

    def validate_lastName(self, value):
        cleaned = (value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("Last name is required.")
        return cleaned

    def validate_suffix(self, value):
        suffix = (value or "").strip()
        if suffix not in ALLOWED_NAME_SUFFIXES:
            raise serializers.ValidationError("Invalid suffix.")
        return suffix

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if not user:
            return attrs

        assert_can_manage_requisitioners(user)

        incoming_number = attrs.get("employeeNumber")
        first_name = attrs.get("firstName", "")
        last_name = attrs.get("lastName", "")
        suffix = attrs.get("suffix", "")
        override_reason = attrs.get("employeeNumberOverrideReason")

        existing = Employee.objects.filter(
            employee_number__isnull=True,
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            suffix=suffix or "",
        ).first()
        if existing and employee_number_changed(existing.employee_number, incoming_number):
            assert_can_update_employee_number(
                user,
                existing,
                incoming_number,
                override_reason=override_reason,
            )

        if incoming_number:
            existing_by_number = Employee.objects.filter(
                employee_number__iexact=incoming_number
            ).first()
            if existing_by_number and employee_number_changed(
                existing_by_number.employee_number, incoming_number
            ):
                assert_can_update_employee_number(
                    user,
                    existing_by_number,
                    incoming_number,
                    override_reason=override_reason,
                )

        return attrs

    def save(self):
        return upsert_employee_and_cascade(
            first_name=self.validated_data["firstName"],
            last_name=self.validated_data["lastName"],
            suffix=self.validated_data.get("suffix", ""),
            employee_number=self.validated_data.get("employeeNumber"),
        )


class RequisitionerTaggedDocumentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True, allow_null=True)
    category = serializers.SerializerMethodField()
    orgUnit = serializers.SerializerMethodField()
    uploadedAt = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    keywords = serializers.SerializerMethodField()

    def get_category(self, obj):
        return obj.category.name if obj.category_id else "—"

    def get_orgUnit(self, obj):
        if obj.folder and obj.folder.org_unit_id:
            return obj.folder.org_unit.name
        return "—"

    def get_uploadedAt(self, obj):
        return serialize_api_datetime(obj.created_at)

    def get_owner(self, obj):
        if not obj.uploader_id:
            return "—"
        uploader = obj.uploader
        full_name = f"{uploader.first_name} {uploader.last_name}".strip()
        return full_name or uploader.email or "—"

    def get_keywords(self, obj):
        if isinstance(obj.keywords, list):
            return obj.keywords
        return []
