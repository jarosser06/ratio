# Ratio Client Library Documentation

## Overview

The Ratio Client Library provides a Python interface for interacting with the Ratio system. Based on the codebase, it offers APIs for authentication, file storage, agent execution, and scheduling.

## Client Initialization

```python
from ratio.client.client import Ratio

# Using private key authentication
client = Ratio(
    app_name="my_application",
    deployment_id="development", 
    entity_id="my_user_id",
    private_key=private_key_bytes
)

# Using existing token
client = Ratio(
    app_name="my_application",
    deployment_id="development",
    token="existing_token",
    token_expires=expiration_datetime
)
```

### Client Parameters

Based on the `Ratio` class constructor:

- `app_name`: The application name (optional)
- `deployment_id`: The deployment identifier (optional)
- `entity_id`: Entity identifier for authentication
- `private_key`: RSA private key in bytes for signing requests
- `token`: Pre-existing authentication token (optional)
- `token_expires`: Expiration datetime for the token (optional)
- `auth_header`: Authentication header name (default: "X-Ratio-Authorization")

## Storage API

### File Operations

```python
from ratio.client.requests.storage import (
    PutFileRequest, 
    PutFileVersionRequest,
    GetFileVersionRequest,
    DescribeFileRequest,
    ListFilesRequest,
    DeleteFileRequest,
    CopyFileRequest,
    ChangeFilePermissionsRequest
)

# Create a file
file_request = PutFileRequest(
    file_path="/path/to/file.txt",
    file_type="ratio::file",
    permissions="644",
    owner="user_id",
    group="user_group",
    metadata={"key": "value"}
)
response = client.request(file_request)

# Add content to file
content_request = PutFileVersionRequest(
    file_path="/path/to/file.txt",
    data="File content",
    metadata={"version": "1.0"},
    source_file_ids=["source_id"]
)
response = client.request(content_request)

# Get file content
get_request = GetFileVersionRequest(
    file_path="/path/to/file.txt",
    version_id="optional_version_id"
)
response = client.request(get_request)

# Describe file
describe_request = DescribeFileRequest(file_path="/path/to/file.txt")
response = client.request(describe_request)

# List files
list_request = ListFilesRequest(
    file_path="/directory/path",
    recursive=True
)
response = client.request(list_request)

# Copy file
copy_request = CopyFileRequest(
    source_file_path="/source/path",
    destination_file_path="/dest/path",
    recursive=True,
    version_id="optional_version"
)
response = client.request(copy_request)

# Delete file
delete_request = DeleteFileRequest(
    file_path="/path/to/file.txt",
    force=True,
    recursive=True
)
response = client.request(delete_request)

# Change permissions
perm_request = ChangeFilePermissionsRequest(
    file_path="/path/to/file.txt",
    permissions="755",
    owner="new_owner",
    group="new_group"
)
response = client.request(perm_request)
```

### File Versioning

```python
from ratio.client.requests.storage import (
    ListFileVersionsRequest,
    DescribeFileVersionRequest,
    DeleteFileVersionRequest
)

# List versions
versions_request = ListFileVersionsRequest(file_path="/path/to/file.txt")
response = client.request(versions_request)

# Describe version
version_request = DescribeFileVersionRequest(
    file_path="/path/to/file.txt",
    version_id="version_id"
)
response = client.request(version_request)

# Delete version
delete_version_request = DeleteFileVersionRequest(
    file_path="/path/to/file.txt",
    version_id="version_id",
    force=True
)
response = client.request(delete_version_request)
```

### File Types

