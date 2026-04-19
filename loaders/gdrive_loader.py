import os
import io
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GDriveConnector:
    """Connector to handle secure downloads from Google Drive using a Service Account."""

    def __init__(self):
        # Retrieve the JSON path from environment variables
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not self.creds_path:
            raise ValueError(
                "❌ GOOGLE_APPLICATION_CREDENTIALS variable missing in .env"
            )

        if not os.path.exists(self.creds_path):
            raise FileNotFoundError(f"❌ Secret file not found at: {self.creds_path}")

        self.scopes = ["https://www.googleapis.com/auth/drive.readonly"]

        try:
            # Initialize credentials from the service account file
            self.creds = service_account.Credentials.from_service_account_file(
                self.creds_path, scopes=self.scopes
            )
            self.service = build("drive", "v3", credentials=self.creds)
            logger.info(
                "✅ GDrive connector initialized successfully with Service Account."
            )

        except Exception as e:
            raise Exception(f"💥 Failed to initialize GDrive connector: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(HttpError),
        reraise=True,  # Tenacity will raise the final exception after 3 attempts
    )
    def download_file_by_name(self, filename: str, local_path: str) -> bool:
        """
        Searches for a file by name and downloads it to the specified local path.
        Returns True if successful, False otherwise.
        """
        # 1. Ensure the local directory exists
        target_dir = os.path.dirname(local_path)
        if target_dir:  # On ne crée le dossier que si le chemin en contient un
            os.makedirs(target_dir, exist_ok=True)

        # 2. Search for the file in GDrive
        query = f"name = '{filename}' and trashed = false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get("files", [])

        if not items:
            logger.error(
                f"File '{filename}' not found. Please check GDrive permissions."
            )
            return False

        file_id = items[0]["id"]

        # 3. Stream the download to the local file
        request = self.service.files().get_media(fileId=file_id)
        with io.FileIO(local_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.info(f"Download Progress: {int(status.progress() * 100)}%")

        logger.info(f"Template successfully synchronized to: {local_path}")
        return True
