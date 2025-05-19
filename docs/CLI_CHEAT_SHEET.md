# Ratio CLI Command Cheat Sheet

## File Operations
```bash
# Create files/directories
rto touch <file>                    # Create empty file
rto mkdir <dir> --parents           # Create directory with parents
rto create-file <file> --content="text" --parents

# Read files
rto cat <file>                      # Display file content
rto stat <file>                     # Show file details
rto ls <dir> --detailed             # List directory contents

# Modify files
rto chmod <perms> <file>            # Change permissions
rto chown <owner> <file>            # Change owner
rto chgrp <group> <file>            # Change group

# Delete files
rto rm <file>                       # Delete file
rto rm <dir> --recursive            # Delete directory recursively
```

## File Versions
```bash
rto list-file-versions <file>       # List all versions (lsv)
rto describe-file-version <file>    # Describe version (statv)
rto delete-file-version <file> --version-id=<id>  # Delete specific version (rmv)
```

## Navigation
```bash
rto pwd                             # Print working directory
rto cd <dir>                        # Change directory
rto ls                              # List current directory
rto ls <dir>                        # List specific directory
```

## Agent Execution
```bash
# Execute agents
rto execute --agent-definition-path=<path> --arguments='<json>'
rto execute --agent-definition='<json>' --arguments='<json>' --wait

# Monitor execution
rto list-processes                  # List processes (lsproc)
rto list-processes --status=RUNNING --owner=<entity>
rto describe-process <id>           # Process details (dproc)

# View execution results
rto get-file <response_path>        # Response path from describe-process
# Response paths follow pattern: /root/agent_exec-<parent_id>/agent_exec-<process_id>/response.aio
```

## File Types
```bash
rto put-file-type <type> --description="desc"  # Register file type
rto list-file-types --detailed     # List types (lsft)
rto describe-file-type <type>       # Type details
rto delete-file-type <type>         # Delete type (rmtype)
```

## Subscriptions (Scheduling)
```bash
# Create subscriptions
rto create-subscription <agent_path> <file_path>  # Basic subscription (mksub)
rto create-subscription <agent_path> <dir> --file-event-type=created
rto create-subscription <agent_path> <file> --single-use --expiration="2024-12-31T23:59:59"

# Monitor subscriptions
rto list-subscriptions --detailed   # List all (lssub)
rto describe-subscription <id>      # Subscription details (dsub)
rto delete-subscription <id>        # Delete subscription (rmsub)
```

## File Sync
```bash
# Local to Ratio
rto sync local_file ratio:/remote/file
rto sync local_dir/ ratio:/remote/dir/ --recursive

# Ratio to local
rto sync ratio:/remote/file local_file
rto sync ratio:/remote/dir/ local_dir/ --recursive

# Options
--force                             # Overwrite existing
--dry-run                          # Show what would be done
--include="*.json"                 # Include pattern
--exclude="*.tmp"                  # Exclude pattern
--type-map='{"pdf":"myapp::pdf"}'   # File type mapping
```

## Authentication & Configuration
```bash
# Configure profiles
rto configure --name=<profile>      # Interactive setup
rto configure --name=dev --config-entity=dev_user --set-default

# Entity management
rto create-entity <id>              # Create entity (generates keys)
rto create-entity <id> --public-key=<path>
rto describe-entity <id>            # Entity details
rto list-entities --detailed        # List all entities
rto rotate-key <id>                 # Rotate entity key

# Group management
rto create-group <id> --description="desc"
rto add-to-group <entity> <group>
rto remove-from-group <entity> <group>
rto list-groups --detailed
rto describe-group <id>
```

## System Management
```bash
rto init                            # Initialize system (first time)
rto init --public-key=<path>        # Initialize with existing key
```

## Common Patterns

### Agent Development Workflow
```bash
# 1. Upload agent definition
rto create-file /agents/my_agent.agent --file-type=ratio::agent < local_definition.json

# 2. Test execution
rto execute --agent-definition-path=/agents/my_agent.agent --arguments='{"test": true}' --wait

# 3. Check results
rto stat /tmp/output.json
rto cat /tmp/output.json

# 4. Set up subscription
rto create-subscription /agents/my_agent.agent /data/input --file-event-type=created
```

### File System Navigation
```bash
rto pwd                             # Check current location
rto cd /agents                      # Go to agents directory
rto ls --detailed                   # See what's here
rto stat my_agent.agent             # Check specific file
```

### Debugging Failed Executions
```bash
rto list-processes --status=FAILED  # Find failed processes
rto describe-process <id>           # Get error details (includes failure message)
rto get-file <response_path>        # View full response (for successful processes)
```

### Environment Management
```bash
# Switch between environments
rto configure --name=dev
rto configure --name=prod --set-default

# Deploy to different environments
rto sync local_agents/ ratio:/agents/dev/ --recursive
rto sync local_agents/ ratio:/agents/prod/ --recursive
```

## Global Options
```bash
--config-path=<path>                # Use custom config directory
--profile=<name>                    # Use specific profile
--app-name=<name>                   # Override app name
--deployment-id=<id>                # Override deployment ID
--json                              # Output raw JSON (many commands)
--verbose / -v                      # Verbose output (some commands)
--force / -f                        # Force operation
--dry-run                           # Preview mode (some commands)
```

## Path Conventions
- Agent definitions: `/agents/`
- Data files: `/data/`
- Temporary files: `/tmp/`
- Logs: `/logs/`
- Configuration: Use custom file types for app-specific configs

## Tips
- Use `--parents` when creating files to auto-create directories
- Use `--wait` with execute to see immediate results
- Use `--detailed` with list commands for more information
- Use `--json` for programmatic access to command output
- File paths are absolute; use `rto pwd` and `rto cd` for navigation