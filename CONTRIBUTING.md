Contributing to Ratio
=====================

Thank you for your interest in contributing to Ratio! This guide will help you get started with contributing to the AI Operating System built on AWS.

Getting Started
---------------

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your feature or fix
4. Set up your development environment (see Environment Setup below)
5. Make your changes
6. Run tests to ensure everything works
7. Submit a pull request

Environment Setup
------------------
To hack on Ratio, you must have a copy deployed. 

- Note about AWS account creation
- Note about how to deploy which should just be ```cdk deploy --all``` adding `--require-approval never` ensures no questions about permissions

### Local Environment

Before running any tests or making local client calls, you must set up your environment variables. You have two options:

**Option 1**: Source the dev.sh script
```bash
source dev.sh
```

**Option 2**: Manually set environment variables
```bash
export DA_VINCI_APP_NAME='ratio'
export DA_VINCI_DEPLOYMENT_ID='dev'
export DA_VINCI_RESOURCE_DISCOVERY_STORAGE='dynamodb'
```

These environment variables are required for:

- Running tests
- Making local client calls
- Proper interaction with the development infrastructure

Development Process
-------------------

### Branching

Always create a new branch for your work
Use descriptive branch names (e.g., feature/add-agent-scheduling, fix/storage-permissions-issue)
Keep your branches focused on a single feature or fix

### Pull Requests

- Submit PRs from your feature branch to the main repository's main branch
- Provide a clear description of the changes in your PR
- Reference any related issues
- Ensure all tests pass before submitting
- Be responsive to feedback and questions during the review process

Testing
-------

Ratio uses a test suite to ensure system reliability. Before submitting any PR:

Run all existing tests:
```bash
# Ensure environment variables are set first
source dev.sh

# Execute from root
pytest 
```

Add new tests for your changes:

- For new features: Add comprehensive test coverage
- For bug fixes: Add tests that reproduce the bug and verify the fix
- For API changes: Update integration tests accordingly


Test utilities:

- Use the EntityManager and test fixtures in conftest.py
- Follow the patterns established in existing test files
- Clean up test entities and resources after tests complete

Code Style Guidelines
---------------------

### Python Style

- Use double quotes (") for all strings
- Use single quotes (') only for nested strings within double-quoted strings
- Follow PEP 8 guidelines
- Use type hints
- Add docstrings to all public classes and functions
- Follow the patterns established in existing Ratio modules

### Ratio-Specific Guidelines

- Use the established request/response patterns for API endpoints
- Follow the permission model when implementing file operations
- Use the JWT authentication patterns for secured endpoints
- Implement proper error handling and logging
- Follow the established patterns for DynamoDB table clients

### Commit Messages

**IMPORTANT**: Squash your commits! Your PR should contain either:

- A single, well-crafted commit that encompasses all changes
- Multiple commits ONLY if they represent truly distinct, logical units of work

Before submitting your PR, use git rebase -i to squash your work-in-progress commits into meaningful commits.

### Commit Message Format

- Title Line: Concise description of the main change (aim for under 70 characters)
- Blank Line: Always include a blank line after the title
- Details (if needed): Use bullet points for multiple changes
- Use active voice ("Add" not "Added", "Fix" not "Fixed")
- Be specific and concise

#### Good Commit Message Examples:

Single change:

```
Add agent scheduling capability to task manager

Implement scheduling functionality that allows agents to be
scheduled for future execution. Includes cron-style scheduling
and one-time scheduled tasks.
```

Multiple related changes:

```
Fix file permission validation in storage manager

- Add proper octal permission parsing
- Validate entity group membership correctly
- Update tests to cover edge cases
- Fix issue where admin bypass wasn't working
```

Documentation
-------------

- Update the README.md if you're adding new features
- Add docstrings to all new functions and classes following the Ratio pattern
- Update any relevant examples in the codebase
- If you're adding new agents, include agent definition files
- If you're adding new CDK constructs, include example usage
- Update the API documentation for any new endpoints
- Document any new environment variables or configuration options


Agent Development
------------------

When contributing new agents:

- Create the agent definition file in the appropriate directory
- Include comprehensive argument definitions in the `.agent` file notation
- Add appropriate response schemas, if the agent returns anything
- Include example usage in the documentation
- Add tests for the agent functionality as able

Storage System
---------------

When working on the storage system:

- Maintain compatibility with the Unix-style permission model
- Ensure file versioning is properly handled
- Update lineage tracking where appropriate
- Test with different permission scenarios

Authentication System
---------------------

When modifying authentication:

- Maintain backward compatibility
- Ensure JWT tokens are properly validated
- Test with different entity types and permissions
- Update the API client if needed
- DO NOT ISSUE TOKENS OUTSIDE OF THE AUTH API AND SCHEDULER IMPERSONATION

Questions?
-----------
If you have any questions about contributing, feel free to:

- Open an issue for discussion
- Ask in your pull request
- Reach out to the maintainers

**Thank you for supporting Ratio Development!!**