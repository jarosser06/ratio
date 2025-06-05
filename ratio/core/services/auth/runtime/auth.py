"""
Auth API
"""
import json
import logging
import secrets

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC as utc_tz
from typing import Dict

from da_vinci.core.global_settings import setting_value, GlobalSettings

from da_vinci.core.immutable_object import (
    ObjectBody,
    ObjectBodySchema,
    RequiredCondition,
    SchemaAttribute,
    SchemaAttributeType,
)

from ratio.core.core_lib.client import RatioInternalClient
from ratio.core.core_lib.factories.api import (
    ChildAPI,
    Route,
)
from ratio.core.core_lib.jwt import JWTClaims, InternalJWTManager

from ratio.core.tables.entities.client import Entity, EntitiesTableClient

from ratio.core.tables.groups.client import Group, GroupsTableClient

from ratio.core.services.storage_manager.request_definitions import DescribeFileRequest, PutFileRequest


# PROTECTED ENTITY/GROUP WORDS
_PROTECTED_WORDS = [
    "system",
]


class ChallengeRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="entity_id",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class AddEntityToGroupRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="entity_id",
            description="The ID of the entity. This is used to identify the entity in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="group_id",
            description="The ID of the group. This is used to identify the group in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class RemoveEntityFromGroupRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="entity_id",
            description="The ID of the entity. This is used to identify the entity in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="group_id",
            description="The ID of the group. This is used to identify the group in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class CreateEntityRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="create_group",
            description="Whether to create a group with the same ID as the entity. If true, the entity will be added to this group.",
            required=False,
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=True,
        ),
        SchemaAttribute(
            name="create_home",
            description="Whether to create a home directory for the entity. If true, a home directory will be created in /home/<entity_id>.",
            required=False,
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=True,
        ),
        SchemaAttribute(
            name="description",
            description="A description of the entity.",
            required=False,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="entity_id",
            description="The ID of the entity. This is used to identify the entity in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="groups",
            description="A list of groups the entity belongs to. This is used to determine what groups the entity has access to.",
            required=False,
            type_name=SchemaAttributeType.STRING_LIST,
        ),
        SchemaAttribute(
            name="home_directory",
            description="An optional home directory path for the entity. If not provided, a default home directory will be created in /home/.",
            required=False,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="primary_group_id",
            description="The id of the primary group the entity belongs to. This is used to determine what group any new information created by the entity will be owned by.",
            type_name=SchemaAttributeType.STRING,
            required_conditions=[
                RequiredCondition(
                    param="create_group",
                    operator="equals",
                    value=False,
                )
            ],
        ),
        SchemaAttribute(
            name="public_key",
            description="The public key of the entity. This is used to verify the identity of the entity.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class CreateGroupRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="description",
            description="A description of the group.",
            required=False,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="group_id",
            description="The ID of the group. This is used to identify the group in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class DeleteGroupRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="group_id",
            description="The ID of the group. This is used to identify the group in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="force",
            description="Whether to force delete the group. If true, the group will be deleted even if it has members.",
            required=False,
            type_name=SchemaAttributeType.BOOLEAN,
            default_value=False,
        )
    ]


class DeleteEntityRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="entity_id",
            description="The ID of the entity. This is used to identify the entity in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class DescribeGroupRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="group_id",
            description="The ID of the group. This is used to identify the group in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class DescribeEntityRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="entity_id",
            description="The ID of the entity. This is used to identify the entity in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class IntializeRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="admin_entity_id",
            description="The ID of the admin entity. This is used to identify the admin entity in the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="admin_group_id",
            description="The ID of the admin group. This is used to identify the admin group in the system.",
            required=False,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="admin_public_key",
            description="The public key of the admin entity. This is used to verify the identity of the admin entity.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class TokenRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="challenge",
            description="The challenge to verify. This is used to verify the identity of the entity.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="entity_signature",
            description="The signature of the entity. This is used to verify the identity of the entity.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="system_signature",
            description="The signature of the system. This is used to verify the identity of the system.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


