# Ratio Storage Manager (File System) Documentation

## Overview

The Ratio Storage Manager provides a file system abstraction layer that manages files, directories, permissions,
versioning, and metadata within the Ratio platform. It acts as the central data storage and retrieval service, offering Unix-like
file system semantics with advanced features like automatic versioning, lineage tracking, and event-driven notifications.

## Core Concepts

### File System Structure

The Storage Manager implements a hierarchical file system similar to Unix/Linux:

- **Root Directory (`/`)**: Top-level directory owned by the `system` entity
- **Home Directories (`/home/<entity>`)**: Personal directories for each entity
- **Arbitrary Paths**: Users can create custom directory structures with proper permissions

### Key Components

#### 1. Files and Directories
- **Files**: Individual data objects that can contain content
- **Directories**: Containers that can hold other files and directories
- **File Types**: Registered types that define naming restrictions and behavior
- **Permissions**: Unix-style permissions (owner/group/everyone with read/write/execute)

#### 2. Versioning System
- **Automatic Versioning**: Every file modification creates a new version
- **Version History**: Complete history of all file changes
- **Version References**: Ability to reference specific versions
- **Rollback Capability**: Access to any previous version

#### 3. Metadata and Lineage
- **File Metadata**: Custom key-value pairs associated with files
- **Lineage Tracking**: Tracks relationships between files (source → derived)
- **Audit Trail**: Complete history of file operations

## Architecture

### Tables

#### Files Table (`files`)
Stores metadata about files and directories:

- **Primary Key**: `path_hash` (partition) + `name_hash` (sort)
- **Key Attributes**: `file_name`, `file_path`, `file_type`, `owner`, `group`, `permissions`
- **Features**: Permission masks, metadata storage, version tracking

#### File Versions Table (`file_versions`)
Stores individual file versions:

- **Primary Key**: `full_path_hash` (partition) + `version_id` (sort)
- **Key Attributes**: Version linking (previous/next), originator tracking
- **Features**: Linked list structure for version history

#### File Types Table (`file_types`)
Defines available file types:

- **Primary Key**: `type_name`
- **Key Attributes**: `description`, `name_restrictions`, `is_directory_type`
- **Features**: Validation rules, content type definitions

#### File Lineage Table (`file_lineage`)
Tracks relationships between files:

- **Primary Key**: `source_file_id` (partition) + `lineage_file_id` (sort)
- **Key Attributes**: Source and target file information

### S3 Integration

- **Raw Storage**: All file content stored in versioned S3 bucket
- **Automatic Versioning**: S3 versioning enabled for complete history
- **Efficient Storage**: Only metadata stored in DynamoDB, content in S3

## API Reference

### File Operations

#### Create/Update File
```bash
PUT /storage/put_file
{
  "file_path": "/path/to/file",
  "file_type": "ratio::file",
  "permissions": "644",
  "owner": "entity_id",
  "group": "group_id",
  "metadata": {"key": "value"}
}
```

#### Add File Content
```bash
PUT /storage/put_file_version
{
  "file_path": "/path/to/file",
  "data": "file content or binary data",
  "metadata": {"version": "1.0"},
  "origin": "internal",
  "source_files": [
    {
      "source_file_path": "/source/file",
      "source_file_version": "version_id"
    }
  ]
}
```

#### Read File
```bash
GET /storage/get_file_version
{
  "file_path": "/path/to/file",
  "version_id": "optional_specific_version"
}
```

#### List Directory
```bash
GET /storage/list_files
{
  "file_path": "/path/to/directory"
}
```

#### File Information
```bash
GET /storage/describe_file
{
  "file_path": "/path/to/file"
}
```

### Permission Operations

#### Change Permissions
```bash
PUT /storage/change_file_permissions
{
  "file_path": "/path/to/file",
  "permissions": "755"
}
# OR
{
  "file_path": "/path/to/file",
  "owner": "new_owner",
  "group": "new_group"
}
```

#### Validate Access
```bash
POST /storage/validate_file_access
{
  "file_path": "/path/to/file",
  "requested_permission_names": ["read", "write"]
}
```

### Advanced Operations

#### Copy File
```bash
POST /storage/copy_file
{
  "source_file_path": "/source/file",
  "destination_file_path": "/dest/file",
  "recursive": true,
  "version_id": "specific_version"
}
```

#### Delete File
```bash
DELETE /storage/delete_file
{
  "file_path": "/path/to/file",
  "force": false,
  "recursive": false
}
```

### File Type Management

#### Register File Type
```bash
PUT /storage/put_file_type
{
  "file_type": "custom::type",
  "description": "Custom file type",
  "is_directory_type": false,
  "name_restrictions": "^[a-zA-Z0-9_-]+\\.(txt|md)$"
}
```

## Permission System

### Unix-Style Permissions

Permissions follow Unix conventions with three levels:
- **Owner**: The entity that owns the file
- **Group**: The group that owns the file  
- **Everyone**: All other entities

### Permission Types

- **Read (4)**: View file content or list directory contents
- **Write (2)**: Modify file content or create/delete files in directory
- **Execute (1)**: Access file or traverse directory

