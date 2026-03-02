from gdocs_to_markdown.gdocs_to_markdown import GoogleDocs2Markdown
from pathlib import Path


def main():
    gdtm = GoogleDocs2Markdown()

    # Before running, add at least a folder in the following list.
    # In this case, download_path refers to the absolute path where the MkDocs container is mounted.
    # The folders can be loaded from a configuration file in JSON / YAML.
    folders_to_sync = [
        {
            "folder_id": "1InrOx-AAe-4TrYvBTsrhQIeX5yZP7a7TRJPeneZhejTmuaDNcxH4EILEcT2O42nN6utd4DFp",
            "download_path": r"C:\Users\Colin\Downloads\docs\Folder1",
        },
        {
            "folder_id": "1v_n5C2lnK_-dGshtFZH1wi59o4mH-s19jxr52u723G8XpMD0ctSlma4-HIoUjX4vreX-RFT4",
            "download_path": r"C:\Users\Colin\Downloads\docs\Folder2",
        },
        {
            "folder_id": "1nGMkQYMDmHImlv8DoDWs7T_8K9Pr5YxX21BqGNVI0GQ-eS3F1TlWQ7tF5SQzdX7CqgRGLOUv",
            "download_path": r"C:\Users\Colin\Downloads\docs\Folder3",
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
