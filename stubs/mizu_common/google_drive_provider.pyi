"""Google Drive Provider stubs."""

class GoogleDriveProvider:
    """Google Drive操作を提供するクラス."""

    def __init__(self, access_token: str) -> None: ...
    def upload_file(
        self,
        file_path: str,
        parent_folder_id: str,
        file_name: str,
    ) -> str: ...
    def upload_directory(
        self,
        directory_path: str,
        parent_folder_id: str,
        folder_name: str,
    ) -> str: ...
