import os
import msal
import requests
import logging

logger = logging.getLogger(__name__)


class OneDriveConnector:
    """Connector to handle file synchronization from Microsoft OneDrive using MSAL."""

    def __init__(self):
        # TODO: Implement Google Cloud Key Vault to store CLIENT_ID and TENANT_ID
        self.client_id = os.getenv("ONEDRIVE_CLIENT_ID")
        self.tenant_id = os.getenv("ONEDRIVE_TENANT_ID", "common")
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scopes = ["Files.Read"]
        self.token_cache_path = "token_onedrive.bin"

        if not self.client_id:
            logger.error("ONEDRIVE_CLIENT_ID is missing in environment variables.")

        self.app = msal.PublicClientApplication(
            self.client_id, authority=self.authority, token_cache=self._load_cache()
        )

    def _load_cache(self):
        """Loads the token cache from a local file to avoid re-authenticating every time."""
        cache = msal.SerializableTokenCache()
        if os.path.exists(self.token_cache_path):
            with open(self.token_cache_path, "r") as f:
                cache.deserialize(f.read())
        return cache

    def _save_cache(self, cache):
        """Saves the updated token cache to the local file."""
        if cache.has_state_changed:
            with open(self.token_cache_path, "w") as f:
                f.write(cache.serialize())

    def _get_token(self):
        """Retrieves an access token silently or via interactive login if necessary."""
        accounts = self.app.get_accounts()
        result = None

        if accounts:
            # Try to get the token silently from the cache
            result = self.app.acquire_token_silent(self.scopes, account=accounts[0])

        if not result:
            # SSO Mode: Opens the browser for the first authentication
            logger.info(
                "No valid token found in cache. Opening browser for interactive login..."
            )
            result = self.app.acquire_token_interactive(self.scopes)
            self._save_cache(self.app.token_cache)

        return result.get("access_token")

    def download_file_by_name(self, filename: str, dest_path: str) -> bool:
        """
        Searches for a file by name on OneDrive and downloads it to dest_path.
        Returns True if successful, False otherwise.
        """
        token = self._get_token()
        if not token:
            logger.error("Failed to retrieve OneDrive access token.")
            return False

        headers = {"Authorization": f"Bearer {token}"}

        # 1. Search for the file by name
        search_url = (
            f"https://graph.microsoft.com/v1.0/me/drive/root/search(q='{filename}')"
        )
        response = requests.get(search_url, headers=headers).json()

        items = response.get("value", [])
        if not items:
            logger.error(f"File '{filename}' not found on OneDrive.")
            return False

        # Take the first result that matches the search query
        file_id = items[0]["id"]

        # 2. Download the file content
        download_url = (
            f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
        )
        download_resp = requests.get(download_url, headers=headers)

        if download_resp.status_code == 200:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(download_resp.content)
            logger.info(f"OneDrive template '{filename}' synchronized successfully.")
            return True

        logger.error(
            f"Failed to download file. Status code: {download_resp.status_code}"
        )
        return False
