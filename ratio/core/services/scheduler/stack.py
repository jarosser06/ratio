from os import path

from aws_cdk import (
    Duration,
)

from constructs import Construct

from da_vinci.core.resource_discovery import ResourceType

from da_vinci_cdk.stack import Stack

from da_vinci_cdk.constructs.access_management import ResourceAccessRequest
from da_vinci_cdk.constructs.base import resource_namer
from da_vinci_cdk.constructs.event_bus import EventBusSubscriptionFunction
from da_vinci_cdk.constructs.global_setting import GlobalSetting, GlobalSettingType
from da_vinci_cdk.constructs.service import SimpleRESTService

from da_vinci_cdk.framework_stacks.services.event_bus.stack import EventBusStack

from ratio.core.stack import RatioCoreStack
from ratio.core.services.agent_manager.stack import AgentManagerStack
from ratio.core.services.storage_manager.stack import StorageManagerStack

from ratio.core.tables.entities.stack import Entity, EntitiesTableStack

from ratio.core.services.scheduler.tables.filesystem_subscriptions.stack import (
    FilesystemSubscription,
    FilesystemSubscriptionsTableStack,
)

from ratio.core.services.scheduler.tables.general_subscriptions.stack import (
    GeneralSubscription,
    GeneralSubscriptionsTableStack,
)



class SchedulerStack(Stack):
    def __init__(self, app_name: str, app_base_image: str, architecture: str,
                 deployment_id: str, stack_name: str, scope: Construct):
        """
        Scheduler Stack

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
                AgentManagerStack,
                EntitiesTableStack,
                EventBusStack,
                FilesystemSubscriptionsTableStack,
                GeneralSubscriptionsTableStack,
                RatioCoreStack,
                StorageManagerStack,
            ],
            deployment_id=deployment_id,
            scope=scope,
            stack_name=stack_name,
        )

        base_dir = self.absolute_dir(__file__)

        self.runtime_path = path.join(base_dir, 'runtime')

        # Flag for recursion detection
        self.enforce_recursion_detection_setting = GlobalSetting(
            description="Whether the scheduler should enforce recursion detection. This is enabled by default.",
            namespace="ratio::core",
            setting_key="enforce_recursion_detection",
            setting_type=GlobalSettingType.BOOLEAN,
            setting_value="True",
            scope=self,
        )

        self.recursion_detection_threshold = GlobalSetting(
            description="The threshold for recursion detection. This is enabled by default. If a subscription is triggered within this threshold from the last execution, it will be ignored. In seconds.",
            namespace="ratio::core",
            setting_key="recursion_detection_threshold",
            setting_type=GlobalSettingType.INTEGER,
            setting_value="300",
            scope=self,
        )

        self.scheduler_manager = SimpleRESTService(
            base_image=self.app_base_image,
            description="Scheduler Manager Service",
            entry=self.runtime_path,
            index="api.py",
            handler="handler",
            memory_size=256,
            resource_access_requests=[
                ResourceAccessRequest(
                    resource_name="event_bus",
                    resource_type=ResourceType.ASYNC_SERVICE,
                ),
                ResourceAccessRequest(
                    resource_name=FilesystemSubscription.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name=GeneralSubscription.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="internal_signing_kms_key_id",
                    resource_type="KMS_KEY",
                    policy_name="default",
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
            ],
            scope=self,
            service_name="scheduler",
            timeout=Duration.seconds(90),
        )

        self.fs_update_handler = EventBusSubscriptionFunction(
            base_image=self.app_base_image,
            construct_id="scheduler-fs-update-handler",
            description="Scheduler File System Update Handler",
            entry=self.runtime_path,
            event_type="ratio::file_event",
            function_name=resource_namer(name="scheduler-fs-update-handler", scope=self),
            index="fs_event_handler.py",
            handler="fs_update_handler",
            memory_size=256,
            resource_access_requests=[
                ResourceAccessRequest(
                    resource_name="agent_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
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
                    resource_name=Entity.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read",
                ),
                ResourceAccessRequest(
                    resource_name=FilesystemSubscription.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
            ],
            scope=self,
            timeout=Duration.seconds(90),
        )

        self.general_event_handler = EventBusSubscriptionFunction(
            base_image=self.app_base_image,
            construct_id="scheduler-general-event-handler",
            description="Scheduler General Event Handler",
            entry=self.runtime_path,
            event_type="ratio::system_event",
            function_name=resource_namer(name="scheduler-general-event-handler", scope=self),
            index="general_event_handler.py",
            handler="general_event_handler",
            memory_size=256,
            resource_access_requests=[
                ResourceAccessRequest(
                    resource_name="agent_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
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
                    resource_name=Entity.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read",
                ),
                ResourceAccessRequest(
                    resource_name=GeneralSubscription.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
            ],
            scope=self,
            timeout=Duration.seconds(90),
        )