# Ratio REF System Documentation

## Overview

The Ratio REF (Reference) system enables dynamic value resolution, dependency management, and data transformation in agent execution workflows. REF strings allow agents to reference values from previous executions or input arguments, while the transformation system provides powerful data manipulation capabilities.

## Execution Order and Transform Pipeline

Understanding the execution order is crucial for proper agent development:

### Simple Agent Execution Flow
```
1. Agent Arguments Received
2. Transform Arguments Applied (if defined)
3. Arguments Validated Against Agent Schema
4. Agent Execution
5. Response Generated
6. Transform Results Applied (if defined)  
7. Response Validated Against Response Schema
8. Final Response Stored
```

### Composite Agent Execution Flow
```
1. Composite Agent Arguments Received
2. Instructions Parsed and Dependencies Calculated
3. For Each Child Agent:
   a. REF Values Resolved
   b. Transform Arguments Applied (if defined)
   c. Arguments Validated Against Child Agent Schema
   d. Child Agent Execution
   e. Response Generated
   f. Transform Results Applied (if defined)
   g. Response Validated Against Child Response Schema
   h. Response Added to Reference System
4. Response Reference Map Resolved
5. Final Composite Response Assembled
```

### Critical Transform Timing

**Transform Arguments:**
- Applied **after** REF resolution but **before** schema validation
- Must produce output that conforms to the agent's argument schema
- Can create new arguments or modify existing ones
- Useful for data preparation, combining inputs, or format conversion

**Transform Results:**
- Applied **after** agent execution but **before** final response validation
- Must produce output that conforms to the agent's response schema
- Can create new response fields or modify existing ones
- Useful for response formatting, data extraction, or cleanup

## Reference String Format

REF strings follow the pattern: `REF:<context>.<key>[.<attribute>]`

- **context**: Either `arguments` or an execution ID
- **key**: The specific value to reference
- **attribute**: Optional attribute accessor for complex types

### Examples
```
REF:arguments.input_file          // Reference an argument
REF:arguments.user_name           // Reference a simple argument value
REF:execution_1.response_data     // Reference a response from execution_1
REF:file_processor.output_file.path  // Reference file path attribute
REF:data_analyzer.results.first   // Reference first item in a list
```

## Dependency Resolution and Execution Order

### Automatic Dependency Calculation

The execution engine automatically calculates dependencies based on REF usage:

1. **Parsing Phase**: All agent arguments are scanned for REF strings
2. **Dependency Graph**: A directed graph is built showing which executions depend on others
3. **Execution Order**: Agents execute only when all their dependencies are completed
4. **Condition Evaluation**: Conditional executions are evaluated once dependencies are met

### Nested Reference Support

REF strings support nested resolution in complex data structures:

```json
{
  "user_profile": {
    "name": "REF:user_data.profile.name",
    "preferences": {
      "theme": "REF:user_settings.display.theme",
      "language": "REF:arguments.default_language"
    }
  },
  "file_list": [
    "REF:file_scan.documents.0",
    "REF:file_scan.documents.1"
  ]
}
```

## Object Transformation System

The transformation system provides powerful data manipulation capabilities that work seamlessly with REF resolution. Transforms directly modify their target context (arguments or response) and can create new fields or modify existing ones.

### Transform Structure

Transforms use a two-phase approach: variable resolution followed by data transformation.

**Transform Arguments (replaces pre_transforms):**
```json
{
  "transform_arguments": {
    "variables": {
      "prompt_parts": ["REF:arguments.analysis_prompt", "REF:arguments.file_to_analyze"],
      "separator": "\n\n"
    },
    "transforms": {
      "prompt": "join(prompt_parts, separator)"
    }
  }
}
```

