from gdocs_to_markdown.gdocs_to_markdown import GoogleDocs2Markdown
from pathlib import Path


def main():
    gdtm = GoogleDocs2Markdown()

    # Before running, add at least a folder in the following list.
    # In this case, download_path refers to the absolute path where the MkDocs container is mounted.
    # The folders can be loaded from a configuration file in JSON / YAML.
    download_base_path = Path(__file__).resolve().parent / "docs"
    folders_to_sync = [
        {
            "folder_id": "1Uf2tyvzWCgAd6U2rMD7wzRf2PTtycAku7tael9RSzRk-yMROC1uve-MsAn4sCY6z80bcCGvS",
            "download_path": str(download_base_path / "Period 4"),
        },
        {
            "folder_id": "1oj7MVhzb3WM7fSZbjdiBpqmE16YY0i2ywYc1FBNSSiV08QfbSS2ENK4qRjWNoM4QgybYwLXz",
            "download_path": str(download_base_path / "Period 6"),
        },
        {
            "folder_id": "1MkKlqUeCc2WCXRcFM5YPAEV4OpX3I-0PkD8E5U_6hl90ie84UnwL1dMPVs4LDWrF-iegZFsZ",
            "download_path": str(download_base_path / "Period 8"),
        },
        {
            "folder_id": "1V5p0vw4i_Ueo6UieMibbNm9E-4SVU2dap78Td0AfHyqW29v1KgFPQe9JNxVbUbpXaym3nBlk",
            "download_path": str(download_base_path / "Period 1"),
        },
        {
            "folder_id": "1qrw0I_yFKxJNs17wJRvOeg9U_SFywIzJjJtSkZupxuGssuHy9JlJ8JgRjfUgCZcP9O9sXWHj",
            "download_path": str(download_base_path / "Period 3"),
        },
        {
            "folder_id": "1StmQIo6WVXxlJWJ6DiQJwXNlhAyCQzDK3D2OHbDavWAZ2bmVIwteDBZ9X-QlE4ofw6AZujNN",
            "download_path": str(download_base_path / "Period 5"),
        },
    ]

    for folder in folders_to_sync:
        print(f"Parsing folder with id {folder.get('folder_id')}")
        folder_structure = gdtm.get_folder_structure_given_root(
            folder_id=folder.get("folder_id")
        )
        print(f"Downloading files locally in {folder.get('download_path')}")
        gdtm.save_folder_structure_in_path(folder_structure, Path(folder.get("download_path")))


if __name__ == "__main__":
    main()
