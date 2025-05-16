from aws_cdk import Aws, aws_iam as cdk_iam

from constructs import Construct


class SSMSecretManagerManagedPolicy(Construct):
    def __init__(self, scope: Construct, construct_id: str, app_name: str, deployment_id: str):
        """
        Creates a managed policy for SSM secret management

        Keyword arguments:
        scope -- The parent of the construct
        construct_id -- The ID of the construct
        app_name -- Name of the application
        deployment_id -- Deployment identifier
        """
        super().__init__(scope, construct_id)
        
        policy_statements = [
            cdk_iam.PolicyStatement(
                actions=[
                    "ssm:GetParameter",
                    "ssm:DeleteParameter",
                    "ssm:PutParameter",
                ],
                resources=[
                    f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter/{app_name}/{deployment_id}/ratio/secrets/*"
                ]
            )
        ]
        
        self.managed_policy = cdk_iam.ManagedPolicy(
            scope=self,
            id=f'{construct_id}-ssm-secret-mgr-policy',
            statements=policy_statements,
        )


class SSMSecretReaderManagedPolicy(Construct):
    def __init__(self, scope: Construct, construct_id: str, app_name: str, deployment_id: str):
        """
        Creates a managed policy for SSM secret reading

        Keyword arguments:
        scope -- The parent of the construct
        construct_id -- The ID of the construct
        app_name -- Name of the application
        deployment_id -- Deployment identifier
        """
        super().__init__(scope, construct_id)
        
        policy_statements = [
            cdk_iam.PolicyStatement(
                actions=[
                    "ssm:GetParameter"
                ],
                resources=[
                    f"arn:aws:ssm:*:*:parameter/{app_name}/{deployment_id}/ratio/secrets/*"
                ]
            )
        ]
        
        self.managed_policy = cdk_iam.ManagedPolicy(
            scope=self,
            id=f'{construct_id}-ssm-secret-reader-policy',
            statements=policy_statements,
        )