### Permission Format

Permissions are specified as a 3-digit octal number:

- First digit: Owner permissions
- Second digit: Group permissions
- Third digit: Everyone permissions

**Examples:**
- `755`: Owner (rwx), Group (r-x), Everyone (r-x)
- `644`: Owner (rw-), Group (r--), Everyone (r--)
- `700`: Owner (rwx), Group (---), Everyone (---)

### Access Control

Access is determined by:
1. **Admin Override**: Admins have full access to all files
2. **Owner Check**: File owner has permissions defined in owner bits
3. **Group Check**: Group members have permissions defined in group bits
4. **Everyone Check**: All other entities have permissions defined in everyone bits

## File Types

### Built-in Types

- **`ratio::file`**: Standard file type for general content
- **`ratio::directory`**: Directory type for containers
- **`ratio::agent`**: Agent definition files
- **`ratio::agent_io`**: Agent input/output files

### Custom File Types

Create custom types with specific validation rules:

```bash
rto put-file-type custom::config \
  --description="Configuration files" \
  --name-restrictions="^.*\\.config\\.json$"
```

## Versioning and Lineage

### Automatic Versioning

Every file modification creates a new version:
- Versions are linked in chronological order
- Each version has a unique S3 version ID
- Previous versions remain accessible indefinitely

### Lineage Tracking

Track relationships between files:
- **Source Files**: Files that contributed to creating another file
- **Derived Files**: Files created from other source files
- **Impact Analysis**: Understand downstream effects of changes

### Version Management

```bash
# List all versions
rto list-file-versions /path/to/file

# Get specific version
rto get-file-version /path/to/file --version-id=specific_version

# Delete specific version
rto delete-file-version /path/to/file --version-id=version_to_delete
```

## Event System

### File Events

The Storage Manager publishes events for:
- **Created**: New file or directory created
- **Updated**: File metadata or content modified
- **Deleted**: File or directory removed
- **Version Created**: New version of existing file added
- **Version Deleted**: Specific version removed

### Event Structure

```json
{
  "file_path": "/path/to/file",
  "file_type": "ratio::file",
  "file_event_type": "created",
  "is_directory": false,
  "requestor": "entity_id",
  "details": {
    "version_id": "new_version_id"
  }
}
```

### Integration with Scheduler

File events automatically trigger subscribed agents through the Scheduler service.

## Best Practices

### Directory Structure

```
/
├── home/
│   ├── entity1/
│   │   ├── data/
│   │   ├── agents/
│   └── entity2/
│       └── data/
|       └── agents/
├── shared/
│   ├── templates/
│   └── resources/
├── agents/
│   ├── core/
│   └── purpose/
└── run/
    └─── agent-execute....
```

### Security Guidelines

1. **Principle of Least Privilege**: Grant minimal necessary permissions
2. **Group-Based Access**: Use groups for shared resources
3. **Regular Audits**: Monitor file access and permissions
4. **Secure Defaults**: Default to restrictive permissions (644 for files, 755 for directories)

### Performance Optimization

1. **Efficient Queries**: Use specific paths rather than scanning
2. **Metadata Usage**: Store searchable information in metadata
3. **Version Management**: Clean up old versions when not needed
4. **Batch Operations**: Group related operations together

### File Organization

1. **Logical Grouping**: Organize files by purpose or project
2. **Consistent Naming**: Use consistent naming conventions
3. **Metadata Documentation**: Use metadata for descriptions and tags
4. **Type Classification**: Use appropriate file types for validation

## Integration Examples

### Agent File Processing

```python
# Agent reading input file
input_file = system.arguments["input_file"]
file_data = system.get_file_version(input_file)
content = json.loads(file_data["data"])

# Agent writing output file
output_path = "/tmp/processed_data.json"
system.put_file(
    file_path=output_path,
    file_type="ratio::file",
    data=json.dumps(processed_data),
    metadata={"agent": "data_processor", "version": "1.0"}
)
```

### CLI File Operations

```bash
# Create directory structure
rto mkdir /projects/analysis --parents --permissions=755

# Upload data file
rto sync local_data.csv ratio:/projects/analysis/input.csv

# Set up file monitoring
rto create-subscription /agents/processor.agent /projects/analysis \
    --file-event-type=created --file-type=ratio::file
```

## Error Handling

### Common Errors

- **404 Not Found**: File or directory doesn't exist
- **403 Forbidden**: Insufficient permissions
- **400 Bad Request**: Invalid file type or path format
- **409 Conflict**: File already exists when creating

### Error Recovery

1. **Permission Denied**: Check file ownership and permissions
2. **File Not Found**: Verify path and ensure file exists
3. **Version Conflicts**: Use specific version IDs for precision
4. **Storage Errors**: Check S3 connectivity and permissions

## Monitoring and Maintenance

### Health Monitoring

- **S3 Connectivity**: Ensure bucket accessibility
- **DynamoDB Performance**: Monitor read/write capacity
- **Version Growth**: Track storage usage over time

### Maintenance Tasks

- **Version Cleanup**: Remove old versions when appropriate
- **Permission Audits**: Regular review of file permissions