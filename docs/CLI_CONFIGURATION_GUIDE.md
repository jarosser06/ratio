# Ratio CLI Configuration Guide

## Overview

The Ratio CLI (`rto`) uses a configuration system to manage authentication credentials, connection settings, and state information like the current working directory. This guide explains how configuration works, how to set it up, and how it's used.

## Configuration Directory Structure

The CLI stores configuration in a dedicated directory (default: `~/.rto/`):

```
~/.rto/
├── config.json          # Main configuration file
├── tokens/               # Cached authentication tokens
│   ├── default.token
│   └── prod.token
└── keys/                 # Generated private keys
    ├── admin_priv_key.pem
    └── dev_user_priv_key.pem
```

## Configuration File Format

The main configuration file (`config.json`) stores:

```json
{
  "default_profile": "default",
  "working_directory": "/data/projects",
  "profiles": {
    "default": {
      "entity_id": "admin",
      "app_name": "ratio",
      "deployment_id": "dev",
      "private_key_path": "/home/user/.rto/keys/admin_priv_key.pem"
    },
    "prod": {
      "entity_id": "prod_admin",
      "app_name": "ratio",
      "deployment_id": "prod",
      "private_key_path": "/home/user/.rto/keys/prod_admin_priv_key.pem"
    }
  }
}
```

### Configuration Fields

- **`default_profile`**: The profile name to use when none is specified via `--profile`
- **`working_directory`**: Current working directory for file operations (globally tracked across all profiles)
- **`profiles`**: Named collections of connection and authentication parameters

### Profile Fields

Each profile contains these configuration parameters:

- **`entity_id`**: The identity/user to authenticate as in the Ratio system
- **`app_name`**: The Ratio application name (typically "ratio")  
- **`deployment_id`**: The environment identifier (e.g., "dev", "staging", "prod")
- **`private_key_path`**: Absolute path to the private key file for this entity

### Profile vs Global Settings

**Global Settings** (apply to all profiles):
- `working_directory`: Shared across all profiles
- `default_profile`: Which profile to use by default

**Profile-Specific Settings**:
- `entity_id`, `app_name`, `deployment_id`, `private_key_path`: Unique per profile
- Cached tokens (stored separately per profile in `tokens/` directory)

## Working Directory Management

**Important**: The working directory is stored globally in the configuration file, not per-profile. This means:

- `rto pwd` always shows the same directory regardless of which profile is active
- `rto cd /some/path` changes the working directory for all future commands
- The working directory persists between CLI sessions
- Relative paths in commands are resolved against this working directory

### Working Directory Examples

```bash
# Check current working directory
rto pwd
# Output: /

# Change working directory
rto cd /data/projects
rto pwd
# Output: /data/projects

# Relative paths now resolve against /data/projects
rto ls input/          # Lists /data/projects/input/
rto stat config.json   # Checks /data/projects/config.json

# Switch profiles - working directory stays the same
rto --profile=prod pwd
# Output: /data/projects (still the same)
```

## Profile Management

### Creating Profiles

#### Interactive Configuration

The `configure` command walks you through setting up a profile:

```bash
# Configure a new profile interactively
rto configure --name=dev

# Example interaction:
# Entity ID [admin]: dev_user
# App name [ratio]: ratio  
# Deployment ID [dev]: development
# Private key path [/home/user/private_key.pem]: /home/user/.ssh/dev_key.pem
# Profile 'dev' saved successfully.
```

How the interactive prompts work:
- **Brackets show defaults**: `[admin]` means "admin" is the default
- **Defaults come from**: Environment variables, existing profile values, or built-ins
- **Empty input**: Accepts the default value
- **Validation**: Checks if private key file exists (warns if not found)

#### Non-Interactive Configuration

Specify all parameters directly:

```bash
# Configure a profile non-interactively
rto configure --name=prod \
    --config-entity=prod_admin \
    --config-app=ratio \
    --config-deployment=production \
    --config-key=/secure/keys/prod_admin.pem \
    --set-default

# Configure without setting as default
rto configure --name=staging \
    --config-entity=staging_user \
    --config-deployment=staging \
    --config-key=~/.ssh/staging_key.pem \
    --non-interactive
```

