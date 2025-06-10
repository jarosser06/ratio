# Core Ratio Stack

from constructs import Construct

from aws_cdk import (
    Duration,
    aws_cognito as cdk_cognito,
    aws_iam as cdk_iam,
    aws_kms as cdk_kms,
)

from aws_cdk.aws_apigatewayv2 import WebSocketApi, WebSocketStage

from da_vinci_cdk.stack import Stack

from da_vinci_cdk.constructs.access_management import ResourceAccessPolicy
from da_vinci_cdk.constructs.base import resource_namer
from da_vinci_cdk.constructs.global_setting import GlobalSetting, GlobalSettingType
from da_vinci_cdk.constructs.service import APIGatewayRESTService


from ratio.core.tables.entities.stack import Entity, EntitiesTableStack

from ratio.core.tables.groups.stack import Group, GroupsTableStack



class RatioCoreStack(Stack):
    def __init__(self, app_name: str, deployment_id: str, scope: Construct, stack_name: str):
        super().__init__(
            app_name=app_name,
            deployment_id=deployment_id,
            required_stacks=[
                EntitiesTableStack,
                GroupsTableStack,
            ],
            scope=scope,
            stack_name=stack_name
        )

        # Create a KMS key for signing JWTs
        self.jwt_signing_key = cdk_kms.Key(
            self,
            "RatioCoreJWTKey",
            alias="ratio-signing-key",
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

        self.user_pool = cdk_cognito.UserPool(
            self,
            "ratio-user-pool",
            user_pool_name="ratio-users",
            sign_in_aliases=cdk_cognito.SignInAliases(email=True),
            auto_verify=cdk_cognito.AutoVerifiedAttrs(email=True),
            password_policy=cdk_cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
            ),
            self_sign_up_enabled=False,
        )

        # Create User Pool Domain
        self.user_pool_domain = cdk_cognito.UserPoolDomain(
            self,
            "ratio-user-pool-domain",
            user_pool=self.user_pool,
            cognito_domain=cdk_cognito.CognitoDomainOptions(
                domain_prefix=f"ratio-{self.deployment_id}",
            ),
        )

        admin_table_actions = [
            "dynamodb:BatchGetItem",
            "dynamodb:BatchWriteItem",
            "dynamodb:DescribeTable",
            "dynamodb:GetRecords",
            "dynamodb:ConditionCheckItem",
            "dynamodb:GetItem",
            "dynamodb:DeleteItem",
            "dynamodb:UpdateItem",
            "dynamodb:PutItem",
            "dynamodb:Query",
            "dynamodb:GetShardIterator",
            "dynamodb:Scan"
        ]

        admin_table_arns = [
            Stack.of(self).format_arn(
                service="dynamodb",
                resource="table",
                resource_name=resource_namer(name=Entity.table_name, scope=self),
            ),
            Stack.of(self).format_arn(
                service="dynamodb",
                resource="table",
                resource_name=resource_namer(name=Group.table_name, scope=self),
            ),
        ]

        admin_table_resources = admin_table_arns + [f"{tbl_arn}/*" for tbl_arn in admin_table_arns]

        ResourceAccessPolicy(
            scope=self,
            policy_statements=[
                cdk_iam.PolicyStatement(
                    effect=cdk_iam.Effect.ALLOW,
                    actions=["cognito-idp:GetUser"],
                    resources=[self.user_pool.user_pool_arn]
                ),
                cdk_iam.PolicyStatement(
                    effect=cdk_iam.Effect.ALLOW,
                    actions=admin_table_actions,
                    resources=admin_table_resources,
                )
            ],
            resource_name="PUBLIC_API_ACCESS",
            resource_type="RATIO_CUSTOM_POLICY",
        )

        custom_context = self.node.get_context("custom_context")

        oauth_callback_urls = custom_context["oauth_callback_urls"]

        token_validity_hours = custom_context.get("token_validity_hours", 8)

        self.user_pool_client = cdk_cognito.UserPoolClient(
            self,
            "ratio-user-pool-client",
            user_pool=self.user_pool,
            auth_flows=cdk_cognito.AuthFlow(user_srp=True),
            o_auth=cdk_cognito.OAuthSettings(
                flows=cdk_cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[
                    cdk_cognito.OAuthScope.OPENID,
                    cdk_cognito.OAuthScope.EMAIL,
                    cdk_cognito.OAuthScope.PROFILE,
                    cdk_cognito.OAuthScope.custom("aws.cognito.signin.user.admin"),
                ],
                callback_urls=oauth_callback_urls,
            ),
            id_token_validity=Duration.hours(token_validity_hours),
        )

        # Set up the API Gateway for the Ratio Core Service
        self.api = APIGatewayRESTService(
            service_name="api",
            scope=self,
        )

        GlobalSetting(
            scope=self,
            description="The ID of the API Gateway for the Ratio Core Service.",
            namespace="ratio::core",
            setting_key="rest_api_id",
            setting_type=GlobalSettingType.STRING,
            setting_value=self.api.api.http_api_id,
        )

        # Set up the Websocket API
        self.ws_api = WebSocketApi(self, "ratio-ws-api")

        WebSocketStage(
            self,
            "ratio-ws-api-stage",
            web_socket_api=self.ws_api,
            stage_name=self.node.get_context("deployment_id"),
            auto_deploy=True
        )

        self.websocket_access_statement = cdk_iam.PolicyStatement(
            actions=["execute-api:ManageConnections"],
            resources=[f"arn:aws:execute-api:{self.region}:{self.account}:{self.ws_api.api_id}/*"]
        )

        self.default_access_policy = ResourceAccessPolicy(
            scope=self,
            policy_statements=[
                self.websocket_access_statement,
            ],
            resource_name="websocket_api",
            resource_type="RATIO_CUSTOM_POLICY",
        )

        GlobalSetting(
            scope=self,
            description="The ID of the WebSocket API for the Ratio Core Service. MODIFY WITH CAUTION",
            namespace="ratio::core",
            setting_key="websocket_api_id",
            setting_type=GlobalSettingType.STRING,
            setting_value=self.ws_api.api_id,
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
            setting_key="token_active_minutes",
            setting_type=GlobalSettingType.INTEGER,
            setting_value=60, # Default to 60 minutes
            description="The number of minutes the token is active for. MODIFY WITH CAUTION",
        )