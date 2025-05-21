import json
import sys

from argparse import ArgumentParser

from ratio.client.client import Ratio
from ratio.client.requests.auth import InitializeRequest

from rto.commands.base import RTOCommand
from rto.config import RTOConfig
from rto.keys import generate_rsa_key_pair


class InitializeCommand(RTOCommand):
    """
    Initialize the ratio system
    """
    name = "init"
    description = "Initialize the ratio system"
    requires_authentication = False

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        No Op for this command
        """
        parser.add_argument("--public-key", help="Path to the public key file", type=str, required=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.
        """
        public_key = args.public_key

        private_key_value = None

        if public_key:
            with open(public_key, "rb") as f:
                public_key_value = f.read()

        else:
            private_key_value, public_key_value = generate_rsa_key_pair()

        # Create the request
        request = InitializeRequest(
            admin_entity_id=args.entity,
            admin_public_key=public_key_value.decode("utf-8"),
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 201:
            if resp.status_code == 400:
                loaded_error_message = json.loads(resp.response_body)

                if "unavailable" == loaded_error_message["message"]:
                    print("The ratio system is already initialized.")

                else:
                    print(f"Error: {loaded_error_message['message']}", file=sys.stderr)

            else:
                raise Exception(f"Error: {resp.status_code} - {resp.response_body}")

        print("Ratio system initialized successfully.")

        with open("private_key.pem", "wb") as pem_file:
            pem_file.write(private_key_value)