import time
import datetime
import pytest

from ratio.client.requests.scheduler import (
    CreateSubscriptionRequest,
    DeleteSubscriptionRequest,
    DescribeSubscriptionRequest,
    ListSubscriptionsRequest,
)

from ratio.client.requests.storage import (
    ChangeFilePermissionsRequest,
    PutFileRequest,
    PutFileVersionRequest,
    DeleteFileRequest,
)


class TestSchedulerAPI:
    """Test suite for Ratio Scheduler API"""

    @pytest.fixture
    def test_agent_definition(self, admin_client, home_directory):
        """Create and cleanup test agent definition file"""
        file_path = f"{home_directory}/test_agent.py"

        # Create agent file
        create_req = PutFileRequest(
            file_path=file_path,
            file_type="ratio::file",
            metadata={"description": "Test agent file"},
            permissions="755"  # Executable permissions
        )

        resp = admin_client.request(create_req)
        assert resp.status_code in [200, 201]

        # Add agent content
        content = "def handle_event(event):\n    print('Processing event:', event)\n    return True"

        content_req = PutFileVersionRequest(
            data=content,
            file_path=file_path,
            metadata={"version": "1.0", "author": "admin"},
        )

        resp = admin_client.request(content_req)

        assert resp.status_code in [200, 201]

        yield file_path
        # Cleanup handled by home_directory fixture

    @pytest.fixture
    def test_subscription(self, admin_client, test_agent_definition, home_directory):
        """Create test subscription"""
        file_path = f"{home_directory}/watched_file.txt"

        # Create file to watch
        create_req = PutFileRequest(
            file_path=file_path,
            file_type="ratio::file",
            permissions="644"
        )

        resp = admin_client.request(create_req)

        assert resp.status_code in [200, 201]

        # Create subscription
        sub_req = CreateSubscriptionRequest(
            agent_definition=test_agent_definition,
            file_path=file_path,
            single_use=False
        )

        resp = admin_client.request(sub_req)

        assert resp.status_code in [200, 201]

        subscription_id = resp.response_body.get('subscription_id')

        assert subscription_id, "No subscription ID returned"

        yield {
            "id": subscription_id,
            "file_path": file_path,
            "agent_definition": test_agent_definition
        }

    def test_create_subscription(self, admin_client, test_agent_definition, home_directory):
        """Test creating a subscription"""
        file_path = f"{home_directory}/create_sub_test.txt"

        # Create file to watch
        create_req = PutFileRequest(
            file_path=file_path,
            file_type="ratio::file",
            permissions="644"
        )

        resp = admin_client.request(create_req)

        assert resp.status_code in [200, 201]

        # Create subscription
        sub_req = CreateSubscriptionRequest(
            agent_definition=test_agent_definition,
            file_path=file_path,
            single_use=True
        )

        resp = admin_client.request(sub_req)

        assert resp.status_code in [200, 201]

        subscription_id = resp.response_body.get('subscription_id')

        assert subscription_id, "No subscription ID returned"

        # Verify subscription properties
        assert resp.response_body.get("file_path") == file_path

        assert resp.response_body.get("single_use") is True

    def test_describe_subscription(self, admin_client, test_subscription):
        """Test describing a subscription"""
        describe_req = DescribeSubscriptionRequest(
            subscription_id=test_subscription["id"]
        )

        resp = admin_client.request(describe_req)

        assert resp.status_code == 200

        # Verify subscription details
        assert resp.response_body.get("subscription_id") == test_subscription["id"]

        assert resp.response_body.get("file_path") == test_subscription["file_path"]

        assert resp.response_body.get("agent_definition") == test_subscription["agent_definition"]

    def test_list_subscriptions(self, admin_client, test_subscription):
        """Test listing all subscriptions"""
        list_req = ListSubscriptionsRequest()

        resp = admin_client.request(list_req)

        assert resp.status_code == 200

        # Verify our test subscription is in the list
        subscription_ids = [s.get("subscription_id") for s in resp.response_body]

        assert test_subscription["id"] in subscription_ids

        # Test listing with file_path filter
        list_by_file_req = ListSubscriptionsRequest(
            file_path=test_subscription["file_path"]
        )

        resp = admin_client.request(list_by_file_req)

        assert resp.status_code == 200

        # Should only return our subscription
        assert len(resp.response_body) >= 1

        assert resp.response_body[0].get("subscription_id") == test_subscription["id"]

    def test_delete_subscription(self, admin_client, test_agent_definition, home_directory):
        """Test deleting a subscription"""
        # Create a file and subscription specifically for deletion
        file_path = f"{home_directory}/delete_sub_test.txt"

        # Create file to watch
        create_req = PutFileRequest(
            file_path=file_path,
            file_type="ratio::file",
            permissions="644"
        )

        resp = admin_client.request(create_req)

        assert resp.status_code in [200, 201]

        # Create subscription
        sub_req = CreateSubscriptionRequest(
            agent_definition=test_agent_definition,
            file_path=file_path
        )

        resp = admin_client.request(sub_req)

        assert resp.status_code in [200, 201]

        subscription_id = resp.response_body.get("subscription_id")

        # Delete the subscription
        delete_req = DeleteSubscriptionRequest(
            subscription_id=subscription_id
        )

        resp = admin_client.request(delete_req)

        assert resp.status_code == 200

        # Verify it's gone
        describe_req = DescribeSubscriptionRequest(
            subscription_id=subscription_id
        )

        resp = admin_client.request(describe_req, raise_for_status=False)

        assert resp.status_code == 404

    def test_agent_definition_permissions(self, admin_client, home_directory, create_test_entity, create_client):
        """Test agent definition permissions validation"""
        # Create test user
        user = create_test_entity("agent_perm_test_user")

        user_client = create_client(user)

        # Create agent file with restrictive permissions
        agent_path = f"{home_directory}/restricted_agent.py"

        create_req = PutFileRequest(
            file_path=agent_path,
            file_type="ratio::file",
            permissions="700"  # Only owner can access
        )

        resp = admin_client.request(create_req)

        assert resp.status_code in [200, 201]

        # Add agent content
        content_req = PutFileVersionRequest(
            data="def handle_event(event):\n    return True",
            file_path=agent_path
        )

        resp = admin_client.request(content_req)

        assert resp.status_code in [200, 201]

        # Create file to watch - with accessible permissions
        file_path = f"{home_directory}/watched_by_restricted.txt"

        file_req = PutFileRequest(
            file_path=file_path,
            file_type="ratio::file",
            permissions="644"  # Everyone can read
        )

        resp = admin_client.request(file_req)

        assert resp.status_code in [200, 201]

        # Try to create subscription as user - should fail due to agent permissions
        sub_req = CreateSubscriptionRequest(
            agent_definition=agent_path,
            file_path=file_path
        )

        resp = user_client.request(sub_req, raise_for_status=False)

        assert resp.status_code == 403, "User should not be able to use restricted agent"

        # Admin updates agent permissions to be accessible
        perm_req = ChangeFilePermissionsRequest(
            file_path=agent_path,
            permissions="755"  # Everyone can read and execute
        )

        resp = admin_client.request(perm_req)

        assert resp.status_code in [200, 201]

        # Now user should be able to create subscription
        resp = user_client.request(sub_req)

        assert resp.status_code in [200, 201], "User should be able to use agent after permissions change"

    def test_missing_agent_file(self, admin_client, home_directory):
        """Test behavior with non-existent agent definition"""
        # Create file to watch
        file_path = f"{home_directory}/watched_by_missing.txt"

        file_req = PutFileRequest(
            file_path=file_path,
            file_type="ratio::file",
            permissions="644"
        )

        resp = admin_client.request(file_req)

        assert resp.status_code in [200, 201]
        
        # Try to create subscription with non-existent agent
        missing_agent = f"{home_directory}/does_not_exist.py"

        sub_req = CreateSubscriptionRequest(
            agent_definition=missing_agent,
            file_path=file_path
        )

        resp = admin_client.request(sub_req, raise_for_status=False)

        assert resp.status_code == 404, "Should fail with 404 when agent file doesn't exist"

    def test_expiration_and_single_use(self, admin_client, test_agent_definition, home_directory):
        """Test subscription with expiration and single use flag"""
        file_path = f"{home_directory}/expiring_test.txt"

        # Create file to watch
        create_req = PutFileRequest(
            file_path=file_path,
            file_type="ratio::file",
            permissions="644"
        )

        resp = admin_client.request(create_req)

        assert resp.status_code in [200, 201]

        # Create subscription with future expiration
        expiration = datetime.datetime.now() + datetime.timedelta(days=1)

        sub_req = CreateSubscriptionRequest(
            agent_definition=test_agent_definition,
            file_path=file_path,
            expiration=expiration,
            single_use=True
        )

        resp = admin_client.request(sub_req)

        assert resp.status_code in [200, 201]

        subscription_id = resp.response_body.get("subscription_id")

        # Verify expiration and single_use set correctly
        describe_req = DescribeSubscriptionRequest(
            subscription_id=subscription_id
        )

        resp = admin_client.request(describe_req)

        assert resp.status_code == 200

        # Check fields (format may vary, so just check existence)
        assert resp.response_body.get("expiration") is not None, "Expiration not set"

        assert resp.response_body.get("single_use") is True, "Single use flag not set"