#### Updating Existing Profiles

Re-run configure with the same name to update:

```bash
# Update existing profile (shows current values as defaults)
rto configure --name=dev
# Current values will be shown as defaults in prompts

# Update specific fields only
rto configure --name=dev --config-key=/new/path/to/key.pem --non-interactive
```

### Profile Operations

#### Listing Profiles

```bash
# View configuration file to see all profiles
cat ~/.rto/config.json

# Check which profile is default
cat ~/.rto/config.json | jq -r .default_profile
```

#### Deleting Profiles

```bash
# Manual deletion (edit ~/.rto/config.json)
# Remove the profile from the "profiles" object
# Update "default_profile" if needed

# Or delete entire configuration to start fresh
rm -rf ~/.rto/
```

### Profile Configuration Details

#### Configuration Arguments

When using `rto configure`, use these specific argument names:

- `--config-entity` (not `--entity`) - Sets the entity_id
- `--config-app` (not `--app-name`) - Sets the app_name  
- `--config-deployment` (not `--deployment-id`) - Sets the deployment_id
- `--config-key` (not `--private-key`) - Sets the private_key_path

#### Setting Default Profile

```bash
# Method 1: During configuration
rto configure --name=prod --set-default

# Method 2: Update existing profile to be default  
rto configure --name=existing_profile --set-default

# Method 3: Manual editing
# Edit ~/.rto/config.json: "default_profile": "desired_profile_name"
```

#### Profile Validation

The configure command performs validation:

