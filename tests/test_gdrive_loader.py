import pytest
from unittest.mock import MagicMock, patch
import os
from loaders.gdrive_loader import GDriveConnector


@pytest.fixture
def mock_service():
    with patch("loaders.gdrive_loader.build") as mock_build:
        mock_drive = MagicMock()
        mock_build.return_value = mock_drive
        yield mock_drive


@pytest.fixture
def connector(mock_service):
    # On mocke l'existence du fichier ET la variable d'environnement
    with patch.dict(
        os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "fake_path.json"}
    ), patch(
        "google.oauth2.service_account.Credentials.from_service_account_file"
    ), patch("os.path.exists", return_value=True):
        return GDriveConnector()


def test_download_file_by_name_not_found(connector, mock_service):
    """Verifies behavior when file is missing on GDrive."""
    # We mock the return value of the .execute() chain
    mock_service.files().list().execute.return_value = {"files": []}

    result = connector.download_file_by_name("missing_file.docx", "local/path.docx")

    assert result is False

    # We check that list() was called with the correct query
    # We use assert_any_call because the mock records the setup calls too
    mock_service.files().list.assert_any_call(
        q="name = 'missing_file.docx' and trashed = false", fields="files(id, name)"
    )


def test_download_file_by_name_success(connector, mock_service, tmp_path):
    """Verifies successful download simulation."""
    mock_service.files().list().execute.return_value = {
        "files": [{"id": "12345", "name": "resume_template.docx"}]
    }

    local_file = tmp_path / "resume_template.docx"

    with patch("loaders.gdrive_loader.MediaIoBaseDownload") as mock_download_cls:
        mock_downloader = mock_download_cls.return_value
        mock_downloader.next_chunk.return_value = (None, True)

        result = connector.download_file_by_name(
            "resume_template.docx", str(local_file)
        )

        assert result is True
        assert os.path.exists(local_file)


def test_retry_logic_on_http_error(connector, mock_service):
    from googleapiclient.errors import HttpError

    # Setup de l'erreur
    mock_resp = MagicMock(status=500, reason="Internal Server Error")
    err = HttpError(resp=mock_resp, content=b"Error")

    # On cible exactement la méthode list() du service mocké
    mock_service.files().list.side_effect = err

    with pytest.raises(HttpError):
        connector.download_file_by_name("test.docx", "path.docx")

    # Vérifie que la méthode list a bien été appelée 3 fois (grâce à tenacity)
    assert mock_service.files().list.call_count == 3
