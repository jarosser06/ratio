# Built In File Types

## ratio::root

Root filesystem directory type. The base of the entire file system hierarchy. Files created with this type
are flagged as directories and cannot be linked to content or file versions directly.

## ratio::directory

Standard directory file type. Files created with this type are flagged as directories and cannot be linked to
content or file versions directly.

## ratio::file

Standard generic file type to store data in the system

## ratio::agent

File type for agent definitions that define agents that operate within the system

- Name must end with .agent extension
- Name only allows alphanumeric characters, underscores, and hyphens

## ratio::agent_response

- Name must end with .agent_response extension
- Name only allows alphanumeric characters, underscores, and hyphens