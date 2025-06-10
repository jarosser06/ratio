from os import path

from constructs import Construct

from aws_cdk import (
    aws_events as cdk_events,
    aws_events_targets as cdk_events_targets,
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

from da_vinci.core.resource_discovery import ResourceType

from da_vinci_cdk.stack import Stack

from da_vinci_cdk.constructs.access_management import ResourceAccessRequest
from da_vinci_cdk.constructs.base import resource_namer
from da_vinci_cdk.constructs.event_bus import EventBusSubscriptionFunction
from da_vinci_cdk.constructs.global_setting import (
    GlobalSetting,
    GlobalSettingLookup,
    GlobalSettingType,
)
from da_vinci_cdk.constructs.lambda_function import LambdaFunction
from da_vinci_cdk.constructs.service import SimpleRESTService

from ratio.core.stack import RatioCoreStack

from ratio.core.services.storage_manager.stack import StorageManagerStack

from ratio.core.services.process_manager.tables.processes.stack import Process, ProcessesTableStack

from ratio.core.services.storage_manager.cdk.filesystem import RegisteredFileType


class ProcessManagerStack(Stack):
    def __init__(self, app_name: str, app_base_image: str, architecture: str,
                 deployment_id: str, stack_name: str, scope: Construct):
        """
        Tool Manager Stack

        Keyword Arguments:
            app_name: The name of the app.
            app_base_image: The base image for the app.
            architecture: The architecture of the app.
            deployment_id: The deployment ID.
            stack_name: The name of the stack.
            scope: The scope of the stack.
        """

        super().__init__(
            app_name=app_name,
            app_base_image=app_base_image,
            architecture=architecture,
            requires_exceptions_trap=True,
            required_stacks=[
                ProcessesTableStack,
                RatioCoreStack,
                StorageManagerStack,
            ],
            deployment_id=deployment_id,
            scope=scope,
            stack_name=stack_name,
        )

        base_dir = self.absolute_dir(__file__)

        self.runtime_path = path.join(base_dir, 'runtime')

        GlobalSetting(
            scope=self,
            namespace="ratio::process_manager",
            setting_key="default_global_working_dir",
            description="Default global working directory for the tool manager, this is used when no working directory is specified and this is not None",
            setting_value="/run",
        )

        self.process_manager = SimpleRESTService(
            base_image=self.app_base_image,
            description="Manages the tool execution system",
            entry=self.runtime_path,
            index="api.py",
            handler="handler",
            memory_size=512,
            resource_access_requests=[
                ResourceAccessRequest(
                    resource_name="event_bus",
                    resource_type=ResourceType.ASYNC_SERVICE,
                ),
                ResourceAccessRequest(
                    resource_name="PUBLIC_API_ACCESS",
                    resource_type="RATIO_CUSTOM_POLICY",
                ),
                ResourceAccessRequest(
                    resource_name="internal_signing_kms_key_id",
                    resource_type="KMS_KEY",
                    policy_name="signer",
                ),
                ResourceAccessRequest(
                    resource_name=Process.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
                ResourceAccessRequest(
                    resource_name="websocket_api",
                    resource_type="RATIO_CUSTOM_POLICY",
                ),
            ],
            scope=self,
            service_name="process_manager",
            timeout=Duration.seconds(90),
        )

        self.process_complete = EventBusSubscriptionFunction(
            base_image=self.app_base_image,
            construct_id="tool-process-complete-handler",
            description="Tool Manager Process Complete Handler",
            entry=self.runtime_path,
            event_type="ratio::tool_response",
            function_name=resource_namer(name="process-complete-handler", scope=self),
            index="event_handlers.py",
            handler="process_complete_handler",
            memory_size=512,
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
                    resource_name=Process.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
                ResourceAccessRequest(
                    resource_name="websocket_api",
                    resource_type="RATIO_CUSTOM_POLICY",
                ),
            ],
            scope=self,
            timeout=Duration.minutes(5),
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

        route_key = HttpRouteKey.with_(path="/process/{proxy+}", method=HttpMethod.POST)

        HttpRoute(
            scope=self,
            id="api-route",
            integration=HttpLambdaIntegration(
                "api-lambda-integration",
                handler=self.process_manager.handler.function,
            ),
            route_key=route_key,
            http_api=self.api,
        )

        self.composite_tool_handler = EventBusSubscriptionFunction(
            base_image=self.app_base_image,
            construct_id="tool-composite-tool-handler",
            description="Tool Manager Composite Tool Handler",
            entry=self.runtime_path,
            event_type="ratio::execute_composite_tool",
            function_name=resource_namer(name="composite-tool-handler", scope=self),
            index="event_handlers.py",
            handler="execute_composite_tool_handler",
            memory_size=512,
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
                    resource_name=Process.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
            ],
            scope=self,
            timeout=Duration.minutes(5),
        )

        GlobalSetting(
            scope=self,
            namespace="ratio::process_manager",
            setting_key="global_process_timeout_minutes",
            description="Global timeout in minutes for an tool to run before it is considered timed out",
            setting_value=5,
            setting_type=GlobalSettingType.INTEGER,
        )

        self.tool_reconcile_handler = LambdaFunction(
            base_image=self.app_base_image,
            construct_id="tool-reconcile-handler",
            description="Tool Manager Reconcile Handler",
            entry=self.runtime_path,
            function_name=resource_namer(name="tool-reconcile-handler", scope=self),
            index="reconcile.py",
            handler="reconcile_processes",
            memory_size=256,
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
                    resource_name=Process.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
            ],
            scope=self,
            timeout=Duration.minutes(10),
        )

        self.parallel_reconciliation_handler = EventBusSubscriptionFunction(
            base_image=self.app_base_image,
            construct_id="parallel-completion-reconciliation-handler",
            description="Handles parallel completion reconciliation for stuck parallel groups",
            entry=self.runtime_path,
            event_type="ratio::parallel_completion_reconciliation",
            function_name=resource_namer(name="parallel-reconciliation-handler", scope=self),
            index="reconcile.py",
            handler="parallel_completion_reconciliation_handler",
            memory_size=256,
            resource_access_requests=[
                ResourceAccessRequest(
                    resource_name="event_bus",
                    resource_type=ResourceType.ASYNC_SERVICE,
                ),
                ResourceAccessRequest(
                    resource_name="internal_signing_kms_key_id",
                    resource_type="KMS_KEY",
                    policy_name="default",
                ),
                ResourceAccessRequest(
                    resource_name=Process.table_name,
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

        rule = cdk_events.Rule(
            self, "ToolReconcileRule",
            rule_name="ratio_tool_reconcile_rule",
            schedule=cdk_events.Schedule.rate(Duration.minutes(15)),
        )

        rule.add_target(cdk_events_targets.LambdaFunction(self.tool_reconcile_handler.function))

        RegisteredFileType(
            scope=self,
            content_type="application/json",
            description="Tool File Type",
            name_restrictions="^[a-zA-Z0-9_-]+\\.tool$",
            type_name="ratio::tool",
        )

        RegisteredFileType(
            scope=self,
            content_type="application/json",
            description="Arguments/Responses from an tool run. AIO stands for Tool Input/Output",
            name_restrictions="^[a-zA-Z0-9_-]+\\.aio$",
            type_name="ratio::tool_io",
        )

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

        WebSocketRoute(
            scope=self,
            id="default-route",
            integration=WebSocketLambdaIntegration(
                "default-integration",
                handler=self.process_manager.handler.function,
            ),
            route_key="$default",
            web_socket_api=self.ws_api,
        )