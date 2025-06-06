{
  "description": "Mathematical processor that evaluates formulas with custom functions and handles element-wise operations on arrays",
  "arguments": [
    {
      "name": "formula",
      "type_name": "string",
      "description": "Mathematical formula to evaluate",
      "required": true
    },
    {
      "name": "values",
      "type_name": "object",
      "description": "Dictionary of variable names and their values",
      "required": true
    },
    {
      "name": "function_definitions",
      "type_name": "object",
      "description": "Custom function definitions",
      "required": false,
      "default_value": {}
    },
    {
      "name": "result_file_path",
      "type_name": "string",
      "description": "Path where result should be saved",
      "required": false
    }
  ],
  "responses": [
    {
      "name": "result",
      "type_name": "any",
      "description": "The calculated result",
      "required": true
    },
    {
      "name": "result_file_path",
      "type_name": "file",
      "description": "Path to file containing calculation results",
      "required": true
    },
    {
      "name": "formula_used",
      "type_name": "string",
      "description": "The formula that was evaluated",
      "required": true
    },
    {
      "name": "functions_available",
      "type_name": "number",
      "description": "Number of functions available",
      "required": true
    }
  ],
  "system_event_endpoint": "ratio::tool::math::execution"
}