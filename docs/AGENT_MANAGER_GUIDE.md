# Ratio Agent Manager Documentation

## Overview

The Ratio Agent Manager is the core orchestration service responsible for executing agents, managing processes, resolving dependencies, and coordinating complex workflows within the Ratio platform. It provides both simple (direct) and composite (workflow-based) agent execution capabilities with comprehensive process tracking, event-driven coordination, and reference resolution.

## Architecture

### Core Components

The Agent Manager consists of several interconnected components:

#### 1. API Layer (`api.py`)
- REST API for agent execution and process management
- Handles validation, authorization, and request routing
- Supports both inline agent definitions and file-based definitions

#### 2. Execution Engine (`engine.py`)
- Orchestrates composite agent workflows
- Manages dependency resolution and execution order
- Handles REF reference resolution
- Coordinates file I/O and response mapping

#### 3. Event Handlers (`event_handlers.py`)
- Process completion handling
- Composite agent execution coordination
- Event bus integration for asynchronous processing

#### 4. Process Management (`tables/processes/`)
- Process lifecycle tracking
- Parent-child relationship management
- Status monitoring and reporting

#### 5. Reference System (`reference.py`)
- Dynamic value resolution (REF strings)
- Type-aware attribute access
- Cross-agent data flow management

## Agent Types

### Simple (Direct) Agents

Simple agents execute a single function directly and return results immediately.

**Characteristics:**
- Single Lambda function execution
- Direct input/output mapping
- Defined by `system_event_endpoint`
- Synchronous execution pattern

**Event Flow:**
```
API Request → Process Creation → Lambda Event → Agent Execution → Response Event → Process Completion
```

### Composite (Workflow) Agents

Composite agents orchestrate multiple sub-agents to accomplish complex tasks. These can be nested arbitrarily deep, allowing composite agents to contain other composite agents as sub-steps.

**Characteristics:**
- Multi-step workflow orchestration
- Dependency management between steps
- Conditional execution support
- Defined by `instructions` array
- Support for nested composite agents (unlimited depth)

**Event Flow:**
```
API Request → Process Creation → Engine Initialization → Child Process Creation → 
Sub-Agent Executions → Dependency Resolution → Final Response Assembly
```

**Nested Structure Example:**
```
Composite Agent (Level 1)
├── Simple Agent (step1)
├── Composite Agent (step2)
│   ├── Simple Agent (step2.1)
│   ├── Composite Agent (step2.2)
│   │   ├── Simple Agent (step2.2.1)
│   │   └── Simple Agent (step2.2.2)
│   └── Simple Agent (step2.3)
└── Simple Agent (step3)
```

## Process Lifecycle

### Process States

Processes progress through defined states during their lifecycle:

- **RUNNING**: Process is actively executing
- **COMPLETED**: Process finished successfully
- **FAILED**: Process encountered an error
- **SKIPPED**: Process was skipped due to unmet conditions
- **TERMINATED**: Process was manually terminated

### Process Hierarchy

The Agent Manager maintains a hierarchical process structure that supports unlimited nesting depth:

```
System Process (parent_process_id = "SYSTEM")
├── Composite Agent Process (Level 1)
│   ├── Child Process (execution_id = "step1")
│   ├── Composite Agent Process (Level 2, execution_id = "step2")
│   │   ├── Child Process (execution_id = "substep1")
│   │   ├── Child Process (execution_id = "substep2")
│   │   └── Composite Agent Process (Level 3, execution_id = "substep3")
│   │       ├── Child Process (execution_id = "deepstep1")
│   │       └── Child Process (execution_id = "deepstep2")
│   └── Child Process (execution_id = "step3")
```

## Event System Integration

### Event Types

The Agent Manager uses several event types for coordination:

#### 1. `ratio::agent::{agent_name}::execution`
**Purpose:** Direct agent execution
**Schema:** `SystemExecuteAgentRequest`
**Triggered by:** Simple agent execution requests

```python
{
    "arguments_path": "/path/to/args.aio",
    "argument_schema": [...],
    "process_id": "uuid",
    "parent_process_id": "uuid",
    "response_schema": [...],
    "token": "jwt_token",
    "working_directory": "/work/dir"
}
```

#### 2. `ratio::agent_response`
**Purpose:** Agent completion notification
**Schema:** `SystemExecuteAgentResponse`
**Triggered by:** Agent completion (success or failure)

```python
{
    "process_id": "uuid",
    "parent_process_id": "uuid",
    "status": "COMPLETED|FAILED",
    "response": "/path/to/response.aio",
    "failure": "error message",
    "token": "jwt_token"
}
```

#### 3. `ratio::execute_composite_agent`
**Purpose:** Composite agent execution
**Schema:** `ExecuteAgentInternalRequest`
**Triggered by:** Composite agent execution requests

```python
{
    "agent_definition_path": "/path/to/agent.agent",
    "arguments_path": "/path/to/args.aio",
    "process_id": "uuid",
    "parent_process_id": "uuid",
    "working_directory": "/work/dir",
    "token": "jwt_token"
}
```

### Event Flow Details

#### Simple Agent Execution

1. **API Request Processing**
   ```python
   POST /execute
   {
       "agent_definition_path": "/agents/simple_agent.agent",
       "arguments": {"input": "value"}
   }
   ```

2. **Process Creation**
   - Create process record with RUNNING status
   - Validate permissions and working directory
   - Initialize execution environment

3. **Event Publication**
   ```python
   EventBusEvent(
       event_type="ratio::agent::simple_agent::execution",
       body=SystemExecuteAgentRequest(...)
   )
   ```

4. **Agent Execution**
   - Lambda function receives event
   - Processes arguments and executes logic
   - Publishes response event

5. **Process Completion**
   - Process complete handler receives response
   - Updates process status to COMPLETED/FAILED
   - Stores response file path

#### Composite Agent Execution

1. **API Request Processing**
   ```python
   POST /execute
   {
       "agent_definition_path": "/agents/workflow.agent",
       "arguments": {"source_file": "/data/input.csv"}
   }
   ```

2. **Process Creation**
   - Create parent process for workflow
   - Load agent definition and validate
   - Initialize execution engine

3. **Engine Initialization**
   ```python
   execution_engine = ExecutionEngine(
       arguments=arguments,
       instructions=agent_definition.instructions,
       response_reference_map=response_reference_map
   )
   ```

4. **Dependency Analysis**
   - Parse instructions for REF dependencies
   - Build dependency graph
   - Determine execution order

5. **Child Process Creation**
   - Create child process for each ready instruction
   - Prepare arguments with REF resolution
   - Schedule execution events

6. **Sub-Agent Execution**
   - Each child publishes appropriate event type
   - Simple children: `ratio::agent::{name}::execution`
   - Composite children: `ratio::execute_composite_agent`

7. **Completion Handling**
   - Each completion triggers `ratio::agent_response`
   - Process complete handler updates engine state
   - Determines next available executions
   - Continues until all instructions complete

8. **Response Assembly**
   - Engine resolves response reference map
   - Creates final response file
   - Marks parent process as COMPLETED

#### Nested Composite Agent Execution

For nested composite agents, the process repeats recursively:

1. **Parent Composite Agent** starts execution
2. **Child Composite Agent** is identified in instructions
3. **New Execution Engine** is created for the child composite
4. **Child's Children** are created and executed
5. **Child Composite** completes and returns response
6. **Parent Composite** receives child response and continues

This nesting can continue indefinitely, with each level managing its own execution engine and process hierarchy.