**Transform Results (replaces post_transforms):**
```json
{
  "transform_results": {
    "variables": {
      "raw_data": "REF:response.response_body"
    },
    "transforms": {
      "files": "raw_data.files",
      "total_count": "REF:response.response_body.files.length"
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

### Variable Resolution Examples

**Building Complex Arrays:**
```json
{
  "transform_arguments": {
    "variables": {
      "file_paths": ["REF:scan_results.documents", "REF:scan_results.images"],
      "metadata": "REF:file_processor.file_info",
      "separator": " | "
    },
    "transforms": {
      "input_summary": "join(file_paths, separator)",
      "data_context": "metadata"
    }
  }
}
```

**Data Preparation Pipeline:**
```json
{
  "transform_arguments": {
    "variables": {
      "raw_records": "REF:data_fetcher.sales_data",
      "filter_date": "REF:arguments.cutoff_date",
      "high_value_threshold": 1000
    },
    "transforms": {
      "processed_data": "map(raw_records, {id: item.sale_id, amount: item.total})",
      "summary_stats": "sum(raw_records, item.total)"
    }
  }
}
```

### Complete Transform Examples

**File Analysis with Variable Preparation:**
```json
{
  "execution_id": "analyze_with_llm",
  "agent_definition_path": "/agents/core/bedrock_text.agent",
  "transform_arguments": {
    "variables": {
      "prompt_parts": ["REF:arguments.analysis_prompt", "REF:arguments.file_to_analyze"],
      "separator": "\n\n"
    },
    "transforms": {
      "prompt": "join(prompt_parts, separator)"
    }
  },
  "arguments": {
    "model_id": "REF:arguments.model_id"
  }
}
```

**Response Processing with Variables:**
```json
{
  "transform_results": {
    "variables": {
      "result_items": "REF:response.processed_items",
      "success_items": "map(result_items, item.success)",
      "delimiter": "; "
    },
    "transforms": {
      "summary_report": "join(map(result_items, item.description), delimiter)",
      "success_count": "sum(success_items, item.value)",
      "completion_rate": "REF:response.total_processed"
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
- Use in function calls: `join(prompt_parts, separator)`
- Transform keys create/modify fields in arguments or response

### Error Handling

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
    "summary": "join(undefined_var, ', ')"  // undefined_var not in variables
  }
}

// ❌ Error: schema validation failure
{
  "transforms": {
    "required_field": "invalid_function(data)"  // Function doesn't exist or fails
  }
}
```

### Built-in Mapping Functions

#### map() Function
Transforms arrays using templates:

```json
{
  "user_summaries": "map(REF:user_data.users, {name: item.full_name, email: item.contact.email})"
}
```

**String Template Version:**
```json
{
  "file_paths": "map(REF:file_scan.results, item.file_path)"
}
```

#### sum() Function
Calculates numeric totals:

```json
{
  "total_cost": "sum(REF:invoice_data.line_items, item.amount)",
  "total_hours": "sum(REF:time_entries.entries, item.duration)"
}
```

#### join() Function
Combines array elements into strings:

```json
{
  "file_list": "join(REF:scan_results.files, \", \")",
  "tag_string": "join(REF:metadata.tags, \" | \")"
}
```

**Auto-extraction for Objects:**
```json
// If array contains objects with 'name' property, join() automatically extracts names
{
  "participant_names": "join(REF:meeting_data.attendees, \", \")"
}
// Result: "Alice Johnson, Bob Smith, Carol Williams"
```

### Advanced Transform Patterns

#### Nested Function Calls
```json
{
  "summary": "join(map(REF:data.items, item.title), \" and \")"
}
```

#### Array Processing Pipeline
```json
{
  "transform_arguments": {
    "variables": {
      "valid_entries": "REF:data_validator.clean_data"
    },
    "transforms": {
      "processed_entries": "map(valid_entries, {id: item.identifier, value: item.amount})"
    }
  },
  "transform_results": {
    "variables": {
      "processed_items": "REF:response.processed_items"
    },
    "transforms": {
      "total_processed": "sum(processed_items, item.value)",
      "summary_text": "join(map(processed_items, item.description), \"; \")"
    }
  }
}
```

#### Conditional Data Shaping
```json
{
  "transform_arguments": {
    "variables": {
      "all_users": "REF:user_data.all_users"
    },
    "transforms": {
      "active_users": "map(all_users, {name: item.name, status: item.active_status})",
      "user_count": "REF:user_data.all_users.length"
    }
  }
}
```

## Supported Reference Types

### 1. String References
Simple string values with no special attributes.

```
REF:arguments.user_name
REF:text_processor.cleaned_text
```

### 2. Number References  
Numeric values (integers or floats) with no special attributes.

```
REF:calculator.result
REF:arguments.max_iterations
```

### 3. Boolean References
Boolean values with no special attributes.

```
REF:validator.is_valid
REF:arguments.debug_mode
```

### 4. List References
Array/list values with special attribute support.

**Supported Attributes:**
- `length`: Returns the number of items in the list
- `first`: Returns the first item (or null if empty)
- `last`: Returns the last item (or null if empty)  
- `<index>`: Returns item at specific index (0-based)

**Examples:**
```
REF:data_processor.items           // Entire list
REF:data_processor.items.length    // Number of items
REF:data_processor.items.first     // First item
REF:data_processor.items.last      // Last item
REF:data_processor.items.0         // Item at index 0
REF:data_processor.items.5         // Item at index 5
```

### 5. Object References
Dictionary/object values with attribute access support.

**Attribute Access:**
- `<key>`: Returns the value associated with the specified key

**Examples:**
```
REF:api_response.data              // Entire object
REF:api_response.data.status       // Access 'status' key
REF:api_response.data.user         // Access 'user' key
REF:user_info.profile.email        // Nested object access
```

### 6. File References
File path references with special file-related attributes.

**Supported Attributes:**
- `path`: Returns the full file path
- `file_name`: Returns just the filename (basename)
- `parent_directory`: Returns the directory containing the file
- *No attribute*: Returns the file contents

**Examples:**
```
REF:file_uploader.document         // File contents
REF:file_uploader.document.path    // Full file path
REF:file_uploader.document.file_name  // Just filename
REF:file_uploader.document.parent_directory  // Parent directory
```

## Complete Transform Examples

### Data Processing Pipeline

```json
{
  "execution_id": "analyze_sales",
  "agent_definition_path": "/agents/sales_analyzer.agent",
  "arguments": {
    "raw_data": "REF:data_fetcher.sales_records"
  },
  "transform_arguments": {
    "variables": {
      "sales_records": "REF:data_fetcher.sales_records"
    },
    "transforms": {
      "total_records": "REF:data_fetcher.sales_records.length",
      "high_value_sales": "map(sales_records, {amount: item.total, customer: item.customer_name})",
      "revenue_total": "sum(sales_records, item.total)"
    }
  },
  "transform_results": {
    "variables": {
      "insights": "REF:response.insights",
      "analyzed_records": "REF:response.analyzed_records"
    },
    "transforms": {
      "summary_report": "join(map(insights, item.description), \"\\n\")",
      "processed_count": "REF:response.analyzed_records.length",
      "success_percentage": "REF:response.success_rate"
    }
  }
}
```

### File Processing Workflow

```json
{
  "execution_id": "process_documents",
  "agent_definition_path": "/agents/document_processor.agent", 
  "arguments": {
    "input_files": "REF:file_scanner.discovered_files"
  },
  "transform_arguments": {
    "variables": {
      "discovered_files": "REF:file_scanner.discovered_files"
    },
    "transforms": {
      "file_paths": "map(discovered_files, item.path)",
      "file_names": "map(discovered_files, item.file_name)",
      "total_files": "REF:file_scanner.discovered_files.length"
    }
  },
  "transform_results": {
    "variables": {
      "results": "REF:response.results"
    },
    "transforms": {
      "processed_files": "map(results, {name: item.filename, status: item.processing_status})",
      "summary": "join(results, \" | \")",
      "completion_rate": "sum(results, item.success_flag)"
    }
  }
}
```

## Error Handling

### Transform Errors

Transform functions can fail for several reasons:

```json
// MappingError examples:
{
  "invalid_template": "map(REF:data.items, item.invalid_path)",     // Attribute not found
  "wrong_type": "sum(REF:data.strings, item.value)",          // Not a number
  "missing_array": "join(REF:data.missing_field, \", \")"         // Array doesn't exist
}
```

### Reference Resolution Errors

The system will throw `InvalidReferenceError` for:
- Malformed REF strings
- References to non-existent executions
- References to non-existent response keys
- Invalid attribute access for unsupported types

### Runtime Resolution Errors

- **File Access**: Requires valid authentication token
- **Index Out of Bounds**: Accessing invalid list indices
- **Missing Keys**: Accessing non-existent object keys
- **Type Mismatches**: Attempting unsupported operations

## Schema Validation and Transforms

### Critical Guidelines

1. **Transform Arguments Output**: Must conform to the target agent's argument schema
2. **Transform Results Output**: Must conform to the agent's response schema
3. **Type Safety**: Transform functions are type-aware and will fail on type mismatches
4. **Schema First**: Always define accurate schemas - transforms must produce valid output

## Implementation Notes

- References are resolved recursively for nested data structures
- File references require authentication tokens for content access
- The dependency graph prevents circular dependencies
- Missing optional references resolve to `null` rather than causing errors
- Transform functions execute with the mapping functions defined in the system
- Variables are resolved first, then merged with original context before transforms execute
- Transform results directly modify the arguments or response objects
- Schema validation occurs after transforms are applied to ensure compliance