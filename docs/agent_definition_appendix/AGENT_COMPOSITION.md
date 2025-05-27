# Agent Definition Composition

Ratio's agent composition system enables you to build sophisticated, multi-step workflows by orchestrating individual agents into complex composite agents. This system provides powerful features including automatic dependency resolution, conditional execution, parallel processing, and dynamic value referencing.

## Core Concepts

### Agent Definitions

An agent definition specifies how an agent should be executed, what arguments it accepts, and what responses it produces. Agent definitions can be either:

- **Primitive Agents**: Execute a single system function (have a `system_event_endpoint`)
- **Composite Agents**: Orchestrate multiple other agents through `instructions`

### Basic Structure

```json
{
  "description": "Description of what this agent does",
  "arguments": [
    {
      "name": "input_parameter",
      "type_name": "string",
      "description": "Description of the parameter",
      "required": true
    }
  ],
  "instructions": [
    {
      "execution_id": "step_1",
      "agent_definition_path": "/path/to/agent.agent",
      "arguments": {
        "param": "value"
      }
    }
  ],
  "responses": [
    {
      "name": "output_value",
      "type_name": "string",
      "description": "Description of the response",
      "required": true
    }
  ],
  "response_reference_map": {
    "output_value": "REF:step_1.result"
  }
}
```

## Reference System (REF)

The REF system is the backbone of agent composition, enabling dynamic value resolution between agents and arguments.

### REF String Format

REF strings follow the pattern: `REF:<context>.<key>[.<attribute>]`

- **context**: Either `arguments` or an execution ID
- **key**: The specific value to reference  
- **attribute**: Optional attribute accessor for complex types

### Reference Types and Attributes

#### String References
```json
{
  "text_input": "REF:arguments.user_message",
  "processed_text": "REF:text_processor.cleaned_output"
}
```

#### List References
```json
{
  "all_files": "REF:file_scanner.documents",
  "file_count": "REF:file_scanner.documents.length",
  "first_file": "REF:file_scanner.documents.first",
  "last_file": "REF:file_scanner.documents.last",
  "third_file": "REF:file_scanner.documents.2"
}
```

#### Object References
```json
{
  "user_data": "REF:api_call.response",
  "user_name": "REF:api_call.response.name",
  "user_email": "REF:api_call.response.profile.email"
}
```

#### File References
```json
{
  "file_content": "REF:file_processor.output_file",
  "file_path": "REF:file_processor.output_file.path",
  "file_name": "REF:file_processor.output_file.file_name",
  "parent_dir": "REF:file_processor.output_file.parent_directory"
}
```

## Dependency Management

Dependencies are automatically calculated based on REF usage, creating a directed acyclic graph (DAG) that determines execution order.

### Automatic Dependency Resolution

```json
{
  "instructions": [
    {
      "execution_id": "fetch_data",
      "agent_definition_path": "/agents/api_client.agent",
      "arguments": {
        "endpoint": "REF:arguments.api_endpoint"
      }
    },
    {
      "execution_id": "process_data",
      "agent_definition_path": "/agents/data_processor.agent",
      "arguments": {
        "raw_data": "REF:fetch_data.response_data"
      }
    },
    {
      "execution_id": "generate_report",
      "agent_definition_path": "/agents/report_generator.agent",
      "arguments": {
        "processed_data": "REF:process_data.cleaned_data",
        "metadata": "REF:fetch_data.metadata"
      }
    }
  ]
}
```

**Execution Order**: `fetch_data` → `process_data` → `generate_report`

### Manual Dependencies

You can explicitly specify dependencies when automatic resolution isn't sufficient:

```json
{
  "execution_id": "cleanup_task",
  "agent_definition_path": "/agents/cleanup.agent",
  "dependencies": ["fetch_data", "process_data"],
  "arguments": {
    "working_directory": "REF:arguments.temp_dir"
  }
}
```

## Conditional Execution

Execute agents conditionally based on dynamic evaluation of previous results or arguments.

### Condition Structure

```json
{
  "execution_id": "conditional_step",
  "agent_definition_path": "/agents/error_handler.agent",
  "conditions": [
    {
      "param": "REF:api_call.status_code",
      "operator": "not_equals",
      "value": 200
    }
  ],
  "arguments": {
    "error_message": "REF:api_call.error"
  }
}
```

### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Exact equality | `{"param": "REF:status.code", "operator": "equals", "value": 200}` |
| `not_equals` | Not equal | `{"param": "REF:status.result", "operator": "not_equals", "value": "failed"}` |
| `exists` | Value is not null | `{"param": "REF:user.email", "operator": "exists"}` |
| `not_exists` | Value is null | `{"param": "REF:error.message", "operator": "not_exists"}` |
| `greater_than` | Numeric comparison | `{"param": "REF:metrics.score", "operator": "greater_than", "value": 0.8}` |
| `less_than` | Numeric comparison | `{"param": "REF:file.size", "operator": "less_than", "value": 1000000}` |
| `contains` | String/array contains | `{"param": "REF:tags.list", "operator": "contains", "value": "urgent"}` |
| `in` | Value in collection | `{"param": "REF:status.code", "operator": "in", "value": [200, 201, 202]}` |
| `starts_with` | String prefix | `{"param": "REF:file.name", "operator": "starts_with", "value": "report_"}` |

