# Condition Evaluator Documentation

## Overview

The Condition Evaluator system provides a flexible mechanism for evaluating conditions based on reference values. It supports both
simple conditions and complex nested condition groups with different logical operators.

## Condition Format

### Single Condition

A single condition is represented as a dictionary with the following structure:

```json
{
  "param": "<parameter_value>",
  "operator": "<comparison_operator>",
  "value": "<expected_value>"
}
```

- **param**: The actual value to compare, can be a direct value or a REF string
- **operator**: The comparison operator to apply
- **value**: The expected value to compare against (optional for some operators)

### Condition List

A condition list is an array of individual conditions or condition groups:

```json
[
  {
    "param": "user.age",
    "operator": "greater_than",
    "value": 18
  },
  {
    "param": "user.country",
    "operator": "equals",
    "value": "US"
  }
]
```

By default, conditions in a list are combined with AND logic.

### Condition Group

A condition group allows for nested conditions with explicit logic operators:

```json
{
  "logic": "OR",
  "conditions": [
    {
      "param": "user.subscription",
      "operator": "equals",
      "value": "premium"
    },
    {
      "param": "user.is_admin",
      "operator": "equals",
      "value": true
    }
  ]
}
```

## Supported Operators

The Condition Evaluator supports the following comparison operators:

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Checks if values are equal | `{"param": "user.role", "operator": "equals", "value": "admin"}` |
| `not_equals` | Checks if values are not equal | `{"param": "user.status", "operator": "not_equals", "value": "inactive"}` |
| `exists` | Checks if value is not null | `{"param": "user.email", "operator": "exists"}` |
| `not_exists` | Checks if value is null | `{"param": "user.deleted_at", "operator": "not_exists"}` |
| `greater_than` | Checks if value is greater than expected | `{"param": "user.age", "operator": "greater_than", "value": 18}` |
| `less_than` | Checks if value is less than expected | `{"param": "item.quantity", "operator": "less_than", "value": 10}` |
| `greater_than_or_equal` | Checks if value is greater than or equal to expected | `{"param": "user.level", "operator": "greater_than_or_equal", "value": 5}` |
| `less_than_or_equal` | Checks if value is less than or equal to expected | `{"param": "product.price", "operator": "less_than_or_equal", "value": 99.99}` |
| `contains` | Checks if value contains expected substring/item | `{"param": "user.permissions", "operator": "contains", "value": "delete"}` |
| `not_contains` | Checks if value does not contain expected substring/item | `{"param": "text.content", "operator": "not_contains", "value": "prohibited"}` |
| `in` | Checks if value is in expected collection | `{"param": "user.country", "operator": "in", "value": ["US", "CA", "UK"]}` |
| `not_in` | Checks if value is not in expected collection | `{"param": "user.status", "operator": "not_in", "value": ["banned", "suspended"]}` |
| `starts_with` | Checks if string value starts with expected prefix | `{"param": "file.name", "operator": "starts_with", "value": "invoice_"}` |
| `ends_with` | Checks if string value ends with expected suffix | `{"param": "file.extension", "operator": "ends_with", "value": ".pdf"}` |

## Reference Resolution

The Condition Evaluator supports dynamic value resolution using the REF system. When a parameter starts with `REF:`, the actual value is resolved using the Reference object:

```json
{
  "param": "REF:user_data.profile.age",
  "operator": "greater_than",
  "value": 18
}
```

See the REF System Documentation for complete details on reference resolution.

## Logic Operators

Condition groups support two logic operators:

- **AND**: All conditions must evaluate to true (default)
- **OR**: At least one condition must evaluate to true

## Examples

### Simple Condition List (AND Logic)

```json
[
  {"param": "user.is_active", "operator": "equals", "value": true},
  {"param": "user.age", "operator": "greater_than", "value": 18}
]
```

Evaluates to true if the user is active AND the user's age is greater than 18.

### Condition Group with OR Logic

```json
[
  {
    "logic": "OR",
    "conditions": [
      {"param": "user.subscription", "operator": "equals", "value": "premium"},
      {"param": "user.is_admin", "operator": "equals", "value": true}
    ]
  }
]
```

Evaluates to true if the user has a premium subscription OR is an admin.

### Complex Nested Conditions

```json
[
  {"param": "user.is_active", "operator": "equals", "value": true},
  {
    "logic": "OR",
    "conditions": [
      {"param": "user.age", "operator": "greater_than", "value": 21},
      {
        "logic": "AND",
        "conditions": [
          {"param": "user.age", "operator": "greater_than", "value": 18},
          {"param": "user.has_parental_consent", "operator": "equals", "value": true}
        ]
      }
    ]
  }
]
```

Evaluates to true if:
- The user is active AND
- Either:
  - The user's age is greater than 21, OR
  - The user's age is greater than 18 AND has parental consent

### Using Reference Resolution

```json
[
  {"param": "REF:current_context.customer_id", "operator": "exists"},
  {"param": "REF:user_profile.access_level", "operator": "greater_than_or_equal", "value": 3}
]
```

Evaluates to true if the customer ID exists in the current context AND the user's access level is greater than or equal to 3.

## Error Handling

The Condition Evaluator handles errors in the following ways:

- If a parameter resolution fails, the condition evaluates to false
- If an unknown operator is encountered, an error is raised
- If a condition is malformed (missing required fields), the evaluation fails and returns false

## Best Practices

1. **Clear Structure**: Organize complex conditions using nested groups
2. **Consistent Parameters**: Use consistent parameter formats across conditions
3. **Error Handling**: Account for potential null values in parameters
4. **Reference Use**: Leverage REF strings for dynamic value resolution
5. **Logic Grouping**: Use explicit logic operators for clarity in complex conditions