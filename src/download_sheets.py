from gdocs_to_markdown.sheets_downloader import SheetsDownloader
from pathlib import Path


def main():
    downloader = SheetsDownloader()

    # Your folders with their IDs extracted from the Drive links
    folders_to_sync = [
        {
            "folder_id": "1T6-kWTIJKrnmud1HmQMZEOS6z4vAuqKJTh5-mC4evfPVcBHNhQyFP39QTI5nK_QlRBDfZvFf",
            "download_path": r"C:\Users\Colin\Downloads\student_art\Folder1",
        },
        {
            "folder_id": "1L8vg-FG2DyT45uZfA57apJP-bfQrn4DzGG4bGGVhXFuF3L_tw8k2zmyyGsnALTwLgAwf5pQz",
            "download_path": r"C:\Users\Colin\Downloads\student_art\Folder2",
        },
        {
            "folder_id": "1qSyHfilPtkxOj-biub29q0C5Iplg_h_4qHpiwxSBHk2qUIzs4UNrS6ZscLeS6BnO_-LPKBkG",
            "download_path": r"C:\Users\Colin\Downloads\student_art\Folder3",
        },
    ]

    for folder in folders_to_sync:
        print(f"\nProcessing folder with id {folder.get('folder_id')}")
        downloader.download_folder(
            folder_id=folder.get("folder_id"),
            output_path=folder.get("download_path"),
        )


if __name__ == "__main__":
    main()
