import hashlib
import os

from datetime import datetime, UTC as utc_tz
from typing import List, Optional, Union
from uuid import uuid4

from da_vinci.core.orm.client import (
    TableClient,
    TableObject,
    TableObjectAttribute,
    TableObjectAttributeType,
    TableScanDefinition,
)


class FilesystemSubscription(TableObject):
    table_name = "filesystem_subscriptions"

    table_description = "Tracks tool subscriptions to file system events"

    partition_key_attribute = TableObjectAttribute(
        name="full_path_hash",
        attribute_type=TableObjectAttributeType.STRING,
        description="The hash of the full path of the file that is being subscribed to.",
    )

    sort_key_attribute = TableObjectAttribute(
        name="subscription_id",
        attribute_type=TableObjectAttributeType.STRING,
        description="The unique ID of the subscription.",
        default=lambda: str(uuid4()),
    )

    ttl_attribute = TableObjectAttribute(
        name="expiration",
        attribute_type=TableObjectAttributeType.DATETIME,
        description="The optional datetime the subscription will expire.",
        optional=True,
    )

    attributes = [
        TableObjectAttribute(
            name="tool_definition",
            attribute_type=TableObjectAttributeType.STRING,
            description="The path to the tool that will be executed for the subscription.",
            optional=True,
        ),

        TableObjectAttribute(
            name="created_on",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the subscription was created.",
            optional=False,
            default=datetime.now(tz=utc_tz),
        ),

        TableObjectAttribute(
            name="execution_working_directory",
            attribute_type=TableObjectAttributeType.STRING,
            description="The optional working directory for the tool execution.",
            optional=True,
        ),

        TableObjectAttribute(
            name="file_path",
            attribute_type=TableObjectAttributeType.STRING,
            description="The full path of the file that was updated.",
            optional=False,
        ),

        TableObjectAttribute(
            name="last_execution",
            attribute_type=TableObjectAttributeType.DATETIME,
            description="The date and time the subscription was last executed",
            optional=True,
        ),

        TableObjectAttribute(
            name="file_event_type",
            attribute_type=TableObjectAttributeType.STRING,
            description="The type of file system event to which the subscription is limited. E.g. create, delete, update etc",
            optional=True,
        ),

        TableObjectAttribute(
            name="file_type",
            attribute_type=TableObjectAttributeType.STRING,
            description="The file type to which the subscription is limited. E.g. ratio::file, ratio::directory etc",
            optional=True,
        ),

        TableObjectAttribute(
            name="process_owner",
            attribute_type=TableObjectAttributeType.STRING,
            description="The owner of the process.",
            optional=False,
        ),

        TableObjectAttribute(
            name="single_use",
            attribute_type=TableObjectAttributeType.BOOLEAN,
            description="Whether the subscription is single use or not.",
            optional=False,
            default=False,
        ),
    ]

    @staticmethod
    def create_full_path_hash_from_path(file_path: str) -> str:
        """
        Create a full path hash from a complete file path.
        Separates the file name from its parent path and generates the hash.

        Keyword arguments:
        file_path -- The complete file path to generate the hash from.

        Returns:
            The generated full path hash
        """
        # Split the path into parent path and file name
        parent_path, file_name = os.path.split(file_path)

        # Generate name hash from file name
        name_hash = hashlib.sha256(file_name.encode()).hexdigest()

        # Generate path hash from parent path
        path_hash = hashlib.sha256(parent_path.encode()).hexdigest()

        # Join the two hashes and create the full path hash
        joined_keys = "-".join([path_hash, name_hash])

        return hashlib.sha256(joined_keys.encode()).hexdigest()


class FilesystemSubscriptionsTableClient(TableClient):
    def __init__(self, app_name: Optional[str] = None, deployment_id: Optional[str] = None):
        super().__init__(
            default_object_class=FilesystemSubscription,
            app_name=app_name,
            deployment_id=deployment_id
        )

    def delete(self, subscription: FilesystemSubscription) -> None:
        """
        Delete a subscription.

        Keyword arguments:
        subscription -- The subscription to delete.
        """
        self.delete_object(table_object=subscription)

    def get(self, full_path_hash: str, subscription_id: str) -> Union[FilesystemSubscription, None]:
        """
        Get a subscription by its full path hash and subscription ID.

        Keyword arguments:
        full_path_hash -- The full path hash of the subscription.
        subscription_id -- The ID of the subscription.
        """
        return self.get_object(partion_key_value=full_path_hash, sort_key_value=subscription_id)

    def get_by_full_path_hash(self, full_path_hash: str) -> List[FilesystemSubscription]:
        """
        Get all subscriptions by their full path hash.

        Keyword arguments:
        full_path_hash -- The full path hash of the subscription.
        """
        parameters = {
            "KeyConditionExpression": "FullPathHash = :full_path_hash",
            "ExpressionAttributeValues": {
                ":full_path_hash": {"S": full_path_hash},
            },
        }

        subscriptions = []

        for page in self.paginated(call='query', parameters=parameters):
            subscriptions.extend(page)

        return subscriptions

    def get_by_subscription_id(self, subscription_id: str) -> Optional[FilesystemSubscription]:
        """
        Get a subscription by its subscription ID using the GSI.
        Returns a single subscription or None if not found.

        Keyword arguments:
        subscription_id -- The ID of the subscription.
        """
        parameters = {
            "IndexName": "subscription_id-index",
            "KeyConditionExpression": "SubscriptionId = :subscription_id",
            "ExpressionAttributeValues": {
                ":subscription_id": {"S": subscription_id},
            },
        }
        
        subscriptions = []

        for page in self.paginated(call='query', parameters=parameters):
            subscriptions.extend(page)
        
        # Return the first (and should be only) subscription or None
        return subscriptions[0] if subscriptions else None

    def list_by_file_path_or_owner(self, file_path: Optional[str] = None, process_owner: Optional[str] = None) -> List[FilesystemSubscription]:
        """
        Get subscriptions by file_path and/or owner.
        If file_path is provided, uses a more efficient query on full_path_hash.
        Otherwise, falls back to a scan with owner filter.

        Keyword arguments:
        file_path -- The full path to the file or directory to subscribe to.
        owner -- The owner of the subscriptions to list.

        Returns:
            List of matching Subscription objects
        """
        if not file_path and not process_owner:
            raise ValueError("At least one of file_path or owner must be provided")

        # If we have a file_path, we can use a more efficient query on the hash
        if file_path:
            # Generate the full_path_hash from the file_path
            path_hash = FilesystemSubscription.create_full_path_hash_from_path(file_path)

            # Set up query parameters for the hash
            parameters = {
                "KeyConditionExpression": "FullPathHash = :full_path_hash",
                "ExpressionAttributeValues": {
                    ":full_path_hash": {"S": path_hash},
                },
            }

            # If owner is also specified, add it as a filter
            if process_owner:
                parameters["FilterExpression"] = "ProcessOwner = :owner"

                parameters["ExpressionAttributeValues"][":owner"] = {"S": process_owner}

            # Execute the query
            subscriptions = []

            for page in self.paginated(call='query', parameters=parameters):
                subscriptions.extend(page)

            return subscriptions

        # If we only have owner, we need to do a full scan
        else:
            scan_definition = TableScanDefinition(table_object_class=self.default_object_class)

            scan_definition.add("process_owner", "equal", process_owner)

            return self.full_scan(scan_definition=scan_definition)

    def put(self, subscription: FilesystemSubscription) -> None:
        """
        Put a subscription.

        Keyword arguments:
        subscription -- The subscription to put.
        """
        self.put_object(table_object=subscription)