### Complex Conditions

```json
{
  "conditions": [
    {
      "logic": "OR",
      "conditions": [
        {"param": "REF:user.role", "operator": "equals", "value": "admin"},
        {
          "logic": "AND", 
          "conditions": [
            {"param": "REF:user.level", "operator": "greater_than", "value": 5},
            {"param": "REF:user.verified", "operator": "equals", "value": true}
          ]
        }
      ]
    }
  ]
}
```

## Parallel Execution

Execute agents in parallel over collections, dramatically improving performance for batch operations.

### Basic Parallel Execution

```json
{
  "execution_id": "process_files",
  "agent_definition_path": "/agents/file_processor.agent",
  "parallel_execution": {
    "iterate_over": "REF:file_scanner.file_list",
    "child_argument_name": "input_file"
  }
}
```

### Parallel with Static Collections

```json
{
  "execution_id": "describe_agent_files",
  "agent_definition_path": "/agents/core/describe_file.agent",
  "parallel_execution": {
    "iterate_over": [
      "/agents/core/bedrock_text.agent",
      "/agents/core/cohere_embedding.agent", 
      "/agents/core/math.agent"
    ],
    "child_argument_name": "file_path"
  }
}
```

### Accessing Parallel Results

Parallel executions return their results as a list, maintaining the order of the input collection:

```json
{
  "response_reference_map": {
    "all_results": "REF:process_files.response",
    "first_result": "REF:process_files.response.first",
    "result_count": "REF:process_files.response.length"
  }
}
```

## Advanced Composition Patterns

### Pipeline Processing

Create sequential data processing pipelines:

```json
{
  "description": "Document processing pipeline",
  "arguments": [
    {"name": "input_documents", "type_name": "list", "required": true}
  ],
  "instructions": [
    {
      "execution_id": "extract_text",
      "agent_definition_path": "/agents/text_extractor.agent",
      "parallel_execution": {
        "iterate_over": "REF:arguments.input_documents",
        "child_argument_name": "document_path"
      }
    },
    {
      "execution_id": "analyze_sentiment",
      "agent_definition_path": "/agents/sentiment_analyzer.agent", 
      "parallel_execution": {
        "iterate_over": "REF:extract_text.response",
        "child_argument_name": "text_content"
      }
    },
    {
      "execution_id": "generate_summary",
      "agent_definition_path": "/agents/summarizer.agent",
      "arguments": {
        "all_sentiments": "REF:analyze_sentiment.response",
        "document_count": "REF:extract_text.response.length"
      }
    }
  ]
}
```

### Conditional Branching

Execute different paths based on runtime conditions:

```json
{
  "instructions": [
    {
      "execution_id": "validate_input",
      "agent_definition_path": "/agents/validator.agent",
      "arguments": {"data": "REF:arguments.user_data"}
    },
    {
      "execution_id": "process_valid_data",
      "agent_definition_path": "/agents/data_processor.agent",
      "conditions": [
        {"param": "REF:validate_input.is_valid", "operator": "equals", "value": true}
      ],
      "arguments": {"data": "REF:arguments.user_data"}
    },
    {
      "execution_id": "handle_invalid_data",
      "agent_definition_path": "/agents/error_handler.agent",
      "conditions": [
        {"param": "REF:validate_input.is_valid", "operator": "equals", "value": false}
      ],
      "arguments": {"errors": "REF:validate_input.validation_errors"}
    }
  ]
}
```

### Fan-out/Fan-in Pattern

Process data in parallel and aggregate results:

```json
{
  "instructions": [
    {
      "execution_id": "split_data",
      "agent_definition_path": "/agents/data_splitter.agent",
      "arguments": {"dataset": "REF:arguments.large_dataset"}
    },
    {
      "execution_id": "parallel_analysis", 
      "agent_definition_path": "/agents/analyzer.agent",
      "parallel_execution": {
        "iterate_over": "REF:split_data.chunks",
        "child_argument_name": "data_chunk"
      }
    },
    {
      "execution_id": "aggregate_results",
      "agent_definition_path": "/agents/aggregator.agent",
      "arguments": {
        "partial_results": "REF:parallel_analysis.response",
        "total_chunks": "REF:split_data.chunks.length"
      }
    }
  ]
}
```

## Response Mapping

Map outputs from child agents to the composite agent's response schema:

```json
{
  "responses": [
    {
      "name": "processed_count",
      "type_name": "number",
      "description": "Number of items processed",
      "required": true
    },
    {
      "name": "success_rate", 
      "type_name": "number",
      "description": "Percentage of successful operations",
      "required": true
    },
    {
      "name": "error_details",
      "type_name": "list",
      "description": "Details of any errors encountered",
      "required": false
    }
  ],
  "response_reference_map": {
    "processed_count": "REF:parallel_processor.response.length",
    "success_rate": "REF:calculate_metrics.success_percentage", 
    "error_details": "REF:error_collector.error_list"
  }
}
```

