from os import path

from aws_cdk import Duration

from constructs import Construct

from da_vinci.core.resource_discovery import ResourceType

from da_vinci_cdk.stack import Stack

from da_vinci_cdk.constructs.access_management import ResourceAccessRequest
from da_vinci_cdk.constructs.base import resource_namer
from da_vinci_cdk.constructs.event_bus import EventBusSubscriptionFunction
from da_vinci_cdk.constructs.global_setting import GlobalSetting
from da_vinci_cdk.constructs.service import SimpleRESTService

from ratio.core.stack import RatioCoreStack

from ratio.core.services.storage_manager.stack import StorageManagerStack

from ratio.core.services.agent_manager.tables.processes.stack import Process, ProcessesTableStack

from ratio.core.services.storage_manager.cdk.filesystem import RegisteredFileType


class AgentManagerStack(Stack):
    def __init__(self, app_name: str, app_base_image: str, architecture: str,
                 deployment_id: str, stack_name: str, scope: Construct):
        """
        Agent Manager Stack

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
            namespace="ratio::agent_manager",
            setting_key="default_global_working_dir",
            description="Default global working directory for the agent manager, this is used when no working directory is specified and this is not None",
            setting_value="NOT_SET",
        )

        self.agent_manager = SimpleRESTService(
            base_image=self.app_base_image,
            description="Manages the agent execution system",
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
            service_name="agent_manager",
            timeout=Duration.seconds(90),
        )

        self.process_complete = EventBusSubscriptionFunction(
            base_image=self.app_base_image,
            construct_id="agent-process-complete-handler",
            description="Agent Manager Process Complete Handler",
            entry=self.runtime_path,
            event_type="ratio::agent_response",
            function_name=resource_namer(name="process-complete-handler", scope=self),
            index="event_handlers.py",
            handler="process_complete_handler",
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
        )

        self.composite_agent_handler = EventBusSubscriptionFunction(
            base_image=self.app_base_image,
            construct_id="agent-composite-agent-handler",
            description="Agent Manager Composite Agent Handler",
            entry=self.runtime_path,
            event_type="ratio::execute_composite_agent",
            function_name=resource_namer(name="composite-agent-handler", scope=self),
            index="event_handlers.py",
            handler="execute_composite_agent_handler",
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
        )

        RegisteredFileType(
            scope=self,
            content_type="application/json",
            description="Agent File Type",
            name_restrictions="^[a-zA-Z0-9_-]+\\.agent$",
            type_name="ratio::agent",
        )

        RegisteredFileType(
            scope=self,
            content_type="application/json",
            description="Arguments/Responses from an agent run. AIO stands for Agent Input/Output",
            name_restrictions="^[a-zA-Z0-9_-]+\\.aio$",
            type_name="ratio::agent_io",
        )