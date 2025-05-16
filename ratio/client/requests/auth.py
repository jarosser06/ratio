from typing import List, Optional

from ratio.client.client import (
    RequestAttributeType,
    RequestBodyAttribute,
    RequestBody,
)


class InitializeRequest(RequestBody):
    """
    Initialize the system with the admin information

    This can only be called once, and it is used to set up the admin entity
    """
    path = '/initialize'

    attribute_definitions = [
        RequestBodyAttribute(
            name="admin_entity_id",
            optional=False,
            attribute_type=RequestAttributeType.STRING,
        ),
        RequestBodyAttribute(
            name="admin_group_id",
            optional=True,
            attribute_type=RequestAttributeType.STRING,
        ),
        RequestBodyAttribute(
            name="admin_public_key",
            optional=False,
            attribute_type=RequestAttributeType.STRING,
        ),
    ]

    def __init__(self, admin_entity_id: str, admin_public_key: str, admin_group_id: Optional[str] = None):
        """
        Initialize the initialize request

        Keyword arguments:
        admin_entity_id -- The entity ID of the admin
        admin_public_key -- The public key of the admin
        admin_group_id -- The group ID of the admin
        """
        super().__init__(
            admin_entity_id=admin_entity_id,
            admin_public_key=admin_public_key,
            admin_group_id=admin_group_id
        )


class CreateEntityRequest(RequestBody):
    """
    Create a new entity with the given public key
    """
    path = '/auth/create_entity'

    requires_auth = True
    
    attribute_definitions = [
        RequestBodyAttribute(
            name="create_group",
            attribute_type=RequestAttributeType.BOOLEAN,
            optional=True,
            default=True,
        ),
        RequestBodyAttribute(
            name="create_home",
            attribute_type=RequestAttributeType.BOOLEAN,
            optional=True,
            default=True,
        ),
        RequestBodyAttribute(
            name="description",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="entity_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="groups",
            attribute_type=RequestAttributeType.LIST,
            optional=True,
        ),
        RequestBodyAttribute(
            name="home_directory",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="primary_group_id",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="public_key",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, entity_id: str, public_key: str, create_group: bool = True, create_home: bool = True, description: Optional[str] = None,
                 groups: Optional[List[str]] = None, home_directory: Optional[str] = None, primary_group_id: Optional[str] = None):
        """
        Initialize the create entity request

        Keyword arguments:
        entity_id -- The ID of the entity to create
        public_key -- The public key of the entity
        description -- Optional description of the entity
        groups -- Optional list of groups to add the entity to
        create_group -- Whether to create a group for the entity
        create_home -- Whether to create a home directory for the entity. If true and the home_directory is not set, a default home directory will be created
        primary_group_id -- The ID of the primary group for the entity
        """
        super().__init__(
            entity_id=entity_id,
            public_key=public_key,
            description=description,
            groups=groups,
            create_group=create_group,
            create_home=create_home,
            home_directory=home_directory,
            primary_group_id=primary_group_id
        )


class CreateGroupRequest(RequestBody):
    """
    Create a new group with the given group_id
    """
    path = '/auth/create_group'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="description",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="group_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, group_id: str, description: Optional[str] = None):
        """
        Initialize the create group request

        Keyword arguments:
        group_id -- The ID of the group to create
        description -- Optional description of the group
        """
        super().__init__(
            group_id=group_id,
            description=description
        )


class AddEntityToGroupRequest(RequestBody):
    """
    Add an entity to a group with the given group_id
    """
    path = '/auth/add_entity_to_group'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="entity_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="group_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, entity_id: str, group_id: str):
        """
        Initialize the add entity to group request

        Keyword arguments:
        entity_id -- The ID of the entity to add
        group_id -- The ID of the group to add the entity to
        """
        super().__init__(
            entity_id=entity_id,
            group_id=group_id
        )


class RemoveEntityFromGroupRequest(RequestBody):
    """
    Remove an entity from a group with the given group_id
    """
    path = '/auth/remove_entity_from_group'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="entity_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="group_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, entity_id: str, group_id: str):
        """
        Initialize the remove entity from group request

        Keyword arguments:
        entity_id -- The ID of the entity to remove
        group_id -- The ID of the group to remove the entity from
        """
        super().__init__(
            entity_id=entity_id,
            group_id=group_id
        )


class DeleteGroupRequest(RequestBody):
    """
    Delete a group with the given group_id
    """
    path = '/auth/delete_group'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="group_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
        RequestBodyAttribute(
            name="force",
            attribute_type=RequestAttributeType.BOOLEAN,
            optional=True,
            default=False,
        ),
    ]

    def __init__(self, group_id: str, force: Optional[bool] = False):
        """
        Initialize the delete group request

        Keyword arguments:
        group_id -- The ID of the group to delete
        force -- Whether to force delete the group
        """
        super().__init__(
            group_id=group_id,
            force=force,
        )


class DeleteEntityRequest(RequestBody):
    """
    Delete an entity with the given entity_id
    """
    path = '/auth/delete_entity'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="entity_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, entity_id: str):
        """
        Initialize the delete entity request

        Keyword arguments:
        entity_id -- The ID of the entity to delete
        """
        super().__init__(
            entity_id=entity_id
        )


class DescribeGroupRequest(RequestBody):
    """
    Describe a group with the given group_id
    """
    path = '/auth/describe_group'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="group_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, group_id: str):
        """
        Initialize the describe group request

        Keyword arguments:
        group_id -- The ID of the group to describe
        """
        super().__init__(
            group_id=group_id
        )


class DescribeEntityRequest(RequestBody):
    """
    Describe an entity with the given entity_id
    """
    path = '/auth/describe_entity'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="entity_id",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, entity_id: str):
        """
        Initialize the describe entity request

        Keyword arguments:
        entity_id -- The ID of the entity to describe
        """
        super().__init__(
            entity_id=entity_id
        )


class ListEntitiesRequest(RequestBody):
    """
    List all entities the calling entity has access to view
    """
    attribute_definitions = []

    path = '/auth/list_entities'

    requires_auth = True

    def __init__(self):
        """
        Initialize the list entities request
        """
        super().__init__()


class ListGroupsRequest(RequestBody):
    """
    List all groups the calling entity has access to view
    """
    path = '/auth/list_groups'
    
    attribute_definitions = []

    requires_auth = True

    def __init__(self):
        """
        Initialize the list groups request
        """
        super().__init__()


class RotateEntityKeyRequest(RequestBody):
    """
    Rotate the public key for an entity
    """
    path = '/auth/rotate_entity_key'

    requires_auth = True

    attribute_definitions = [
        RequestBodyAttribute(
            name="entity_id",
            attribute_type=RequestAttributeType.STRING,
            optional=True,
        ),
        RequestBodyAttribute(
            name="public_key",
            attribute_type=RequestAttributeType.STRING,
            optional=False,
        ),
    ]

    def __init__(self, entity_id: str, public_key: str):
        """
        Initialize the rotate entity key request

        Keyword arguments:
        entity_id -- The ID of the entity to rotate the key for
        public_key -- The new public key for the entity
        """
        super().__init__(
            entity_id=entity_id,
            public_key=public_key
        )