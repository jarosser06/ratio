Ratio
=====

Ratio is an agent composition platform designed for AI systems to build and evolve their own capabilities. Rather than hoping
AI can reason its way to solutions, Ratio provides structured building blocks where AI can have genuine agency within principled
guardrails.

The system treats everything as files: agent definitions, execution artifacts, documentation. This creates a persistent knowledge
base that AI can reference, analyze, and learn from. Agents can generate other agents, analyze past executions, and build
self-documenting catalogs of what works.

Named after the Golden Ratio, it's an attempt to find the right balance between AI capability and engineering safety. Meant to be 
infrastructure that lets AI systems evolve systematically rather than chaotically.

## Architecture Overview

![Ratio Architecture](docs/Ratio%20High%20Level.jpeg)

## How It Works

Ratio enables AI to bootstrap itself through:

- **File-Based Everything**: Agent definitions, execution results, and system documentation stored as versioned files
- **Agent Composition**: Complex workflows built by orchestrating simpler agents with automatic dependency resolution
- **Self-Documentation**: Agents that generate catalogs and documentation about system capabilities
- **Execution Analysis**: Full artifact trails allowing agents to learn from past successes and failures
- **Event-Driven Evolution**: Reactive automation that responds to system changes

## Extensibility & Integration Potential
Ratio's architecture is designed to work with existing AI infrastructure rather than replace it:

- **Execution Flexibility**: While currently Lambda-based, the system can potentially support any execution environment that reports back through Ratio's event system
- **Framework Integration**: The agent model could be extended to orchestrate MCP clients, Bedrock Agents, or other AI frameworks
- **Compute Options**: Future agents could spawn traditional servers, containers, or specialized hardware

The core requirement is simply that execution completes and reports status back to Ratio. This approach means Ratio can evolve to
incorporate new agent frameworks and execution models as they emerge, while providing consistent orchestration, dependency
management, and evolution capabilities across all of them.

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

## Agent Subscriptions
Ratio's scheduler enables reactive automation through event subscriptions. Agents can automatically execute
when system events occur, creating responsive workflows that adapt to changes.

```bash
# Create subscription to update file type catalog when types change
rto create-subscription file_types_update /agents/system/update_catalog.agent

# Subscribe to file system changes
rto create-subscription filesystem_created /agents/processors/new_file_handler.agent \
    --filter '{"file_path": "/data/incoming", "file_type": "ratio::document"}'
```

### Basic Example: File Type Catalog Updates
Create a subscription that triggers when file types are updated in the system:

```bash
rto mksub file_types_update /agents/system/update_file_type_catalog.agent
```

**What This Does:**

- **Event Type**: file_types_update - triggers when file type definitions change in the system
- **Agent**: /agents/system/update_file_type_catalog.agent - executes automatically when the event occurs

**Workflow**

When file types are updated in the system, the subscribed agent automatically:

Retrieves current file type definitions from the system API
Updates a local catalog file (e.g., /data/file_types_catalog.json)
Provides other agents easy file-based access to file type metadata instead of requiring direct API calls

The subscription runs indefinitely until manually deleted with `rto rmsub <subscription_id>`.

## Core Features
- **Automatic Dependency Resolution**: `REF:` references create execution dependencies
- **Parallel Processing**: Execute agents over collections with `parallel_execution`
- **Conditional Execution**: Run agents based on dynamic conditions
- **File System**: Versioned storage with lineage tracking and Unix-like permissions
- **Event-Driven Triggers**: Auto-execute agents on subscriptions to system events
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
- **Scheduler**: System event-based triggers
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