# Tool Definition Composition Reference

Ratio's tool composition system enables you to build multi-step workflows by
orchestrating individual tools into complex composite tools. This system provides automatic
dependency resolution, conditional execution, parallel processing, dynamic value referencing,
and data transformation capabilities.

## Core Concepts

### Tool Definitions

An tool definition specifies how an tool should be executed, what arguments it accepts, and what responses it produces. Tool definitions can be either:

- **Primitive Tools**: Execute a single system function (have a `system_event_endpoint`)
- **Composite Tools**: Orchestrate multiple other tools through `instructions`

### Basic Structure

```json
{
  "description": "Description of what this tool does",
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
      "tool_definition_path": "/path/to/tool.tool",
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

The REF system is the backbone of tool composition, enabling dynamic value resolution between
tools and arguments.

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

## Data Transformation System

The transformation system provides data manipulation capabilities that work with REF resolution.
Transforms can modify tool arguments before execution or process tool responses
after completion.

### Transform Types

#### Transform Arguments
Applied **after** REF resolution but **before** schema validation. Used to:
- Prepare and combine input data
- Convert data formats
- Create new arguments from existing ones
- Build complex data structures

#### Transform Results
Applied **after** tool execution but **before** final response validation. Used to:
- Format response data
- Extract specific information
- Create summary data
- Clean up response structure

### Transform Structure

Transforms use a two-phase approach: variable resolution followed by data transformation.

```json
{
  "transform_arguments": {
    "variables": {
      "variable_name": "REF:source.data",
      "static_value": "constant"
    },
    "transforms": {
      "new_argument": "function_call(variable_name)"
    }
  },
  "transform_responses": {
    "variables": {
      "result_data": "REF:response.output"
    },
    "transforms": {
      "formatted_result": "process(result_data)"
    }
  }
}
```

### Transform Execution Flow

1. **Variable Resolution Phase**: 
   - All variables are resolved using standard REF resolution
   - Variables can contain REF strings, arrays, objects, or static values
   - Variables become available in the local transform context

2. **Context Merging Phase**:
   - Original arguments/response are merged with resolved variables
   - Variables override original values on key conflicts
   - Creates unified context object for transforms

3. **Transform Execution Phase**:
   - Transform functions execute against the merged context
   - Local variables referenced directly by name (no REF: prefix)
   - Transform results directly modify the arguments/response object

### Built-in Transform Functions

Transform functions support both **positional** and **keyword argument** syntax for improved readability and flexibility.

#### Function Call Syntax

**Positional Arguments (traditional):**
```json
{
  "result": "function_name(arg1, arg2)"
}
```

**Keyword Arguments (recommended):**
```json
{
  "result": "function_name(param1=arg1, param2=arg2)"
}
```

Keyword arguments provide better readability and allow parameters to be specified in any order.

#### get_object_property() Function
Extracts properties from objects using dot notation paths.

**Function Signature:**
```python
get_object_property(obj: Any, property_path: str) -> Any
```

**Positional Usage:**
```json
{
  "user_name": "get_object_property(user_data, \"name\")",
  "user_email": "get_object_property(user_data, \"profile.email\")"
}
```

**Keyword Usage:**
```json
{
  "user_name": "get_object_property(obj=user_data, property_path=\"name\")",
  "nested_value": "get_object_property(obj=api_response, property_path=\"data.items.0.title\")"
}
```

**Array Indexing Support:**
```json
{
  "first_item": "get_object_property(obj=data_array, property_path=\"0\")",
  "nested_array_item": "get_object_property(obj=complex_data, property_path=\"results.2.value\")"
}
```

#### json_parse() Function
Parses JSON strings into structured data objects.

**Function Signature:**
```python
json_parse(json_string: str) -> Union[Dict, List, Any]
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "raw_json": "REF:api_call.response_body"
    },
    "transforms": {
      "parsed_data": "json_parse(json_string=raw_json)",
      "user_info": "get_object_property(obj=parsed_data, property_path=\"user\")"
    }
  }
}
```

#### pipeline() Function
Executes a sequence of operations on data, with each operation receiving the output of the previous step.

**Function Signature:**
```python
pipeline(initial_value: Any, operations: List[Dict]) -> Any
```

**Pipeline Operations Syntax:**
Pipeline operations support keyword argument syntax, making data flow explicit and readable.

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "json_string": "REF:api_response.body",
      "property_path": "user.profile.name"
    },
    "transforms": {
      "extracted_name": "pipeline(json_string, [json_parse(json_string=current), get_object_property(obj=current, property_path=property_path)])"
    }
  }
}
```

