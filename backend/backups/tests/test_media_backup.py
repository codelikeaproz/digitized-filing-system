import tempfile
import zipfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from documents.models import Document, Folder
from orgunits.models import OrgUnit

from backups.services import create_media_backup


class MediaBackupTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.settings_override = override_settings(
            MEDIA_ROOT=root / "media",
            BACKUP_TEMP_DIR=root / "backups",
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.temp_dir.cleanup()

    def test_documents_are_grouped_by_org_unit_and_folder_names(self):
        office = OrgUnit.objects.create(name="College of Information Sciences")
        suboffice = OrgUnit.objects.create(name="Software Development Office", parent=office)
        records = Folder.objects.create(name="Records", org_unit=suboffice)
        reports = Folder.objects.create(name="Reports", parent=records, org_unit=suboffice)
        document = Document.objects.create(title="Annual Report", folder=reports)
        document.file.save("annual-report.pdf", ContentFile(b"%PDF-1.4\nbackup test"), save=True)

        backup_path, _ = create_media_backup()

        with zipfile.ZipFile(backup_path) as archive:
            archive_path = (
                "documents/College of Information Sciences/Software Development Office/"
                "Records/Reports/annual-report.pdf"
            )
            self.assertIn(
                archive_path,
                archive.namelist(),
            )
            manifest = archive.read("MEDIA_BACKUP_MANIFEST.csv").decode("utf-8")
            self.assertIn(archive_path, manifest)
            self.assertIn(document.file.name, manifest)