```python
from ratio.client.requests.storage import (
    PutFileTypeRequest,
    DescribeFileTypeRequest,
    ListFileTypesRequest,
    DeleteFileTypeRequest
)

# Create file type
type_request = PutFileTypeRequest(
    file_type="custom::type",
    description="Custom file type",
    is_container_type=False,
    name_restrictions="^[a-zA-Z0-9_-]+$"
)
response = client.request(type_request)

# Describe file type
describe_type_request = DescribeFileTypeRequest(file_type="custom::type")
response = client.request(describe_type_request)

# List file types
list_types_request = ListFileTypesRequest()
response = client.request(list_types_request)

# Delete file type
delete_type_request = DeleteFileTypeRequest(file_type="custom::type")
response = client.request(delete_type_request)
```

## Authentication API

### Entity Management

```python
from ratio.client.requests.auth import (
    InitializeRequest,
    CreateEntityRequest,
    DescribeEntityRequest,
    ListEntitiesRequest,
    DeleteEntityRequest,
    RotateEntityKeyRequest
)

# Initialize system (first time setup)
init_request = InitializeRequest(
    admin_entity_id="admin",
    admin_public_key=public_key_pem,
    admin_group_id="admin_group"
)
response = client.request(init_request)

# Create entity
create_request = CreateEntityRequest(
    entity_id="new_user",
    public_key=public_key_pem,
    description="User description",
    create_group=True,
    create_home=True,
    groups=["group1", "group2"],
    home_directory="/custom/home",
    primary_group_id="primary_group"
)
response = client.request(create_request)

# Describe entity
describe_request = DescribeEntityRequest(entity_id="user_id")
response = client.request(describe_request)

# List entities
list_request = ListEntitiesRequest()
response = client.request(list_request)

# Rotate entity key
rotate_request = RotateEntityKeyRequest(
    entity_id="user_id",
    public_key=new_public_key_pem
)
response = client.request(rotate_request)

# Delete entity
delete_request = DeleteEntityRequest(entity_id="user_id")
response = client.request(delete_request)
```

### Group Management

```python
from ratio.client.requests.auth import (
    CreateGroupRequest,
    DescribeGroupRequest,
    ListGroupsRequest,
    AddEntityToGroupRequest,
    RemoveEntityFromGroupRequest,
    DeleteGroupRequest
)

# Create group
create_group_request = CreateGroupRequest(
    group_id="developers",
    description="Development team"
)
response = client.request(create_group_request)

# Describe group
describe_group_request = DescribeGroupRequest(group_id="developers")
response = client.request(describe_group_request)

# List groups
list_groups_request = ListGroupsRequest()
response = client.request(list_groups_request)

# Add entity to group
add_request = AddEntityToGroupRequest(
    entity_id="user_id",
    group_id="developers"
)
response = client.request(add_request)

# Remove entity from group
remove_request = RemoveEntityFromGroupRequest(
    entity_id="user_id",
    group_id="developers"
)
response = client.request(remove_request)

# Delete group
delete_group_request = DeleteGroupRequest(
    group_id="developers",
    force=True
)
response = client.request(delete_group_request)
```

## Agent API

### Agent Execution

```python
from ratio.client.requests.agent import ExecuteAgentRequest

# Execute with inline definition
execute_request = ExecuteAgentRequest(
    agent_definition={"key": "value"},  # JSON object
    arguments={"arg1": "value1"},
    execute_as="other_user",
    working_directory="/work/dir"
)
response = client.request(execute_request)

# Execute from file path
execute_request = ExecuteAgentRequest(
    agent_definition_path="/path/to/agent.json",
    arguments={"arg1": "value1"},
    working_directory="/work/dir"
)
response = client.request(execute_request)
```

### Agent Validation

```python
from ratio.client.requests.agent import ValidateAgentRequest

# Validate inline definition
validate_request = ValidateAgentRequest(
    agent_definition={"key": "value"}
)
response = client.request(validate_request)

# Validate from file
validate_request = ValidateAgentRequest(
    agent_definition_path="/path/to/agent.json"
)
response = client.request(validate_request)
```

### Process Management

