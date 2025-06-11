from os import path

from aws_cdk import (
    Duration,
)

from aws_cdk.aws_apigatewayv2 import (
    HttpApi,
    HttpMethod,
    HttpRoute,
    HttpRouteKey,
    WebSocketApi,
    WebSocketRoute,
)
from aws_cdk.aws_apigatewayv2_integrations import (
    HttpLambdaIntegration,
    WebSocketLambdaIntegration,
)

from constructs import Construct

from da_vinci.core.global_settings import GlobalSetting as GlobalSettingTblObj
from da_vinci.core.resource_discovery import ResourceType

from da_vinci_cdk.stack import Stack

from da_vinci_cdk.constructs.access_management import (
    ResourceAccessRequest,
)
from da_vinci_cdk.constructs.base import resource_namer
from da_vinci_cdk.constructs.global_setting import GlobalSettingLookup
from da_vinci_cdk.constructs.lambda_function import LambdaFunction

from ratio.core.stack import RatioCoreStack
from ratio.core.services.storage_manager.stack import StorageManagerStack


class AuthStack(Stack):
    def __init__(self, app_name: str, app_base_image: str, architecture: str, deployment_id: str,
                 stack_name: str, scope: Construct):
        """
        Creates the API stack for the application.

        Keyword arguments:
        app_name -- Name of the application
        app_base_image -- Base image for the application
        architecture -- Architecture of the application
        deployment_id -- Deployment identifier
        stack_name -- Name of the stack
        scope -- The parent of the construct
        """
        super().__init__(
            app_name=app_name,
            app_base_image=app_base_image,
            architecture=architecture,
            requires_event_bus=True,
            requires_exceptions_trap=True,
            required_stacks=[
                RatioCoreStack,
                StorageManagerStack,
            ],
            deployment_id=deployment_id,
            scope=scope,
            stack_name=stack_name,
        )

        base_dir = self.absolute_dir(__file__)

        self.runtime_path = path.join(base_dir, "runtime")

        self.auth_handler = LambdaFunction(
            construct_id="ratio-auth-handler",
            description="Ratio Auth Service Handler",
            ignore_settings_table_access=True, # Setting this up in resource_access_requests
            base_image=self.app_base_image,
            function_name=resource_namer(name="ratio-auth-handler", scope=self),
            entry=self.runtime_path,
            index="api",
            handler="handler",
            resource_access_requests=[
                ResourceAccessRequest(
                    resource_name="event_bus",
                    resource_type=ResourceType.ASYNC_SERVICE,
                ),
                ResourceAccessRequest(
                    resource_name="internal_signing_kms_key_id",
                    resource_type="KMS_KEY",
                    policy_name="signer",
                ),
                ResourceAccessRequest(
                    resource_name="PUBLIC_API_ACCESS",
                    resource_type="RATIO_CUSTOM_POLICY",
                ),
                ResourceAccessRequest(
                    resource_name=GlobalSettingTblObj.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
            ],
            scope=self,
            timeout=Duration.seconds(30),
        )

        api_id = GlobalSettingLookup(
            scope=self,
            construct_id="rest-api-id-lookup",
            namespace="ratio::core",
            setting_key="rest_api_id",
        )

        self.api = HttpApi.from_http_api_attributes(
            scope=self,
            id="ratio-api",
            http_api_id=api_id.get_value()
        )

        route_key = HttpRouteKey.with_(path="/auth/{proxy+}", method=HttpMethod.POST)

        HttpRoute(
            scope=self,
            id="api-route",
            integration=HttpLambdaIntegration(
                "api-lambda-integration",
                handler=self.auth_handler.function,
            ),
            route_key=route_key,
            http_api=self.api,
        )

        # Special System Initialize Route
        HttpRoute(
            scope=self,
            id="system-initialize-route",
            integration=HttpLambdaIntegration(
                "system-initialize-lambda-integration",
                handler=self.auth_handler.function,
            ),
            route_key=HttpRouteKey.with_(path="/initialize", method=HttpMethod.POST),
            http_api=self.api,
        )

        # Set connect and disconnect routes for WebSocket API
        ws_api_id = GlobalSettingLookup(
            scope=self,
            construct_id="ws-api-id-lookup",
            namespace="ratio::core",
            setting_key="websocket_api_id",
        )

        self.ws_api = WebSocketApi.from_web_socket_api_attributes(
            scope=self,
            id="ratio-ws-api",
            web_socket_id=ws_api_id.get_value()
        )

        ws_integration = WebSocketLambdaIntegration(
            "auth-execute-integration",
            handler=self.auth_handler.function,
        )

        WebSocketRoute(
            scope=self,
            id="auth-execute-connect-route",
            integration=ws_integration,
            route_key="$connect",
            web_socket_api=self.ws_api,
        )

        WebSocketRoute(
            scope=self,
            id="auth-execute-disconnect-route",
            integration=ws_integration,
            route_key="$disconnect",
            web_socket_api=self.ws_api,
        )

        WebSocketRoute(
            scope=self,
            id="auth-execute-default-route",
            integration=ws_integration,
            route_key="$default",
            web_socket_api=self.ws_api,
        )