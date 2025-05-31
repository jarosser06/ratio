# Primitive Agent Creation Guide

## Overview

Primitive agents in Ratio are single-function agents that execute a specific task and return results. They consist of two parts:

1. **Agent Definition** (`.agent` file): JSON schema defining inputs, outputs, and execution endpoint
2. **Runtime Implementation** (Python code): The actual execution logic

## Agent Definition Structure

Primitive agents have a `system_event_endpoint` field that distinguishes them from composite agents:

```json
{
  "description": "Brief description of what the agent does",
  "arguments": [
    {
      "name": "parameter_name",
      "type_name": "string|number|boolean|object|list|file",
      "description": "Parameter description",
      "required": true,
      "default_value": "optional_default"
    }
  ],
  "responses": [
    {
      "name": "output_name", 
      "type_name": "string|number|boolean|object|list|file",
      "description": "Output description",
      "required": true
    }
  ],
  "system_event_endpoint": "ratio::agent::your_agent_name::execution"
}
```

## Runtime Implementation

### Basic Structure

```python
import logging
from typing import Dict
from da_vinci.core.logging import Logger
from da_vinci.event_bus.client import fn_event_response
from da_vinci.exception_trap.client import ExceptionReporter
from ratio.agents.agent_lib import RatioSystem

_FN_NAME = "ratio.agents.your_agent_name"

@fn_event_response(exception_reporter=ExceptionReporter(), function_name=_FN_NAME, logger=Logger(_FN_NAME))
def handler(event: Dict, context: Dict):
    """Execute the agent"""
    system = RatioSystem.from_da_vinci_event(event)

    with system:
        # Extract arguments
        input_param = system.arguments["required_param"]

        optional_param = system.arguments.get("optional_param", default_return="default_value")

        # Your logic here
        result = process_data(input_param, optional_param)

        # Return success
        system.success(response_body={
            "output_name": result
        })
```

### Key Patterns

1. **Always use context manager**: `with system:`
2. **Required arguments**: `system.arguments["param_name"]`
3. **Optional arguments**: `system.arguments.get("param_name", default_return="default")`
4. **Success response**: `system.success(response_body={...})`
5. **Failure response**: `system.failure("error message")` (auto-handled by context manager)

### File Operations

```python
# Reading files
file_data = system.get_file_version("/path/to/input.json")
content = file_data["data"]

# Writing files
system.put_file(
    file_path="/path/to/output.json",
    file_type="ratio::file",
    data=content,
    metadata={"created_by": "my_agent"}
)
```

## Stack Definition

Create a CDK stack to deploy the agent:

```python
from os import path
from aws_cdk import Duration
from constructs import Construct
from da_vinci_cdk.stack import Stack
from da_vinci.core.resource_discovery import ResourceType
from da_vinci_cdk.constructs.access_management import ResourceAccessRequest
from da_vinci_cdk.constructs.base import resource_namer
from da_vinci_cdk.constructs.event_bus import EventBusSubscriptionFunction
from ratio.core.services.storage_manager.stack import StorageManagerStack

class YourAgentStack(Stack):
    def __init__(self, app_name: str, app_base_image: str, architecture: str, 
                 deployment_id: str, stack_name: str, scope: Construct):

        super().__init__(
            app_name=app_name,
            app_base_image=app_base_image,
            architecture=architecture,
            requires_event_bus=True,
            requires_exceptions_trap=True,
            required_stacks=[StorageManagerStack],
            deployment_id=deployment_id,
            scope=scope,
            stack_name=stack_name,
        )

        base_dir = self.absolute_dir(__file__)

        runtime_path = path.join(base_dir, "runtime")

        self.agent_execute = EventBusSubscriptionFunction(
            base_image=self.app_base_image,
            construct_id="your-agent-execution",
            event_type="ratio::agent::your_agent_name::execution",
            description="Your agent description",
            entry=runtime_path,
            index="run.py",
            handler="handler",
            function_name=resource_namer("agent-your-name", scope=self),
            memory_size=256,
            resource_access_requests=[
                ResourceAccessRequest(
                    resource_name="event_bus",
                    resource_type=ResourceType.ASYNC_SERVICE,
                ),
                ResourceAccessRequest(
                    resource_name="internal_signing_kms_key_id",
                    resource_type="KMS_KEY",
                    policy_name="default",
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
            ],
            scope=self,
            timeout=Duration.minutes(5),
        )
```

## Directory Structure

```
your_agent/
├── your_agent.agent          # Agent definition
├── runtime/
│   ├── Dockerfile           # Standard Dockerfile
│   └── run.py              # Runtime implementation
└── stack.py                # CDK stack definition
```

## Supported Types

- `string`: Text data
- `number`: Numeric values  
- `boolean`: True/false values
- `object`: JSON objects
- `list`: Arrays
- `file`: File paths (special handling by system)

## Error Handling

The context manager automatically handles exceptions. For explicit failures:

```python
with system:
    if invalid_condition:
        system.failure("Descriptive error message")
        return
    
    # Normal processing continues...
    system.success(response_body=result)
```

## Complete Example

Here's a simple text processing agent:

### hello_world.agent
```json
{
  "description": "A simple greeting agent",
  "arguments": [
    {
      "name": "name",
      "type_name": "string",
      "description": "The name to greet",
      "required": true
    },
    {
      "name": "greeting_type",
      "type_name": "string",
      "description": "Type of greeting",
      "required": false,
      "default_value": "hello",
      "enum": ["hello", "hi", "hey"]
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

### runtime/run.py
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

    system = RatioSystem.from_da_vinci_event(event)

    with system:
        # Extract arguments
        name = system.arguments["name"]

        greeting_type = system.arguments.get("greeting_type", default_return="hello")

        # Generate response
        message = f"{greeting_type.title()}, {name}! Welcome to Ratio."

        # Return success
        system.success(response_body={
            "message": message
        })
```

### runtime/Dockerfile
```dockerfile
ARG IMAGE
FROM $IMAGE

COPY ./* ${LAMBDA_TASK_ROOT}/
```

## That's It

Primitive agents are simple: define the interface in JSON, implement the logic in Python with the
RatioSystem context manager, and deploy with a CDK stack. The system handles argument validation,
file operations, and error reporting automatically.