```python
from ratio.client.requests.agent import (
    DescribeProcessRequest,
    ListProcessesRequest
)

# Describe process
describe_request = DescribeProcessRequest(process_id="process_123")
response = client.request(describe_request)

# List processes
list_request = ListProcessesRequest(
    process_owner="user_id",
    parent_process_id="parent_123",
    status="COMPLETED"
)
response = client.request(list_request)
```

## Scheduler API

### Subscription Management

```python
from ratio.client.requests.scheduler import (
    CreateSubscriptionRequest,
    DescribeSubscriptionRequest,
    ListSubscriptionsRequest,
    DeleteSubscriptionRequest
)

# Create subscription
create_request = CreateSubscriptionRequest(
    agent_definition="/path/to/agent.py",
    file_path="/watched/path",
    file_event_type="created",  # "created", "deleted", "updated", "version_created", "version_deleted"
    expiration=datetime_object,
    file_type="ratio::file",
    owner="user_id",
    single_use=True
)
response = client.request(create_request)

# Describe subscription
describe_request = DescribeSubscriptionRequest(
    subscription_id="sub_123"
)
response = client.request(describe_request)

# List subscriptions
list_request = ListSubscriptionsRequest(
    file_path="/watched/path",
    owner="user_id"
)
response = client.request(list_request)

# Delete subscription
delete_request = DeleteSubscriptionRequest(
    subscription_id="sub_123"
)
response = client.request(delete_request)
```

## Request/Response Handling

### Making Requests

```python
# All requests follow this pattern
response = client.request(request_object, raise_for_status=True)

# Access response data
status_code = response.status_code
response_body = response.response_body
```

### Error Handling

```python
from ratio.client.client import RequestAttributeError

try:
    response = client.request(request, raise_for_status=False)
    if response.status_code >= 400:
        print(f"Error: {response.status_code}")
        print(f"Body: {response.response_body}")
except RequestAttributeError as e:
    print(f"Invalid request attribute: {e.attribute_name}")
except ValueError as e:
    print(f"Request failed: {e}")
```

## Authentication Details

### Token Management

```python
# Refresh token manually
client.refresh_token(entity_id="user_id", private_key=private_key_bytes)

# Sign message (used internally)
signature = Ratio.sign_message_rsa(
    private_key_pem=private_key_bytes,
    message="message_to_sign"
)
```

### Challenge/Response Flow

The client automatically handles the challenge/response authentication flow:

1. Sends `ChallengeRequest` with entity_id
2. Receives challenge and system signature
3. Signs challenge with private key
4. Sends `TokenRequest` with signatures
5. Receives authentication token

## Request Body Attributes

### Attribute Types

From `RequestAttributeType`:
- `ANY`: Any value type
- `BOOLEAN`: Boolean values
- `DATETIME`: Datetime objects or ISO format strings
- `FLOAT`: Float values
- `INTEGER`: Integer values
- `LIST`: List values
- `OBJECT`: Dictionary/object values
- `OBJECT_LIST`: List of objects
- `STRING`: String values

### Custom Request Bodies

```python
from ratio.client.client import RequestBody, RequestBodyAttribute, RequestAttributeType

class CustomRequest(RequestBody):
    path = '/custom/endpoint'
    requires_auth = True
    
    attribute_definitions = [
        RequestBodyAttribute(
            name="required_field",
            attribute_type=RequestAttributeType.STRING,
            optional=False
        ),
        RequestBodyAttribute(
            name="optional_field",
            attribute_type=RequestAttributeType.OBJECT,
            optional=True,
            default={}
        ),
        RequestBodyAttribute(
            name="conditional_field",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
            required_if_attrs_not_set=["other_field"]
        )
    ]
    
    def __init__(self, required_field: str, optional_field: dict = None):
        super().__init__(
            required_field=required_field,
            optional_field=optional_field
        )
```

## Response Structure

All responses from `client.request()` have:
- `status_code`: HTTP status code
- `response_body`: Response data (usually dict, sometimes string)

The structure of `response_body` varies by endpoint - check the test files for examples of expected response formats.