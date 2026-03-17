import os
import re
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO
import fitz

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from .config import TOKEN_FILE_PATH, CREDENTIALS_FILE_PATH
from googleapiclient.discovery import build


class SheetsDownloader:
    """Download Google Sheets as PNG images and auto-crop blank space."""

    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self):
        self.creds = self._authenticate()
        self.drive_service = build("drive", "v3", credentials=self.creds)

    def _authenticate(self):
        """Authenticate with Google Drive API."""
        creds = None

        if os.path.exists(TOKEN_FILE_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE_PATH, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE_PATH, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE_PATH, "w") as token:
                token.write(creds.to_json())

        return creds

    def get_sheets_in_folder(self, folder_id: str):
        """Get all Google Sheets in a folder."""
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        results = self.drive_service.files().list(
            q=query, spaces="drive", fields="files(id, name)", pageSize=100
        ).execute()
        return results.get("files", [])

    def get_sheet_gids(self, sheet_id: str):
        """Get all sheet GIDs (tab IDs) in a spreadsheet."""
        try:
            from googleapiclient.discovery import build as build_sheets
            sheets_service = build_sheets("sheets", "v4", credentials=self.drive_service._http.credentials)
            result = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheets = result.get("sheets", [])
            return [(sheet["properties"]["title"], sheet["properties"]["sheetId"]) for sheet in sheets]
        except Exception as e:
            print(f"    Warning: Could not get sheet tabs: {e}")
            return [("Sheet1", 0)]  # Fallback to default sheet

    def _sanitize_file_name(self, value: str) -> str:
        """Make a Windows-safe file name."""
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", value).strip()
        sanitized = re.sub(r"\s+", " ", sanitized)
        return sanitized[:180] if sanitized else "untitled"

    def _download_sheet_tab_pdf(self, sheet_id: str, sheet_gid: int = 0) -> bytes:
        """Download one sheet tab as PDF bytes using authenticated docs export URL."""
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export"
        params = {
            "format": "pdf",
            "gid": sheet_gid,
            "single": "true",
            "portrait": "false",
            "fitw": "true",
            "sheetnames": "false",
            "printtitle": "false",
            "pagenum": "UNDEFINED",
            "gridlines": "false",
            "fzr": "false",
        }

        headers = {}
        self.creds.apply(headers)

        response = requests.get(
            export_url,
            params=params,
            headers=headers,
            allow_redirects=True,
            timeout=60,
        )
        response.raise_for_status()
        return response.content

    def download_sheet_as_png(self, sheet_id: str, sheet_gid: int = 0) -> Image.Image:
        """Download a Google Sheet tab as PDF and render first page to PNG image."""
        pdf_bytes = self._download_sheet_tab_pdf(sheet_id, sheet_gid)
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            page = document.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            img = Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")
            return img
        finally:
            document.close()

    def crop_whitespace(self, img: Image.Image) -> Image.Image:
        """Crop blank/white space from the edges of an image."""
        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Get bounding box of non-white content
        # Define white as RGB(255, 255, 255) with some tolerance
        img_array = img.getdata()
        width, height = img.size

        # Find non-white pixels
        min_x, min_y = width, height
        max_x, max_y = 0, 0

        for y in range(height):
            for x in range(width):
                pixel = img_array[y * width + x]
                # If pixel is not mostly white (allow some tolerance)
                if not (pixel[0] > 240 and pixel[1] > 240 and pixel[2] > 240):
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        # If entire image is white, return original
        if min_x == width or min_y == height:
            return img

        # Crop with a small margin
        margin = 5
        left = max(0, min_x - margin)
        top = max(0, min_y - margin)
        right = min(width, max_x + margin)
        bottom = min(height, max_y + margin)

        return img.crop((left, top, right, bottom))

    def download_folder(self, folder_id: str, output_path: str):
        """Download all sheets from a folder as PNGs with cropped whitespace."""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        sheets = self.get_sheets_in_folder(folder_id)

        if not sheets:
            print(f"No sheets found in folder {folder_id}")
            return

        print(f"Found {len(sheets)} sheets in folder {folder_id}")

        for sheet in sheets:
            sheet_id = sheet["id"]
            sheet_name = sheet["name"]

            try:
                print(f"  Downloading: {sheet_name}")
                
                # Get sheet tabs (if there are multiple tabs, download the first one)
                sheet_gids = self.get_sheet_gids(sheet_id)
                
                for tab_name, gid in sheet_gids:
                    try:
                        print(f"    Processing tab: {tab_name}")
                        img = self.download_sheet_as_png(sheet_id, gid)

                        print(f"      Cropping whitespace...")
                        img_cropped = self.crop_whitespace(img)

                        # Save the image
                        safe_sheet_name = self._sanitize_file_name(sheet_name)
                        safe_tab_name = self._sanitize_file_name(tab_name)

                        if len(sheet_gids) > 1:
                            output_file = output_path / f"{safe_sheet_name} - {safe_tab_name}.png"
                        else:
                            output_file = output_path / f"{safe_sheet_name}.png"
                        
                        img_cropped.save(output_file)
                        print(f"      Saved to: {output_file}")

                    except Exception as e:
                        print(f"      Error processing tab {tab_name}: {e}")

            except Exception as e:
                print(f"  Error downloading {sheet_name}: {e}")

        print(f"Download complete for folder {folder_id}")
