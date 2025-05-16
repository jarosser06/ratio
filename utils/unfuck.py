"""
Unfuck the shit I did on accident
"""

from ratio.core.services.storage_manager.tables.files.client import File, FilesTableClient

_files_to_create = [
    File(
        path_hash="8a5edab282632443219e051e4ade2d1d5bbc671c781051bf1437897cbdfea0f1",
        name_hash="8a5edab282632443219e051e4ade2d1d5bbc671c781051bf1437897cbdfea0f1",
        file_name="/",
        file_path="/",
        file_type="ratio::root",
        owner="system",
        group="system",
        is_directory=True,
        description="Root FS Directory",
        permissions="664",
    ),
    File(
        path_hash="8a5edab282632443219e051e4ade2d1d5bbc671c781051bf1437897cbdfea0f1",
        name_hash="4ea140588150773ce3aace786aeef7f4049ce100fa649c94fbbddb960f1da942",
        file_name="home",
        file_path="/",
        file_type="ratio::directory",
        owner="system",
        group="system",
        is_directory=True,
        description="Entity Default Home Directory",
        permissions="664",
    )
]

def main():
    files_tbl_client = FilesTableClient()

    for ratio_file in _files_to_create:
        files_tbl_client.put(file=ratio_file)

# Define main
if __name__ == "__main__":
    main()