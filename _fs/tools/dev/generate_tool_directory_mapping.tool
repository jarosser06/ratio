{
  "description": "Efficiently analyzes available tools using built-in file listing and generates a structured capability map",
  "arguments": [
    {
      "name": "tools_directory",
      "type_name": "file",
      "description": "Directory containing tool definitions to analyze",
      "default_value": "/tools/core",
      "required": false
    },
    {
      "name": "mapping_file_name",
      "type_name": "string",
      "description": "The file name to save the map as",
      "required": false,
      "default_value": "tools_map.md"
    }
  ],
  "instructions": [
    {
      "execution_id": "scan_tool_files",
      "tool_definition_path": "/tools/core/list_directory.tool",
      "arguments": {
        "directory_path": "REF:arguments.tools_directory"
      },
      "transform_results": {
        "variables": {
          "all_files": "REF:response.files",
        },
        "transforms": {
          "tool_files": "pipeline(all_files, [filter(array=current, condition_string=\"item.file_path contains '.tool'\"), map(array=current, template=\"item.file_path\")])",
          "file_count": "REF:response.files.length"
        }
      }
    },
    {
      "execution_id": "analyze_each_tool",
      "tool_definition_path": "/tools/dev/file_analyzer.tool",
      "parallel_execution": {
        "iterate_over": "REF:scan_tool_files.tool_files",
        "child_argument_name": "file_to_analyze"
      },
      "arguments": {
        "analysis_prompt": "Analyze the following tool definition and provide a clear explanation of:\n\n1. What this tool does (brief description)\n2. What arguments it accepts (name, type, required/optional, purpose)\n3. What responses it returns (name, type, description)\n4. Key capabilities this tool provides\n\nKeep the response concise and well-structured.\n\ntool Definition:",
        "model_id": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "max_tokens": 1500,
        "temperature": 0.1
      }
    },
    {
      "execution_id": "combine_all_analyses",
      "tool_definition_path": "/tools/core/combine_content.tool",
      "arguments": {
        "separator": "\n\n---\n\n"
      },
      "transform_arguments": {
        "variables": {
          "directory": "REF:arguments.tools_directory",
          "file_name": "REF:arguments.mapping_file_name",
          "parallel_results": "REF:analyze_each_tool.response",
          "separator": "/"
        },
        "transforms": {
          "content_list": "map(array=parallel_results, template=\"item.analysis_result\")",
          "output_file_type": "ratio::markdown",
          "output_file_path": "join(array=[directory, file_name], separator=separator)" 
        }
      }
    }
  ],
  "responses": [
    {
      "name": "combined_analysis",
      "type_name": "string",
      "description": "All tool analyses combined into a single string",
      "required": true
    },
    {
      "name": "tool_count",
      "type_name": "number",
      "description": "Number of tools analyzed",
      "required": true
    },
    {
      "name": "tool_files",
      "type_name": "list",
      "description": "The tool files analyzed",
      "required": true
    },
    {
      "name": "files_processed",
      "type_name": "number",
      "description": "Number of analysis files successfully combined",
      "required": true
    }
  ],
  "response_reference_map": {
    "tool_count": "REF:analyze_each_tool.response.length",
    "tool_files": "REF:scan_tool_files.tool_files",
    "combined_analysis": "REF:combine_all_analyses.combined_content",
    "files_processed": "REF:combine_all_analyses.items_processed"
  }
}