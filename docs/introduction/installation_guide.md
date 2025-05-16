# Ratio Installation Guide

This guide will walk you through the process of installing and configuring Ratio, the AI Operating System built on Cloud Native AWS Technologies.

## Prerequisites

Before installing Ratio, ensure your system meets the following requirements:

- **Python 3.12+**: Ratio is built using Python 3.12 and requires this version or newer
- **Docker** or compatible container runtime: Required for building and running the containerized components
- **AWS Account**: With permissions to create and manage the required AWS resources
- **AWS CDK**: For infrastructure deployment and management
- **Poetry**: For Python dependency management

## Installation Steps

### 1. Clone the Repository

First, clone the Ratio repository to your local machine:

```bash
git clone https://github.com/jarosser06/ratio.git

cd ratio
```

### 2. Install Dependencies

Use Poetry to install the required dependencies:

```bash
poetry install
```

This will create a virtual environment and install all dependencies defined in the `pyproject.toml` file.

### 3. AWS Configuration

Ensure your AWS CLI is properly configured with credentials that have sufficient permissions:

```bash
aws configure
```

You will need to provide:
- AWS Access Key ID
- AWS Secret Access Key
- Default region name
- Default output format (optional)

### 4. Deploy Ratio

Deploy all components of Ratio using the provided Makefile:

```bash
make deploy
```

This will use AWS CDK to create all the necessary resources in your AWS account, including:
- DynamoDB tables for metadata storage
- S3 buckets for file storage
- Lambda functions for the API, Storage Manager, and Agent Manager
- API Gateway endpoints
- IAM roles and policies
- KMS key for JWT signing

If you prefer to deploy specific components individually, you can use:

```bash
# Deploy only the API stack
make deploy_api

# Deploy only the Storage Manager stack
make deploy_storage
```

## System Initialization

After deploying Ratio, you need to initialize the system by creating the admin entity:

1. Generate an RSA key pair for the admin entity
2. Use the Ratio client to send an initialization request
3. Create additional entities and groups as needed

Detailed instructions for system initialization are available in the [Getting Started](../introduction/quick-start-example.md) guide.

## Troubleshooting

### Common Issues

- **Deployment Failures**: Ensure your AWS account has sufficient permissions and service quotas
- **Dependency Issues**: Verify that you're using Python 3.12+ and have installed all dependencies with Poetry
- **Environment Configuration**: Check that all required environment variables are set correctly

If you encounter any issues during installation, refer to the [Troubleshooting](../operations/troubleshooting.md) guide or open an issue in the GitHub repository.

## Next Steps

After successfully installing Ratio, continue to the [Quick Start Example](../introduction/quick-start-example.md) to learn how to use the system for basic operations.