**Pipeline Flow:**
1. **Step 1**: `json_parse(json_string=current)` - parses the JSON string (current = initial json_string)
2. **Step 2**: `get_object_property(obj=current, property_path=property_path)` - extracts property from parsed object (current = parsed JSON)

**Complex Pipeline Example:**
```json
{
  "transform_arguments": {
    "variables": {
      "api_data": "REF:data_fetch.response",
      "filter_criteria": "active",
      "separator": ", "
    },
    "transforms": {
      "processed_summary": "pipeline(api_data, [json_parse(json_string=current), get_object_property(obj=current, property_path=\"users\"), map(array=current, template=\"item.name\"), join(array=current, separator=separator)])"
    }
  }
}
```

#### map() Function
Transforms arrays using templates with support for both object templates and simple extraction.

**Function Signature:**
```python
map(array: List, template: Union[Dict, str]) -> List
```

**Object Template Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "user_list": "REF:user_data.users"
    },
    "transforms": {
      "user_summaries": "map(array=user_list, template={name: item.full_name, email: item.contact.email})"
    }
  }
}
```

**String Template Usage:**
```json
{
  "file_paths": "map(array=file_scan_results, template=\"item.file_path\")"
}
```

**With Keyword Arguments:**
```json
{
  "extracted_names": "map(array=users, template=\"item.name\")",
  "structured_data": "map(array=raw_records, template={id: item.user_id, status: item.active})"
}
```

#### sum() Function
Calculates numeric totals from array elements.

**Function Signature:**
```python
sum(array: List, item_path: str) -> Union[int, float]
```

**Usage:**
```json
{
  "transform_responses": {
    "variables": {
      "invoice_items": "REF:response.line_items"
    },
    "transforms": {
      "total_cost": "sum(array=invoice_items, item_path=\"item.amount\")",
      "item_count": "REF:response.line_items.length"
    }
  }
}
```

#### join() Function
Combines array elements into strings with configurable separators.

**Function Signature:**
```python
join(array: List, separator: str) -> str
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "file_list": "REF:scan_results.files",
      "tag_list": "REF:metadata.tags",
      "delimiter": ", "
    },
    "transforms": {
      "file_summary": "join(array=file_list, separator=delimiter)",
      "tag_string": "join(array=tag_list, separator=\" | \")"
    }
  }
}
```

**Auto-extraction for Objects:**
```json
// If array contains objects with 'name' property, join() automatically extracts names
{
  "participant_names": "join(array=meeting_attendees, separator=\", \")"
}
// Result: "Alice Johnson, Bob Smith, Carol Williams"
```

#### if() Function
A ternary operator that returns one of two values based on a condition.

**Function Signature:**
```python
if(condition: Any, true_value: Any, false_value: Any) -> Any
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "error_count": "REF:validation.error_count",
      "status": "REF:process.status"
    },
    "transforms": {
      "result_message": "if(error_count, \"Errors found\", \"Success\")",
      "priority_level": "if(status, \"high\", \"normal\")"
    }
  }
}
```

#### filter() Function
Filters array elements based on condition expressions using 'item' to reference each element.

**Function Signature:**
```python
filter(array: List, condition_string: str) -> List
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "all_records": "REF:data_source.records"
    },
    "transforms": {
      "active_records": "filter(array=all_records, condition_string=\"item.status == 'active'\")",
      "high_priority": "filter(array=all_records, condition_string=\"item.priority > 5 and item.urgent == true\")"
    }
  }
}
```

**Supported Operators in Conditions:**
- Comparison: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Logical: `and`, `or`, `not`
- Examples: `"item.score > 80"`, `"item.type == 'urgent' and item.assigned == true"`

#### group_by() Function
Groups array elements by the specified key path.

**Function Signature:**
```python
group_by(array: List, key_path: str) -> Dict
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "transactions": "REF:financial_data.transactions"
    },
    "transforms": {
      "by_category": "group_by(array=transactions, key_path=\"item.category\")",
      "by_status": "group_by(array=transactions, key_path=\"item.status\")"
    }
  }
}
```

#### sort() Function
Sorts arrays by key path with configurable direction.

**Function Signature:**
```python
sort(array: List, key_path: str = None, direction: str = "asc") -> List
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "user_scores": "REF:evaluation.scores"
    },
    "transforms": {
      "sorted_ascending": "sort(array=user_scores, key_path=\"item.score\", direction=\"asc\")",
      "sorted_descending": "sort(array=user_scores, key_path=\"item.priority\", direction=\"desc\")"
    }
  }
}
```

#### unique() Function
Returns array with duplicate values removed, preserving order.

**Function Signature:**
```python
unique(array: List) -> List
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "all_tags": "REF:content.tags",
      "categories": "REF:items.categories"
    },
    "transforms": {
      "unique_tags": "unique(array=all_tags)",
      "distinct_categories": "unique(array=categories)"
    }
  }
}
```

#### flatten() Function
Flattens nested arrays one level deep.

**Function Signature:**
```python
flatten(array: List) -> List
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "nested_results": "REF:parallel_process.response"
    },
    "transforms": {
      "flattened_data": "flatten(array=nested_results)"
    }
  }
}
```

#### datetime_now() Function
Returns current date and time in the specified format.

**Function Signature:**
```python
datetime_now(format: str = "iso") -> Union[str, int]
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "current_time": "datetime_now(format=\"iso\")",
      "timestamp": "datetime_now(format=\"unix\")"
    },
    "transforms": {
      "created_at": "current_time",
      "processing_time": "timestamp"
    }
  }
}
```

**Parameters:**
- `format`: Format type - `"iso"` for ISO 8601 string (default), `"unix"` for Unix timestamp

**Examples:**
```json
{
  "transform_arguments": {
    "variables": {
      "report_date": "datetime_now()",
      "log_timestamp": "datetime_now(format=\"unix\")"
    },
    "transforms": {
      "report_metadata": "create_object(generated_at=report_date, timestamp=log_timestamp)"
    }
  }
}
```

#### create_object() Function
Creates an object from keyword arguments, useful for building structured data within transforms.

**Function Signature:**
```python
create_object(**kwargs) -> Dict
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "user_name": "REF:user_data.name",
      "user_email": "REF:user_data.email",
      "current_time": "datetime_now()"
    },
    "transforms": {
      "user_summary": "create_object(name=user_name, email=user_email, last_updated=current_time)",
      "metadata": "create_object(version=\"1.0\", status=\"active\")"
    }
  }
}
```

**Complex Example:**
```json
{
  "transform_arguments": {
    "variables": {
      "file_list": "REF:scanner.files",
      "process_time": "datetime_now()",
      "total_size": "REF:scanner.total_bytes"
    },
    "transforms": {
      "scan_report": "create_object(files=file_list, scanned_at=process_time, total_size_bytes=total_size, file_count=REF:scanner.files.length)",
      "summary": "create_object(status=\"completed\", message=\"Scan finished successfully\")"
    }
  }
}
```

#### list_files() Function
Lists files in a directory with optional glob pattern filtering. Limited to 50 results.

**Function Signature:**
```python
list_files(directory_path: str, pattern: str = None) -> List[str]
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "workspace_dir": "REF:arguments.workspace_path"
    },
    "transforms": {
      "all_files": "list_files(directory_path=workspace_dir)",
      "python_files": "list_files(directory_path=workspace_dir, pattern=\"*.py\")",
      "config_files": "list_files(directory_path=\"/config\", pattern=\"*.json\")"
    }
  }
}
```

#### list_file_versions() Function
Lists all versions of a specific file.

**Function Signature:**
```python
list_file_versions(file_path: str) -> List[Dict]
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "target_file": "REF:arguments.file_path"
    },
    "transforms": {
      "file_history": "list_file_versions(file_path=target_file)"
    }
  }
}
```

#### describe_version() Function
Returns metadata for a specific file version.

**Function Signature:**
```python
describe_version(file_path: str, version_id: str = None) -> Dict
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "file_path": "REF:arguments.document_path",
      "version": "REF:arguments.version_id"
    },
    "transforms": {
      "file_metadata": "describe_version(file_path=file_path)",
      "specific_version": "describe_version(file_path=file_path, version_id=version)"
    }
  }
}
```

#### read_file() Function
Reads content of a file, optionally specifying version.

**Function Signature:**
```python
read_file(file_path: str, version_id: str = None) -> str
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "config_path": "REF:arguments.config_file"
    },
    "transforms": {
      "config_content": "read_file(file_path=config_path)",
      "previous_version": "read_file(file_path=config_path, version_id=\"v1.2\")"
    }
  }
}
```

#### read_files() Function
Reads content of multiple files. Limited to 5 files maximum.

**Function Signature:**
```python
read_files(file_paths: List[str]) -> List[str]
```

**Usage:**
```json
{
  "transform_arguments": {
    "variables": {
      "source_files": "REF:file_scanner.important_files"
    },
    "transforms": {
      "file_contents": "read_files(file_paths=source_files)"
    }
  }
}
```

### Transform Examples

#### JSON Processing Pipeline
```json
{
  "execution_id": "process_api_response",
  "tool_definition_path": "/tools/data_processor.tool",
  "transform_arguments": {
    "variables": {
      "raw_response": "REF:api_call.response_body",
      "user_path": "data.user",
      "name_path": "profile.display_name"
    },
    "transforms": {
      "user_name": "pipeline(raw_response, [json_parse(json_string=current), get_object_property(obj=current, property_path=user_path), get_object_property(obj=current, property_path=name_path)])"
    }
  }
}
```

#### Data Preparation Pipeline
```json
{
  "execution_id": "analyze_with_llm",
  "tool_definition_path": "/tools/core/bedrock_text.tool",
  "transform_arguments": {
    "variables": {
      "prompt_parts": ["REF:arguments.analysis_prompt", "REF:arguments.file_to_analyze"],
      "separator": "\n\n"
    },
    "transforms": {
      "prompt": "join(array=prompt_parts, separator=separator)"
    }
  },
  "arguments": {
    "model_id": "REF:arguments.model_id"
  }
}
```

#### Response Processing
```json
{
  "execution_id": "process_results",
  "tool_definition_path": "/tools/data_processor.tool",
  "arguments": {
    "raw_data": "REF:data_fetcher.results"
  },
  "transform_responses": {
    "variables": {
      "processed_items": "REF:response.processed_items",
      "success_template": "item.success",
      "delimiter": "; "
    },
    "transforms": {
      "summary_report": "join(array=map(array=processed_items, template=\"item.description\"), separator=delimiter)",
      "success_count": "sum(array=map(array=processed_items, template=success_template), item_path=\"item.value\")"
    }
  }
}
```

#### Complex Data Shaping with Pipeline
```json
{
  "transform_arguments": {
    "variables": {
      "api_response": "REF:data_fetcher.raw_response",
      "sales_path": "data.sales_records",
      "threshold": 1000
    },
    "transforms": {
      "high_value_sales": "pipeline(api_response, [json_parse(json_string=current), get_object_property(obj=current, property_path=sales_path), map(array=current, template={amount: item.total, customer: item.customer_name})])",
      "revenue_total": "pipeline(api_response, [json_parse(json_string=current), get_object_property(obj=current, property_path=sales_path), sum(array=current, item_path=\"item.total\")])"
    }
  }
}
```

### Variable Reference Rules

**In Variables Section:**
- Use `REF:` for external references (arguments, execution responses)
- Can reference complex paths: `REF:file_processor.results.0.path`
- Can build arrays: `["REF:arg1", "REF:arg2", "static_value"]`
- Can use static values: `"separator": "\n\n"`

**In Transforms Section:**
- Reference variables directly by name: `prompt_parts`, `separator`
- Reference original context with REF: `REF:response.items`
- Use in function calls: `join(array=prompt_parts, separator=separator)`
- Transform keys create/modify fields in arguments or response

**In Pipeline Operations:**
- Use `current` to reference the flowing pipeline value
- Use variable names to reference declared variables
- Use string literals with quotes: `property_path="user.name"`

### Transform Error Handling

**Variable Resolution Errors:**
- Invalid REF strings in variables section
- Missing referenced executions or arguments
- Type mismatches in variable assignment

**Transform Execution Errors:**
- Undefined variables referenced in transforms
- Invalid function calls or parameters
- Schema validation failures after transforms

**Example Error Scenarios:**
```json
// ❌ Error: undefined variable
{
  "variables": {
    "data": "REF:processor.results"
  },
  "transforms": {
    "summary": "join(array=undefined_var, separator=', ')"  // undefined_var not in variables
  }
}

