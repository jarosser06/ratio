# Introduction to Ratio: AI Operating System

## What is Ratio?

Ratio is a AI Operating System that enables organizations to build, deploy, and manage
complex data processing workflows through autonomous agents. Unlike traditional monolithic systems
or simple task orchestration platforms, Ratio provides a complete distributed operating environment
for agent development with integrated storage, authentication, scheduling, and execution management.

At its core, Ratio approaches AI and data processing by providing a operating system
specifically designed for autonomous agents. Just as traditional operating systems provide essential
services for applications on a single machine, Ratio provides the fundamental infrastructure
that agents need to operate effectively across cloud environments.

## Key Principles

### Operating System for Agents
Ratio provides the foundational services that agents need across a distributed infrastructure:
process management, file systems, inter-process communication, and resource management.
Just as a traditional OS abstracts hardware complexity, Ratio abstracts the complexity of
cloud infrastructure.

### System-Level Services
All agent interactions flow through operating system services: the event bus for inter-process
communication across the cluster, the storage manager for global file system access, and
the process manager for execution control of the agents. This provides the reliability and
observability that agents need to operate effectively in a environment.

### Integrated Environment
The integrated storage manager provides a Unix-like file system with automatic versioning, lineage
tracking support, and granular permissions. This eliminates the complexity of managing separate
storage solutions while ensuring data integrity and accessibility across all agents.

### Built for Agents
Ratio is designed specifically for agent development and operation. The operating system handles
infrastructure complexity while exposing the right abstractions for building sophisticated agent
workflows.

## Operating System Services

### 1. Process Management (Agent System)
**Simple Agents** execute single functions with direct input/output mapping, perfect for data
transformations, API calls, or discrete calculations.

**Composite Agents** orchestrate multiple sub-agents to accomplish complex tasks, supporting
unlimited nesting depth and sophisticated dependency management.

```json
{
  "description": "Data processing pipeline",
  "instructions": [
    {
      "execution_id": "validate",
      "agent_definition_path": "/agents/validator.agent",
      "arguments": {"file": "REF:arguments.input_file"}
    },
    {
      "execution_id": "transform",
      "agent_definition_path": "/agents/transformer.agent",
      "arguments": {"validated_data": "REF:validate.output"},
      "conditions": [{"param": "REF:validate.success", "value": true}]
    }
  ]
}
```

### 2. REF Resolution System
The dynamic reference system enables data flow between agents using `REF:` strings. This allows
composite agents to wire together complex dependencies without hard-coding values:

- `REF:arguments.input_file` - Reference input arguments
- `REF:validator.results.status` - Reference outputs from previous steps
- `REF:processor.files.0.path` - Access nested data with type-aware attributes

### File System (Storage Manager)
A file system providing:

- **Global namespace** accessible from any agent anywhere
- **Automatic versioning** with complete history across the cluster
- **Lineage tracking** showing data dependencies across distributed processes
- **Unix-style permissions** for granular access control
- **Event notifications** for file system changes
- **Metadata management** for rich data annotation

### 4. Security & Access Control
Enterprise-grade security with:

- RSA key-based entity authentication
- Group-based permission management
- File-level access controls
- API token management with automatic refresh

### 5. Task Scheduler
Event-driven automation that triggers agents based on:

- File system changes (creation, modification, deletion)
- Time-based schedules
- Custom event patterns
- One-time or recurring executions

## Debugging & Observability
One of Ratio's greatest strengths is its debugging capabilities:

### Centralized Exception Handling
The Da Vinci framework's exception trap automatically captures:

- Complete stack traces with full context
- Originating events that triggered failures
- Metadata and correlation information
- Automatic storage with 2-day retention, configurable through global settings

### Event Bus Visibility
Every system interaction is recorded in the event bus response table:

- Complete event payloads and processing results
- Success/failure status with detailed error information
- Event causation chains via linked event IDs
- 8-hour retention for immediate debugging, configurable global setting

### Process Hierarchy Tracking
The process management system provides crystal-clear visibility:

- Parent-child relationships for nested workflows
- Real-time status at every execution level
- Failure point identification in complex workflows
- Execution timing and resource usage

**Key distributed debugging benefits:**
- Each process maintains immutable execution records
- Failures remain isolated without affecting other system components
- Complete execution context is preserved automatically
- Workflows can be replayed reliably with identical inputs

## Beyond Core: Compute Flexibility
While Ratio includes AWS Lambda integration out of the box, the operating system's
event-driven design enables deployment flexibility that spans across any compute infrastructure.

### Any Compute, Same OS Interface

The event bus acts as a universal API layer. As long as your agent can:

1. Subscribe to events from the Da Vinci event bus
2. Process the `SystemExecuteAgentRequest` payload
3. Publish `ratio::agent_response` events when complete

**You can use any execution environment imaginable.**

### Expanded Compute Options

**EC2 Instances**
- Long-running processes that exceed Lambda's 15-minute limit
- Memory-intensive workloads requiring more than 10GB RAM
- Applications requiring persistent storage or specialized hardware

**Container Orchestration**
- ECS/Fargate for applications with complex dependencies
- Kubernetes clusters for cloud-native deployments
- Custom container environments with specific OS requirements

**Specialized Hardware**
- GPU instances for machine learning and AI workloads
- High-memory instances for in-memory analytics
- Spot instances for cost-effective batch processing

**On-Premises Integration**
- Wrap legacy systems as Ratio agents
- Maintain sensitive data processing within corporate boundaries
- Integrate with existing data centers via VPN or direct connect

### Event Type Flexibility

The event naming convention is completely customizable, enabling:

**Domain-Specific Patterns**
```
ecommerce::order::process
ml::model::train
finance::report::generate
```

**Organizational Namespacing**
```
team-alpha::data-pipeline::v2
customer-acme::batch-process
legacy::mainframe::job-handler
```

**Integration Patterns**
```
webhook::github::push
external::partner-api::callback
migration::database::sync
```

### Multi-Interface Agents

Agents can listen to multiple event types simultaneously:
- Different versions for backward compatibility
- Multiple triggers for the same business logic
- Fan-in patterns from diverse event sources

### External System Integration

**Direct Integration**
- Third-party webhooks publishing events to your bus
- Partner APIs sending events using custom protocols
- IoT devices triggering processing workflows

**Legacy System Wrapping**
- SOAP services exposed as Ratio agents
- Mainframe batch jobs triggered by events
- Database procedures called via event interface

## Documentation

- [CLI Cheat Sheet](CLI_CHEAT_SHEET.md)
- [CLI Configuration Guide](CLI_CONFIGURATION_GUIDE.md)
- [Authoring Agents](AGENT_AUTHORING.md)
- [Agent Manager Guide](AGENT_MANAGER_GUIDE.md)
- [Storage Manager Guide](STORAGE_GUIDE.md)
- [References In Detail](REFERENCES.md)
- [DA Vinci Troubleshooting](DA_VINCI_TROUBLESHOOTING.md)
- [Client SDK Documentation](CLIENT_SDK.md)