import json
import os
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_NAME = "recorder-to-text"
INDEX_FILENAME = "index.html"
METADATA_FILENAME = "meetings.json"

_BASE_DIR = Path(__file__).parent.parent


def _get_credentials() -> Credentials:
    token_path = _BASE_DIR / "token.json"
    creds_path = _BASE_DIR / "credentials.json"

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds


class DriveManager:
    def __init__(self):
        creds = _get_credentials()
        self.service = build("drive", "v3", credentials=creds)
        self._folder_id: str | None = None

    def _get_folder_id(self) -> str:
        if self._folder_id:
            return self._folder_id

        # 既存フォルダを検索
        result = self.service.files().list(
            q=f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)",
        ).execute()

        files = result.get("files", [])
        if files:
            self._folder_id = files[0]["id"]
            return self._folder_id

        # 作成
        meta = {
            "name": FOLDER_NAME,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = self.service.files().create(body=meta, fields="id").execute()
        self._folder_id = folder["id"]
        return self._folder_id

    def _upload_or_update(
        self, content: str, filename: str, mime_type: str = "text/html"
    ) -> tuple[str, str]:
        folder_id = self._get_folder_id()
        media = MediaInMemoryUpload(content.encode("utf-8"), mimetype=mime_type)

        # 既存ファイルを検索
        result = self.service.files().list(
            q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
            fields="files(id)",
        ).execute()
        existing = result.get("files", [])

        if existing:
            file_id = existing[0]["id"]
            self.service.files().update(fileId=file_id, media_body=media).execute()
        else:
            meta = {"name": filename, "parents": [folder_id]}
            file = self.service.files().create(
                body=meta, media_body=media, fields="id"
            ).execute()
            file_id = file["id"]

            # 誰でも閲覧可能にする（リンク共有）
            self.service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()

        preview_url = f"https://drive.google.com/file/d/{file_id}/preview"
        web_url = f"https://drive.google.com/file/d/{file_id}/view"
        return file_id, preview_url, web_url

    def load_meetings(self) -> list[dict]:
        folder_id = self._get_folder_id()
        result = self.service.files().list(
            q=f"name='{METADATA_FILENAME}' and '{folder_id}' in parents and trashed=false",
            fields="files(id)",
        ).execute()
        files = result.get("files", [])
        if not files:
            return []

        content = self.service.files().get_media(fileId=files[0]["id"]).execute()
        return json.loads(content.decode("utf-8"))

    def save_meeting(
        self, html_content: str, filename: str, metadata: dict
    ) -> dict:
        file_id, preview_url, web_url = self._upload_or_update(html_content, filename)

        entry = {
            "id": filename.replace(".html", ""),
            "date": metadata["date"],
            "time": metadata["time"],
            "title": metadata["title"],
            "participants": metadata["participants"],
            "file_id": file_id,
            "preview_url": preview_url,
            "web_url": web_url,
        }
        return entry

    def update_index(self, index_html: str) -> str:
        _, _, web_url = self._upload_or_update(index_html, INDEX_FILENAME)
        return web_url

    def save_metadata(self, meetings: list[dict]):
        content = json.dumps(meetings, ensure_ascii=False, indent=2)
        self._upload_or_update(content, METADATA_FILENAME, mime_type="application/json")