// ❌ Error: schema validation failure
{
  "transforms": {
    "required_field": "invalid_function(data)"  // Function doesn't exist or fails
  }
}
```

## Dependency Management

Dependencies are automatically calculated based on REF usage, creating a directed acyclic graph
(DAG) that determines execution order.

### Automatic Dependency Resolution

```json
{
  "instructions": [
    {
      "execution_id": "fetch_data",
      "tool_definition_path": "/tools/api_client.tool",
      "arguments": {
        "endpoint": "REF:arguments.api_endpoint"
      }
    },
    {
      "execution_id": "process_data",
      "tool_definition_path": "/tools/data_processor.tool",
      "arguments": {
        "raw_data": "REF:fetch_data.response_data"
      }
    },
    {
      "execution_id": "generate_report",
      "tool_definition_path": "/tools/report_generator.tool",
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
  "tool_definition_path": "/tools/cleanup.tool",
  "dependencies": ["fetch_data", "process_data"],
  "arguments": {
    "working_directory": "REF:arguments.temp_dir"
  }
}
```

## Conditional Execution

Execute tools conditionally based on dynamic evaluation of previous results or arguments.

### Condition Structure

```json
{
  "execution_id": "conditional_step",
  "tool_definition_path": "/tools/error_handler.tool",
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

Execute tools in parallel over collections, dramatically improving performance for batch operations.

**Important Note**: Parallel execution can only iterate over externally generated lists.
The `iterate_over` does not have any ability to reference transformed arguments.

### Basic Parallel Execution

```json
{
  "execution_id": "process_files",
  "tool_definition_path": "/tools/file_processor.tool",
  "parallel_execution": {
    "iterate_over": "REF:file_scanner.file_list",
    "child_argument_name": "input_file"
  }
}
```

### Parallel with Static Collections

```json
{
  "execution_id": "describe_tool_files",
  "tool_definition_path": "/tools/core/describe_file.tool",
  "parallel_execution": {
    "iterate_over": [
      "/tools/core/bedrock_text.tool",
      "/tools/core/cohere_embedding.tool", 
      "/tools/core/math.tool"
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

### Pipeline Processing with Transforms

Create sequential data processing pipelines with data transformation:

```json
{
  "description": "Document processing pipeline with transforms",
  "arguments": [
    {"name": "input_documents", "type_name": "list", "required": true}
  ],
  "instructions": [
    {
      "execution_id": "extract_text",
      "tool_definition_path": "/tools/text_extractor.tool",
      "parallel_execution": {
        "iterate_over": "REF:arguments.input_documents",
        "child_argument_name": "document_path"
      }
    },
    {
      "execution_id": "analyze_sentiment",
      "tool_definition_path": "/tools/sentiment_analyzer.tool",
      "transform_arguments": {
        "variables": {
          "extracted_texts": "REF:extract_text.response"
        },
        "transforms": {
          "combined_texts": "map(array=extracted_texts, template=\"item.content\")"
        }
      },
      "arguments": {
        "text_count": "REF:extract_text.response.length"
      },
      "parallel_execution": {
        "iterate_over": "REF:extract_text.response",
        "child_argument_name": "text_content"
      }
    },
    {
      "execution_id": "generate_summary",
      "tool_definition_path": "/tools/summarizer.tool",
      "transform_arguments": {
        "variables": {
          "sentiment_results": "REF:analyze_sentiment.response"
        },
        "transforms": {
          "average_sentiment": "sum(array=sentiment_results, item_path=\"item.score\")",
          "sentiment_summary": "join(array=map(array=sentiment_results, template=\"item.label\"), separator=\", \")"
        }
      },
      "arguments": {
        "document_count": "REF:extract_text.response.length"
      }
    }
  ]
}
```

### Conditional Branching with Transform Logic

Execute different paths based on transformed data:

```json
{
  "instructions": [
    {
      "execution_id": "validate_input",
      "tool_definition_path": "/tools/validator.tool",
      "arguments": {"data": "REF:arguments.user_data"}
    },
    {
      "execution_id": "process_valid_data",
      "tool_definition_path": "/tools/data_processor.tool",
      "conditions": [
        {"param": "REF:validate_input.is_valid", "operator": "equals", "value": true}
      ],
      "transform_arguments": {
        "variables": {
          "valid_records": "REF:validate_input.clean_records"
        },
        "transforms": {
          "processed_data": "map(array=valid_records, template={id: item.identifier, value: item.data})"
        }
      },
      "arguments": {
        "processing_mode": "REF:arguments.mode",
        "batch_size": "REF:validate_input.clean_records.length"
      }
    },
    {
      "execution_id": "handle_invalid_data",
      "tool_definition_path": "/tools/error_handler.tool",
      "conditions": [
        {"param": "REF:validate_input.is_valid", "operator": "equals", "value": false}
      ],
      "transform_arguments": {
        "variables": {
          "error_details": "REF:validate_input.validation_errors"
        },
        "transforms": {
          "error_summary": "join(array=map(array=error_details, template=\"item.message\"), separator=\"; \")"
        }
      },
      "arguments": {
        "error_count": "REF:validate_input.validation_errors.length"
      }
    }
  ]
}
```

### Fan-out/Fan-in Pattern with Result Aggregation

Process data in parallel and transform aggregated results:

```json
{
  "instructions": [
    {
      "execution_id": "split_data",
      "tool_definition_path": "/tools/data_splitter.tool",
      "arguments": {"dataset": "REF:arguments.large_dataset"}
    },
    {
      "execution_id": "parallel_analysis", 
      "tool_definition_path": "/tools/analyzer.tool",
      "parallel_execution": {
        "iterate_over": "REF:split_data.chunks",
        "child_argument_name": "data_chunk"
      }
    },
    {
      "execution_id": "aggregate_results",
      "tool_definition_path": "/tools/aggregator.tool",
      "transform_arguments": {
        "variables": {
          "analysis_results": "REF:parallel_analysis.response"
        },
        "transforms": {
          "successful_analyses": "sum(array=map(array=analysis_results, template=\"item.success_flag\"), item_path=\"item.value\")",
          "combined_metrics": "sum(array=analysis_results, item_path=\"item.metric_value\")"
        }
      },
      "arguments": {
        "total_chunks": "REF:split_data.chunks.length"
      },
      "transform_responses": {
        "variables": {
          "final_summary": "REF:response.aggregated_data"
        },
        "transforms": {
          "completion_percentage": "sum(array=final_summary, item_path=\"item.completion_rate\")",
          "summary_report": "join(array=map(array=final_summary, template=\"item.description\"), separator=\"\\n\")"
        }
      }
    }
  ]
}
```

## Response Mapping

Map outputs from child tools to the composite tool's response schema:

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
  "tool_definition_path": "/tools/retry_handler.tool",
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
  "tool_definition_path": "/tools/cleanup.tool", 
  "dependencies": ["main_process", "error_handler"],
  "arguments": {
    "temp_files": "REF:main_process.temporary_files",
    "should_cleanup": true
  }
}
```

## Best Practices

### Use Simple REF for Direct References
Use direct REF strings in arguments for simple value passing. Only use transforms when actual data manipulation is needed:

```json
// ✅ Good: Simple reference - use direct REF
{
  "arguments": {
    "user_id": "REF:validate_user.user_id",
    "file_path": "REF:file_scanner.primary_file"
  }
}

// ❌ Avoid: Unnecessary transform for simple pass-through
{
  "transform_arguments": {
    "variables": {
      "user_id": "REF:validate_user.user_id"
    },
    "transforms": {
      "user_id": "user_id"  // No actual transformation
    }
  }
}

// ✅ Good: Transform when actual manipulation is needed
{
  "transform_arguments": {
    "variables": {
      "file_list": "REF:scanner.files",
      "metadata": "REF:scanner.metadata"
    },
    "transforms": {
      "file_summary": "join(array=file_list, separator=', ')",
      "total_files": "REF:scanner.files.length"
    }
  }
}
```

### Use Keyword Arguments for Clarity
Prefer keyword arguments for transform functions to improve readability:

```json
// ✅ Good: Clear keyword arguments
{
  "extracted_name": "get_object_property(obj=user_data, property_path=\"profile.name\")",
  "joined_list": "join(array=items, separator=\", \")"
}

// ❌ Avoid: Positional arguments (harder to understand)
{
  "extracted_name": "get_object_property(user_data, \"profile.name\")",
  "joined_list": "join(items, \", \")"
}
```

### Declare Path Variables for Reusability
Declare property paths and other constants as variables for better maintainability:

```json
{
  "transform_arguments": {
    "variables": {
      "json_data": "REF:api_response.body",
      "user_path": "data.user.profile",
      "name_field": "display_name"
    },
    "transforms": {
      "user_name": "pipeline(json_data, [json_parse(json_string=current), get_object_property(obj=current, property_path=user_path), get_object_property(obj=current, property_path=name_field)])"
    }
  }
}
```

### Meaningful Execution IDs
Use descriptive execution IDs that clearly indicate the step's purpose:
```json
{"execution_id": "fetch_user_profile"}  // Good
{"execution_id": "step_1"}              // Avoid
```

### Explicit Response Schemas
Always define clear response schemas for reusable tools:
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

### Parallel Processing for Scale
Use parallel execution for independent batch operations:
```json
{
  "parallel_execution": {
    "iterate_over": "REF:batch_items.list",
    "child_argument_name": "item"
  }
}
```

### Transform Variable Management
Organize complex transforms with clear variable naming:
```json
{
  "transform_arguments": {
    "variables": {
      "source_records": "REF:data_source.records",
      "filter_criteria": "REF:arguments.filter",
      "processing_mode": "batch"
    },
    "transforms": {
      "filtered_data": "map(array=source_records, template=\"item.data\")",
      "batch_size": "REF:data_source.records.length"
    }
  }
}
```

## Complete Example: Advanced Document Analysis Workflow

```json
{
  "description": "Comprehensive document analysis with transforms, parallel processing, and conditional logic",
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
      "tool_definition_path": "/tools/document_validator.tool",
      "arguments": {
        "file_paths": "REF:arguments.document_paths"
      },
      "transform_responses": {
        "variables": {
          "validation_results": "REF:response.validation_results"
        },
        "transforms": {
          "valid_count": "sum(array=validation_results, item_path=\"item.is_valid\")",
          "error_summary": "join(array=map(array=validation_results, template=\"item.error_message\"), separator=\"; \")"
        }
      }
    },
    {
      "execution_id": "extract_basic_info",
      "tool_definition_path": "/tools/basic_extractor.tool",
      "parallel_execution": {
        "iterate_over": "REF:validate_documents.valid_documents",
        "child_argument_name": "document_path"
      },
      "transform_responses": {
        "variables": {
          "extraction_results": "REF:response"
        },
        "transforms": {
          "total_pages": "sum(array=extraction_results, item_path=\"item.page_count\")",
          "file_summary": "join(array=map(array=extraction_results, template=\"item.filename\"), separator=\", \")"
        }
      }
    },
    {
      "execution_id": "detailed_analysis",
      "tool_definition_path": "/tools/detailed_analyzer.tool",
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
      },
      "transform_arguments": {
        "variables": {
          "basic_results": "REF:extract_basic_info.response"
        },
        "transforms": {
          "context_data": "map(array=basic_results, template={file: item.filename, pages: item.page_count})"
        }
      },
      "arguments": {
        "analysis_mode": "REF:arguments.analysis_depth"
      }
    },
    {
      "execution_id": "comprehensive_analysis", 
      "tool_definition_path": "/tools/comprehensive_analyzer.tool",
      "conditions": [
        {"param": "REF:arguments.analysis_depth", "operator": "equals", "value": "comprehensive"}
      ],
      "parallel_execution": {
        "iterate_over": "REF:validate_documents.valid_documents", 
        "child_argument_name": "document_path"
      },
      "transform_arguments": {
        "variables": {
          "detailed_results": "REF:detailed_analysis.response",
          "basic_data": "REF:extract_basic_info.response"
        },
        "transforms": {
          "combined_context": "map(array=detailed_results, template={analysis: item.insights, metadata: item.metadata})",
          "processing_summary": "join(array=map(array=basic_data, template=\"item.summary\"), separator=\"\\n\")"
        }
      }
    },
    {
      "execution_id": "aggregate_results",
      "tool_definition_path": "/tools/result_aggregator.tool",
      "transform_arguments": {
        "variables": {
          "basic_results": "REF:extract_basic_info.response",
          "detailed_results": "REF:detailed_analysis.response", 
          "comprehensive_results": "REF:comprehensive_analysis.response"
        },
        "transforms": {
          "analysis_summary": "map(array=basic_results, template={file: item.filename, status: item.status})",
          "combined_insights": "join(array=map(array=detailed_results, template=\"item.key_findings\"), separator=\"; \")"
        }
      },
      "arguments": {
        "analysis_level": "REF:arguments.analysis_depth",
        "total_documents": "REF:extract_basic_info.response.length"
      },
      "transform_responses": {
        "variables": {
          "aggregated_data": "REF:response.summary"
        },
        "transforms": {
          "completion_report": "join(array=map(array=aggregated_data, template=\"item.description\"), separator=\"\\n\")",
          "success_metrics": "sum(array=aggregated_data, item_path=\"item.success_count\")"
        }
      }
    },
    {
      "execution_id": "generate_report",
      "tool_definition_path": "/tools/report_generator.tool",
      "transform_arguments": {
        "variables": {
          "summary_data": "REF:aggregate_results.summary",
          "document_metrics": "REF:extract_basic_info.response"
        },
        "transforms": {
          "executive_summary": "join(array=map(array=summary_data, template=\"item.key_point\"), separator=\"\\n• \")",
          "document_stats": "map(array=document_metrics, template={name: item.filename, pages: item.page_count})"
        }
      },
      "arguments": {
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
      "description": "Summary of processing results with metrics",
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