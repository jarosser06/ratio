from os import path

from aws_cdk import (
    Duration,
)

from constructs import Construct

from da_vinci.core.global_settings import GlobalSetting
from da_vinci.core.resource_discovery import ResourceType

from da_vinci_cdk.stack import Stack

from da_vinci_cdk.constructs.access_management import ResourceAccessRequest
from da_vinci_cdk.constructs.service import SimpleRESTService

from ratio.core.cdk.managed_policies import (
    SSMSecretManagerManagedPolicy,
)

from ratio.core.services.process_manager.stack import ProcessManagerStack
from ratio.core.services.scheduler.stack import SchedulerStack
from ratio.core.services.storage_manager.stack import StorageManagerStack

from ratio.core.tables.entities.stack import Entity, EntitiesTableStack

from ratio.core.api.tables.groups.stack import Group, GroupsTableStack


class RatioAPIStack(Stack):
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
                ProcessManagerStack,
                EntitiesTableStack,
                GroupsTableStack,
                SchedulerStack,
                StorageManagerStack,
            ],
            deployment_id=deployment_id,
            scope=scope,
            stack_name=stack_name,
        )

        base_dir = self.absolute_dir(__file__)

        self.runtime_path = path.join(base_dir, "runtime")

        secret_manager_policy = SSMSecretManagerManagedPolicy(
            app_name=self.app_name,
            deployment_id=self.deployment_id,
            construct_id="api-ssm-secret-mgr",
            scope=self,
        )

        self.api_handler = SimpleRESTService(
            description="Ratio API Service",
            ignore_settings_table_access=True, # Setting this up in resource_access_requests
            base_image=self.app_base_image,
            entry=self.runtime_path,
            index="api",
            handler="handler",
            managed_policies=[secret_manager_policy.managed_policy],
            resource_access_requests=[
                ResourceAccessRequest(
                    resource_name="process_manager",
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
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name=GlobalSetting.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name=Group.table_name,
                    resource_type=ResourceType.TABLE,
                    policy_name="read_write",
                ),
                ResourceAccessRequest(
                    resource_name="scheduler",
                    resource_type=ResourceType.REST_SERVICE,
                ),
                ResourceAccessRequest(
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
            ],
            public=False,
            scope=self,
            service_name="api",
            timeout=Duration.seconds(90),
        )