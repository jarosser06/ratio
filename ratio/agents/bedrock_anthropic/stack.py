"""
Bedrock Anthropic Agent Stack
"""
from os import path

from aws_cdk import Duration
from aws_cdk.aws_iam import ManagedPolicy

from constructs import Construct

from da_vinci_cdk.stack import Stack

from da_vinci.core.resource_discovery import ResourceType

from da_vinci_cdk.constructs.access_management import ResourceAccessRequest
from da_vinci_cdk.constructs.base import resource_namer
from da_vinci_cdk.constructs.event_bus import EventBusSubscriptionFunction

from ratio.core.services.storage_manager.stack import StorageManagerStack


class RatioBedrockAnthropicAgent(Stack):
    def __init__(self, app_name: str, app_base_image: str, architecture: str, deployment_id: str,
                 stack_name: str, scope: Construct):
        """
        Ratio Bedrock Anthropic Agent Stack

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
                StorageManagerStack,
            ],
            deployment_id=deployment_id,
            scope=scope,
            stack_name=stack_name,
        )

        base_dir = self.absolute_dir(__file__)

        self.runtime_path = path.join(base_dir, "runtime")

        self.agent_execute = EventBusSubscriptionFunction(
            base_image=self.app_base_image,
            construct_id="ratio-agent-bedrock-anthropic-execution",
            event_type="ratio::agent::bedrock_anthropic::execution",
            description="Agent execution for Bedrock Anthropic agent",
            entry=self.runtime_path,
            index="run.py",
            handler="handler",
            function_name=resource_namer("agent-bedrock-anthropic", scope=self),
            memory_size=512,
            managed_policies=[
                ManagedPolicy.from_managed_policy_arn(
                    scope=self,
                    id='extraction-amazon-bedrock-full-access',
                    managed_policy_arn='arn:aws:iam::aws:policy/AmazonBedrockFullAccess'
                ),
            ],
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
                    resource_name="storage_manager",
                    resource_type=ResourceType.REST_SERVICE,
                ),
            ],
            scope=self,
            timeout=Duration.minutes(5),
        )