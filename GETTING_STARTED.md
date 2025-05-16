Ratio CLI (RTO) Usage Guide
===========================

Ratio is an AI Operating System built on Cloud Native AWS Technologies. This guide explains how to use the Ratio Terminal Operator (RTO) command line interface to interact with the system.

Table of Contents
-----------------

- [Installation](#installation)
- [System Initialization](#system-initialization)
- [Authentication and Configuration](#authentication-and-configuration)
- [Entity Management](#entity-management)
- [File System Navigation](#file-system-navigation)
- [File Management](#file-management)
- [File Types](#file-types)
- [Agent Management](#agent-management)
- [Scheduler and Subscriptions](#scheduler-and-subscriptions)
- [Common Operations](#common-operations)

Installation
------------

Prerequisites:
- Python 3.12+
- AWS account with appropriate permissions
- AWS CDK
- Poetry for dependency management

Setup:
```bash
# Clone the repository
git clone https://github.com/jarosser06/ratio.git

# Install dependencies
cd ratio
poetry install

# Deploy all stacks if not using an already deployed version of Ratio
make deploy
```

System Initialization
---------------------

Initialize the system:
```bash
# Initialize the system with default admin entity
rto init

# Initialize with a custom public key file
rto init --public-key /path/to/public_key
```

This creates an admin entity and saves the private key to `private_key.pem`.

Authentication and Configuration
--------------------------------

### Configure profiles

Create profiles for different entities:
```bash
# Create a default profile
rto configure

# Create a named profile
rto configure --name user1 --config-entity user1 --config-key /path/to/user1_key.pem

# Set as default profile
rto configure --name user1 --set-default
```

### Use different profiles

```bash
# Run a command with a specific profile
rto --profile user1 list-files

# After setting default, commands use that profile
rto list-files
```

Entity Management
-----------------

### Create and manage entities

```bash
# Create a new entity (user)
rto create-entity new_user --description "Regular user"

# Create entity and generate keys
rto create-entity new_user
# Keys will be saved to new_user_priv_key.pem and new_user_pub_key

# Create entity without home directory
rto create-entity service_entity --no-create-home

# Create entity with custom home directory
rto create-entity custom_user --home-directory /custom/home/path
```

### Manage groups

```bash
# Create a group
rto create-group developers --description "Development team"

# Add entity to group
rto add-to-group user1 developers

# Remove entity from group
rto remove-from-group user1 developers

# Delete a group
rto delete-group developers --force
```

### View entity and group information

```bash
# List all entities
rto list-entities
rto list-entities --detailed

# List all groups
rto list-groups
rto list-groups --detailed

# View entity details
rto describe-entity user1

# View group details
rto describe-group developers
```

### Update entity information

```bash
# Rotate entity's encryption key
rto rotate-key user1 --public-key /path/to/new_key
```

File System Navigation
----------------------

```bash
# Print working directory
rto pwd

# Change directory
rto cd /path/to/directory
rto cd ..          # Go up one level
rto cd /           # Go to root
rto cd ~/          # Go to home directory

# List files in current directory
rto ls
rto ls /path       # List files in specific path
rto ls -l          # Detailed listing
```

File Management
---------------

### Create files and directories

```bash
# Create directory
rto mkdir /path/to/new_dir
rto mkdir -p /nested/path/new_dir  # Create parent directories if needed

# Create file
rto create-file /path/to/file.txt "File content"
rto touch /path/to/empty_file  # Create empty file

# Create with specific file type
rto create-file --file-type custom::document /path/to/doc.txt "Content"

# Create with permissions
rto create-file --permissions 644 /path/to/file.txt "Content"
```

### Manage files

```bash
# Get file content
rto get-file /path/to/file.txt
rto cat /path/to/file.txt

# Get file content and save to local file
rto get-file /path/to/file.txt --output local_file.txt

# View file details
rto describe-file /path/to/file.txt
rto stat /path/to/file.txt

# Change permissions
rto chmod 644 /path/to/file.txt

# Change owner
rto chown new_owner /path/to/file.txt

# Change group
rto chgrp new_group /path/to/file.txt

# Delete file
rto delete-file /path/to/file.txt
rto rm /path/to/file.txt

# Delete directory and contents
rto rm -r /path/to/directory
```

### File versions

```bash
# List versions of a file
rto list-file-versions /path/to/file.txt
rto lsv /path/to/file.txt

# Get specific version
rto get-file /path/to/file.txt --version-id VERSION_ID

# Describe specific version
rto describe-file-version /path/to/file.txt --version-id VERSION_ID

# Delete a specific version
rto delete-file-version /path/to/file.txt --version-id VERSION_ID
```

### Sync files

```bash
# Sync from local to Ratio
rto sync ./local_directory ratio:/remote/directory

# Sync from Ratio to local
rto sync ratio:/remote/directory ./local_directory

# Recursive sync with exclusions
rto sync -r ./local_dir ratio:/remote/dir --exclude "*.tmp" --include "*.txt"
```

File Types
----------

```bash
# List file types
rto list-file-types
rto lsft --detailed

# Show specific file type details
rto describe-file-type custom::document

# Create or update a file type
rto put-file-type custom::document --description "Custom document format"

# Create container file type
rto put-file-type custom::folder --description "Custom folder" --is-container-type

# Delete a file type
rto delete-file-type custom::document
rto rmtype custom::document
```

Agent Management
----------------

### Execute agents

```bash
# Execute agent from definition file
rto execute --agent-definition-path /path/to/agent.def --arguments '{"input": "value"}'

# Execute with inline definition
rto execute --agent-definition '{"arguments":[...],"description":"..."}' --arguments '{"input": "value"}'

# Execute as a different entity (admin only)
rto execute --agent-definition-path /path/to/agent.def --execute-as other_entity

# Execute with working directory
rto execute --agent-definition-path /path/to/agent.def --working-directory /path/to/workdir

# Wait for completion
rto execute --agent-definition-path /path/to/agent.def --wait
```

### View processes

```bash
# List processes
rto list-processes
rto lsproc

# Filter processes
rto list-processes --owner user1
rto list-processes --status RUNNING

# Get process details
rto describe-process PROCESS_ID
```

Scheduler and Subscriptions
---------------------------

```bash
# Create subscription for file changes
rto create-subscription /path/to/agent.def /path/to/watched_file.txt

# Create single-use subscription
rto create-subscription /path/to/agent.def /path/to/file.txt --single-use

# Create subscription with expiration
rto create-subscription /path/to/agent.def /path/to/file.txt --expiration "2023-12-31T23:59:59"

# Create subscription for specific file event
rto create-subscription /path/to/agent.def /path/to/file.txt --file-event-type created

# List subscriptions
rto list-subscriptions
rto lssub

# Get subscription details
rto describe-subscription SUBSCRIPTION_ID
rto dsub SUBSCRIPTION_ID

# Delete subscription
rto delete-subscription SUBSCRIPTION_ID
rto rmsub SUBSCRIPTION_ID
```

Common Operations
-----------------

### Initialization workflow

```bash
# Initialize the system
rto init

# Create a service entity
rto create-entity service1 --description "Service account"

# Create a group for services
rto create-group services --description "Service accounts"

# Add entity to group
rto add-to-group service1 services

# Configure a profile for the new entity
rto configure --name service_profile --config-entity service1 --config-key service1_priv_key.pem
```

### File management workflow

```bash
# Create directory structure
rto mkdir -p /projects/demo

# Create a custom file type
rto put-file-type demo::doc --description "Demo document type"

# Create a document
rto create-file --file-type demo::doc /projects/demo/document.txt "Document content"

# Create additional version
echo "Updated content" | rto create-file --file-type demo::doc /projects/demo/document.txt

# List versions
rto lsv /projects/demo/document.txt

# Get specific version
rto get-file /projects/demo/document.txt --version-id VERSION_ID
```

### Agent and subscription workflow

```bash
# Create an agent definition file
rto create-file --file-type ratio::agent /agents/process_doc.def '{
  "arguments": [
    {"name": "input_file", "type_name": "file", "required": true}
  ],
  "description": "Document processing agent",
  "responses": [
    {"name": "result", "type_name": "string", "required": true}
  ],
  "system_event_endpoint": "ratio::agent::processor::execution"
}'

# Create a file to monitor
rto create-file /data/monitor.txt "Initial content"

# Create a subscription
rto create-subscription /agents/process_doc.def /data/monitor.txt

# Update the file to trigger the agent
echo "New content" | rto create-file /data/monitor.txt

# Check process status
rto list-processes --status COMPLETED
```

This guide covers the basic usage of the Ratio Terminal Operator. For more detailed information about specific commands, use the `--help` flag:

```bash
rto --help
rto command --help
```