## Error Handling and Resilience

### Conditional Error Handling

```json
{
  "execution_id": "retry_on_failure",
  "agent_definition_path": "/agents/retry_handler.agent",
  "conditions": [
    {"param": "REF:primary_task.status", "operator": "equals", "value": "failed"}
  ],
  "arguments": {
    "original_request": "REF:arguments.request_data",
    "failure_reason": "REF:primary_task.error_message"
  }
}
```

### Cleanup Tasks

```json
{
  "execution_id": "cleanup",
  "agent_definition_path": "/agents/cleanup.agent", 
  "dependencies": ["main_process", "error_handler"],
  "arguments": {
    "temp_files": "REF:main_process.temporary_files",
    "should_cleanup": true
  }
}
```

## Best Practices

### 1. Meaningful Execution IDs
Use descriptive execution IDs that clearly indicate the step's purpose:
```json
{"execution_id": "fetch_user_profile"}  // Good
{"execution_id": "step_1"}              // Avoid
```

### 2. Explicit Response Schemas
Always define clear response schemas for reusable agents:
```json
{
  "responses": [
    {
      "name": "user_id",
      "type_name": "string", 
      "description": "Unique identifier for the user",
      "required": true
    }
  ]
}
```

### 3. Conditional Validation
Use conditions to validate prerequisites:
```json
{
  "conditions": [
    {"param": "REF:arguments.api_key", "operator": "exists"}
  ]
}
```

### 4. Parallel Processing for Scale
Use parallel execution for independent batch operations:
```json
{
  "parallel_execution": {
    "iterate_over": "REF:batch_items.list",
    "child_argument_name": "item"
  }
}
```

### 5. Defensive Error Handling
Always plan for failure scenarios:
```json
{
  "execution_id": "handle_api_errors",
  "conditions": [
    {"param": "REF:api_call.status_code", "operator": "greater_than", "value": 299}
  ]
}
```

## Complete Example: Document Analysis Workflow

```json
{
  "description": "Comprehensive document analysis with parallel processing and conditional logic",
  "arguments": [
    {
      "name": "document_paths",
      "type_name": "list",
      "description": "List of document file paths to analyze",
      "required": true
    },
    {
      "name": "analysis_depth", 
      "type_name": "string",
      "description": "Level of analysis: basic, detailed, or comprehensive",
      "required": true
    }
  ],
  "instructions": [
    {
      "execution_id": "validate_documents",
      "agent_definition_path": "/agents/document_validator.agent",
      "arguments": {
        "file_paths": "REF:arguments.document_paths"
      }
    },
    {
      "execution_id": "extract_basic_info",
      "agent_definition_path": "/agents/basic_extractor.agent",
      "parallel_execution": {
        "iterate_over": "REF:validate_documents.valid_documents",
        "child_argument_name": "document_path"
      }
    },
    {
      "execution_id": "detailed_analysis",
      "agent_definition_path": "/agents/detailed_analyzer.agent",
      "conditions": [
        {
          "param": "REF:arguments.analysis_depth",
          "operator": "in",
          "value": ["detailed", "comprehensive"]
        }
      ],
      "parallel_execution": {
        "iterate_over": "REF:validate_documents.valid_documents",
        "child_argument_name": "document_path"
      }
    },
    {
      "execution_id": "comprehensive_analysis", 
      "agent_definition_path": "/agents/comprehensive_analyzer.agent",
      "conditions": [
        {"param": "REF:arguments.analysis_depth", "operator": "equals", "value": "comprehensive"}
      ],
      "parallel_execution": {
        "iterate_over": "REF:validate_documents.valid_documents", 
        "child_argument_name": "document_path"
      }
    },
    {
      "execution_id": "aggregate_results",
      "agent_definition_path": "/agents/result_aggregator.agent",
      "arguments": {
        "basic_results": "REF:extract_basic_info.response",
        "detailed_results": "REF:detailed_analysis.response", 
        "comprehensive_results": "REF:comprehensive_analysis.response",
        "analysis_level": "REF:arguments.analysis_depth"
      }
    },
    {
      "execution_id": "generate_report",
      "agent_definition_path": "/agents/report_generator.agent",
      "arguments": {
        "aggregated_data": "REF:aggregate_results.summary",
        "document_count": "REF:extract_basic_info.response.length"
      }
    }
  ],
  "responses": [
    {
      "name": "analysis_report",
      "type_name": "file", 
      "description": "Generated analysis report",
      "required": true
    },
    {
      "name": "document_count",
      "type_name": "number",
      "description": "Number of documents processed",
      "required": true
    },
    {
      "name": "processing_summary",
      "type_name": "object",
      "description": "Summary of processing results",
      "required": true
    }
  ],
  "response_reference_map": {
    "analysis_report": "REF:generate_report.report_file",
    "document_count": "REF:extract_basic_info.response.length",
    "processing_summary": "REF:aggregate_results.summary"
  }
}
```