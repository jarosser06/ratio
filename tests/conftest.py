# conftest.py
import pytest

from ratio.client.client import Ratio
from ratio.client.requests.auth import (
    CreateEntityRequest,
    DeleteEntityRequest,
    InitializeRequest
)
from ratio.client.requests.storage import DeleteFileRequest, PutFileRequest

# Local imports
from helpers import EntityManager, EntityCredentials


@pytest.fixture(scope="session")
def entity_manager():
    """Session-scoped entity manager"""

    manager = EntityManager()

    yield manager


@pytest.fixture(scope="session")
def admin_entity(entity_manager) -> EntityCredentials:
    """Session-scoped admin entity credentials"""
    admin_id = "admin"

    # Check if admin already exists
    if entity_manager.entity_exists(admin_id):
        return entity_manager.load_entity(admin_id)

    else:
        # Create new admin entity
        admin = entity_manager.create_entity(
            entity_id=admin_id,
            metadata={"group_id": "admin"}
        )

        # Initialize system
        init_req = InitializeRequest(
            admin_entity_id=admin_id,
            admin_group_id="admin",
            admin_public_key=admin.public_key_pem,
        )

        client = Ratio()

        response = client.request(request=init_req)
        
        # Extract serializable data from response
        admin.metadata["init_response"] = {
            "status_code": response.status_code,
            "response_body": response.response_body  # This should already be a dict
        }

        entity_manager.update_entity(admin)

        return admin


@pytest.fixture(scope="session")
def admin_client(admin_entity) -> Ratio:
    """Session-scoped admin client"""
    client = Ratio()

    client.refresh_token(entity_id=admin_entity.entity_id, private_key=admin_entity.private_key)

    return client


@pytest.fixture
def create_test_entity(entity_manager, admin_client):
    """Factory fixture for creating test entities"""
    created_entities = []

    def _create_entity(entity_id: str, create_group: bool = True, **metadata) -> EntityCredentials:
        entity = entity_manager.create_entity(entity_id, metadata)

        created_entities.append(entity.entity_id)

        # Create entity in the system
        request = CreateEntityRequest(
            entity_id=entity_id,
            public_key=entity.public_key_pem,
            create_group=create_group,
        )

        response = admin_client.request(request=request)

        # Extract serializable data from response
        entity.metadata["create_response"] = {
            "status_code": response.status_code,
            "response_body": response.response_body
        }

        entity.metadata["create_group"] = create_group

        entity_manager.update_entity(entity)

        return entity

    yield _create_entity

    # Cleanup created entities
    for entity_id in created_entities:
        try:
            delete_request = DeleteEntityRequest(entity_id=entity_id)

            admin_client.request(request=delete_request)

            entity_manager.delete_entity(entity_id)

        except Exception:
            pass


@pytest.fixture
def create_client(entity_manager):
    """Factory fixture for creating authenticated clients"""
    clients = []

    def _create_client(entity: EntityCredentials) -> Ratio:
        client = Ratio()

        client.refresh_token(entity_id=entity.entity_id, private_key=entity.private_key)

        clients.append(client)

        return client

    yield _create_client


@pytest.fixture
def home_directory(admin_client):
    """Create test home directory"""
    home_path = "/test_home"

    # Create directory
    req = PutFileRequest(
        file_path=home_path,
        file_type="ratio::directory",
        metadata={"description": "Test home directory"},
        permissions="775",
    )

    resp = admin_client.request(req)

    assert resp.status_code in [200, 201]

    yield home_path

    # Cleanup - delete directory and contents
    try:
        delete_req = DeleteFileRequest(file_path=home_path, recursive=True)

        admin_client.request(delete_req)

    except Exception:
        pass