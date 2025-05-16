# Agent Definition Overview

## Agent Definition Schema

An agent definition file is a JSON configuration that defines how an agent operates, including its inputs, outputs, and execution instructions. The schema includes:

### Core Components

1. **argument_definitions**: An list of input parameters the agent accepts.
   - Each argument includes type, name, description, and required flag.
   - Supported types include "string", "integer", "file", "object", and "list".

2. **description**: A string describing the agent's purpose and functionality.

3. **instructions** OR **system_event_endpoint**: 
   - **instructions**: List of sub-agent execution steps (used for composite agents)
   - **system_event_endpoint**: String endpoint for Lambda-based agents (used for standalone agents)

4. **response_definitions**: List of output parameters the agent produces.
   - Each response includes type, name, description, and required flag.

## Agent Instruction Schema

Each instruction within a composite agent follows the AgentInstructionSchema:

1. **agent_definition_path**: String path to the sub-agent definition file.
   - Format: "/agents/agent_name.agent"
   - Must be provided if agent_definition is not.

2. **agent_definition**: Object containing inline agent definition.
   - Must be provided if agent_definition_path is not.

3. **execution_id**: Unique identifier for the execution instance.
   - Used for REF references between agents.
   - Format: Must match regex ^[a-zA-Z0-9_\\-]+$

4. **arguments**: Object mapping argument names to values.
   - Optional if all sub-agent arguments have defaults.

## The REF System

The REF system allows dynamic references to pass data between agents and access context information during execution. This enables building complex agent pipelines where outputs from earlier steps feed into later steps.

### Usage

When using the REF system in agent definitions, the references are processed into proper JSON values at execution time. The REF string itself is not passed as a literal to the agent but is replaced with the actual value it references.
For example, if you have an instruction like:

```json
{
  "agent_definition_path": "/agents/process_data.agent",
  "execution_id": "process-step",
  "arguments": {
    "input_data": "REF:previous-step.response.raw_data",
    "config": "REF:arguments.config_file"
  }
}
```
At execution time, these references would be resolved to their actual values:

If previous-step.response.raw_data contained {"results": [1, 2, 3]}, then input_data would receive that JSON object, not the REF string
If arguments.config_file contained the text of a configuration file, then config would receive that content

This allows for seamless data passing between agents without requiring explicit parsing or string manipulation by the agents themselves. The system handles the reference resolution transparently, ensuring that each agent receives properly formatted inputs according to its argument definitions.

### REF Syntax and Contexts

1. **Agent Arguments**:
   - `REF:arguments.<argument_name>` - References a basic argument value

   - For file arguments:
     - `REF:arguments.<file_argument_name>` - The file content (default)
     - `REF:arguments.<file_argument_name>.file_name` - Just the file name
     - `REF:arguments.<file_argument_name>.file_path` - Directory path
     - `REF:arguments.<file_argument_name>.full_path` - Complete path with filename
     - `REF:arguments.<file_argument_name>.added_on` - ISO timestamp of file addition
     - `REF:arguments.<file_argument_name>.owner` - File owner
     - `REF:arguments.<file_argument_name>.group` - Owner group
     - `REF:arguments.<file_argument_name>.metadata` - Additional file metadata

2. **Agent Responses**:
   - `REF:<execution_id>.response.<response_key>` - References output from a previous agent

3. **List Operations**:
   - `REF:arguments.<list_argument>.first` - First item in list
   - `REF:arguments.<list_argument>.last` - Last item in list
   - `REF:arguments.<list_argument>.<idx>` - Item at specific index

### Execution Model

The system follows a dependency-based execution model:

1. The system analyzes all instructions and their REF dependencies.
2. Instructions are scheduled for execution when all their dependencies (referenced values) are available.
3. When an agent completes, the system re-evaluates remaining instructions to see if any new ones can now run.
4. This continues until all instructions have been executed or a failure occurs.

This model allows for efficient execution of complex agent workflows, where some steps can execute in parallel if they don't depend on each other, while maintaining proper sequencing where dependencies exist.

### Example Use Cases

1. **Data Processing Pipeline**: 
   - First agent retrieves data
   - Second agent validates and transforms it
   - Third agent analyzes results

2. **File Operations**:
   - Process multiple files in sequence
   - Extract metadata from files
   - Transform file contents

3. **Composite Analysis**:
   - Gather information from multiple sources
   - Combine and process the information
   - Generate comprehensive outputs

This agent system architecture enables building sophisticated workflows by composing simpler agents, with the REF system providing the glue that connects them together.