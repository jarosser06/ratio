import uuid

import boto3

from botocore.exceptions import ClientError

from da_vinci.core.execution_environment import load_runtime_environment_variables


class SSMSecretManager:
    def __init__(self):
        """
        Initialize the SSM Secret Manager
        """
        self.ssm_client = boto3.client("ssm")

        env_vars = load_runtime_environment_variables()

        app_name = env_vars["app_name"]

        deployment_id = env_vars["deployment_id"]

        self.prefix = f"/{app_name}/{deployment_id}/ratio/secrets"

    @staticmethod
    def create_secret_string(secret_id: str) -> str:
        """
        Create a secret string from the secret ID

        Keyword arguments:
        secret_id -- The ID of the secret
        """
        return f"HIDDEN_SECRET:{secret_id}"

    def mask_secret(self, secret_value: str) -> str:
        """
        Store a secret in SSM and return a masked ID

        Keyword arguments:
        secret_value -- The secret value to store
        """
        # Generate secret ID
        secret_id = str(uuid.uuid4())

        param_path = f"{self.prefix}/{secret_id}"
        
        # Store in SSM with encryption
        self.ssm_client.put_parameter(
            Name=param_path,
            Value=secret_value,
            Type="SecureString",
            Overwrite=False
        )

        return self.create_secret_string(secret_id)

    def unmask_secret(self, secret_id: str) -> str:
        """
        Retrieve a secret from SSM using the masked ID

        Keyword arguments:
        secret_id -- The ID of the secret
        secret_str -- The masked secret string
        """
        if secret_id.startswith("HIDDEN_SECRET"):
            secret_id = secret_id.split(":")[1]

        param_path = f"{self.prefix}/{secret_id}"
        
        try:
            response = self.ssm_client.get_parameter(
                Name=param_path,
                WithDecryption=True
            )

            return response["Parameter"]["Value"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                raise ValueError(f"No secret found for ID: {secret_id}") from e

            raise

    def delete_secret(self, secret_id: str) -> None:
        """
        Delete a secret from SSM
        
        Args:
            secret_id: The ID of the secret to delete
            
        Raises:
            ValueError: If the secret doesn't exist
        """
        if secret_id.startswith("HIDDEN_SECRET"):
            secret_id = secret_id.split(":")[1]

        param_path = f"{self.prefix}{secret_id}"
        
        try:
            self.ssm_client.delete_parameter(Name=param_path)

        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                raise ValueError(f"No secret found for ID: {secret_id}") from e

            raise