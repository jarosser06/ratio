import json
import os
from argparse import ArgumentParser

from ratio.client.client import Ratio
from rto.commands.base import RTOCommand, RTOErrorMessage
from rto.config import RTOConfig


class ConfigureCommand(RTOCommand):
    """
    Configure RTO CLI settings
    """
    name = "configure"
    description = "Configure RTO CLI settings and credentials"
    requires_authentication = False

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """Configure the command line argument parser."""
        parser.add_argument("--name", help="Profile name to configure (default: default)", default="default")

        parser.add_argument("--config-entity", help="Entity ID to use for this profile", type=str)

        parser.add_argument("--config-app", help="App name to use for this profile", type=str)

        parser.add_argument("--config-deployment", help="Deployment ID to use for this profile", type=str)

        parser.add_argument("--config-key", help="Path to private key file for this profile", type=str)

        parser.add_argument("--set-default", help="Set as default profile", action="store_true", default=False)

        parser.add_argument("--non-interactive", help="Don't prompt for missing values", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- Ratio client instance
        args -- the parsed arguments
        """
        # Use the distinct argument name
        profile_name = args.name

        # If profile exists, load values as defaults
        profile_exists = profile_name in config._config["profiles"] 

        profile_values = {}

        if profile_exists:
            profile_values = config.get_profile(profile_name)

            print(f"Updating existing profile: {profile_name}")

        else:
            print(f"Creating new profile: {profile_name}")

        # Get entity ID
        entity_id = args.config_entity

        if not entity_id and not args.non_interactive:
            default = profile_values.get("entity_id", "admin")

            entity_id = input(f"Entity ID [{default}]: ") or default

        # Get deployment ID
        deployment_id = args.config_deployment

        if not deployment_id and not args.non_interactive:
            default = profile_values.get("deployment_id", os.getenv("DA_VINCI_DEPLOYMENT_ID", "dev"))

            deployment_id = input(f"Deployment ID [{default}]: ") or default

        # Get private key path
        private_key_path = args.config_key

        if not private_key_path and not args.non_interactive:
            default = profile_values.get("private_key_path", os.path.expanduser("~/.rto/private_key.pem"))

            private_key_path = input(f"Private key path [{default}]: ") or default

        # Save the profile
        config.add_profile(
            profile_name=profile_name,
            entity_id=entity_id,
            deployment_id=deployment_id,
            private_key_path=private_key_path,
            set_default=args.set_default
        )

        print(f"Profile '{profile_name}' saved successfully.")

        if args.set_default:
            print(f"Set '{profile_name}' as the default profile.")


class GetCurrentProfileCommand(RTOCommand):
    """
    Get current profile information
    """
    name = "get-profile"

    description = "Get current profile information"

    requires_authentication = False  # No auth needed to view profile

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.
        """
        parser.add_argument("--json", help="Output as JSON", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.
        """
        # Get profile info
        profile_name = args.profile or config.get_default_profile()

        if not profile_name:
            print("No profile selected or configured")

            return

        try:
            profile_data = config.get_profile(profile_name)

            if args.json:
                # Add profile name to the output
                output = {"profile_name": profile_name}

                output.update(profile_data)

                print(json.dumps(output, indent=2))

            else:
                print(f"Profile Name: {profile_name}")

                for key, value in profile_data.items():
                    print(f"{key}: {value}")

        except ValueError as e:
            raise RTOErrorMessage(f"Error getting profile: {e}")