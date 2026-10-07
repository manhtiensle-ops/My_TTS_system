"""
auth.py — Giao thức xác thực OAuth 2.0 quản lý token cho YouTube API.
"""

import json
from pathlib import Path
from typing import Optional
from vieneu_sdk.youtube.config import YouTubeConfig


class YouTubeAuthManager:
    """Quản lý xác thực OAuth 2.0 và lưu trữ Refresh Token."""

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]

    def __init__(self, config: YouTubeConfig):
        self.config = config

    def get_credentials(self):
        """Khởi tạo hoặc khôi phục Credentials từ token cache."""
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        cache_path = self.config.token_cache_path

        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                creds = Credentials(
                    token=data.get("token"),
                    refresh_token=data.get("refresh_token"),
                    token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=self.config.client_id,
                    client_secret=self.config.client_secret,
                    scopes=self.SCOPES,
                )

                if creds.valid:
                    return creds
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    self._save_credentials(creds)
                    return creds
            except Exception as e:
                print(f"⚠️ Không thể khôi phục token từ cache: {e}. Tiến hành xác thực mới...")

        # Lần đầu xác thực qua Flow
        return self._run_oauth_flow()

    def _run_oauth_flow(self):
        from google_auth_oauthlib.flow import InstalledAppFlow

        client_config = {
            "installed": {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        flow = InstalledAppFlow.from_client_config(client_config, scopes=self.SCOPES)

        try:
            creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")
        except Exception:
            # Fallback console flow nếu chạy headless SSH
            creds = flow.run_console()

        self._save_credentials(creds)
        return creds

    def _save_credentials(self, creds):
        cache_path = self.config.token_cache_path
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
        }
        cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_service(self):
        from googleapiclient.discovery import build
        creds = self.get_credentials()
        return build("youtube", "v3", credentials=creds, cache_discovery=False)
