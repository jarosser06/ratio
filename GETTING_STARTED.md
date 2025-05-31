Ratio CLI (RTO) Getting Started Guide
=====================================

Ratio is an AI Operating System built on Cloud Native AWS Technologies. This guide walks you through installing and configuring the Ratio Terminal Operator (RTO) command line interface.

## Prerequisites

- Python 3.12+
- AWS account with appropriate permissions
- AWS CDK installed and configured
- Poetry for dependency management

## Installation

### Step 1: Set Up Python Environment

**Virtual Environment Recommended**: Ratio recommends using a Python virtual environment to isolate dependencies and avoid conflicts with other Python projects on your system.

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/jarosser06/ratio.git
cd ratio

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
poetry install
```

The virtual environment ensures Ratio's dependencies don't interfere with other Python projects and makes it easy to manage different versions.

### Step 2: Run Installation Script

The `install.sh` script handles both AWS infrastructure deployment and local system initialization:

```bash
# Full installation (deploys infrastructure and initializes system)
./install.sh

# Skip deployment if infrastructure already exists
./install.sh --skip-deploy

# Customize configuration
./install.sh --entity-id myuser --deployment-id production
```

**Installation Options:**
- `--skip-deploy` - Skip CDK deployment (deploy runs by default)
- `--entity-id ID` - Entity ID for admin user (default: admin)
- `--deployment-id ID` - Deployment ID (default: dev)
- `--verbose` - Show detailed output

The installation script will:
1. Validate the rto command is available
2. Deploy AWS infrastructure via CDK (unless --skip-deploy is used)
3. Set up configuration directories in `~/.rto`
4. Copy shell utilities to `~/.rto/shell/bin`
5. Initialize the Ratio system and create the admin entity
6. Configure the default CLI profile

## Understanding Key Concepts

### Admin Entity
The entity specified during installation becomes the admin user for your Ratio system. This entity has full system privileges.

### Deployment ID
The deployment ID (default: "dev") identifies your Ratio environment. Multiple deployments can exist in the same AWS account for different environments (dev, staging, production).

### Configuration Directory
Ratio stores configuration and keys in `~/.rto/`:
- `~/.rto/keys/` - Private keys for entities
- `~/.rto/shell/` - Shell configuration and utilities
- `~/.rto/shell/bin/` - Custom shell commands

## Verify Installation

Test that Ratio is working correctly:

```bash
# Check current directory
rto pwd

# List root directories
rto ls

# Test file operations
rto mkdir /test
rto create-file /test/hello.txt "Hello, Ratio!"
rto cat /test/hello.txt
```

## Bootstrap System Files

Use the `fs_sync` utility to populate your Ratio filesystem from the root of the ratio project:

```bash
# From the ratio project root directory
./ratio_shell/execute

# Run fs_sync to upload local _fs directory to Ratio
fs_sync
```

The `fs_sync` command maps your local `_fs` directory structure directly to the Ratio filesystem (e.g., `_fs/agents/` → `ratio:/agents/`). This must be run from the ratio project root where the `_fs` directory is located.

## Interactive Shell

Launch the interactive Ratio shell for easier navigation:

```bash
./ratio_shell/execute
```

The shell provides:
- Unix-like commands (`ls`, `cd`, `pwd`, `mkdir`, `rm`, `cat`)
- Access to custom utilities in `~/.rto/shell/bin/`
- Command history and tab completion
- Integration with your configured Ratio profile

## Next Steps

- Create additional entities: `rto create-entity username`
- Define agent workflows in `/agents/`
- Set up file monitoring with subscriptions
- Explore the file system: `rto ls /` to see available directories

## Troubleshooting

**Command not found**: Ensure your virtual environment is activated and `poetry install` completed successfully.

**CDK deployment fails**: Check AWS credentials and permissions. Deployment logs are saved to `deploy.log` if not running with `--verbose`.

**Profile configuration issues**: Run `rto configure` to reconfigure your default profile manually.

## CLI Reference

For detailed command information:
```bash
rto --help                    # Main help
rto command --help           # Command-specific help
```

Common commands:
- `rto ls` - List files and directories
- `rto cd /path` - Change working directory  
- `rto pwd` - Print current directory
- `rto create-file /path/file.txt "content"` - Create a file
- `rto execute --agent-definition-path /path/agent.def` - Run an agent
- `rto list-processes` - View running processes