class TokenRotateRequest(ObjectBodySchema):
    attributes = [
        SchemaAttribute(
            name="entity_id",
            description="The ID of the entity. This is used to identify the entity in the system.",
            required=False,
            type_name=SchemaAttributeType.STRING,
        ),
        SchemaAttribute(
            name="public_key",
            description="The public key of the entity. This is used to verify the identity of the entity.",
            required=True,
            type_name=SchemaAttributeType.STRING,
        ),
    ]


@dataclass
class ChallengeObject:
    entity_id: str
    expires_at: str
    nonce: str
    timestamp: str

    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
        }


class AuthAPI(ChildAPI):
    """
    Auth API for managing entities and groups in the system.
    """
    routes = [
        Route(
            path="/auth/challenge",
            method_name="challenge",
            request_body_schema=ChallengeRequest,
        ),
        Route(
            path="/initialize",
            method_name="initialize",
            request_body_schema=IntializeRequest,
        ),
        Route(
            path="/auth/add_entity_to_group",
            method_name="add_entity_to_group",
            requires_auth=True,
            request_body_schema=AddEntityToGroupRequest,
        ),
        Route(
            path="/auth/remove_entity_from_group",
            method_name="remove_entity_from_group",
            requires_auth=True,
            request_body_schema=RemoveEntityFromGroupRequest,
        ),
        Route(
            path="/auth/create_entity",
            method_name="create_entity",
            requires_auth=True,
            request_body_schema=CreateEntityRequest,
        ),
        Route(
            path="/auth/create_group",
            method_name="create_group",
            requires_auth=True,
            request_body_schema=CreateGroupRequest,
        ),
        Route(
            path="/auth/delete_group",
            method_name="delete_group",
            requires_auth=True,
            request_body_schema=DeleteGroupRequest,
        ),
        Route(
            path="/auth/delete_entity",
            method_name="delete_entity",
            requires_auth=True,
            request_body_schema=DeleteEntityRequest,
        ),
        Route(
            path="/auth/describe_group",
            method_name="describe_group",
            requires_auth=True,
            request_body_schema=DescribeGroupRequest,
        ),
        Route(
            path="/auth/describe_entity",
            method_name="describe_entity",
            requires_auth=True,
            request_body_schema=DescribeEntityRequest,
        ),
        Route(
            path="/auth/list_entities",
            method_name="list_entities",
            requires_auth=True,
        ),
        Route(
            path="/auth/list_groups",
            method_name="list_groups",
            requires_auth=True,
        ),
        Route(
            path="/auth/rotate_entity_key",
            method_name="rotate_entity_key",
            requires_auth=True,
            request_body_schema=TokenRotateRequest,
        ),
        Route(
            path="/auth/token",
            method_name="token",
            request_body_schema=TokenRequest,
        ),
    ]

    @staticmethod
    def validate_auth_id(auth_id: str, protected_words: list) -> bool:
        """
        Validates if the given auth_id is not a protected word.

        Keyword arguments:
        entity_name -- The name of the entity to validate
        protected_words -- A list of protected words that are not allowed in the entity name
        """
        return auth_id not in protected_words

    def _validate_admin_entity(self, request_context: Dict) -> bool:
        """
        Validates if the entity is an admin entity.

        Keyword arguments:
        request_context -- The request context containing the entity_id
        """
        claims = JWTClaims.from_claims(request_context["request_claims"])

        logging.debug(f"Recognized claims: {claims}")

        entity_id = claims.entity

        auth_groups = claims.authorized_groups

        admin_entity_id = setting_value(namespace="ratio::core", setting_key="admin_entity_id")

        logging.debug(f"Admin entity ID set to: {admin_entity_id}")

        admin_group_id = setting_value(namespace="ratio::core", setting_key="admin_group_id")

        logging.debug(f"Admin group ID set to: {admin_group_id}")

        # Check if the entity is the admin entity or belongs to the admin group
        return entity_id == admin_entity_id or admin_group_id in auth_groups

    def challenge(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Creates a challenge for the given entity_id

        Keyword arguments:
        request_body -- The request body containing the entity_id
        request_context -- The request context containing the entity_id
        """
        entity_id = request_body['entity_id'].lower()

        # Generate a random nonce
        nonce = secrets.token_urlsafe(16)

        # Generate a timestamp
        timestamp = datetime.now(tz=utc_tz).isoformat()

        # Set the expiration time to 5 minutes from now
        expires_at = (datetime.now(tz=utc_tz) + timedelta(minutes=5)).isoformat()

        # Create the challenge object
        challenge_object = ChallengeObject(
            entity_id=entity_id,
            expires_at=expires_at,
            nonce=nonce,
            timestamp=timestamp,
        )

        encoded_str = InternalJWTManager.encode_segment(segment=challenge_object.to_dict())

        # Sign the challenge
        jwt_manager = InternalJWTManager(
            kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id")
        )

        signed_challenge = jwt_manager.sign_with_kms(data=encoded_str)

        return self.respond(
            status_code=201,
            body={
                "challenge": encoded_str,
                "system_signature": signed_challenge,
            },
        )

    def create_entity(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Creates a new entity with the given public key

        Keyword arguments:
        request_body -- The request body containing the entity_id and public_key
        request_context -- The request context containing the entity_id
        """
        logging.debug("Creating entity")

        if not self._validate_admin_entity(request_context=request_context):
            return self.respond(
                status_code=403,
                body={"message": "access denied"},
            )

        # Validate the entity by checking if it exists
        entities_client = EntitiesTableClient()

        formatted_entity_id = request_body['entity_id'].lower()

        existing_entity = entities_client.get(entity_id=formatted_entity_id)

        if existing_entity:
            return self.respond(
                status_code=403,
                body={"message": "entity already exists"},
            )

        # Validate the entity ID
        if not self.validate_auth_id(auth_id=formatted_entity_id, protected_words=_PROTECTED_WORDS):
            return self.respond(
                status_code=403,
                body={"message": "invalid entity id"},
            )

        starting_groups = request_body['groups'] or []

        primary_group_id = request_body.get('primary_group_id')

        if request_body['create_group']:
            # Validate the group IDs
            groups_client = GroupsTableClient()

            existing_group = groups_client.get(group_id=formatted_entity_id)

            if not existing_group:
                group = Group(
                    group_id=formatted_entity_id,
                    description=f"{formatted_entity_id} group",
                )

                # Create the new group
                groups_client.put(group=group)

                starting_groups.append(formatted_entity_id)

                primary_group_id = formatted_entity_id

        else:
            starting_groups.append(request_body['primary_group_id'])

        home_directory = request_body.get('home_directory')

        if not home_directory and request_body['create_home']:
            home_directory = f"/home/{formatted_entity_id}"

        entity = Entity(
            description=request_body.get('description'),
            entity_id=formatted_entity_id,
            groups=starting_groups,
            home_directory=home_directory,
            key_last_updated_on=datetime.now(tz=utc_tz),
            primary_group_id=primary_group_id,
            public_key=request_body['public_key'],
        )

        # Create the new entity
        entities_client.put(entity=entity)

        # Create the entity home directory if not provided
        if request_body['create_home']:
            # Create the home directory
            storage_client = RatioInternalClient(service_name="storage_manager", token=request_context["signed_token"])

            # Check if the home directory already exists
            describe_req = ObjectBody(
                body={
                    "file_path": home_directory,
                },
                schema=DescribeFileRequest,
            )

            describe_res = storage_client.request(path="/storage/describe_file", request=describe_req)

            # Only create the home directory if it doesn't exist
            if describe_res.status_code != 200:
                home_dir_req = ObjectBody(
                    body={
                        "file_path": home_directory,
                        "file_type": "ratio::directory",
                        "owner": formatted_entity_id,
                        "group": primary_group_id,
                        "permissions": "755",
                    },
                    schema=PutFileRequest,
                )

                home_dir_res = storage_client.request(path="/storage/put_file", request=home_dir_req)

                if home_dir_res.status_code < 200 or home_dir_res.status_code > 201:
                    if home_dir_res.status_code >= 500:
                        resp_code = 500

                        resp_body = {"message": "internal server error occurred, failed to create home directory"}

                    elif home_dir_res.status_code >= 400:
                        resp_code = 400

                        original_message = home_dir_res.response_body

                        try:
                            original_message = json.loads(original_message)["message"]

                        except:
                            logging.info("Failed to parse error message")

                        resp_body = {"message": f"failed to create home directory {home_directory}, storage response: {original_message}"}

                    logging.debug(f"Failed to create home directory: {home_dir_res}")

                    return self.respond(
                        status_code=resp_code,
                        body=resp_body,
                    )

        return self.respond(
            status_code=201,
            body=entity.to_dict(json_compatible=True),
        )

    def create_group(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Creates a new group with the given group_id

        Keyword arguments:
        request_body -- The request body containing the group_id
        request_context -- The request context containing the group_id
        """
        logging.debug("Creating group")

        if not self._validate_admin_entity(request_context=request_context):
            return self.respond(
                status_code=403,
                body={"message": "access denied"},
            )

        proper_group_id = request_body['group_id'].lower()

        # Validate the group ID
        if not self.validate_auth_id(auth_id=proper_group_id, protected_words=_PROTECTED_WORDS):
            return self.respond(
                status_code=403,
                body={"message": "invalid group id"},
            )

        # Validate the group ID
        groups_client = GroupsTableClient()

        existing_group = groups_client.get(group_id=proper_group_id)

        if existing_group:
            return self.respond(
                status_code=403,
                body={"message": "group already exists"},
            )

        group = Group(
            group_id=proper_group_id,
            description=request_body['description'] or f"{proper_group_id} group",
        )

        # Create the new group
        groups_client.put(group=group)

        return self.respond(
            status_code=201,
            body=group.to_dict(json_compatible=True),
        )

    def add_entity_to_group(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Adds the entity to the group with the given group_id

        Keyword arguments:
        request_body -- The request body containing the entity_id and group_id
        request_context -- The request context containing the entity_id
        """
        logging.debug("Adding entity to group")

        if not self._validate_admin_entity(request_context=request_context):
            return self.respond(
                status_code=403,
                body={"message": "access denied"},
            )

        # Validate the entity ID
        entities_client = EntitiesTableClient()

        formatted_entity_id = request_body['entity_id'].lower()

        existing_entity = entities_client.get(entity_id=formatted_entity_id)

        if not existing_entity:
            return self.respond(
                status_code=404,
                body={"message": "entity not found"},
            )

        # Validate the group ID
        groups_client = GroupsTableClient()

        formatted_group_id = request_body['group_id'].lower()

        existing_group = groups_client.get(group_id=formatted_group_id)

        if not existing_group:
            return self.respond(
                status_code=404,
                body={"message": "group not found"},
            )

        members = existing_group.members or []

        if formatted_entity_id in members:
            return self.respond(
                status_code=400,
                body={"message": "entity already a member"},
            )

        # Add the entity to the group
        members.append(formatted_entity_id)

        existing_group.members = members

        groups_client.put(group=existing_group)

        return self.respond(
            status_code=200,
            body={},
        )

    def remove_entity_from_group(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Removes the entity from the group with the given group_id

        Keyword arguments:
        request_body -- The request body containing the entity_id and group_id
        request_context -- The request context containing the entity_id
        """
        logging.debug("Removing entity from group")

        if not self._validate_admin_entity(request_context=request_context):
            return self.respond(
                status_code=403,
                body={"message": "access denied"},
            )

        # Validate the entity ID
        entities_client = EntitiesTableClient()

        formatted_entity_id = request_body['entity_id'].lower()

        existing_entity = entities_client.get(entity_id=formatted_entity_id)

        if not existing_entity:
            return self.respond(
                status_code=404,
                body={"message": "entity not found"},
            )

        # Validate the group ID
        groups_client = GroupsTableClient()

        formatted_group_id = request_body['group_id'].lower()

        existing_group = groups_client.get(group_id=formatted_group_id)

        if not existing_group:
            return self.respond(
                status_code=404,
                body={"message": "group not found"},
            )

        if formatted_entity_id not in existing_group.members:
            return self.respond(
                status_code=400,
                body={"message": "entity not a member"},
            )

        # Remove the entity from the group
        existing_group.members.remove(formatted_entity_id)

        groups_client.put(group=existing_group)

        return self.respond(
            status_code=200,
            body={},
        )

    def delete_group(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Deletes the group with the given group_id

        Keyword arguments:
        request_body -- The request body containing the group_id
        request_context -- The request context containing the group_id
        """
        logging.debug("Deleting group")

        if not self._validate_admin_entity(request_context=request_context):
            return self.respond(
                status_code=403,
                body={"message": "access denied"},
            )

        # Validate the group ID
        groups_client = GroupsTableClient()

        formatted_group_id = request_body['group_id'].lower()

        existing_group = groups_client.get(group_id=formatted_group_id)

        if not existing_group:
            return self.respond(
                status_code=404,
                body={"message": "group not found"},
            )

        if formatted_group_id == "system":
            return self.respond(
                status_code=400,
                body={"message": "cannot delete system group"},
            )

        # Check for group members
        if existing_group.members:
            if not request_body.get('force', default_return=False):
                logging.debug(f"Group {formatted_group_id} has members, cannot delete without force")

                return self.respond(
                    status_code=400,
                    body={"message": "group has members, cannot delete without force"},
                )

            # Force enabled remove the group from all members
            entities = EntitiesTableClient()

            for member in existing_group.members:
                entity = entities.get(entity_id=member)

                if entity:
                    logging.debug(f"Found entity: {entity.entity_id}, removing group {formatted_group_id}")

                    if entity.primary_group_id == formatted_group_id:
                        logging.debug(f"Entity {member} is the primary group of {formatted_group_id}")

                        return self.respond(
                            status_code=400,
                            body={"message": f"cannot delete group, it is the primary group of entity {member}"},
                        )

                    entity.groups.remove(formatted_group_id)

                    entities.put(entity=entity)

                else:
                    logging.debug(f"Entity not found: {member} for group {formatted_group_id}")

        # Delete the group
        groups_client.delete(group=existing_group)

        return self.respond(
            status_code=200,
            body={},
        )

    def delete_entity(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Deletes the entity with the given entity_id

        Keyword arguments:
        request_body -- The request body containing the entity_id
        request_context -- The request context containing the entity_id
        """
        logging.debug("Deleting entity")

        if not self._validate_admin_entity(request_context=request_context):
            return self.respond(
                status_code=403,
                body={"message": "access denied"},
            )

        # Validate the entity ID
        entities_client = EntitiesTableClient()

        formatted_entity_id = request_body['entity_id'].lower()

        if formatted_entity_id == "system":
            return self.respond(
                status_code=400,
                body={"message": "cannot delete system entity"},
            )

        existing_entity = entities_client.get(entity_id=formatted_entity_id)

        if not existing_entity:
            return self.respond(
                status_code=404,
                body={"message": "entity not found"},
            )

        # Delete the entity
        entities_client.delete(entity=existing_entity)

        return self.respond(
            status_code=200,
            body={},
        )

    def describe_group(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Describes the group with the given group_id

        Keyword arguments:
        request_body -- The request body containing the group_id
        request_context -- The request context containing the group_id
        """
        logging.debug("Describing group")

        formatted_group_id = request_body['group_id'].lower()

        if not self._validate_admin_entity(request_context=request_context):
            return self.respond(
                status_code=403,
                body={"message": "access denied"},
            )

        # Validate the group ID
        groups_client = GroupsTableClient()

        existing_group = groups_client.get(group_id=formatted_group_id)

        if not existing_group:
            return self.respond(
                status_code=404,
                body={"message": "group not found"},
            )

        return self.respond(
            status_code=200,
            body=existing_group.to_dict(json_compatible=True),
        )

    def describe_entity(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Describes the entity with the given entity_id

        Keyword arguments:
        request_body -- The request body containing the entity_id
        request_context -- The request context containing the entity_id
        """
        logging.debug("Describing entity")

        formatted_entity_id = request_body['entity_id'].lower()

        if not self._validate_admin_entity(request_context=request_context):

            # Validate the requesting entity is the same as the entity being described
            claims = JWTClaims.from_claims(request_context["request_claims"])

            if formatted_entity_id != claims.entity:
                return self.respond(
                    status_code=403,
                    body={"message": "access denied"},
                )

        # Validate the entity ID
        entities_client = EntitiesTableClient()

        existing_entity = entities_client.get(entity_id=formatted_entity_id)

        if not existing_entity:
            return self.respond(
                status_code=404,
                body={"message": "entity not found"},
            )

        return self.respond(
            status_code=200,
            body=existing_entity.to_dict(json_compatible=True),
        )

    def list_entities(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Lists all entities in the system

        Keyword arguments:
        request_body -- The request body containing the entity_id
        request_context -- The request context containing the entity_id
        """
        claims = JWTClaims.from_claims(request_context["request_claims"])

        entity_id = claims.entity

        entities_client = EntitiesTableClient()

        if self._validate_admin_entity(request_context=request_context):
            # If the entity has admin access, allow listing all entities
            all_entities = entities_client._all_objects()

            entities = [entity.to_dict(json_compatible=True, exclude_attribute_names=["public_key"]) for entity in all_entities]

        else:
            # Only allow listing the entity itself
            entity_obj = entities_client.get(entity_id=entity_id)

            entities = [entity_obj.to_dict(json_compatible=True, exclude_attribute_names=["public_key"])]

        return self.respond(
            status_code=200,
            body=entities,
        )

    def list_groups(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Lists all groups in the system

        Keyword arguments:
        request_body -- The request body containing the group_id
        request_context -- The request context containing the group_id
        """
        logging.debug("Listing groups")

        claims = JWTClaims.from_claims(claims=request_context["request_claims"])

        authorized_groups = claims.authorized_groups

        groups_client = GroupsTableClient()

        if self._validate_admin_entity(request_context=request_context):
            logging.debug("Admin entity ID found in authorized groups")

            all_groups = groups_client._all_objects()

            groups = [group.to_dict(json_compatible=True, exclude_attribute_names=["members"]) for group in all_groups]

        else:
            available_groups = groups_client.batch_get(group_ids=authorized_groups)

            groups = [group.to_dict(json_compatible=True, exclude_attribute_names=["members"]) for group in available_groups]

        return self.respond(
            status_code=200,
            body=groups,
        )

    def initialize(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Initializes the challenge with the admin entity's public key

        Keyword arguments:
        request_body -- The request body containing the admin entity's public key
        request_context -- The request context containing the admin entity's public key
        """
        logging.debug("Initializing the system")

        global_settings = GlobalSettings()

        system_already_initialized_setting = global_settings.get(
            namespace="ratio::core",
            setting_key="installation_initialized"
        )

        system_already_initialized = system_already_initialized_setting.value_as_type()

        logging.debug(f"System already initialized flag value: {system_already_initialized}")

        if system_already_initialized:
            logging.debug("System already initialized")

            return self.respond(
                status_code=400,
                body={"message": "unavailable"},
            )

        admin_entity_id = request_body['admin_entity_id'].lower()

        # Validate the admin entity ID
        if not self.validate_auth_id(auth_id=admin_entity_id, protected_words=_PROTECTED_WORDS):
            return self.respond(
                status_code=400,
                body={"message": "invalid entity id"},
            )

        admin_group_id = request_body.get('admin_group_id')

        if admin_group_id:
            # Validate the admin group ID
            if not self.validate_auth_id(auth_id=admin_group_id.lower(), protected_words=_PROTECTED_WORDS):
                return self.respond(
                    status_code=400,
                    body={"message": "invalid group id"},
                )

            admin_group_id = admin_group_id.lower()

        else:
            admin_group_id = admin_entity_id

        admin_group = Group(
            description="Administrator group, provides complete access to the system",
            group_id=admin_group_id,
            members=[admin_entity_id],
        )

        # Initialize the new group
        groups_client = GroupsTableClient()

        groups_client.put(group=admin_group)

        # Create a new entity with the given public key
        entities_client = EntitiesTableClient()

        entity = Entity(
            description="Administrator entity, has complete access to the system",
            entity_id=admin_entity_id,
            groups=[admin_group_id],
            home_directory="/root",
            primary_group_id=admin_group_id,
            key_last_updated_on=datetime.now(tz=utc_tz),
            public_key=request_body["admin_public_key"],
        )

        entities_client.put(entity=entity)

        logging.debug(f"Created admin entity: {admin_entity_id}")

        # Create token on behalf of the admin entity
        jwt_manager = InternalJWTManager(
            kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id"),
        )

        token, _ = jwt_manager.create_token(
            authorized_groups=entity.groups,
            entity=admin_entity_id,
            custom_claims={
                "auth_method": "challenge_response",
                "challenge_timestamp": datetime.now(tz=utc_tz).isoformat(),
                "nonce": secrets.token_urlsafe(16),
            },
            home="/root",
            is_admin=True,
            primary_group=admin_group_id,
        )

        # Create home directory for the admin entity
        storage_client = RatioInternalClient(
            service_name="storage_manager",
            token=token,
        )

        root_dir_req = ObjectBody(
            body={
                "file_path": "/root",
                "file_type": "ratio::directory",
                "permissions": "750",
            },
            schema=PutFileRequest,
        )

        # Check if the home directory already exists
        describe_req = ObjectBody(
            body={
                "file_path": "/root",
            },
            schema=DescribeFileRequest,
        )

        describe_res = storage_client.request(path="/storage/describe_file", request=describe_req)

        # Only create the home directory if it doesn't exist
        if describe_res.status_code != 200:
            logging.debug("Home directory does not exist ... creating")

            # Create the home directory
            resp = storage_client.request(path="/storage/put_file", request=root_dir_req)

            if resp.status_code != 200:
                logging.error(f"Failed to create admin home directory: {resp.response_body}")

                return self.respond(
                    status_code=500,
                    body={"message": f"failed to create home directory: {resp.response_body}"},
                )

        # Save the admin entity id
        admin_entity_id_setting = global_settings.get(
            namespace="ratio::core",
            setting_key="admin_entity_id"
        )

        admin_entity_id_setting.setting_value = admin_entity_id

        global_settings.put(admin_entity_id_setting)

        # Save the admin group id
        admin_group_id_setting = global_settings.get(
            namespace="ratio::core",
            setting_key="admin_group_id"
        )

        admin_group_id_setting.setting_value = admin_group_id

        global_settings.put(admin_group_id_setting)

        # Initialize the system entity and group

        sys_group = Group(
            group_id="system",
            description="System group, provides system access to resources",
            members=["system"],
        )

        # Create the new group
        groups_client.put(group=sys_group)

        sys_entity = Entity(
            entity_id="system",
            description="System entity, provides system access to resources",
            groups=["system"],
            home_directory="/root",
            primary_group_id="system",
        )

        entities_client.put(entity=sys_entity)

        # Save the system already initialized setting
        system_already_initialized_setting.setting_value = 'true'

        global_settings.put(system_already_initialized_setting)

        return self.respond(
            status_code=201,
            body={
                "admin_group_id": admin_group_id,
                "admin_entity_id": admin_entity_id,
            },
        )

    def rotate_entity_key(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Rotates the public key of the entity

        Keyword arguments:
        request_body -- The request body containing the entity_id and new public_key
        request_context -- The request context containing the entity_id
        """
        logging.debug("Rotating entity key")

        # Validate either the entity of the request or the admin entity
        claims = JWTClaims.from_claims(request_context["request_claims"])

        requesting_entity = claims.entity

        changing_entity = request_body.get("entity_id")

        if changing_entity:
            changing_entity = changing_entity.lower()

            if requesting_entity != changing_entity and not self._validate_admin_entity(request_context=request_context):
                return self.respond(
                    status_code=403,
                    body={"message": "access denied"},
                )

        else:
            changing_entity = requesting_entity

        entities = EntitiesTableClient()

        entity_obj = entities.get(entity_id=changing_entity)

        if not entity_obj:
            return self.respond(
                status_code=404,
                body={"message": "entity not found"},
            )

        # Update the public key
        entity_obj.public_key = request_body['public_key']

        entity_obj.key_last_updated_on = datetime.now(tz=utc_tz)

        entities.put(entity=entity_obj)

        return self.respond(
            status_code=200,
            body={
                "entity_id": entity_obj.entity_id,
                "public_key": entity_obj.public_key,
            },
        )

    def token(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Verifies the challenge and returns a token
        Keyword arguments:
        request_body -- The request body containing the challenge
        request_context -- The request context containing the challenge
        """
        # Decode the challenge
        jwt_manager = InternalJWTManager(
            expiry_minutes=setting_value(namespace="ratio::core", setting_key="token_active_minutes"),
            kms_key_id=setting_value(namespace="ratio::core", setting_key="internal_signing_kms_key_id"),
        )

        decoded_challenge = jwt_manager.decode_segment(segment=request_body["challenge"])

        expires_at = datetime.fromisoformat(decoded_challenge["expires_at"])

        if datetime.now(tz=utc_tz) > expires_at:
            return self.respond(status_code=403, body={"message": "invalid challenge"})

        entity_id = decoded_challenge["entity_id"]

        logging.debug(f"Looking for entity id: {entity_id}")

        entities_client = EntitiesTableClient()

        entity = entities_client.get(entity_id=entity_id)

        if not entity:
            logging.debug(f"Entity not found: {entity_id}")

            return self.respond(status_code=403, body={"message": "access denied"})

        if not entity.enabled:
            logging.debug(f"Entity is disabled: {entity_id}")

            return self.respond(status_code=403, body={"message": "access denied"})

        entity_public_key = entity.public_key

        if entity_public_key:
            # Use JWT manager to verify entity signature
            logging.debug(f"Verifying entity signature with public key: {entity_public_key}")

            is_valid_entity = jwt_manager.verify_with_public_key(
                data=request_body['challenge'],
                public_key=entity_public_key,
                signature=request_body['entity_signature'],
            )

        else:
            # If no public key is available, we cannot verify the entity signature
            is_valid_entity = False

        # Verify system signature
        is_valid_system = jwt_manager.verify_with_kms(
            data=request_body['challenge'],
            signature=request_body['system_signature']
        )

        # Only proceed if both signatures are valid
        if not (is_valid_entity and is_valid_system):
            logging.debug(f"Invalid signatures detected: entity ({is_valid_entity}), system ({is_valid_system})")

            return self.respond(status_code=403, body={"message": "access denied"})

        # Check if the entity is admin or part of the admin group
        admin_entity_id = setting_value(namespace="ratio::core", setting_key="admin_entity_id")

        admin_group_id = setting_value(namespace="ratio::core", setting_key="admin_group_id")

        if entity_id == admin_entity_id or admin_group_id in entity.groups:
            logging.debug(f"Entity is admin or part of the admin group: {entity_id}")

            is_admin = True

        else:
            logging.debug(f"Entity is not admin or part of the admin group: {entity_id}")

            is_admin = False

        # Create JWT token with appropriate claims
        token, token_expires = jwt_manager.create_token(
            authorized_groups=entity.groups,
            entity=entity.entity_id,
            custom_claims={
                "auth_method": "challenge_response",
                "challenge_timestamp": decoded_challenge["timestamp"],
                "nonce": decoded_challenge["nonce"],
            },
            home=entity.home_directory,
            primary_group=entity.primary_group_id,
            is_admin=is_admin,
        )

        return self.respond(
            body={
                "expires_at": token_expires.isoformat(),
                "token": token,
            },
            status_code=201,
        )