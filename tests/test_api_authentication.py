# test_api_authentication.py
import pytest

from ratio.client.requests.auth import (
    CreateGroupRequest,
    DeleteEntityRequest,
    DescribeEntityRequest,
    ListEntitiesRequest,
    RotateEntityKeyRequest,
)

from ratio.client.requests.storage import (
    DescribeFileRequest,
)


class TestRatioAuthentication:
    """Test suite for Ratio API authentication"""

    def test_create_group(self, admin_client):
        """Test group creation"""
        grp_request = CreateGroupRequest(
            group_id="the_swansons",
            description="This is a test of creating test groups",
        )

        grp_resp = admin_client.request(request=grp_request)

        assert grp_resp is not None
        # Add specific assertions about the response

    def test_create_entity(self, admin_client, create_test_entity):
        """Test entity creation"""
        user = create_test_entity("test_user", description="Test user account")

        assert user.entity_id == "test_user"

        assert "create_response" in user.metadata

        assert user.metadata["create_group"] == True

        # Describe the entity in the system
        entity_describe_request = DescribeEntityRequest(
            entity_id=user.entity_id,
        )

        describe_resp = admin_client.request(request=entity_describe_request)

        assert describe_resp.status_code == 200

        assert describe_resp is not None

        assert describe_resp.response_body["entity_id"] == user.entity_id

        assert describe_resp.response_body["home_directory"] == "/home/test_user"

        # Validate the home directory exists

        describe_file_request = DescribeFileRequest(
            file_path="/home/test_user",
        )

        describe_file_resp = admin_client.request(request=describe_file_request)

        assert describe_file_resp.status_code == 200

    def test_list_entities_permissions(self, admin_client, create_test_entity, create_client):
        """Test entity listing with different permissions"""
        # Create a test user
        user = create_test_entity("test_list_user", role="standard_user")

        user_client = create_client(user)

        # Admin lists entities
        admin_entities_resp = admin_client.request(request=ListEntitiesRequest())

        # User lists entities  
        user_entities_resp = user_client.request(request=ListEntitiesRequest())

        assert admin_entities_resp is not None

        assert user_entities_resp is not None
        # Add assertions about permission differences

    def test_rotate_entity_key(self, admin_client, entity_manager, create_test_entity, create_client):
        """Test key rotation functionality"""
        # Create initial user
        user = create_test_entity("test_rotate_user")

        # Generate new keys
        new_private_key, new_public_key = entity_manager.generate_rsa_key_pair()

        # Rotate key as admin
        rotate_request = RotateEntityKeyRequest(
            entity_id=user.entity_id,
            public_key=new_public_key.decode(),
        )

        rotate_resp = admin_client.request(request=rotate_request)

        assert rotate_resp is not None

        # Update the entity with new keys
        user.private_key = new_private_key

        user.public_key = new_public_key

        entity_manager.update_entity(user)

        # Create new client with updated credentials
        new_user_client = create_client(user)

        # Test that new client works
        list_resp = new_user_client.request(request=ListEntitiesRequest())

        assert list_resp is not None

    def test_entity_metadata_persistence(self, entity_manager, create_test_entity):
        """Test that entity metadata persists across loads"""
        # Create entity with metadata
        user = create_test_entity(
            "test_metadata_user",
            department="engineering",
            access_level="admin",
            custom_data={"key": "value"}
        )

        # Load the entity
        loaded_user = entity_manager.load_entity("test_metadata_user")

        assert loaded_user is not None

        assert loaded_user.metadata["department"] == "engineering"

        assert loaded_user.metadata["access_level"] == "admin"

        assert loaded_user.metadata["custom_data"]["key"] == "value"

    def test_delete_entity(self, admin_client, create_test_entity):
        """Test entity deletion"""
        # Create a test user
        user = create_test_entity("test_delete_user")

        # Validate the user exists
        describe_request = DescribeEntityRequest(
            entity_id=user.entity_id,
        )

        describe_resp = admin_client.request(request=describe_request)

        assert describe_resp.status_code == 200, "User should exist before deletion"

        # Delete the user
        delete_request = DeleteEntityRequest(
            entity_id=user.entity_id,
        )

        delete_resp = admin_client.request(request=delete_request)

        assert delete_resp.status_code == 200