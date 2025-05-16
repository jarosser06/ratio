import pytest

from ratio.client.requests.storage import (
    ChangeFilePermissionsRequest,
    CopyFileRequest,
    DescribeFileTypeRequest,
    DescribeFileRequest,
    DescribeFileVersionRequest,
    DeleteFileRequest,
    DeleteFileTypeRequest,
    DeleteFileVersionRequest,
    GetFileVersionRequest,
    ListFilesRequest,
    ListFileVersionsRequest,
    PutFileRequest,
    PutFileTypeRequest,
    PutFileVersionRequest,
)


class TestStorageAPI:
    """Test suite for Ratio Storage API"""

    @pytest.fixture
    def test_file_type(self, admin_client):
        """Create and cleanup test file type"""
        file_type = "test_file_type"

        # Create file type
        req = PutFileTypeRequest(
            file_type=file_type,
            description="Custom file type for testing",
            content_search_instructions_path="/instructions/search",
            is_container_type=False,
        )

        resp = admin_client.request(req)

        assert resp.status_code == 200

        yield file_type

        # Cleanup - delete file type
        try:
            delete_req = DeleteFileTypeRequest(file_type=file_type)

            admin_client.request(delete_req)

        except Exception:
            pass  # Ignore cleanup errors

    @pytest.fixture
    def test_file(self, admin_client, home_directory, test_file_type):
        """Create test file with content"""
        file_path = f"{home_directory}/test_file.txt"

        # Create file
        create_req = PutFileRequest(
            file_path=file_path,
            file_type=test_file_type,
            metadata={"description": "Test file"},
            permissions="644"
        )

        resp = admin_client.request(create_req)

        assert resp.status_code in [200, 201]

        # Add content
        content_req = PutFileVersionRequest(
            data="Test file content v1",
            file_path=file_path,
            metadata={"version": "1.0", "author": "admin"},
        )

        resp = admin_client.request(content_req)

        assert resp.status_code in [200, 201]

        yield file_path
        # Cleanup handled by home_directory fixture

    def test_create_file_type(self, admin_client):
        """Test creating a custom file type"""
        req = PutFileTypeRequest(
            file_type="custom_type",
            description="Custom file type for testing",
            content_search_instructions_path="/instructions/search",
            is_container_type=False,
            name_restrictions="^[a-zA-Z0-9_-]+$"
        )

        resp = admin_client.request(req)

        assert resp.status_code == 200

        # Verify file type was created
        describe_req = DescribeFileTypeRequest(file_type="custom_type")

        describe_resp = admin_client.request(describe_req)

        assert describe_resp.status_code == 200

        # Cleanup
        delete_req = DeleteFileTypeRequest(file_type="custom_type")

        admin_client.request(delete_req)

    def test_create_and_read_file(self, admin_client, home_directory, test_file_type):
        """Test creating a file and reading its content"""
        file_path = f"{home_directory}/read_test.txt"

        content = "This is test content"

        # Create file
        create_req = PutFileRequest(
            file_path=file_path,
            file_type=test_file_type,
            permissions="644"
        )

        create_resp = admin_client.request(create_req)

        assert create_resp.status_code in [200, 201]

        # Add content
        content_req = PutFileVersionRequest(
            data=content,
            file_path=file_path,
            metadata={"version": "1.0"},
        )

        content_resp = admin_client.request(content_req)

        assert content_resp.status_code in [200, 201]

        # Read content
        read_req = GetFileVersionRequest(file_path=file_path)

        read_resp = admin_client.request(read_req)

        assert read_resp.status_code == 200

        assert read_resp.response_body['data'] == content

    def test_file_permissions(self, admin_client, create_test_entity, create_client, test_file):
        """Test file permission management"""
        # Create test user
        user = create_test_entity("permission_test_user")

        user_client = create_client(user)

        # Admin changes permissions to be more restrictive
        perm_req = ChangeFilePermissionsRequest(
            file_path=test_file,
            owner="admin",
            group="admin", 
            permissions="600",  # Only owner can read/write
        )

        perm_resp = admin_client.request(perm_req)

        assert perm_resp.status_code == 200, "Failed to change permissions on original file as admin"

        # User tries to read file - should fail
        read_req = GetFileVersionRequest(file_path=test_file)

        read_resp = user_client.request(read_req, raise_for_status=False)

        assert read_resp.status_code == 403, "User was not restricted from reading the file"

        # Admin makes file readable by all
        perm_req2 = ChangeFilePermissionsRequest(
            file_path=test_file,
            permissions="644",  # Owner can read/write, others can read
        )

        perm_resp2 = admin_client.request(perm_req2)

        assert perm_resp2.status_code == 200, "Failed to change permissions on restricted file as owner"

        # User should now be able to read
        read_resp2 = user_client.request(read_req)

        assert read_resp2.status_code == 200, "User failed to read the file after permissions changed"

    def test_file_versioning(self, admin_client, test_file):
        """Test file versioning functionality"""
        # Add multiple versions
        versions = []

        for i in range(3):
            version_req = PutFileVersionRequest(
                data=f"Content version {i+1}",
                file_path=test_file,
                metadata={"version": f"{i+1}.0"},
            )

            resp = admin_client.request(version_req)

            assert resp.status_code in [200, 201], f"Failed to add version {i+1}"

            versions.append(resp.response_body.get('version_id'))

        # List versions
        list_req = ListFileVersionsRequest(file_path=test_file)

        list_resp = admin_client.request(list_req)

        assert list_resp.status_code == 200

        assert len(list_resp.response_body['versions']) >= 3

        # Get specific version (the second one)
        if versions[1]:
            get_version_req = GetFileVersionRequest(
                file_path=test_file,
                version_id=versions[1]
            )

            get_resp = admin_client.request(get_version_req)

            assert get_resp.status_code == 200

            assert get_resp.response_body['data'] == "Content version 2"

    def test_copy_file(self, admin_client, test_file, home_directory):
        """Test copying files"""
        dest_path = f"{home_directory}/copied_file.txt"

        # Validate there is a file version to copy
        describe_req = DescribeFileVersionRequest(file_path=test_file)

        describe_resp = admin_client.request(describe_req)

        assert describe_resp.status_code == 200, "Failed to describe file versions"

        # Copy file
        copy_req = CopyFileRequest(
            source_file_path=test_file,
            destination_file_path=dest_path,
        )

        copy_resp = admin_client.request(copy_req)

        assert copy_resp.status_code in [200, 201], "Failed to copy file"

        # Verify copy exists
        describe_req = DescribeFileRequest(file_path=dest_path)

        describe_resp = admin_client.request(describe_req)

        assert describe_resp.status_code == 200, "Copied file does not exist"

        # Verify content was copied
        get_req = GetFileVersionRequest(file_path=dest_path)

        get_resp = admin_client.request(get_req)

        assert get_resp.status_code == 200, "Failed to get copied file content"

    def test_delete_file_version(self, admin_client, test_file):
        """Test deleting specific file versions"""
        # Add a new version
        version_req = PutFileVersionRequest(
            data="Version to delete",
            file_path=test_file,
            metadata={"version": "2.0"},
        )

        version_resp = admin_client.request(version_req)

        version_id = version_resp.response_body.get('version_id')

        # Delete the version
        delete_req = DeleteFileVersionRequest(
            file_path=test_file,
            version_id=version_id
        )

        delete_resp = admin_client.request(delete_req)

        assert delete_resp.status_code == 200, f"Failed to delete file version {version_id}"

        # Verify version is gone
        list_req = ListFileVersionsRequest(file_path=test_file)

        list_resp = admin_client.request(list_req)

        version_ids = [v['version_id'] for v in list_resp.response_body['versions']]

        assert version_id not in version_ids

    def test_delete_file(self, admin_client, home_directory, test_file_type):
        """Test deleting files"""
        file_path = f"{home_directory}/delete_test.txt"
        
        # Create file
        create_req = PutFileRequest(
            file_path=file_path,
            file_type=test_file_type,
            permissions="644"
        )

        create_resp = admin_client.request(create_req)

        assert create_resp.status_code in [200, 201], "Failed to create file for deletion test"

        # Delete file
        delete_req = DeleteFileRequest(file_path=file_path)

        delete_resp = admin_client.request(delete_req)

        assert delete_resp.status_code == 200, "Failed to delete file"

        # Verify file is gone
        describe_req = DescribeFileRequest(file_path=file_path)

        describe_resp = admin_client.request(describe_req, raise_for_status=False)

        assert describe_resp.status_code == 404, "File was not deleted successfully"

    def test_list_files(self, admin_client, home_directory, test_file_type):
        """Test listing files in a directory"""
        # Create multiple files
        file_names = ["file1.txt", "file2.txt", "file3.txt"]

        for name in file_names:
            req = PutFileRequest(
                file_path=f"{home_directory}/{name}",
                file_type=test_file_type,
                permissions="644"
            )
            admin_client.request(req)

        # List files
        list_req = ListFilesRequest(file_path=home_directory)

        list_resp = admin_client.request(list_req)

        assert list_resp.status_code == 200, "Failed to list files"

        # Verify all files are listed
        listed_files = [f['file_path'] for f in list_resp.response_body['files']]

        for name in file_names:
            assert f"{home_directory}/{name}" in listed_files, f"File {name} not found in list"

    def test_user_file_access(self, admin_client, create_test_entity, create_client, home_directory, test_file_type):
        """Test file access with different users"""
        # Create test users
        user1 = create_test_entity("file_user1")

        user2 = create_test_entity("file_user2") 

        user1_client = create_client(user1)

        user2_client = create_client(user2)
        
        # Admin creates a file owned by user1
        file_path = f"{home_directory}/user1_file.txt"

        create_req = PutFileRequest(
            file_path=file_path,
            file_type=test_file_type,
            owner=user1.entity_id,
            group=user1.entity_id,
            permissions="640"  # Owner: rw, Group: r, Others: none
        )

        admin_client.request(create_req)

        # Add content
        content_req = PutFileVersionRequest(
            data="User1's private file",
            file_path=file_path,
        )

        admin_client.request(content_req)

        # User1 can read their own file
        read_req = GetFileVersionRequest(file_path=file_path)

        user1_read = user1_client.request(read_req)

        assert user1_read.status_code == 200, "User1 failed to read their own file"

        # User2 cannot read the file
        user2_read = user2_client.request(read_req, raise_for_status=False)

        assert user2_read.status_code == 403, "User2 was able to read User1's file"

        # User1 changes permissions to allow others to read
        perm_req = ChangeFilePermissionsRequest(
            file_path=file_path,
            permissions="644"  # Everyone can read
        )

        user1_client.request(perm_req)

        # Now user2 can read
        user2_read2 = user2_client.request(read_req)

        assert user2_read2.status_code == 200, "User2 failed to read User1's file after permissions changed"

    def test_recursive_directory_operations(self, admin_client, home_directory):
        """Test recursive directory operations"""
        # Create nested directory structure
        nested_dirs = [
            f"{home_directory}/dir1",
            f"{home_directory}/dir1/subdir1", 
            f"{home_directory}/dir1/subdir2",
        ]

        for dir_path in nested_dirs:
            req = PutFileRequest(
                file_path=dir_path,
                file_type="ratio::directory",
                permissions="755"
            )

            admin_client.request(req)

        # Create files in subdirectories
        file_paths = [
            f"{home_directory}/dir1/file1.txt",
            f"{home_directory}/dir1/subdir1/file2.txt",
            f"{home_directory}/dir1/subdir2/file3.txt"
        ]

        for file_path in file_paths:
            req = PutFileRequest(
                file_path=file_path,
                file_type="ratio::file",
                permissions="644"
            )

            admin_client.request(req)

        # List files recursively
        list_req = ListFilesRequest(
            file_path=f"{home_directory}/dir1",
            recursive=True
        )

        list_resp = admin_client.request(list_req)

        assert list_resp.status_code == 200, "Failed to list files recursively"
        
        # Delete directory recursively
        delete_req = DeleteFileRequest(
            file_path=f"{home_directory}/dir1",
            recursive=True,
        )

        delete_resp = admin_client.request(delete_req)

        assert delete_resp.status_code == 200, "Failed to delete directory recursively"
        
        # Verify everything is gone
        for path in file_paths + nested_dirs:
            describe_req = DescribeFileRequest(file_path=path)

            describe_resp = admin_client.request(describe_req, raise_for_status=False)

            assert describe_resp.status_code == 404, f"Path {path} was not deleted successfully"

    def test_recursive_copy(self, admin_client, home_directory):
        """Test recursive directory copying"""
        # Create nested directory structure

        nested_dirs = [
            f"{home_directory}/src_dir",
            f"{home_directory}/src_dir/subdir1", 
            f"{home_directory}/src_dir/subdir2",
        ]

        for dir_path in nested_dirs:
            req = PutFileRequest(
                file_path=dir_path,
                file_type="ratio::directory",
                permissions="755"
            )

            admin_client.request(req)

        # Create files in subdirectories
        file_paths = [
            f"{home_directory}/src_dir/root_file.txt",
            f"{home_directory}/src_dir/subdir1/file1.txt",
            f"{home_directory}/src_dir/subdir2/file2.txt"
        ]

        for i, file_path in enumerate(file_paths):
            # Create file
            create_req = PutFileRequest(
                file_path=file_path,
                file_type="ratio::file",
                permissions="644"
            )

            admin_client.request(create_req)

            # Add content
            content_req = PutFileVersionRequest(
                data=f"Content for file {i}",
                file_path=file_path,
                metadata={"version": "1.0"},
            )

            admin_client.request(content_req)

        dest_path = f"{home_directory}/dest_dir"

        # Copy directory recursively
        copy_req = CopyFileRequest(
            source_file_path=f"{home_directory}/src_dir",
            destination_file_path=dest_path,
            recursive=True,
        )

        copy_resp = admin_client.request(copy_req)

        assert copy_resp.status_code in [200, 201], "Failed to copy directory recursively"

        # Verify all expected elements were copied
        expected_paths = [
            dest_path,
            f"{dest_path}/subdir1",
            f"{dest_path}/subdir2",
            f"{dest_path}/root_file.txt",
            f"{dest_path}/subdir1/file1.txt",
            f"{dest_path}/subdir2/file2.txt"
        ]

        for path in expected_paths:
            describe_req = DescribeFileRequest(file_path=path)

            describe_resp = admin_client.request(describe_req)

            assert describe_resp.status_code == 200, f"Path {path} was not copied successfully"

        # Verify content was copied correctly
        for i, original_path in enumerate(file_paths):
            # Calculate corresponding destination path
            dest_file_path = original_path.replace(f"{home_directory}/src_dir", dest_path)

            # Get content
            get_req = GetFileVersionRequest(file_path=dest_file_path)

            get_resp = admin_client.request(get_req)

            assert get_resp.status_code == 200, f"Failed to get content for {dest_file_path}"

            assert get_resp.response_body['data'] == f"Content for file {i}", "File content was not copied correctly"