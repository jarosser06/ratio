Ratio
=====

Ratio is an AI composition platform designed to support building autonomous AI systems. The intent was
to have a cloud-native framework/platform, that provides an operational safety net around
flexible process execution.

## Architecture Overview

![Ratio Architecture](docs/Ratio%20High%20Level.png)

## Extensibility & Integration Potential
Ratio's architecture is designed to work with existing AI infrastructure rather than replace it:

- **Execution Flexibility**: While currently Lambda-based, the system can potentially support any execution environment that reports back through Ratio's event system
- **Compute Options**: Future tools could spawn traditional servers, containers, or specialized hardware

The core requirement is simply that execution completes and reports status back to Ratio. This approach means Ratio can be updated to
incorporate new agent frameworks and execution models as they emerge.

## Tool Composition Example

Define complex workflows by composing tools:

```json
{
  "description": "Document processing pipeline",
  "arguments": [
    {"name": "input_files", "type_name": "list", "required": true}
  ],
  "instructions": [
    {
      "execution_id": "validate",
      "tool_definition_path": "/tools/validator.tool",
      "arguments": {"files": "REF:arguments.input_files"}
    },
    {
      "execution_id": "process_parallel",
      "tool_definition_path": "/tools/processor.tool", 
      "parallel_execution": {
        "iterate_over": "REF:validate.valid_files",
        "child_argument_name": "file_path"
      }
    },
    {
      "execution_id": "generate_report",
      "tool_definition_path": "/tools/reporter.tool",
      "conditions": [
        {"param": "REF:process_parallel.response.length", "operator": "greater_than", "value": 0}
      ],
      "arguments": {
        "results": "REF:process_parallel.response",
        "total_processed": "REF:process_parallel.response.length"
      }
    }
  ]
}
```

Execute the workflow:
```bash
rto execute --tool-definition-path=/tools/pipeline.tool \
    --arguments='{"input_files": ["/data/doc1.pdf", "/data/doc2.pdf"]}'
```

## Tool Subscriptions
Ratio's scheduler enables reactive automation through event subscriptions. Tools can automatically execute
when system events occur, creating responsive workflows that adapt to changes.

```bash
# Create subscription to update file type catalog when types change
rto create-subscription file_types_update /tools/system/update_catalog.tool

# Subscribe to file system changes
rto create-subscription filesystem_created /tools/processors/new_file_handler.tool \
    --filter '{"file_path": "/data/incoming", "file_type": "ratio::document"}'
```

### Basic Example: File Type Catalog Updates
Create a subscription that triggers when file types are updated in the system:

```bash
rto mksub file_types_update /tools/system/update_file_type_catalog.tool
```

**What This Does:**

- **Event Type**: file_types_update - triggers when file type definitions change in the system
- **Tool**: /tools/system/update_file_type_catalog.tool - executes automatically when the event occurs

**Workflow**

When file types are updated in the system, the subscribed tool automatically:

Retrieves current file type definitions from the system API
Updates a local catalog file (e.g., /data/file_types_catalog.json)
Provides other tools easy file-based access to file type metadata instead of requiring direct API calls

The subscription runs indefinitely until manually deleted with `rto rmsub <subscription_id>`.

## Core Features
- **Automatic Dependency Resolution**: `REF:` references create execution dependencies
- **Parallel Processing**: Execute tools over collections with `parallel_execution`
- **Conditional Execution**: Run tools based on dynamic conditions
- **File System**: Versioned storage with lineage tracking and Unix-like permissions
- **Event-Driven Triggers**: Auto-execute tools on subscriptions to system events
- **Nested Composition**: Unlimited depth tool orchestration

## System Components

### File System
```bash
rto ls /tools                    # List tool definitions
rto create-file /data/input.csv   # Create files with automatic versioning
rto create-subscription /tools/processor.tool /data/input --file-event-type=created
```

### Tool Types
- **Simple Tools**: Single function execution with direct I/O
- **Composite Tools**: Multi-step workflows with dependency management

### REF System
Dynamic value resolution between tool executions:
- `REF:arguments.input_file` - Input arguments
- `REF:validator.results` - Previous tool outputs  
- `REF:processor.files.length` - Collection attributes
- `REF:api_call.response.user.email` - Nested object access

## Getting Started

```bash
# Initialize system
rto init
rto configure

# Deploy an tool
rto create-file /tools/my_tool.tool --file-type=ratio::tool < definition.json

# Execute
rto execute --tool-definition-path=/tools/my_tool.tool \
    --arguments='{"input": "value"}' --wait

# Set up automation
rto create-subscription /tools/my_tool.tool /data/trigger_file.txt
```

## Architecture

Built on cloud-native AWS services with:
- **Process Management**: Tool execution and lifecycle tracking
- **Storage Manager**: Versioned file system with metadata and lineage
- **Event Bus**: Inter-tool communication and coordination  
- **Scheduler**: System event-based triggers
- **Authentication**: RSA key-based entity and group management

Designed for AI tool development with integrated debugging, exception handling, and process visibility.

## Documentation

- [Getting Started Guide](GETTING_STARTED.md)
- [Primitive Tool Authoring](docs/PRIMITIVE_TOOL_AUTHORING.md)
- [Composite Tool Authoring](_fs/system/docs/TOOL_COMPOSITION.md)

## Development

Prerequisites: Python 3.12+, AWS account, AWS CDK, Poetry

```bash
git clone https://github.com/jarosser06/ratio.git
cd ratio
poetry install
make deploy
```

## License

Apache 2.0