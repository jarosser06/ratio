# Ratio Agent Authoring Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Agent Architecture](#agent-architecture)
3. [Quick Start](#quick-start)
4. [Agent Types](#agent-types)
5. [Agent Definition Schema](#agent-definition-schema)
6. [Runtime Implementation](#runtime-implementation)
7. [File Operations](#file-operations)
8. [Agent Examples](#agent-examples)
9. [Best Practices](#best-practices)
10. [Testing & Debugging](#testing--debugging)
11. [Deployment](#deployment)
12. [Advanced Topics](#advanced-topics)

## Introduction

The Ratio agent system enables you to create autonomous, distributed agents that can process data, orchestrate workflows, and respond to file system events. This guide covers everything you need to author, test, and deploy agents effectively.

**Prerequisites:**
- Basic understanding of JSON and Python
- Access to a Ratio deployment
- Ratio CLI (`rto`) installed and configured

**Related Documentation:**
- [CLI Command Reference](cli_cheat_sheet.md)
- [Testing & Debugging Guide](agent_testing_debugging.md)
- [Deployment Guide](agent_deployment.md)

## Agent Architecture

Ratio agents consist of two main components:

1. **Agent Definition** (`.agent` file): JSON schema defining inputs, outputs, and execution behavior
2. **Runtime Implementation** (Python code): The actual execution logic for simple agents

```
my_agent/
├── my_agent.agent          # Agent definition
└── runtime/
    └── run.py              # Runtime implementation (simple agents only)
```

## Quick Start

### 1. Create Your First Agent

**hello_world.agent:**
```json
{
  "description": "A simple greeting agent",
  "arguments": [
    {
      "name": "name",
      "type_name": "string",
      "description": "The name to greet",
      "required": true
    }
  ],
  "responses": [
    {
      "name": "message",
      "type_name": "string", 
      "description": "The greeting message",
      "required": true
    }
  ],
  "system_event_endpoint": "ratio::agent::hello_world::execution"
}
```

**runtime/run.py:**
```python
import logging
from typing import Dict
from da_vinci.core.logging import Logger
from da_vinci.event_bus.client import fn_event_response
from da_vinci.exception_trap.client import ExceptionReporter
from ratio.agents.agent_lib import RatioSystem

_FN_NAME = "ratio.agents.hello_world"

@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """Execute the hello world agent"""
    logging.info(f"Received request: {event}")
    
    # Initialize the Ratio system
    system = RatioSystem.from_da_vinci_event(event)
    system.raise_on_failure = True
    
    with system:
        # Extract arguments
        name = system.arguments["name"]
        
        # Generate response
        message = f"Hello, {name}! Welcome to Ratio."
        
        # Return success
        system.success(response_body={
            "message": message
        })
```

### 2. Test Your Agent

```bash
# Upload the agent definition
rto create-file /agents/hello_world.agent --file-type=ratio::agent < hello_world.agent

# Execute the agent
rto execute --agent-definition-path=/agents/hello_world.agent \
    --arguments='{"name": "World"}' \
    --wait

# Check the results
rto describe-process <process_id>
```

## Agent Types

### Simple (Direct) Agents

Execute a single function and return results directly.

**Characteristics:**
- Single execution unit
- Direct input/output mapping
- Implemented as Lambda functions
- Use `system_event_endpoint` in definition

**Use Cases:**
- Data transformations
- API calls
- Simple calculations
- File operations

### Composite (T2) Agents

Orchestrate multiple sub-agents to accomplish complex tasks.

**Characteristics:**
- Define execution workflow
- Coordinate multiple agents
- Support conditional execution
- Use `instructions` array in definition

**Use Cases:**
- Multi-step workflows
- Data pipelines
- Complex business processes
- Agent orchestration

## Agent Definition Schema

### Core Structure

```json
{
  "description": "Human-readable description",
  "arguments": [...],           // Input schema
  "responses": [...],          // Output schema (optional)
  
  // For Simple Agents:
  "system_event_endpoint": "ratio::agent::my_agent::execution",
  
  // For Composite Agents:
  "instructions": [...],
  "response_reference_map": {...}
}
```

### Argument Schema

Arguments define the inputs your agent accepts:

```json
{
  "name": "input_file",
  "type_name": "file",                    // string, number, boolean, object, list, file
  "description": "Path to input file",
  "required": true,
  "default_value": "/default/path",       // Optional
  "enum": ["option1", "option2"],         // Optional
  "regex_pattern": "^/.*\\.json$",        // Optional
  "required_conditions": [                // Optional
    {
      "param": "other_param",
      "operator": "exists"
    }
  ]
}
```

### Response Schema

Responses define the outputs your agent produces:

```json
{
  "name": "output_file",
  "type_name": "file",
  "description": "Path to generated output",
  "required": true
}
```

### Supported Types

- `string`: Text data
- `number`: Numeric values (integers or floats)
- `boolean`: True/false values
- `object`: JSON objects
- `list`: Arrays
- `file`: File paths (handled specially by the system)

## Runtime Implementation

### RatioSystem Class

The `RatioSystem` class provides the core interface for agent development:

```python
from ratio.agents.agent_lib import RatioSystem

# Initialize from event
system = RatioSystem.from_da_vinci_event(event)

# Access arguments (use bracket notation for required args)
value = system.arguments["param_name"]
optional_value = system.arguments.get("param_name", default_return="default")

# Success/failure handling
system.success(response_body={"result": "data"})
system.failure("Error message")
```

### Context Manager Pattern

**Always use the context manager pattern** for proper error handling:

```python
with system:
    # Your agent logic here
    result = process_data(system.arguments["input"])
    system.success(response_body={"output": result})
    
# Automatic failure handling if exception occurs
```

### Error Handling Best Practices

```python
with system:
    try:
        # Risky operation
        result = complex_operation()
        system.success(response_body={"result": result})
    except SpecificException as e:
        # Handle specific errors gracefully
        system.failure(f"Operation failed: {str(e)}")
```

## File Operations

The Ratio system provides seamless file handling capabilities:

### Reading Files

```python
# Read file with automatic permission checks
file_data = system.get_file_version("/path/to/input.json")
content = json.loads(file_data["data"])

# Get file metadata
file_info = system.describe_file("/path/to/file")
```

### Writing Files

```python
# Write file with proper metadata
system.put_file(
    file_path="/path/to/output.json",
    file_type="ratio::file", 
    data=json.dumps(result),
    metadata={"created_by": "my_agent", "processing_time": processing_time}
)
```

### Working with File Arguments

```python
with system:
    # File arguments automatically include path validation
    input_file = system.arguments["input_file"]
    
    # Read the file content
    file_data = system.get_file_version(input_file)
    content = file_data["data"]
    
    # Process content...
    processed = process_content(content)
    
    # Generate unique output path
    import uuid
    output_path = f"/tmp/processed_{uuid.uuid4()}.json"
    
    # Write processed content
    system.put_file(
        file_path=output_path,
        file_type="ratio::file",
        data=processed
    )
    
    system.success(response_body={"output_file": output_path})
```

## Agent Examples

### Example 1: Data Processor

**csv_processor.agent:**
```json
{
  "description": "Process CSV files and generate summaries",
  "arguments": [
    {
      "name": "input_file",
      "type_name": "file",
      "description": "CSV file to process",
      "required": true
    },
    {
      "name": "columns",
      "type_name": "list",
      "description": "Columns to include in summary", 
      "required": false
    }
  ],
  "responses": [
    {
      "name": "summary_file",
      "type_name": "file",
      "description": "Generated summary file",
      "required": true
    },
    {
      "name": "row_count",
      "type_name": "number", 
      "description": "Total rows processed",
      "required": true
    }
  ],
  "system_event_endpoint": "ratio::agent::csv_processor::execution"
}
```

**runtime/run.py:**
```python
import csv
import json
import uuid
from ratio.agents.agent_lib import RatioSystem

@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    system = RatioSystem.from_da_vinci_event(event)
    
    with system:
        # Read input file
        input_file = system.arguments["input_file"]
        file_data = system.get_file_version(input_file)
        csv_content = file_data["data"]
        
        # Process CSV
        reader = csv.DictReader(csv_content.strip().split('\n'))
        rows = list(reader)
        
        # Generate summary
        columns = system.arguments.get("columns", default_return=list(rows[0].keys()) if rows else [])
        summary = {
            "total_rows": len(rows),
            "columns": columns,
            "preview": rows[:5] if rows else []
        }
        
        # Save summary
        output_path = f"/tmp/summary_{uuid.uuid4()}.json"
        system.put_file(
            file_path=output_path,
            file_type="ratio::file",
            data=json.dumps(summary, indent=2),
            metadata={"source_file": input_file}
        )
        
        # Return results
        system.success(response_body={
            "summary_file": output_path,
            "row_count": len(rows)
        })
```

### Example 2: Composite Workflow

**data_pipeline.agent:**
```json
{
  "description": "Data processing pipeline with validation and transformation",
  "arguments": [
    {
      "name": "source_file",
      "type_name": "file", 
      "description": "Raw data file",
      "required": true
    },
    {
      "name": "validation_rules",
      "type_name": "object",
      "description": "Validation configuration",
      "required": true  
    }
  ],
  "responses": [
    {
      "name": "processed_file",
      "type_name": "file",
      "description": "Final processed file",
      "required": true
    },
    {
      "name": "validation_report",
      "type_name": "file", 
      "description": "Validation results",
      "required": true
    }
  ],
  "instructions": [
    {
      "execution_id": "validate",
      "agent_definition_path": "/agents/data_validator.agent",
      "arguments": {
        "input_file": "REF:arguments.source_file",
        "rules": "REF:arguments.validation_rules"
      }
    },
    {
      "execution_id": "transform", 
      "agent_definition_path": "/agents/data_transformer.agent",
      "arguments": {
        "input_file": "REF:arguments.source_file",
        "validation_passed": "REF:validate.passed"
      },
      "conditions": [
        {
          "param": "REF:validate.passed",
          "operator": "equals",
          "value": true
        }
      ]
    },
    {
      "execution_id": "finalize",
      "agent_definition_path": "/agents/data_finalizer.agent", 
      "arguments": {
        "input_file": "REF:transform.output_file"
      }
    }
  ],
  "response_reference_map": {
    "processed_file": "REF:finalize.output_file",
    "validation_report": "REF:validate.report_file"
  }
}
```

## Best Practices

### 1. Argument Validation

```python
# The agent definition validates arguments, so trust the schema
# Always use bracket notation for required arguments
with system:
    input_file = system.arguments["input_file"]  # Will fail if not present
    
    # Use get() with default_return for optional arguments
    timeout = system.arguments.get("timeout", default_return=300)
```

### 2. Structured Logging

```python
import logging

# Use structured logging for better debugging
logging.info(f"Processing file: {input_file}")
logging.debug(f"Using parameters: {parameters}")

# Log progress for long-running operations
for i, item in enumerate(large_dataset):
    if i % 1000 == 0:
        logging.info(f"Processed {i}/{len(large_dataset)} items")
```

### 3. Resource Management

```python
# Use unique paths to avoid conflicts
import uuid
output_path = f"/tmp/agent_output_{uuid.uuid4()}.json"

# Set appropriate metadata
system.put_file(
    file_path=output_path,
    file_type="ratio::file",
    data=content,
    metadata={
        "created_by": "my_agent",
        "source_file": input_file,
        "processing_time": time.time() - start_time
    }
)
```

### 4. Error Messages

```python
# Provide helpful error messages
try:
    result = complex_operation(data)
except ValueError as e:
    system.failure(f"Invalid data format in {input_file}: {str(e)}")
except FileNotFoundError as e:
    system.failure(f"Required file not found: {str(e)}")
except Exception as e:
    system.failure(f"Unexpected error during processing: {str(e)}")
```

## Testing & Debugging

For comprehensive testing and debugging information, see the [Testing & Debugging Guide](agent_testing_debugging.md).

### Quick Testing Workflow

```bash
# 1. Upload agent definition
rto create-file /agents/my_agent.agent --file-type=ratio::agent < local_definition.json

# 2. Test with minimal arguments
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"required_param": "test_value"}' \
    --wait

# 3. Check outputs and logs
rto describe-process <process_id>
rto cat <response_path>
```

### Common Debugging Steps

```bash
# Check agent definition syntax
rto cat /agents/my_agent.agent | jq .

# Test file access
rto stat /data/input.csv

# Monitor execution
rto list-processes --status=RUNNING --owner=my_entity

# Check execution results
rto describe-process <process_id>  # Includes failure message if failed
rto get-file <response_path>       # For successful executions, view full response
```

## Deployment

For comprehensive deployment information, see the [Deployment Guide](agent_deployment.md).

### Basic Deployment Steps

```bash
# 1. Upload agent definition
rto sync my_agent.agent ratio:/agents/my_agent.agent

# 2. Set permissions
rto chmod 644 /agents/my_agent.agent

# 3. Test deployment
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"test": true}' --wait

# 4. Set up scheduling (optional)
rto create-subscription /agents/my_agent.agent /data/input \
    --file-event-type=created
```

## Advanced Topics

### Custom File Types

Register custom file types for domain-specific data:

```bash
# Register custom file type
rto put-file-type myapp::config \
    --description="Application Configuration File" \
    --name-restrictions="^.*\\.config\\.json$"
```

Then use in agent definitions:

```json
{
  "name": "config_file",
  "type_name": "myapp::config",
  "description": "Application configuration",
  "required": true
}
```

### External API Integration

```python
# Example: Webhook integration agent
@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    system = RatioSystem.from_da_vinci_event(event)
    
    with system:
        webhook_url = system.arguments["webhook_url"]
        payload = system.arguments["payload"]
        
        # Make external API call
        import requests
        response = requests.post(webhook_url, json=payload, timeout=30)
        response.raise_for_status()
        
        # Store response 
        output_path = f"/tmp/webhook_response_{uuid.uuid4()}.json"
        system.put_file(
            file_path=output_path,
            file_type="ratio::file",
            data=response.text,
            metadata={"webhook_url": webhook_url, "status_code": response.status_code}
        )
        
        system.success(response_body={
            "response_file": output_path,
            "status_code": response.status_code
        })
```

### Environment-Specific Configuration

Use different agent definitions for different environments:

```bash
# Development
rto sync my_agent.agent ratio:/agents/dev/my_agent.agent

# Production  
rto sync my_agent_prod.agent ratio:/agents/prod/my_agent.agent
```

### Performance Optimization

1. **Minimize file I/O**: Process data in memory when possible
2. **Use appropriate file types**: Register types that match your data
3. **Batch operations**: Process multiple items together
4. **Set timeouts**: Configure appropriate timeout values
5. **Monitor memory**: Be aware of Lambda memory limits

### Security Considerations

1. **Validate inputs**: Don't trust even "validated" inputs completely
2. **Sanitize file paths**: Prevent path traversal attacks
3. **Limit file sizes**: Handle large files appropriately
4. **Use proper permissions**: Set restrictive file permissions
5. **Rotate keys**: Regularly rotate entity keys

---

## Getting Help

- **CLI Commands**: See the [CLI Command Cheat Sheet](CLI_CHEAT_SHEET.md)
- **Agent Debugging**: Check the [Testing & Debugging Guide](AGENT_TESTING_DEBUGGING.md)
- **Agent Deployment Problems**: Review the [Deployment Guide](AGENT_DEPLOYMENT.md)
- **System Logs**: Use `rto list-processes` and `rto describe-process` to investigate issues

This guide provides a comprehensive foundation for authoring agents in the Ratio system. Start with simple agents, test thoroughly, and gradually build more complex workflows as you become familiar with the system.