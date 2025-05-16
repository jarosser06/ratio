# Core Ratio Stack

from constructs import Construct

from aws_cdk import (
    aws_iam as cdk_iam,
    aws_kms as cdk_kms,
)

from da_vinci_cdk.stack import Stack

from da_vinci_cdk.constructs.access_management import ResourceAccessPolicy
from da_vinci_cdk.constructs.global_setting import GlobalSetting, GlobalSettingType


class RatioCoreStack(Stack):
    def __init__(self, app_name: str, deployment_id: str, scope: Construct, stack_name: str):
        super().__init__(
            app_name=app_name,
            deployment_id=deployment_id,
            required_stacks=[],
            scope=scope,
            stack_name=stack_name
        )

        # Create a KMS key for signing JWTs
        self.jwt_signing_key = cdk_kms.Key(
            self,
            "RatioCoreJWTKey",
            key_spec=cdk_kms.KeySpec.RSA_2048,
            key_usage=cdk_kms.KeyUsage.SIGN_VERIFY,
        )

        # Add Key ID to the global settings
        GlobalSetting(
            scope=self,
            description="KMS Key ID for the Internal JWT signing key. MODIFY WITH CAUTION",
            namespace="ratio::core",
            setting_key="internal_signing_kms_key_id",
            setting_type=GlobalSettingType.STRING,
            setting_value=self.jwt_signing_key.key_id,
        )

        self.kms_default_policy = cdk_iam.PolicyStatement(
            actions=[
                "kms:Verify",
                "kms:DescribeKey",
            ],
            resources=[
                self.jwt_signing_key.key_arn,
            ],
        )

        self.kms_key_default_access_policy = ResourceAccessPolicy(
            scope=self,
            policy_name="default",
            policy_statements=[
                self.kms_default_policy,
            ],
            resource_name="internal_signing_kms_key_id",
            resource_type="KMS_KEY",
        )

        self.kms_signer_policy = cdk_iam.PolicyStatement(
            actions=[
                "kms:Sign",
                "kms:Verify",
                "kms:DescribeKey",
                "kms:GetPublicKey",
            ],
            resources=[
                self.jwt_signing_key.key_arn,
            ],
        )

        self.kms_signer_access_policy = ResourceAccessPolicy(
            scope=self,
            policy_name="signer",
            policy_statements=[
                self.kms_signer_policy,
            ],
            resource_name="internal_signing_kms_key_id",
            resource_type="KMS_KEY",
        )

        # Setting indicates whether the installation has been initialized
        GlobalSetting(
            scope=self,
            description="Indicates whether the installation has been initialized. MANAGED BY SYSTEM, DO NOT MODIFY",
            namespace="ratio::core",
            setting_key="installation_initialized",
            setting_type=GlobalSettingType.BOOLEAN,
            setting_value=False,
        )

        GlobalSetting(
            scope=self,
            description="The ID of the desginated admin entity set up by initialization event. MODIFY WITH CAUTION",
            namespace="ratio::core",
            setting_key="admin_entity_id",
            setting_type=GlobalSettingType.STRING,
        )

        GlobalSetting(
            scope=self,
            description="The ID of the desginated admin group set up by initialization event. MODIFY WITH CAUTION",
            namespace="ratio::core",
            setting_key="admin_group_id",
            setting_type=GlobalSettingType.STRING,
        )

        GlobalSetting(
            scope=self,
            namespace="ratio::core",
            setting_key="token_active_hours",
            setting_type=GlobalSettingType.INTEGER,
            setting_value=2,
            description="The number of hours the token is active for. MODIFY WITH CAUTION",
        )