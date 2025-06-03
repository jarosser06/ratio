# Da Vinci Framework Troubleshooting: Exception Trap & Event Bus Systems

## Overview

The Da Vinci framework provides two critical subsystems for troubleshooting Ratio tool issues: the Exception Trap and the Event Bus
System. Understanding how these work is crucial for diagnosing problems in tool execution.

## Exception Trap System

### Purpose
The Exception Trap automatically captures and logs exceptions from tool executions.

### How It Works

#### Environment Activation
The Exception Trap is controlled by the environment variable `DaVinciFramework_ExceptionTrapEnabled`:
```python
def exception_trap_enabled() -> bool:
    return getenv(EXCEPTION_TRAP_ENV_VAR, 'false').lower() == 'true'
```

#### Exception Capture Process
Tools use the `@fn_exception_reporter` decorator to automatically capture exceptions:
```python
@fn_exception_reporter(
    function_name="ratio.tools.my_tool",
    metadata={"additional": "context"},
    logger=Logger("my_namespace"),
    re_raise=False
)
def handler(event: Dict, context: Dict):
    # Tool logic here
    pass
```

#### Exception Data Structure
Based on the `ReportedException` class:
- `exception`: The exception message string
- `exception_traceback`: Full stack trace
- `function_name`: Name of the function that failed
- `originating_event`: The event that triggered the failure  
- `log_execution_id`: Links to associated log execution (optional)
- `log_namespace`: Categorizes the log source (optional)
- `metadata`: Additional context (optional)

#### Storage
Exceptions are stored in the `da_vinci_trapped_exceptions` table with these attributes:
- `function_name`: Partition key
- `exception_id`: Sort key (auto-generated UUID)
- `created`: When the exception was created
- `exception`: The exception message
- `exception_traceback`: Full traceback
- `originating_event`: Event that caused the exception
- `trapped_on`: Timestamp when trapped (auto-generated)
- `time_to_live`: Auto-expires after 2 days

## Event Bus System

### Purpose
The Event Bus coordinates asynchronous communication between tools and system components.

### Core Components

#### Event Structure
Based on the `Event` class:
- `event_id`: Unique identifier (auto-generated UUID)
- `event_type`: Determines which handlers process the event
- `body`: The actual event payload
- `created`: Timestamp (auto-generated)
- `callback_event_type`: Optional event to fire on success
- `callback_event_type_on_failure`: Optional event to fire on failure
- `previous_event_id`: For event chaining

#### Event Handlers
Functions subscribe to events using the `@fn_event_response` decorator:
```python
@fn_event_response(
    exception_reporter=ExceptionReporter(),
    function_name="ratio.tools.my_handler", 
    logger=Logger("my_namespace"),
    handle_callbacks=True,  # Send callback events
    re_raise=False
)
def handler(event: Dict, context: Dict):
    # Process the event
    pass
```

#### Event Flow in Ratio Tool System

**1. Tool Execution Request**
- Event Type: `ratio::tool::{tool_name}::execution`
- Schema: `SystemExecuteToolRequest`
- Contains: `arguments_path`, `argument_schema`, `process_id`, `token`, `working_directory`

**2. Tool Response**  
- Event Type: `ratio::tool_response`
- Schema: `SystemExecuteToolResponse`
- Contains: `process_id`, `status`, `response`, `failure`, `token`

**3. Composite Tool Execution**
- Event Type: `ratio::execute_composite_tool`
- Schema: `ExecuteToolInternalRequest`
- Contains: `tool_definition_path`, `arguments_path`, `process_id`, `working_directory`

### Event Bus Tables

#### Event Bus Subscriptions (`da_vinci_event_bus_subscriptions`)
- `event_type`: Partition key - the event type to listen for
- `function_name`: Sort key - the Lambda function to invoke
- `active`: Whether the subscription is enabled
- `generates_events`: List of events this function produces
- `record_created`/`record_last_updated`: Timestamps

#### Event Bus Responses (`da_vinci_event_bus_responses`)  
- `event_type`: Partition key
- `response_id`: Sort key (auto-generated UUID)
- `originating_event_id`: Links back to triggering event
- `original_event_body`: Copy of the triggering event
- `response_status`: SUCCESS, FAILURE, ROUTED, NO_ROUTE
- `failure_reason`: Error details if failed
- `failure_traceback`: Stack trace if failed
- `time_to_live`: Auto-expires after 8 hours

### Callback Event Handling
The system supports automatic callback events:

