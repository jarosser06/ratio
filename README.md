Ratio
=====
An AI Operating System built on Cloud Native AWS Technologies.

Ratio is named after the Golden Ratio, representing the ideal balance between AI capabilities and engineering infrastructure.
The system is designed to enable AI expansion within the confines of thoughtful, robust engineering - ensuring that as AI
capabilities grow, they do so within a secure, manageable framework.

To get started check out the [Getting Started Guide](GETTING_STARTED.md)

For further reading about the system internals, check out the [introduction](docs/INTRODUCTION.md)


The Intent
----------
When designing and building Ratio, the intent was to build a system while keeping the following aspects into account:

### Authentication & Authorization at Scale
- Entity-based (not just user-based) authentication system, most interactions with the system are likely not direct
user interactions
- Permissions model needed to support both data access as well as compute.
- Identity verification is important when "agents" working across a more distributed system.
- Any "entity" representing the system itself should still be held to the same restrictions as all other entities. Only the
administrative entities should have complete control, and that level of access should not be granted to the system.

### Unified Resource Model
- Everything is a file and lives in a versioned filesystem
- Files and agents share the same management interface since agent definitions are files in the system

### Composability & Reusability
- Agents can be composed from other agents
- Resources can reference each other through paths

### Cloud-Native Operations
- Serverless-first design
- Be lazy and make deployment simple with CDK

### Thoughtful Control Plane
- Administrative oversight capabilities
- Metadata and lineage tracking built in
- Permission boundaries


Development
-----------

Ratio is built on the Da Vinci framework and follows Da Vinci patterns for deployment, service structure, and resource management.
Prerequisites

- Python 3.12+
- AWS account with appropriate permissions
- AWS CDK
- Poetry for dependency management

License
-------
Apache 2.0