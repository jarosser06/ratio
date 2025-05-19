# Ratio REF System Documentation

## Overview

The Ratio REF (Reference) system enables dynamic value resolution and dependency management in agent execution workflows. REF strings allow agents to reference values from previous executions or input arguments, creating a flexible and powerful data flow mechanism.

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

## Error Handling

### Invalid Reference Errors

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

## Advanced Usage Patterns

### Conditional Execution

References can be used in execution conditions:

```json
{
  "execution_id": "cleanup_processor",
  "conditions": [
    {
      "operator": "equals",
      "param": "REF:data_validator.is_valid",
      "value": true
    }
  ]
}
```

### Response Mapping

References are commonly used in response reference maps:

```json
{
  "response_reference_map": {
    "final_result": "REF:data_processor.processed_data",
    "metadata": "REF:file_analyzer.metadata",
    "status": "REF:validator.status"
  }
}
```

### Complex Transformations

References can participate in object mapping operations:

```json
{
  "object_map": {
    "user_info.name": "REF:profile_processor.user.name",
    "user_info.files": "REF:file_scanner.documents",
    "summary.total_files": "REF:file_scanner.documents.length"
  }
}
```

## Best Practices

1. **Clear Naming**: Use descriptive execution IDs and response keys
2. **Type Safety**: Understand the expected types when using attributes
3. **Error Handling**: Consider default values for optional references
4. **Performance**: Minimize deep nesting in complex workflows
5. **Documentation**: Document complex reference chains in agent definitions

## Implementation Notes

- References are resolved recursively for nested data structures
- File references require authentication tokens for content access
- The dependency graph prevents circular dependencies
- Missing optional references resolve to `null` rather than causing errors
- All reference resolutions are cached during execution for performance