**Success Callbacks:**
```python
# If function returns a result and handle_callbacks=True
if fn_result and handle_callbacks and event_obj.callback_event_type:
    event_publisher.submit(
        event=Event(
            body=fn_result,
            event_type=event_obj.callback_event_type,
            previous_event_id=event_obj.event_id
        )
    )
```

**Failure Callbacks:**
```python
# If exception occurs and callback_event_type_on_failure is set
if event_obj.callback_event_type_on_failure:
    event_publisher.submit(
        event=Event(
            body={
                'da_vinci_event_bus_response': {
                    'status': 'failure',
                    'reason': str(exc),
                    'traceback': traceback.format_exc(),
                },
                'originating_event_details': {...}
            },
            event_type=event_obj.callback_event_type_on_failure
        )
    )
```

## Tool Manager Event Flow

### Process Completion Handler
**Event Type:** `ratio::tool_response`

The `process_complete_handler` processes tool completions:

1. **Updates Process Status:** Marks processes as COMPLETED or FAILED
2. **Handles Composite Tools:** Determines next steps for T2 tools
3. **Triggers Child Executions:** Launches dependent tool executions
4. **Manages Dependencies:** Uses execution engine to resolve REF references

### Composite Tool Handler  
**Event Type:** `ratio::execute_composite_tool`

The `execute_composite_tool_handler`:

1. **Validates Access:** Checks file permissions for tool definitions
2. **Loads Definitions:** Parses tool definition files
3. **Creates Execution Engine:** Sets up dependency resolution
4. **Schedules Executions:** Launches child processes for instructions

## Troubleshooting Common Issues

### Tool Execution Failures

**Check Exception Trap:**
If `DaVinciFramework_ExceptionTrapEnabled=true`, look in `da_vinci_trapped_exceptions` table for:
- Recent entries by `function_name`
- Exception messages and tracebacks
- Originating event context

**Check Event Responses:**
Look in `da_vinci_event_bus_responses` for:
- `response_status` = "FAILURE"
- `failure_reason` and `failure_traceback`
- Match `originating_event_id` to trace flow

### Missing Event Handlers

**Symptoms:**
- Events published but no processing occurs
- `response_status` = "NO_SUBSCRIPTIONS" in responses table

**Check:**
- `da_vinci_event_bus_subscriptions` has active subscription for event type
- Lambda function is deployed and accessible
- Event type string matches exactly

### Process Stuck in RUNNING

**Possible Causes:**
- Child process failed but parent wasn't notified
- Event bus delivery failure
- Lambda timeout without proper cleanup

**Investigation Steps:**
1. Check process table for child process statuses
2. Look for exceptions in trap table
3. Verify event responses for related event IDs

### Schema Validation Errors

**Common in:**
- Tool argument validation
- Response schema validation  
- REF reference resolution

**Errors thrown as:**
- `InvalidObjectSchemaError`
- `InvalidSchemaError`
- `InvalidReferenceError`

## Process Management Integration

The Tool Manager uses both systems extensively:

**Exception Integration:**
```python
try:
    # Tool execution logic
except InvalidSchemaError as invalid_err:
    _close_out_process(
        process=proc,
        failure_reason=f"error preparing for execution {invalid_err}",
        token=token,
    )
```

**Event Integration:**
```python
# Publish to event bus
event_publisher.submit(
    event=EventBusEvent(
        body=response_body,
        event_type="ratio::tool_response"
    )
)
```

## Key Configuration Points

### Exception Trap Setup
```python
# Environment variable
EXCEPTION_TRAP_ENV_VAR = 'DaVinciFramework_ExceptionTrapEnabled'

# Decorator usage
@fn_exception_reporter(
    function_name="my_function",
    re_raise=False  # Don't propagate exceptions
)
```

### Event Bus Setup
```python
# For tools that need to respond to events
@fn_event_response(
    exception_reporter=ExceptionReporter(),
    handle_callbacks=True,  # Enable callback support
    schema=MyEventSchema     # Validate event body
)
```

## Related Tables Summary

**Exception Storage:**
- `da_vinci_trapped_exceptions`: 2-day TTL, stores exception details

**Event Bus Storage:**  
- `da_vinci_event_bus_subscriptions`: Persistent, maps events to handlers
- `da_vinci_event_bus_responses`: 8-hour TTL, tracks event processing outcomes

**Process Management:**
- Process Manager process table: Tracks execution status and hierarchy