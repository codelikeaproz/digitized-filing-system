from rest_framework import serializers

from rest_framework.exceptions import PermissionDenied

from django.utils import timezone



from config.timezone_utils import format_local_datetime

from .document_code_validation import ensure_unique_document_code, normalize_document_code
from .models import Category, Document, DocumentRequisitioner, Folder

from .services import resolve_document_file_path

from .requisitioners import build_requisitioner_full_name, validate_requisitioners_list

from .permissions import resolve_category_org_unit_for_create





RESERVED_FOLDER_NAMES = {"all files", "root", "trash", "recycle bin"}





class CategorySerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    org_unit = serializers.IntegerField(source="org_unit_id", read_only=True, allow_null=True)

    orgUnitId = serializers.CharField(source="org_unit_id", required=False, allow_null=True)

    createdAt = serializers.SerializerMethodField()

    document_count = serializers.SerializerMethodField()

    documentCount = serializers.SerializerMethodField()

    inUse = serializers.SerializerMethodField()



    class Meta:

        model = Category

        fields = [

            "id",

            "name",

            "org_unit",

            "orgUnitId",

            "createdAt",

            "document_count",

            "documentCount",

            "inUse",

        ]



    def get_document_count(self, obj):

        return self.get_documentCount(obj)



    def get_documentCount(self, obj):

        annotated_count = getattr(obj, "active_document_count", None)

        if annotated_count is not None:

            return annotated_count

        return obj.documents.filter(is_deleted=False).count()



    def get_inUse(self, obj):

        return self.get_documentCount(obj) > 0



    def get_createdAt(self, obj):

        return format_local_datetime(obj.created_at)



    def validate_orgUnitId(self, value):

        return value or None



    def validate_name(self, value):

        name = (value or "").strip()

        if not name:

            raise serializers.ValidationError("Category name cannot be empty.")

        return name



    def _assign_category_org_unit(self, attrs):

        request = self.context.get("request")

        user = getattr(request, "user", None) if request else None

        if not user or not getattr(user, "is_authenticated", False):

            return attrs



        requested = attrs.get("org_unit_id")

        try:

            resolved_org_unit_id = resolve_category_org_unit_for_create(user, requested)

        except PermissionDenied as exc:

            detail = exc.detail

            if isinstance(detail, (list, tuple)):

                detail = detail[0] if detail else "Permission denied."

            raise serializers.ValidationError({"orgUnitId": str(detail)}) from exc



        attrs["org_unit_id"] = resolved_org_unit_id

        return attrs



    def validate(self, attrs):

        name = attrs.get("name")

        if name is None and self.instance:

            name = self.instance.name



        if not self.instance:

            attrs = self._assign_category_org_unit(attrs)



        org_unit_id = attrs.get("org_unit_id") if not self.instance else self.instance.org_unit_id

        if self.instance:

            attrs.pop("org_unit_id", None)



        if not name:

            return attrs



        duplicate_queryset = Category.objects.filter(name__iexact=name.strip())

        if org_unit_id:

            duplicate_queryset = duplicate_queryset.filter(org_unit_id=org_unit_id)

        else:

            duplicate_queryset = duplicate_queryset.filter(org_unit__isnull=True)



        if self.instance:

            duplicate_queryset = duplicate_queryset.exclude(pk=self.instance.pk)



        if duplicate_queryset.exists():

            if org_unit_id:

                raise serializers.ValidationError(

                    {"name": "A category with this name already exists in this Office Unit."}

                )

            raise serializers.ValidationError(

                {

                    "name": (

                        "A category with this name already exists as an unassigned (Global) category. "

                        "An Admin can remove it from Manage Categories."

                    )

                }

            )



        return attrs





class FolderSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    parentId = serializers.CharField(source="parent_id", required=False, allow_null=True)

    orgUnitId = serializers.CharField(source="org_unit_id", required=False, allow_null=True)

    createdBy = serializers.CharField(source="created_by_id", read_only=True)

    createdAt = serializers.SerializerMethodField()

    documentCount = serializers.SerializerMethodField()

    subfolderCount = serializers.SerializerMethodField()

    location = serializers.CharField(source="get_full_path", read_only=True)



    class Meta:

        model = Folder

        fields = [

            "id",

            "name",

            "parentId",

            "orgUnitId",

            "createdBy",

            "createdAt",

            "documentCount",

            "subfolderCount",

            "location",

        ]



    def get_documentCount(self, obj):

        return obj.documents.filter(is_deleted=False).count()



    def get_subfolderCount(self, obj):

        return obj.children.filter(is_deleted=False).count()



    def get_createdAt(self, obj):

        return format_local_datetime(obj.created_at)



    def validate_name(self, value):

        if value.strip().lower() in RESERVED_FOLDER_NAMES:

            raise serializers.ValidationError("Reserved folder name cannot be used.")

        return value.strip()



    def validate_parentId(self, value):

        return value or None



    def validate_orgUnitId(self, value):

        return value or None





class DocumentRequisitionerSerializer(serializers.ModelSerializer):

    employeeId = serializers.CharField(source="employee_id", required=False, allow_null=True)
    employeeNumber = serializers.CharField(source="employee_number", required=False, allow_blank=True)
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    suffix = serializers.CharField(required=False, allow_blank=True)
    fullName = serializers.SerializerMethodField()

    class Meta:
        model = DocumentRequisitioner
        fields = [
            "employeeId",
            "source",
            "employeeNumber",
            "firstName",
            "lastName",
            "suffix",
            "fullName",
        ]

    def get_fullName(self, obj):
        return build_requisitioner_full_name(obj.first_name, obj.last_name, obj.suffix)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("employeeId") is None:
            data["employeeId"] = None
        if not data.get("employeeNumber"):
            data["employeeNumber"] = ""
        return data





class DocumentSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    requisitioners = serializers.SerializerMethodField()

    file_name = serializers.SerializerMethodField()

    filePath = serializers.SerializerMethodField()

    file_url = serializers.SerializerMethodField()

    folderId = serializers.CharField(source="folder_id", read_only=True)

    categoryId = serializers.CharField(source="category_id", read_only=True)

    uploaderId = serializers.CharField(source="uploader_id", read_only=True)

    category = serializers.CharField(source="category.name", read_only=True)

    code = serializers.CharField(required=False, allow_blank=True)

    filingYear = serializers.IntegerField(source="filing_year")

    googleDriveLink = serializers.URLField(source="google_drive_link", read_only=True)

    mimeType = serializers.CharField(source="mime_type")

    isDeleted = serializers.BooleanField(source="is_deleted")

    deletedAt = serializers.SerializerMethodField()

    deletedBy = serializers.CharField(source="deleted_by_id", read_only=True)

    createdAt = serializers.SerializerMethodField()

    created_at = serializers.SerializerMethodField()

    mime_type = serializers.CharField(read_only=True)

    file_size = serializers.IntegerField(read_only=True)



    class Meta:

        model = Document

        fields = [

            "id",

            "title",

            "file_name",

            "filePath",

            "file_url",

            "folderId",

            "categoryId",

            "uploaderId",

            "category",

            "code",

            "requestor",

            "requisitioners",

            "description",

            "keywords",

            "filingYear",

            "googleDriveLink",

            "source",

            "mimeType",

            "mime_type",

            "file_size",

            "isDeleted",

            "deletedAt",

            "deletedBy",

            "createdAt",

            "created_at",

        ]



    def get_requisitioners(self, obj):

        requisitioners = obj.requisitioners.all()

        return DocumentRequisitionerSerializer(requisitioners, many=True).data



    def get_filePath(self, obj):

        return resolve_document_file_path(obj)



    def get_file_name(self, obj):

        if obj.file:

            return obj.file.name.rsplit("/", 1)[-1]

        return obj.title



    def get_file_url(self, obj):

        request = self.context.get("request")

        if not obj.file:

            return None

        url = obj.file.url

        return request.build_absolute_uri(url) if request else url



    def get_deletedAt(self, obj):

        return format_local_datetime(obj.deleted_at)



    def get_createdAt(self, obj):

        return format_local_datetime(obj.created_at)



    def get_created_at(self, obj):

        return self.get_createdAt(obj)



    def validate_code(self, value):

        code = normalize_document_code(value)

        ensure_unique_document_code(code, document_id=getattr(self.instance, "pk", None))

        return code





