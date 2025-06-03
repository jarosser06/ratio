# Ratio Tutorial

Three examples using only core tools to help get you started.

## Setup

```bash
mkdir ratio-tutorial

cd ratio-tutorial
```

## Example 1: Hello World

**Goal**: Execute a single tool and get text back.

```bash
# Set up output directory
rto mkdir /output

# Just generate some text
rto execute \
  --tool-definition-path=/tools/core/bedrock_text.tool \
  --arguments='{
    "prompt": "Write a simple hello world message for a new developer learning Ratio tools.",
    "model_id": "anthropic.claude-3-5-haiku-20241022-v1:0",
    "max_tokens": 100,
    "result_file_path": "/output/hello.txt"
  }' \
  --wait

# View the result
rto cat ratio:/output/hello.txt
```

That's it. One tool, text in, text out.

## Example 2: File Processing

**Goal**: Load a file, send it to an LLM, get analysis back.

### Create a sample file:

```bash
cat > sample-data.txt << 'EOF'
Product: Analytics Dashboard
Q4 Revenue: $1.2M
Customers: 150
Growth Rate: 25%
Main Issue: Customer complaints about slow loading times
EOF

rto mkdir /data

# Upload it
rto sync -f sample-data.txt ratio:/data/
```

### Create a simple file analysis tool:

```bash
cat > file-analyzer.tool << 'EOF'
{
  "description": "Load a file and analyze it",
  "arguments": [
    {
      "name": "file_to_analyze",
      "type_name": "file",
      "description": "File to analyze",
      "required": true
    },
    {
      "name": "question",
      "type_name": "string",
      "description": "What to ask about the file",
      "required": true
    }
  ],
  "instructions": [
    {
      "execution_id": "analyze_file",
      "tool_definition_path": "/tools/core/bedrock_text.tool",
      "arguments": {
        "prompt": "REF:arguments.question",
        "model_id": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "max_tokens": 500
      },
      "transform_arguments": {
        "variables": {
          "question": "REF:arguments.question",
          "file_content": "REF:arguments.file_to_analyze",
          "separator": ""
        },
        "transforms": {
          "prompt": "join(array=[question, \"\\n\\nFile content:\\n\", file_content], separator=separator)"
        }
      }
    }
  ],
  "responses": [
    {
      "name": "analysis",
      "type_name": "string",
      "description": "The analysis result",
      "required": true
    }
  ],
  "response_reference_map": {
    "analysis": "REF:analyze_file.response"
  }
}
EOF

rto mkdir /tools/custom

# Upload and run it
rto sync -f file-analyzer.tool ratio:/tools/custom/

rto chmod 755 /tools/custom/file-analyzer.tool

rto execute \
  --tool-definition-path=/tools/custom/file-analyzer.tool \
  --arguments='{
    "file_to_analyze": "/data/sample-data.txt",
    "question": "What are the top 3 priorities this company should focus on?"
  }' \
  --wait
```

Once the process completes, run `rto cat` with the reported response.aio to show what the tool's response values look like.

Example:
```bash
rto cat /run/tool_exec-3db8410e-2ee6-4ae5-9f47-daf566526231/response.aio
```

## Example 3: Multi-File Report

**Goal**: Process multiple files and create a formatted report.

### Create multiple data files:

```bash
cat > metrics.txt << 'EOF'
Revenue: $1.2M
Customers: 150  
Growth: 25%
Churn: 5%
EOF

cat > feedback.txt << 'EOF'
"Loading times are too slow" - Customer A
"Love the new dashboard features" - Customer B  
"Need better mobile support" - Customer C
"Excellent customer service" - Customer D
EOF

cat > roadmap.txt << 'EOF'
Q1 2025: Performance improvements
Q2 2025: Mobile app launch
Q3 2025: Advanced analytics features
Q4 2025: API platform expansion
EOF

# Upload all files
rto sync -f -r *.txt ratio:/data/
```

### Create a report generator:

```bash
cat > report-generator.tool << 'EOF'
{
  "description": "Generate a summary report from multiple data files",
  "arguments": [
    {
      "name": "report_title",
      "type_name": "string", 
      "description": "Title for the report",
      "required": true
    }
  ],
  "instructions": [
    {
      "execution_id": "combine_data",
      "tool_definition_path": "/tools/core/combine_content.tool",
      "arguments": {
        "file_paths": ["/data/metrics.txt", "/data/feedback.txt", "/data/roadmap.txt"],
        "separator": "\n\n--- SECTION ---\n\n"
      }
    },
    {
      "execution_id": "create_report",
      "tool_definition_path": "/tools/core/bedrock_text.tool",
      "arguments": {
        "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "max_tokens": 1000,
        "temperature": 0.2
      },
      "transform_arguments": {
        "variables": {
          "title": "REF:arguments.report_title",
          "data": "REF:combine_data.combined_content",
          "instruction": "Create a business summary report with the title:",
          "format_request": "Use this data to write a brief executive summary with key metrics, customer feedback themes, and roadmap highlights:"
        },
        "transforms": {
          "prompt": "join(array=[instruction, title, \"\\n\\n\", format_request, \"\\n\\n\", data], separator=\"\")"
        }
      }
    },
    {
      "execution_id": "format_final_report",
      "tool_definition_path": "/tools/core/render_template.tool",
      "arguments": {
        "template": "# {{title}}\\n\\nGenerated: {{date}}\\n\\n{{content}}\\n\\n---\\n*Report generated automatically*",
        "variables": {
          "title": "REF:arguments.report_title",
          "date": "December 2024",
          "content": "REF:create_report.response"
        }
      }
    },
    {
      "execution_id": "save_report",
      "tool_definition_path": "/tools/core/put_file.tool",
      "arguments": {
        "file_path": "/output/summary-report.md",
        "file_type": "ratio::markdown",
        "data": "REF:format_final_report.rendered_string"
      }
    }
  ],
  "responses": [
    {
      "name": "report_content",
      "type_name": "string",
      "description": "The generated report content",
      "required": true
    },
    {
      "name": "report_file",
      "type_name": "file",
      "description": "Path to the saved report file", 
      "required": true
    }
  ],
  "response_reference_map": {
    "report_content": "REF:format_final_report.rendered_string",
    "report_file": "REF:save_report.file_path"
  }
}
EOF

# Upload and run
rto sync -f report-generator.tool ratio:/tools/custom/

rto chmod 755 /tools/custom/report-generator.tool

rto execute \
  --tool-definition-path=/tools/custom/report-generator.tool \
  --arguments='{
    "report_title": "Q4 2024 Business Summary"
  }' \
  --wait

# Check the result
rto cat /output/summary-report.md
```