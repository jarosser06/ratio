Object Mapper Agent
===================

Overview
---------
The Object Mapper agent transforms data structures according to mapping rules defined in dot notation format. It handles direct path references and basic transformation functions.

Functionality
-------------
- Maps data from a source object to a target structure using path references
- Supports three built-in transformation functions: map, sum, and join
- Validates output against a response schema

Mapping Rules
-------------
Mapping rules use the format: "output.path": "input.path"

Example:
```json
{
  "customer_info.name": "order.customer.name",
  "order_items": "map(order.items, {name: item.name, quantity: item.quantity})",
  "total_quantity": "sum(order.items, item.quantity)",
  "item_list": "join(map(order.items, item.name), ', ')"
}
```

Transformation Functions
------------------------
map(array, template) - Transforms array items using a template
```
"items": "map(source.items, {name: item.name, count: item.quantity})"
```

sum(array, item_path) - Calculates sum of values in an array
```
"total": "sum(source.items, item.quantity)"
```

join(array, separator) - Combines array elements into a string
```
"names": "join(map(source.users, item.name), ', ')"
```

**NOTE**: NESTED TRANSFORM FUNCTIONS ARE NOT SUPPORTED!!

Agent Definition
----------------
```json
{
  "arguments": [
    {
      "name": "original_object",
      "type_name": "object",
      "description": "Source object to transform",
      "required": true
    },
    {
      "name": "object_map",
      "type_name": "object",
      "description": "Mapping configuration",
      "required": true
    }
  ],
  "description": "Transforms objects based on mapping rules",
  "responses": [
    {
      "name": "response_name_1",
      "type_name": "object",
      "description": "First transformed output",
      "required": true
    },
    {
      "name": "response_name_2",
      "type_name": "string",
      "description": "Second transformed output",
      "required": false
    }
  ],
  "system_event_endpoint": "ratio::agent::object_mapper::execution"
}
```

Response Structure
------------------
- Response objects are defined by the agent's schema
- Each top-level key in the object_map must match a response name
- The object mapper validates that output matches type requirements
- For type 'object', nested structures are created from dot notation paths

Usage Example
--------------
```json
// Input object
{
  "product": {
    "id": "12345",
    "name": "Widget",
    "variants": [
      {"color": "red", "stock": 5},
      {"color": "blue", "stock": 10}
    ]
  }
}

// Object map
{
  "product_info.id": "product.id",
  "product_info.name": "product.name",
  "available_colors": "join(map(product.variants, item.color), ', ')",
  "total_stock": "sum(product.variants, item.stock)"
}

// Result
{
  "product_info": {
    "id": "12345",
    "name": "Widget"
  },
  "available_colors": "red, blue",
  "total_stock": 15
}
```