def normalize_requestor_name(value):

    cleaned = (value or "").strip()

    if not cleaned:

        return None



    def capitalize_part(part):

        return part[:1].upper() + part[1:].lower() if part else ""



    words = []

    for word in cleaned.split():

        words.append("-".join(capitalize_part(piece) for piece in word.split("-") if piece is not None))

    return " ".join(words)





class DocumentEditSerializer(serializers.Serializer):

    folderId = serializers.CharField()

    categoryId = serializers.CharField()

    code = serializers.CharField()

    requisitioners = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    description = serializers.CharField(required=True, allow_blank=False, max_length=50)

    keywords = serializers.ListField(child=serializers.CharField(), allow_empty=False)

    file_name = serializers.CharField(required=False, allow_blank=True)

    googleDriveLink = serializers.URLField(required=False, allow_blank=True)



    def validate_keywords(self, value):

        cleaned = [str(item).strip() for item in (value or []) if str(item).strip()]

        if not cleaned:

            raise serializers.ValidationError("At least one keyword is required.")

        return cleaned



    def validate_description(self, value):

        cleaned = (value or "").strip()

        if not cleaned:

            raise serializers.ValidationError("Description is required.")

        return cleaned[:50]



    def validate_requisitioners(self, value):

        return validate_requisitioners_list(value)



    def validate_code(self, value):

        document = self.context.get("document")

        code = normalize_document_code(value)

        ensure_unique_document_code(code, document_id=getattr(document, "pk", None))

        return code



    def validate_googleDriveLink(self, value):

        link = (value or "").strip()

        if not link:

            return ""

        if not link.lower().startswith("https://drive.google.com/"):

            raise serializers.ValidationError("Google Drive link must start with https://drive.google.com/")

        return link





class DashboardStorageSerializer(serializers.Serializer):

    org_unit_id = serializers.CharField(allow_null=True, required=False)

    org_unit_name = serializers.CharField(allow_null=True, required=False)

    quota_mb = serializers.IntegerField()

    org_units_quota_mb = serializers.IntegerField(required=False, allow_null=True)

    org_units_allocation_remaining_mb = serializers.IntegerField(required=False, allow_null=True)

    used_mb = serializers.FloatField()

    remaining_mb = serializers.FloatField()

    usage_percentage = serializers.FloatField()

    percent_used = serializers.FloatField(required=False)

    children_allocated_mb = serializers.IntegerField(required=False, allow_null=True)

    available_for_allocation_mb = serializers.IntegerField(required=False, allow_null=True)





class OfficeUnitStorageUsageSerializer(serializers.Serializer):

    org_unit_id = serializers.CharField()

    org_unit_name = serializers.CharField()

    quota_mb = serializers.IntegerField()

    used_mb = serializers.FloatField()

    remaining_mb = serializers.FloatField()

    usage_percentage = serializers.FloatField()





class DashboardStatsSerializer(serializers.Serializer):

    scope = serializers.ChoiceField(choices=["global", "office_unit"])

    office_unit_id = serializers.CharField(allow_null=True, required=False)

    office_unit_name = serializers.CharField()

    office_unit_filter = serializers.CharField()

    can_filter_office_units = serializers.BooleanField()

    aggregates_subtree = serializers.BooleanField(required=False, default=False)

    total_documents = serializers.IntegerField()

    google_drive_files = serializers.IntegerField()

    total_org_units = serializers.IntegerField(allow_null=True, required=False)

    total_users = serializers.IntegerField(allow_null=True, required=False)

    deleted_files = serializers.IntegerField(allow_null=True, required=False)

    storage = DashboardStorageSerializer(allow_null=True, required=False)

    storage_by_office_unit = OfficeUnitStorageUsageSerializer(many=True)