- **Profile name**: Must be a valid identifier
- **Private key path**: Warns if file doesn't exist
- **Entity conflicts**: No validation (assumes you know what you're doing)

### Profile Best Practices

#### Naming Conventions

- Use environment names: `dev`, `staging`, `prod`
- Include your name for shared systems: `alice_dev`, `bob_prod`
- Avoid spaces and special characters

#### Key Management Per Profile

```bash
# Generate separate keys for each environment
rto create-entity dev_alice    # Generates keys automatically
rto create-entity prod_alice --public-key=/path/to/existing/key

# Configure profiles with respective keys
rto configure --name=dev --config-entity=dev_alice --config-key=dev_alice_priv_key.pem
rto configure --name=prod --config-entity=prod_alice --config-key=prod_alice_priv_key.pem
```

#### Environment Isolation

```bash
# Separate profiles prevent accidental cross-environment actions
rto --profile=dev execute --agent-definition-path=/agents/test.agent    # Safe
rto --profile=prod execute --agent-definition-path=/agents/test.agent   # Explicit

# Always specify profile for production commands
rto --profile=prod list-processes
rto --profile=prod describe-process 1234-5678
```

### Using Profiles

#### How Profile Selection Works

The CLI determines which profile to use through the following precedence order:

1. **Command-line `--profile` flag** (highest priority)
2. **Default profile** from configuration file
3. **Built-in defaults** if no configuration exists

#### Default Profile

When no `--profile` flag is specified, the CLI uses the default profile:

```bash
# Uses default profile (as specified in config.json)
rto list-files
rto execute --agent-definition-path=/agents/my_agent.agent

# Check which profile is default
cat ~/.rto/config.json | grep default_profile
```

#### Explicit Profile Selection

Override the default for a single command:

```bash
# Use a specific profile for one command
rto --profile=prod list-files

# All global options must come before the command
rto --profile=staging --config-path=/alt/config execute --agent-definition-path=/agents/test.agent

# Multiple profile uses
rto --profile=dev list-processes
rto --profile=prod describe-process 1234-5678
rto --profile=dev execute --agent-definition-path=/agents/test.agent
```

#### Switching Default Profile

Change which profile is used by default:

```bash
# Method 1: Set existing profile as default
rto configure --name=prod --set-default

# Method 2: Configure new profile and make it default
rto configure --name=new_env --set-default

# Method 3: Edit configuration manually
# Edit ~/.rto/config.json and change "default_profile" value
```

#### Profile Configuration Inheritance

When using a profile, these values are loaded in order (later values override earlier ones):

1. **Built-in defaults**:
   - `entity_id`: "admin"
   - `app_name`: Value of `DA_VINCI_APP_NAME` env var or "ratio"
   - `deployment_id`: Value of `DA_VINCI_DEPLOYMENT_ID` env var or "dev"

2. **Profile configuration** (from config.json)

3. **Environment variables**:
   - `DA_VINCI_APP_NAME` → overrides `app_name`
   - `DA_VINCI_DEPLOYMENT_ID` → overrides `deployment_id`

4. **Command-line flags** (highest priority):
   - `--entity` → overrides `entity_id`
   - `--app-name` → overrides `app_name`
   - `--deployment-id` → overrides `deployment_id`
   - `--private-key` → overrides `private_key_path`

#### Configuration Loading Example

Given this configuration:
```json
{
  "default_profile": "dev",
  "profiles": {
    "dev": {
      "entity_id": "dev_user",
      "app_name": "ratio",
      "deployment_id": "development",
      "private_key_path": "/home/user/.rto/keys/dev_key.pem"
    }
  }
}
```

And these environment variables:
```bash
export DA_VINCI_DEPLOYMENT_ID=staging
```

This command:
```bash
rto --entity=test_user list-files
```

Results in:
- `entity_id`: "test_user" (from --entity flag)
- `app_name`: "ratio" (from profile)
- `deployment_id`: "staging" (from environment variable)
- `private_key_path`: "/home/user/.rto/keys/dev_key.pem" (from profile)

## Authentication Flow

### Token Caching

The CLI automatically caches authentication tokens:

1. First authentication generates and caches a token
2. Subsequent commands reuse the cached token
3. Expired tokens are automatically refreshed
4. Tokens are stored per-profile in the `tokens/` directory

### Authentication Process

```bash
# First command with a profile
rto --profile=dev list-files
# 1. Checks for cached token for 'dev' profile
# 2. No token found, authenticates using private key
# 3. Caches the new token
# 4. Executes the command

# Subsequent commands
rto --profile=dev list-processes
# 1. Finds cached token for 'dev' profile
# 2. Token is still valid, uses it directly
# 3. Executes the command
```

### Token Expiration

When a token expires:

```bash
rto list-files
# 1. Tries to use cached token
# 2. Token is expired
# 3. Automatically authenticates with private key
# 4. Updates cached token
# 5. Executes the command
```

## Command-Line Options

### Global Options

These options affect the configuration system:

```bash
--config-path=<path>     # Use custom config directory (default: ~/.rto)
--profile=<name>         # Use specific profile
--app-name=<name>        # Override app name for this command
--deployment-id=<id>     # Override deployment ID for this command
--entity=<id>            # Override entity ID for this command
--private-key=<path>     # Override private key for this command
```

### Option Precedence

Configuration values are resolved in this order (highest to lowest priority):

1. Command-line flags (`--entity=admin`)
2. Environment variables (`DA_VINCI_APP_NAME`, `DA_VINCI_DEPLOYMENT_ID`)
3. Active profile configuration
4. Built-in defaults

## Environment Variables

Some settings can be overridden with environment variables:

```bash
export DA_VINCI_APP_NAME=ratio
export DA_VINCI_DEPLOYMENT_ID=dev

# These will be used as defaults when creating new profiles
rto configure --name=test
```

## Path Resolution

All file paths in commands are resolved against the current working directory:

### Absolute Paths

```bash
# Always interpreted as-is
rto stat /data/input.csv           # Checks /data/input.csv
rto cd /some/path && rto stat /data/input.csv  # Still checks /data/input.csv
```

### Relative Paths

```bash
# Resolved against working directory
rto pwd                            # /data/projects
rto stat input.csv                 # Checks /data/projects/input.csv
rto stat ../shared/config.json     # Checks /data/shared/config.json
```

### Path Examples

```bash
# Set working directory
rto cd /data/projects

# These are equivalent:
rto stat input/data.csv            # Relative to /data/projects
rto stat /data/projects/input/data.csv  # Absolute path

# Parent directory access
rto stat ../shared/config.json     # Resolves to /data/shared/config.json

# Current directory reference
rto stat ./local.json              # Resolves to /data/projects/local.json
```

## Configuration Examples

### Development Setup

```bash
# Configure development environment
rto configure --name=dev \
    --config-entity=dev_user \
    --config-app=ratio \
    --config-deployment=development \
    --config-key=~/.ssh/dev_key.pem

# Set working directory for development
rto cd /data/dev_projects

# Work normally
rto ls
rto execute --agent-definition-path=agents/test_agent.agent
```

### Multi-Environment Workflow

```bash
# Configure multiple environments
rto configure --name=dev --config-deployment=dev --config-entity=dev_admin
rto configure --name=staging --config-deployment=staging --config-entity=staging_admin  
rto configure --name=prod --config-deployment=prod --config-entity=prod_admin --set-default

# Switch between environments
rto --profile=dev list-processes
rto --profile=staging execute --agent-definition-path=/agents/test.agent
rto --profile=prod list-files  # Uses prod as default

# Working directory is shared across all profiles
rto pwd  # Same result regardless of profile
```

### Team Setup

```bash
# Each team member configures their own entity
rto configure --name=default \
    --config-entity=alice \
    --config-deployment=dev \
    --config-key=~/.rto/keys/alice_priv_key.pem

# Shared working directory conventions
rto cd /data/team_project
rto ls shared/
rto stat alice/work_in_progress.json
```

## Troubleshooting Configuration

### Check Current Configuration

```bash
# View current working directory
rto pwd

# If you need to see profile details, check the config file directly
cat ~/.rto/config.json
```

### Configuration Issues

```bash
# Profile not found
rto --profile=nonexistent list-files
# Error: Profile 'nonexistent' does not exist

# Invalid private key
rto list-files
# Error: Authentication failed: private key file not found

# Permission issues
rto list-files  
# Error: Permission denied: Not authorized to list files
# (Check entity permissions in the Ratio system)
```

### Reset Configuration

```bash
# Remove configuration to start fresh
rm -rf ~/.rto/
rto configure --name=default  # Will create new config
```

### Configuration File Corruption

```bash
# If config.json is corrupted, recreate it
mv ~/.rto/config.json ~/.rto/config.json.backup
rto configure --name=default  # Creates new configuration
```

## Security Considerations

### Private Key Security

- Store private keys securely (recommended: `~/.ssh/` or `~/.rto/keys/`)
- Set restrictive permissions: `chmod 600 ~/.rto/keys/*.pem`
- Don't share private keys between team members
- Use different keys for different environments

### Token Security

- Tokens are stored locally in `~/.rto/tokens/`
- Tokens have expiration times and are automatically refreshed
- Remove `~/.rto/tokens/` if you suspect compromise

### Configuration File Security

- Configuration file may contain sensitive paths
- Recommended permissions: `chmod 600 ~/.rto/config.json`
- Don't commit `.rto/` directory to version control

## Best Practices

### Profile Naming

- Use descriptive names: `dev`, `staging`, `prod`
- Match deployment names when possible
- Use personal prefixes for shared systems: `alice_dev`, `bob_prod`

### Working Directory Management

- Set working directory to project root: `rto cd /data/my_project`
- Use relative paths in scripts for portability
- Document expected working directory in project README

### Key Management

- Generate separate keys for each environment
- Use descriptive key filenames: `alice_dev_key.pem`, `prod_admin_key.pem`
- Back up private keys securely
- Rotate keys regularly (use `rto rotate-key`)

### Multi-Environment Workflow

- Always specify profile for production commands: `rto --profile=prod`
- Use scripts to automate environment-specific deployments
- Test configuration with read-only commands first: `rto --profile=prod pwd`