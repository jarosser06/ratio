{
  "description": "Analyzes tool development requests for feasibility and generates the tool if feasible. Uses pessimistic analysis to ensure requests are achievable with available capabilities in 5-7 steps.",
  "arguments": [
    {
      "name": "request",
      "type_name": "string",
      "description": "The tool development request to analyze",
      "required": true
    },
    {
      "name": "tool_directory_mapping",
      "type_name": "string",
      "description": "The tool capability mapping from generate_tool_directory_mapping",
      "required": true
    },
    {
      "name": "tool_name",
      "type_name": "string", 
      "description": "Name for the new tool (without .tool extension)",
      "required": true
    },
    {
      "name": "output_directory",
      "type_name": "string",
      "description": "Directory where the tool should be saved",
      "required": true
    },
    {
      "name": "authoring_manual",
      "type_name": "file",
      "description": "The tool authoring manual with best practices",
      "required": true
    }
  ],
  "instructions": [
    {
      "execution_id": "feasibility_analysis",
      "tool_definition_path": "/tools/core/bedrock_text.tool",
      "transform_arguments": {
        "variables": {
          "prompt_sections": [
            "tool FEASIBILITY ANALYSIS",
            "",
            "User Request:",
            "REF:arguments.request",
            "",
            "Available tool Capabilities:",
            "REF:arguments.tool_directory_mapping",
            "",
            "Authoring Manual:",
            "REF:arguments.authoring_manual",
            "",
            "Analyze this request pessimistically. Only mark as feasible if you can see a clear 5-7 step implementation path using existing tools. Missing capabilities or overly complex workflows should be marked not feasible.",
            "",
            "Respond with exactly this format:",
            "FEASIBILITY: [FEASIBLE or NOT_FEASIBLE]",
            "REASONING: [Your analysis]",
            "SUGGESTED_APPROACH: [Implementation steps if feasible, or missing capabilities if not]"
          ]
        },
        "transforms": {
          "prompt": "join(array=prompt_sections, separator=\"\\n\")"
        }
      },
      "arguments": {
        "model_id": "anthropic.claude-sonnet-4-20250514-v1:0",
        "max_tokens": 2000,
        "temperature": 0.1
      }
    },
    {
      "execution_id": "generate_creation_prompt",
      "tool_definition_path": "/tools/core/bedrock_text.tool",
      "conditions": [
        {"param": "REF:feasibility_analysis.response", "operator": "contains", "value": "FEASIBILITY: FEASIBLE"}
      ],
      "transform_arguments": {
        "variables": {
          "prompt_sections": [
            "tool DEFINITION GENERATION",
            "",
            "Original Request:",
            "REF:arguments.request",
            "",
            "Available tools:",
            "REF:arguments.tool_directory_mapping",
            "",
            "Authoring Manual:",
            "REF:arguments.authoring_manual",
            "",
            "Feasibility Analysis:",
            "REF:feasibility_analysis.response",
            "",
            "Generate a complete JSON tool definition that fulfills the request. Follow the patterns in the authoring manual exactly. Use proper REF strings, dependencies, and conditional logic as needed. Output only valid JSON."
          ]
        },
        "transforms": {
          "prompt": "join(array=prompt_sections, separator=\"\\n\")"
        }
      },
      "arguments": {
        "model_id": "anthropic.claude-sonnet-4-20250514-v1:0",
        "max_tokens": 4000,
        "temperature": 0.1
      }
    },
    {
      "execution_id": "validate_generated_tool",
      "tool_definition_path": "/tools/core/bedrock_text.tool", 
      "conditions": [
        {"param": "REF:feasibility_analysis.response", "operator": "contains", "value": "FEASIBILITY: FEASIBLE"}
      ],
      "transform_arguments": {
        "variables": {
          "prompt_sections": [
            "tool DEFINITION VALIDATION",
            "",
            "Generated tool Definition:",
            "REF:generate_creation_prompt.response",
            "",
            "Authoring Manual:",
            "REF:arguments.authoring_manual",
            "",
            "Validate this tool definition against the authoring manual. Check for:",
            "- Proper JSON structure",
            "- Correct REF usage",
            "- Appropriate dependencies",
            "- Following composition patterns",
            "- Schema compliance",
            "",
            "Respond with exactly:",
            "VALIDATION: [PASS or FAIL]",
            "ISSUES: [List any problems found]",
            "FINAL_tool: [The corrected tool definition if needed, otherwise repeat the original]"
          ]
        },
        "transforms": {
          "prompt": "join(array=prompt_sections, separator=\"\\n\")"
        }
      },
      "arguments": {
        "model_id": "anthropic.claude-3-5-sonnet-20241022-v1:0",
        "max_tokens": 4000,
        "temperature": 0.1
      }
    },
    {
      "execution_id": "save_tool_file",
      "tool_definition_path": "/tools/core/put_file.tool",
      "conditions": [
        {"param": "REF:feasibility_analysis.response", "operator": "contains", "value": "FEASIBILITY: FEASIBLE"},
        {"param": "REF:validate_generated_tool.response", "operator": "contains", "value": "VALIDATION: PASS"}
      ],
      "transform_arguments": {
        "variables": {
          "path_components": [
            "REF:arguments.output_directory",
            "/",
            "REF:arguments.tool_name",
            ".tool"
          ]
        },
        "transforms": {
          "file_path": "join(array=path_components, separator=\"\")"
        }
      },
      "arguments": {
        "file_type": "ratio::tool_definition",
        "data": "REF:generate_creation_prompt.response"
      }
    }
  ],
  "responses": [
    {
      "name": "feasibility_result",
      "type_name": "string",
      "description": "The feasibility analysis result",
      "required": true
    },
    {
      "name": "tool_file_path",
      "type_name": "string",
      "description": "Path to the created tool file (null if not created)",
      "required": false
    },
    {
      "name": "validation_result",
      "type_name": "string",
      "description": "Validation result for the generated tool (null if not feasible)",
      "required": false
    }
  ],
  "response_reference_map": {
    "feasibility_result": "REF:feasibility_analysis.response",
    "tool_file_path": "REF:save_tool_file.file_path",
    "validation_result": "REF:validate_generated_tool.response"
  }
}