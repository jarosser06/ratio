# Testing & Debugging

The Ratio CLI provides several commands to help you test and debug your agents during development.

## Agent Definition Validation

Before deploying an agent, validate its definition file:

```bash
# Upload and validate agent definition
rto create-file /agents/my_agent.agent --file-type=ratio::agent --parents
rto cat /agents/my_agent.agent  # Verify the content was uploaded correctly
```

## Testing Agent Execution

### Execute an Agent

Execute an agent using either an inline definition or a file path:

```bash
# Execute using a definition file on the server
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"input": "test_value"}' \
    --working-directory=/tmp \
    --wait

# Execute with inline definition (for testing)
rto execute --agent-definition='{"description": "test agent", "arguments": [...]}' \
    --arguments='{"param": "value"}' \
    --wait
```

### Monitor Execution Progress

```bash
# List running processes
rto list-processes --status=RUNNING

# Get detailed process information
rto describe-process <process_id>

# Wait for completion and check results
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"input": "test"}' \
    --wait \
    --max-wait-periods=20 \
    --wait-period-seconds=10
```

## Debugging Failed Executions

### Check Process Status

```bash
# List recent failed processes
rto list-processes --status=FAILED --detailed

# Get detailed information about a failed process (includes error message)
rto describe-process <process_id>

# For successful processes, check the response file if needed
rto get-file <response_path>  # Use the response_path from describe-process
# Example: rto get-file /root/agent_exec-306c0c3d-7290-4fb5-8981-87008800e239/agent_exec-02add785-075a-4f29-a4b6-2758dcd2752c/response.aio
```

**Note**: Failed processes will include the error message directly in the `describe-process` output. You typically only need to check the response file for successful executions to see the returned data.

### View Agent Logs

```bash
# Find log files (typically in /logs or /tmp)
rto ls /logs --detailed
rto get-file /logs/agent_execution_<process_id>.log

# Note: Response files follow the pattern:
# /root/agent_exec-<parent_process_id>/agent_exec-<process_id>/response.aio
```

## File System Debugging

### Check File Permissions and Ownership

```bash
# Verify file exists and permissions
rto stat /path/to/file

# List directory contents with details
rto ls /agents --detailed

# Check file versions
rto list-file-versions /agents/my_agent.agent
```

### Debug File Access Issues

```bash
# Test file read access
rto cat /path/to/test_file

# Create test files with specific permissions
rto touch /tmp/test_output.json --permissions=644

# Check directory structure
rto ls /agents --recursive
```

## Development Workflow

### Iterative Testing

```bash
# 1. Update agent definition
rto create-file /agents/my_agent.agent --file-type=ratio::agent < local_agent.json

# 2. Test execution
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"test": true}' \
    --wait

# 3. Check outputs
rto ls /tmp --detailed
rto cat /tmp/agent_output.json

# 4. Clean up test files
rto rm /tmp/agent_output.json
```

### Test with Different Arguments

```bash
# Test with minimal arguments
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"required_param": "value"}'

# Test with full arguments
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{
        "required_param": "value",
        "optional_param": "test",
        "file_input": "/data/test.csv"
    }' \
    --wait
```

## Composite Agent Testing

### Test Individual Sub-Agents

```bash
# Test each sub-agent independently first
rto execute --agent-definition-path=/agents/data_validator.agent \
    --arguments='{"input_file": "/data/test.csv", "rules": {...}}'

rto execute --agent-definition-path=/agents/data_transformer.agent \
    --arguments='{"input_file": "/data/test.csv"}'
```

### Test Full Workflow

```bash
# Execute the composite agent
rto execute --agent-definition-path=/agents/data_pipeline.agent \
    --arguments='{
        "source_file": "/data/input.csv",
        "validation_rules": {...}
    }' \
    --wait \
    --max-wait-periods=30
```

## Performance Testing

### Monitor Execution Time

```bash
# Start execution and note the time
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"large_dataset": "/data/big_file.csv"}' &

# Monitor process status
watch -n 5 'rto describe-process <process_id>'
```

### Resource Usage Debugging

```bash
# Monitor concurrent executions
rto list-processes --owner=my_entity --detailed
```