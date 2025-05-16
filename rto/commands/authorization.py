import json

from argparse import ArgumentParser

from ratio.client.client import Ratio
from ratio.client.requests.auth import (
    AddEntityToGroupRequest,
    CreateEntityRequest,
    CreateGroupRequest,
    DeleteGroupRequest,
    DeleteEntityRequest,
    DescribeGroupRequest,
    DescribeEntityRequest,
    ListEntitiesRequest,
    ListGroupsRequest,
    RemoveEntityFromGroupRequest,
    RotateEntityKeyRequest,
)

from rto.commands.base import RTOCommand, RTOErrorMessage
from rto.keys import generate_rsa_key_pair


class CreateEntityCommand(RTOCommand):
    """
    Create a new entity with the given public key
    """
    name = "create-entity"
    description = "Create a new entity in the system"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("entity_id", help="The ID of the entity to create", type=str)

        parser.add_argument("--public-key", help="Path to the public key file (if not provided, keys will be generated)", type=str)

        parser.add_argument("--description", help="Optional description of the entity", type=str)

        parser.add_argument("--groups", help="Comma-separated list of groups to add the entity to", type=str)

        parser.add_argument("--no-create-group", help="Don't create a group for the entity", action="store_false", dest="create_group", default=True)

        parser.add_argument("--no-create-home", help="Don't create a home directory for the entity", action="store_false", dest="create_home", default=True)

        parser.add_argument("--home-directory", help="Custom home directory path for the entity", type=str)

        parser.add_argument("--primary-group-id", help="The ID of the primary group for the entity", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Get or generate key pair
        public_key_value = None
        private_key_value = None

        if args.public_key:
            try:
                with open(args.public_key, "rb") as f:
                    public_key_value = f.read().decode("utf-8")

            except Exception as e:
                raise RTOErrorMessage(f"Error reading public key file: {e}")

        else:
            # Generate keys
            private_key_value, public_key_value = generate_rsa_key_pair()

            public_key_value = public_key_value.decode("utf-8")

        # Convert comma-separated groups to list if provided
        groups = args.groups.split(",") if args.groups else None

        # Create the request
        request = CreateEntityRequest(
            entity_id=args.entity_id,
            public_key=public_key_value,
            description=args.description,
            groups=groups,
            create_group=args.create_group,
            create_home=args.create_home,
            home_directory=args.home_directory,
            primary_group_id=args.primary_group_id
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code not in [200, 201]:
            if resp.status_code == 409:
                raise RTOErrorMessage(f"Entity {args.entity_id} already exists")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error creating entity: {resp.status_code}")

        # Save the keys if we generated them
        if private_key_value:
            try:
                # Save private key
                private_key_filename = f"{args.entity_id}_priv_key.pem"

                with open(private_key_filename, "wb") as f:
                    f.write(private_key_value)

                # Save public key
                public_key_filename = f"{args.entity_id}_pub_key"

                with open(public_key_filename, "wb") as f:
                    f.write(public_key_value.encode("utf-8"))

                print(f"Keys saved to {private_key_filename} and {public_key_filename}")

            except Exception as e:
                raise RTOErrorMessage(f"Error saving keys: {e}")

        if args.json:
            print(resp.response_body)

            return

        print(f"Entity {args.entity_id} created successfully")


class CreateGroupCommand(RTOCommand):
    """
    Create a new group
    """
    name = "create-group"
    description = "Create a new group in the system"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("group_id", help="The ID of the group to create", type=str)

        parser.add_argument("--description", help="Optional description of the group", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Create the request
        request = CreateGroupRequest(
            group_id=args.group_id,
            description=args.description
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code not in [200, 201]:
            if resp.status_code == 409:
                raise RTOErrorMessage(f"Group {args.group_id} already exists")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error creating group: {resp.status_code}")

        if args.json:
            print(resp.response_body)

            return

        print(f"Group {args.group_id} created successfully")


class AddEntityToGroupCommand(RTOCommand):
    """
    Add an entity to a group
    """
    name = "add-to-group"
    description = "Add an entity to a group"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("entity_id", help="The ID of the entity to add to the group", type=str)

        parser.add_argument("group_id", help="The ID of the group to add the entity to", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Create the request
        request = AddEntityToGroupRequest(
            entity_id=args.entity_id,
            group_id=args.group_id
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code not in [200, 201, 204]:
            if resp.status_code == 404:
                # Determine which resource wasn't found
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"{error_msg.get("message", "Resource not found")}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Entity or group not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to add entity to group")

            elif resp.status_code == 400:
                try:

                    error_msg = json.loads(resp.response_body)
                    raise RTOErrorMessage(f"Invalid request: {error_msg.get("message", resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error adding entity to group: {resp.status_code}")

        if args.json:
            print(resp.response_body)

            return

        print(f"Entity {args.entity_id} added to group {args.group_id} successfully")


class RemoveEntityFromGroupCommand(RTOCommand):
    """
    Remove an entity from a group
    """
    name = "remove-from-group"
    description = "Remove an entity from a group"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("entity_id", help="The ID of the entity to remove from the group", type=str)

        parser.add_argument("group_id", help="The ID of the group to remove the entity from", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Create the request
        request = RemoveEntityFromGroupRequest(
            entity_id=args.entity_id,
            group_id=args.group_id
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code not in [200, 201, 204]:
            if resp.status_code == 404:
                # Determine which resource wasn't found
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"{error_msg.get('message', 'Resource not found')}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Entity or group not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to remove entity from group")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    message = error_msg.get('message', resp.response_body)
                    # Check if it's the "not a member" error
                    if "not a member" in message:
                        raise RTOErrorMessage(f"Entity {args.entity_id} is not a member of group {args.group_id}")

                    else:
                        raise RTOErrorMessage(f"Invalid request: {message}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error removing entity from group: {resp.status_code}")

        if args.json:
            print(resp.response_body)

            return

        print(f"Entity {args.entity_id} removed from group {args.group_id} successfully")


class DeleteGroupCommand(RTOCommand):
    """
    Delete a group
    """
    name = "delete-group"
    description = "Delete a group from the system"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("group_id", help="The ID of the group to delete", type=str)

        parser.add_argument("--force", help="Force deletion even if group has members", action="store_true", default=False)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Add confirmation if not forced
        if not args.force:
            confirmation = input(f"Are you sure you want to delete group '{args.group_id}'? This action cannot be undone. (y/N): ")

            if confirmation.lower() != 'y':
                print("Operation cancelled.")

                return

        # Create the request
        request = DeleteGroupRequest(
            group_id=args.group_id,
            force=args.force
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code not in [200, 201, 204]:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Group {args.group_id} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to delete group {args.group_id}")

            elif resp.status_code == 409:
                raise RTOErrorMessage(f"Group {args.group_id} has members. Use --force to delete anyway.")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error deleting group: {resp.status_code}")

        if args.json:
            print(resp.response_body)

            return

        print(f"Group {args.group_id} deleted successfully")


class DeleteEntityCommand(RTOCommand):
    """
    Delete an entity
    """
    name = "delete-entity"
    description = "Delete an entity from the system"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("entity_id", help="The ID of the entity to delete", type=str)

        parser.add_argument("--force", help="Force deletion without confirmation", action="store_true", default=False)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Add confirmation if not forced
        if not args.force:
            confirmation = input(f"Are you sure you want to delete entity '{args.entity_id}'? This action cannot be undone. (y/N): ")

            if confirmation.lower() != 'y':
                print("Operation cancelled.")

                return

        # Create the request
        request = DeleteEntityRequest(
            entity_id=args.entity_id
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code not in [200, 201, 204]:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Entity {args.entity_id} not found")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to delete entity {args.entity_id}")

            else:
                raise RTOErrorMessage(f"Error deleting entity: {resp.status_code}")

        if args.json:
            print(resp.response_body)

            return

        print(f"Entity {args.entity_id} deleted successfully")


class DescribeGroupCommand(RTOCommand):
    """
    Describe a group
    """
    name = "describe-group"
    description = "Get detailed information about a group"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("group_id", help="The ID of the group to describe", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Create the request
        request = DescribeGroupRequest(
            group_id=args.group_id
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Group {args.group_id} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to describe group {args.group_id}")

            else:
                raise RTOErrorMessage(f"Error describing group: {resp.status_code}")

        if args.json:
            print(resp.response_body)

            return

        # Format and display group information
        try:
            group_data = json.loads(resp.response_body) if isinstance(resp.response_body, str) else resp.response_body

            self._display_group_info(group_data)

        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

    def _display_group_info(self, group_data):
        """
        Display formatted group information

        Keyword arguments:
        group_data -- The group data to display
        """
        print(f"Group ID: {group_data.get('group_id', 'N/A')}")

        print(f"Description: {group_data.get('description', 'N/A')}")

        if 'created_on' in group_data:
            print(f"Created On: {group_data.get('created_on')}")

        # Display members if present
        members = group_data.get('members', [])

        if members:
            print("\nMembers:")

            for member in members:
                print(f"  - {member}")

        else:
            print("\nMembers: None")


class DescribeEntityCommand(RTOCommand):
    """
    Describe an entity
    """
    name = "describe-entity"
    description = "Get detailed information about an entity"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("entity_id", help="The ID of the entity to describe", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Create the request
        request = DescribeEntityRequest(
            entity_id=args.entity_id
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Entity {args.entity_id} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to describe entity {args.entity_id}")

            else:
                raise RTOErrorMessage(f"Error describing entity: {resp.status_code}")

        if args.json:
            print(resp.response_body)

            return

        # Format and display entity information
        try:
            entity_data = json.loads(resp.response_body) if isinstance(resp.response_body, str) else resp.response_body

            self._display_entity_info(entity_data)

        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

    def _display_entity_info(self, entity_data):
        """
        Display formatted entity information

        Keyword arguments:
        entity_data -- The entity data to display
        """
        print(f"Entity ID: {entity_data.get('entity_id', 'N/A')}")

        print(f"Description: {entity_data.get('description', 'N/A')}")

        print(f"Primary Group ID: {entity_data.get('primary_group_id', 'N/A')}")

        print(f"Home Directory: {entity_data.get('home_directory', 'N/A')}")

        # Display groups
        groups = entity_data.get('groups', [])

        if groups:
            print("\nGroups:")

            for group in groups:
                print(f"  - {group}")

        else:
            print("\nGroups: None")

        # Display additional metadata if present
        metadata = entity_data.get('metadata', {})

        if metadata:
            print("\nMetadata:")

            for key, value in metadata.items():
                print(f"  {key}: {value}")


class ListEntitiesCommand(RTOCommand):
    """
    List all entities the calling entity has access to view
    """
    name = "list-entities"
    description = "List entities in the system"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

        parser.add_argument("--detailed", "-d", help="Show detailed entity information", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Create the request
        request = ListEntitiesRequest()

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RTOErrorMessage("Permission denied: Not authorized to list entities")

            else:
                raise RTOErrorMessage(f"Error listing entities: {resp.status_code}")

        if args.json:
            print(resp.response_body)

            return

        # Format and display entities information
        try:
            entities = resp.response_body

            if isinstance(entities, str):
                entities = json.loads(entities)

            self._display_entities(entities, detailed=args.detailed)

        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

    def _display_entities(self, entities, detailed=False):
        """
        Display formatted entities information

        Keyword arguments:
        entities -- The list of entity objects to display
        detailed -- Whether to show detailed information
        """
        if not entities:
            print("No entities found.")
            return

        if detailed:
            # Display full details for each entity
            for entity in entities:
                print(f"\nEntity ID: {entity.get('entity_id', 'N/A')}")

                print(f"Description: {entity.get('description', 'N/A')}")

                print(f"Primary Group: {entity.get('primary_group_id', 'N/A')}")

                print(f"Home Directory: {entity.get('home_directory', 'N/A')}")

                print(f"Enabled: {entity.get('enabled', 'N/A')}")

                print(f"Created On: {entity.get('created_on', 'N/A')}")

                print(f"Key Last Updated: {entity.get('key_last_updated_on', 'N/A')}")

                # Display groups
                groups = entity.get('groups', [])

                if groups:
                    print("Groups:")

                    for group in groups:
                        print(f"  - {group}")
                
                print("-" * 40)  # Separator between entities
        else:
            # Display simple table with basic information
            # Calculate column widths for nice alignment
            id_width = max(max((len(e.get('entity_id', '')) for e in entities), default=8), 8)

            desc_width = max(max((len(str(e.get('description', ''))) for e in entities), default=11), 11)

            group_width = max(max((len(e.get('primary_group_id', '')) for e in entities), default=12), 12)

            # Print headers
            print(f"{'ENTITY ID':<{id_width}} | {'DESCRIPTION':<{desc_width}} | {'PRIMARY GROUP':<{group_width}} | HOME DIRECTORY")

            print(f"{'-' * id_width}-+-{'-' * desc_width}-+-{'-' * group_width}-+-{'-' * 15}")

            # Print each entity
            for entity in entities:
                entity_id = entity.get('entity_id', 'N/A')

                description = str(entity.get('description', ''))

                primary_group = entity.get('primary_group_id', 'N/A')

                home_dir = entity.get('home_directory', 'N/A')

                print(f"{entity_id:<{id_width}} | {description:<{desc_width}} | {primary_group:<{group_width}} | {home_dir}")


class ListGroupsCommand(RTOCommand):
    """
    List all groups the calling entity has access to view
    """
    name = "list-groups"
    description = "List groups in the system"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)
        parser.add_argument("--detailed", "-d", help="Show detailed group information", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Create the request
        request = ListGroupsRequest()

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RTOErrorMessage("Permission denied: Not authorized to list groups")
            else:
                raise RTOErrorMessage(f"Error listing groups: {resp.status_code}")

        if args.json:
            print(resp.response_body)
            return

        # Format and display groups information
        try:
            groups = resp.response_body
            if isinstance(groups, str):
                groups = json.loads(groups)
                
            self._display_groups(groups, detailed=args.detailed)
        except json.JSONDecodeError:
            raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

    def _display_groups(self, groups, detailed=False):
        """
        Display formatted groups information

        Keyword arguments:
        groups -- The list of group objects to display
        detailed -- Whether to show detailed information
        """
        if not groups:
            print("No groups found.")
            return

        if detailed:
            # Display full details for each group
            for group in groups:
                print(f"\nGroup ID: {group.get('group_id', 'N/A')}")
                print(f"Description: {group.get('description', 'N/A')}")
                print(f"Created On: {group.get('created_on', 'N/A')}")
                
                # Display members if present
                members = group.get('members', [])
                if members:
                    print("Members:")
                    for member in members:
                        print(f"  - {member}")
                
                print("-" * 40)  # Separator between groups
        else:
            # Display simple table with basic information
            # Calculate column widths for nice alignment
            id_width = max(max((len(g.get('group_id', '')) for g in groups), default=8), 8)
            desc_width = max(max((len(str(g.get('description', ''))) for g in groups), default=11), 11)
            
            # Print headers
            print(f"{'GROUP ID':<{id_width}} | {'DESCRIPTION':<{desc_width}}")
            print(f"{'-' * id_width}-+-{'-' * desc_width}")
            
            # Print each group
            for group in groups:
                group_id = group.get('group_id', 'N/A')
                description = str(group.get('description', ''))
                
                print(f"{group_id:<{id_width}} | {description:<{desc_width}}")


class RotateEntityKeyCommand(RTOCommand):
    """
    Rotate the public key for an entity
    """
    name = "rotate-key"
    description = "Rotate the public key for an entity"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("entity_id", help="The ID of the entity to rotate the key for", type=str)

        parser.add_argument("--public-key", help="Path to the new public key file (if not provided, new keys will be generated)", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, args):
        """
        Execute the command.
        """
        # Get or generate new key pair
        public_key_value = None

        private_key_value = None

        if args.public_key:
            try:
                with open(args.public_key, "rb") as f:
                    public_key_value = f.read().decode("utf-8")

            except Exception as e:
                raise RTOErrorMessage(f"Error reading public key file: {e}")
        else:
            # Generate new keys
            private_key_value, public_key_value = generate_rsa_key_pair()

            public_key_value = public_key_value.decode("utf-8")

        # Create the request
        request = RotateEntityKeyRequest(
            entity_id=args.entity_id,
            public_key=public_key_value
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code not in [200, 201, 204]:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Entity {args.entity_id} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to rotate key for {args.entity_id}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error rotating key: {resp.status_code}")

        # Save the keys if we generated them
        if private_key_value:
            try:
                # Save private key
                private_key_filename = f"{args.entity_id}_priv_key_new.pem"
                with open(private_key_filename, "wb") as f:
                    f.write(private_key_value)

                # Save public key
                public_key_filename = f"{args.entity_id}_pub_key_new"

                with open(public_key_filename, "wb") as f:
                    f.write(public_key_value.encode("utf-8"))

                print(f"New keys saved to {private_key_filename} and {public_key_filename}")

                print(f"IMPORTANT: Update your configuration to use the new private key for entity {args.entity_id}")
            except Exception as e:
                RTOErrorMessage(f"Error saving keys: {e}")

        if args.json:
            print(resp.response_body)

            return

        print(f"Key for entity {args.entity_id} rotated successfully")