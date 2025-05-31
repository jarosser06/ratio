Ratio
=====
An AI Operating System for composing and managing complex agent workflows with automatic dependency
resolution, parallel processing, and event-driven orchestration.

Ratio is named after the Golden Ratio, attempting to represent an ideal balance between AI
capabilities and engineering infrastructure. It's an attempt to control the chaos!

## Agent Composition Example

Define complex workflows by composing agents:

```json
{
  "description": "Document processing pipeline",
  "arguments": [
    {"name": "input_files", "type_name": "list", "required": true}
  ],
  "instructions": [
    {
      "execution_id": "validate",
      "agent_definition_path": "/agents/validator.agent",
      "arguments": {"files": "REF:arguments.input_files"}
    },
    {
      "execution_id": "process_parallel",
      "agent_definition_path": "/agents/processor.agent", 
      "parallel_execution": {
        "iterate_over": "REF:validate.valid_files",
        "child_argument_name": "file_path"
      }
    },
    {
      "execution_id": "generate_report",
      "agent_definition_path": "/agents/reporter.agent",
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
rto execute --agent-definition-path=/agents/pipeline.agent \
    --arguments='{"input_files": ["/data/doc1.pdf", "/data/doc2.pdf"]}'
```

## Core Features
- **Automatic Dependency Resolution**: `REF:` references create execution dependencies
- **Parallel Processing**: Execute agents over collections with `parallel_execution`
- **Conditional Execution**: Run agents based on dynamic conditions
- **File System**: Versioned storage with lineage tracking and Unix-like permissions
- **Event-Driven Triggers**: Auto-execute agents on file changes
- **Nested Composition**: Unlimited depth agent orchestration

## System Components

### File System
```bash
rto ls /agents                    # List agent definitions
rto create-file /data/input.csv   # Create files with automatic versioning
rto create-subscription /agents/processor.agent /data/input --file-event-type=created
```

### Agent Types
- **Simple Agents**: Single function execution with direct I/O
- **Composite Agents**: Multi-step workflows with dependency management

### REF System
Dynamic value resolution between agent executions:
- `REF:arguments.input_file` - Input arguments
- `REF:validator.results` - Previous agent outputs  
- `REF:processor.files.length` - Collection attributes
- `REF:api_call.response.user.email` - Nested object access

## Getting Started

```bash
# Initialize system
rto init
rto configure

# Deploy an agent
rto create-file /agents/my_agent.agent --file-type=ratio::agent < definition.json

# Execute
rto execute --agent-definition-path=/agents/my_agent.agent \
    --arguments='{"input": "value"}' --wait

# Set up automation
rto create-subscription /agents/my_agent.agent /data/trigger_file.txt
```

## Architecture

Built on cloud-native AWS services with:
- **Process Management**: Agent execution and lifecycle tracking
- **Storage Manager**: Versioned file system with metadata and lineage
- **Event Bus**: Inter-agent communication and coordination  
- **Scheduler**: File-based and time-based triggers
- **Authentication**: RSA key-based entity and group management

Designed for agent development with integrated debugging, exception handling, and process visibility.

## Documentation

- [Getting Started Guide](GETTING_STARTED.md) - Installation and setup
- [Agent Authoring](docs/AGENT_AUTHORING.md) - Creating agents
- [CLI Reference](docs/CLI_CHEAT_SHEET.md) - Command reference
- [Agent Composition](docs/agent_definition_appendix/AGENT_COMPOSITION.md) - Workflow orchestration

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