# Deployment

## Agent Definition Deployment

### 1. Upload Agent Definition

Upload your agent definition file to the Ratio system:

```bash
# Upload agent definition
rto create-file /agents/my_agent.agent --file-type=ratio::agent --parents

# Upload from local file
rto sync my_agent.agent ratio:/agents/my_agent.agent

# Verify upload
rto stat /agents/my_agent.agent
rto cat /agents/my_agent.agent
```

### 2. Set Permissions

Configure appropriate permissions for your agent:

```bash
# Set file permissions (read for execution group)
rto chmod 644 /agents/my_agent.agent

# Set owner and group
rto chown my_service /agents/my_agent.agent
rto chgrp agents /agents/my_agent.agent
```

## File Type Registration

Register custom file types for your agent's inputs and outputs:

```bash
# Register a custom file type
rto put-file-type myapp::config \
    --description="Application configuration files" \
    --name-restrictions="^.*\.config\.json$"

# Register a document type
rto put-file-type myapp::report \
    --description="Generated reports" \
    --name-restrictions="^.*\.report\.(json|pdf)$"

# List all registered file types
rto list-file-types --detailed
```

## Directory Structure Setup

Create the necessary directory structure for your agent:

```bash
# Create agent directory
rto mkdir /agents --parents --permissions=755

# Create data directories
rto mkdir /data/input --parents --permissions=755
rto mkdir /data/output --parents --permissions=755
rto mkdir /tmp/agent_workspace --parents --permissions=777

# Create logs directory
rto mkdir /logs --parents --permissions=755
```

## Agent Execution Setup

### Test Initial Deployment

```bash
# Test the deployed agent
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"test_mode": true}' \
    --working-directory=/tmp/agent_workspace \
    --wait

# Verify execution completed successfully
rto describe-process <process_id>
```

### Production Execution

```bash
# Execute in production mode
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"input_file": "/data/input.csv"}' \
    --working-directory=/tmp/agent_workspace
```

## Scheduled Execution

Set up scheduled execution using subscriptions:

```bash
# Create subscription for file-based triggers
rto create-subscription /agents/my_agent.agent /data/input \
    --file-event-type=created \
    --file-type=ratio::csv

# Create subscription with expiration
rto create-subscription /agents/my_agent.agent /data/daily \
    --file-event-type=updated \
    --expiration="2024-12-31T23:59:59"

# List active subscriptions
rto list-subscriptions --detailed

# Monitor subscription activity
rto describe-subscription <subscription_id>
```

## Multi-Environment Deployment

### Development Environment

```bash
# Configure development profile
rto configure --name=dev \
    --config-entity=dev_agent \
    --config-app=ratio \
    --config-deployment=dev

# Deploy to development
rto sync local_agents/ ratio:/agents/dev/ --recursive
```

### Production Environment

```bash
# Configure production profile
rto configure --name=prod \
    --config-entity=prod_agent \
    --config-app=ratio \
    --config-deployment=prod \
    --set-default

# Deploy to production
rto sync local_agents/ ratio:/agents/prod/ --recursive --force
```

## Deployment Verification

### Functionality Tests

```bash
# Test all agent functions
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"test_suite": "full"}' \
    --wait

# Test with production-like data
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"input_file": "/data/sample_prod.csv"}' \
    --wait

# Verify outputs
rto ls /data/output --detailed
rto stat /data/output/result.json
```

### Performance Verification

```bash
# Test with larger datasets
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"input_file": "/data/large_test.csv"}' \
    --wait \
    --max-wait-periods=50

# Monitor execution
rto list-processes --owner=my_agent --detailed
```

## Rollback Procedures

### Agent Definition Rollback

```bash
# List agent definition versions
rto list-file-versions /agents/my_agent.agent

# Rollback to previous version
rto delete-file-version /agents/my_agent.agent --version-id=<current_version>

# Or replace with backup
rto sync backup/my_agent.agent ratio:/agents/my_agent.agent --force
```

### File System Rollback

```bash
# Backup current state
rto sync ratio:/agents/ backup_$(date +%Y%m%d)/ --recursive

# Restore from backup
rto sync backup_20241201/ ratio:/agents/ --recursive --force
```

## Monitoring and Maintenance

### Regular Health Checks

```bash
# Check agent definition integrity
rto stat /agents/my_agent.agent
rto cat /agents/my_agent.agent | jq .

# Check directory permissions
rto ls /agents --detailed
rto ls /data --detailed

# Review recent executions
rto list-processes --owner=my_agent --detailed
```

### Cleanup Procedures

```bash
# Clean up old process logs
rto rm /logs/old_execution_*.log

# Clean up temporary files
rto rm /tmp/agent_workspace/* --recursive

# Archive old data
rto sync ratio:/data/output/archive/ local_archive/ --recursive
rto rm /data/output/archive/* --recursive
```

## Security Considerations

### Permission Management

```bash
# Review entity permissions
rto describe-entity my_agent
rto list-groups --detailed

# Update group memberships
rto add-to-group my_agent agent_executors
rto remove-from-group my_agent temp_group
```

### Key Rotation

```bash
# Rotate agent keys
rto rotate-key my_agent

# Update configuration with new keys
rto configure --name=prod --config-key=/path/to/new_key.pem
```