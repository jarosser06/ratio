# System Requirements for Ratio

This document outlines the minimum system requirements for deploying and developing Ratio.

## Development Environment Requirements

### Required Software

- **Python 3.12+**: Ratio requires Python 3.12 as specified in the pyproject.toml
- **Docker** or compatible container runtime: Required for building and running the container images used by Ratio's Lambda functions
- **AWS CDK**: Used for infrastructure deployment and management
- **Poetry**: Used for Python dependency management as indicated in the project files
- **Git**: Required for version control and source management

### Hardware Requirements

- Standard development machine with sufficient resources to run Docker containers and Python development tools
- Sufficient disk space for development dependencies, code, and Docker images

### Network Requirements

- Internet connection for AWS service access and dependency downloads
- Access to GitHub repositories for dependency retrieval

## AWS Account Requirements

### Required Permissions

Administrative access to create and manage the following AWS services:

- **AWS Lambda**: Used for running the API, Agent Manager, and Storage Manager services
- **Amazon DynamoDB**: Used for storing metadata about entities, groups, files, and file versions
- **Amazon S3**: Used for storing file content with versioning enabled
- **AWS KMS**: Used for JWT signing and verification
- **Amazon API Gateway**: Used for exposing the API endpoints
- **AWS IAM**: Used for service roles and policies
- **Amazon EventBridge**: Used for the event-driven architecture

### Service Components

Based on the CDK code, Ratio deploys:

- DynamoDB tables:
  - entities
  - groups
  - files
  - file_versions
  - file_types
  - file_lineage
  - processes

- S3 buckets:
  - A versioned bucket for raw file storage

- Lambda functions:
  - API service
  - Storage Manager service
  - Agent Manager service