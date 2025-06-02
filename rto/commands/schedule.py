import json
from argparse import ArgumentParser
from datetime import datetime

from ratio.client.client import Ratio
from ratio.client.requests.scheduler import (
    CreateSubscriptionRequest,
    DeleteSubscriptionRequest,
    DescribeSubscriptionRequest,
    ListSubscriptionsRequest,
)

from rto.commands.base import RTOCommand, RTOErrorMessage
from rto.config import RTOConfig


class CreateSubscriptionCommand(RTOCommand):
    """
    Create a new subscription
    """
    name = "create-subscription"
    alias = "mksub"
    description = "Create a new subscription to trigger an agent when events occur"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("event_type", help="Type of event to subscribe to (e.g., filesystem_update, process_start, file_type_update)", type=str)
        
        parser.add_argument("agent_definition", help="Path to the agent definition that will be executed", type=str)

        parser.add_argument("--execution-working-directory", help="Working directory for agent execution", type=str)

        parser.add_argument("--expiration", help="Date and time when the subscription expires (ISO format: YYYY-MM-DDTHH:MM:SS)", type=str)

        parser.add_argument("--owner", help="Owner of the subscription (admin only)", type=str)

        parser.add_argument("--single-use", help="Subscription triggers only once then is deleted", action="store_true", default=False)

        parser.add_argument("--filter", help="Filter conditions as JSON string", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        config -- The RTO config
        args -- The command line arguments
        """
        # Resolve paths
        agent_definition_path = config.resolve_path(args.agent_definition)

        # Parse expiration if provided
        expiration = None

        if args.expiration:
            try:
                expiration = datetime.fromisoformat(args.expiration)

            except ValueError:
                raise RTOErrorMessage(f"Invalid expiration format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)")

        # Parse filter conditions
        filter_conditions = None

        if args.filter:
            try:
                filter_conditions = json.loads(args.filter)

            except json.JSONDecodeError:
                raise RTOErrorMessage("Invalid JSON format for --filter argument")

        # Create the request
        request = CreateSubscriptionRequest(
            event_type=args.event_type,
            agent_definition=agent_definition_path,
            execution_working_directory=args.execution_working_directory,
            expiration=expiration,
            owner=args.owner,
            single_use=args.single_use,
            filter_conditions=filter_conditions
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 201:
            if resp.status_code == 403:
                raise RTOErrorMessage("Permission denied: Not authorized to create subscriptions")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error creating subscription: {resp.status_code}")

        # Get the response data
        subscription_data = resp.response_body

        # Handle JSON output if requested
        if args.json:
            try:
                print(json.dumps(subscription_data, indent=2))

            except json.JSONDecodeError:
                raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

            return

        # Display success message and subscription details
        subscription_id = subscription_data.get("subscription_id", "Unknown")

        print(f"Subscription created successfully with ID: {subscription_id}")

        # Show additional details
        print("\nSubscription Details:")

        print(f"  Event Type: {subscription_data.get('event_type', args.event_type)}")

        print(f"  Owner: {subscription_data.get('process_owner', 'Unknown')}")

        print(f"  Agent Definition: {subscription_data.get('agent_definition', agent_definition_path)}")
        
        if args.execution_working_directory:
            print(f"  Working Directory: {args.execution_working_directory}")
        
        if expiration:
            print(f"  Expiration: {expiration}")
        
        print(f"  Single Use: {'Yes' if args.single_use else 'No'}")
        
        # Show filter conditions
        filter_conditions = subscription_data.get("filter_conditions", {})

        if filter_conditions:
            print(f"  Filter Conditions:")

            for key, value in filter_conditions.items():
                print(f"    {key}: {value}")


class DeleteSubscriptionCommand(RTOCommand):
    """
    Delete a subscription
    """
    name = "delete-subscription"
    alias = "rmsub"
    description = "Delete a subscription by its ID"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("subscription_id", help="ID of the subscription to delete")

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        config -- The RTO config
        args -- The command line arguments
        """
        # Create the request
        request = DeleteSubscriptionRequest(subscription_id=args.subscription_id)

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Subscription {args.subscription_id} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to delete subscription {args.subscription_id}")

            elif resp.status_code == 400:
                try:
                    error_msg = json.loads(resp.response_body)

                    raise RTOErrorMessage(f"Invalid request: {error_msg.get('message', resp.response_body)}")

                except json.JSONDecodeError:
                    raise RTOErrorMessage(f"Invalid request: {resp.response_body}")

            else:
                raise RTOErrorMessage(f"Error deleting subscription: {resp.status_code}")

        # Parse and display the response
        if args.json and resp.response_body:
            try:
                if isinstance(resp.response_body, str):
                    response_data = json.loads(resp.response_body)

                else:
                    response_data = resp.response_body

                print(json.dumps(response_data, indent=2))

            except json.JSONDecodeError:
                # If cannot parse as JSON but operation was successful, just show success
                print(f"Successfully deleted subscription {args.subscription_id}")

        else:
            print(f"Successfully deleted subscription {args.subscription_id}")


class DescribeSubscriptionCommand(RTOCommand):
    """
    Describe a specific subscription
    """
    name = "describe-subscription"
    alias = "dsub"
    description = "Get detailed information about a specific subscription"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("subscription_id", help="ID of the subscription to describe")

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        config -- The RTO config
        args -- The command line arguments
        """
        # Create the request
        request = DescribeSubscriptionRequest(subscription_id=args.subscription_id)

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 404:
                raise RTOErrorMessage(f"Subscription {args.subscription_id} not found")

            elif resp.status_code == 403:
                raise RTOErrorMessage(f"Permission denied: Not authorized to describe subscription {args.subscription_id}")

            else:
                raise RTOErrorMessage(f"Error describing subscription: {resp.status_code}")

        # Get the subscription details
        subscription = resp.response_body

        # If json flag is set, print the raw response
        if args.json:
            try:
                if isinstance(resp.response_body, str):
                    subscription_data = json.loads(resp.response_body)

                else:
                    subscription_data = resp.response_body

                print(json.dumps(subscription_data, indent=2))

            except json.JSONDecodeError:
                raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

            return

        # Print subscription information in a more formal layout
        print(f"Subscription Information:")

        print(f"  Subscription ID: {subscription.get('subscription_id', 'Unknown')}")

        print(f"  Event Type: {subscription.get('event_type', 'Unknown')}")
        
        # Show filter conditions if present
        filter_conditions = subscription.get('filter_conditions', {})

        if filter_conditions:
            print(f"  Filter Conditions:")

            for key, value in filter_conditions.items():
                print(f"    {key}: {value}")

        print(f"  Agent Definition: {subscription.get('agent_definition', 'Unknown')}")
        
        if "execution_working_directory" in subscription and subscription["execution_working_directory"]:
            print(f"  Working Directory: {subscription['execution_working_directory']}")

        # Handle owner (using process_owner field)
        print(f"  Owner: {subscription.get('process_owner', 'Unknown')}")

        # Handle expiration
        expiration = subscription.get("expiration")

        if expiration is None or expiration == "":
            print(f"  Expiration: Never")

        else:
            print(f"  Expiration: {expiration}")

        # Handle single use
        if "single_use" in subscription:
            single_use = "Yes" if subscription["single_use"] else "No"

            print(f"  Single Use: {single_use}")

        # Print timestamps if present
        if "created_on" in subscription and subscription["created_on"]:
            print(f"  Created On: {subscription['created_on']}")

        # Print last execution if present
        if "last_execution" in subscription and subscription["last_execution"]:
            print(f"  Last Execution: {subscription['last_execution']}")


class ListSubscriptionsCommand(RTOCommand):
    """
    List scheduler subscriptions
    """
    name = "list-subscriptions"
    alias = "lssub"
    description = "List subscriptions with optional filtering"
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        """
        Configure the command line argument parser.

        Keyword arguments:
        parser -- The argument parser to configure
        """
        parser.add_argument("--event-type", help="Filter subscriptions by event type", type=str)

        parser.add_argument("--owner", help="Filter subscriptions by owner", type=str)

        parser.add_argument("--json", help="Output raw JSON response", action="store_true", default=False)

        parser.add_argument("--detailed", "-d", help="Show detailed information for each subscription", 
                            action="store_true", default=False)

    def execute(self, client: Ratio, config: RTOConfig, args):
        """
        Execute the command.

        Keyword arguments:
        client -- The Ratio client
        config -- The RTO config
        args -- The command line arguments
        """
        # Create the request
        request = ListSubscriptionsRequest(
            event_type=args.event_type,
            owner=args.owner
        )

        resp = client.request(request, raise_for_status=False)

        if resp.status_code != 200:
            if resp.status_code == 403:
                raise RTOErrorMessage("Permission denied: Not authorized to list subscriptions")

            else:
                raise RTOErrorMessage(f"Error listing subscriptions: {resp.status_code} -- {resp.response_body}")

        # Get the subscriptions from the response
        subscriptions = resp.response_body

        # Handle JSON output if requested
        if args.json:
            try:
                print(json.dumps(subscriptions, indent=2))

            except json.JSONDecodeError:
                raise RTOErrorMessage(f"Could not parse response as JSON: {resp.response_body}")

            return

        # Check if we found any subscriptions
        if not subscriptions:
            print("No subscriptions found.")

            return

        # Display the subscriptions based on the detail level requested
        if args.detailed:
            # Display detailed information for each subscription
            self._show_detailed_subscriptions(subscriptions)

        else:
            # Display simple table of subscriptions
            self._show_simple_subscriptions(subscriptions)

    def _show_simple_subscriptions(self, subscriptions):
        """
        Display a simple table of subscriptions.

        Keyword arguments:
        subscriptions -- List of subscription dictionaries
        """
        # Format and print the header
        header_format = "{:<36} {:<20} {:<30} {:<24}"

        print(header_format.format(
            "SUBSCRIPTION ID", 
            "EVENT TYPE",
            "PRIMARY FILTER", 
            "OWNER"
        ))

        print("-" * 110)

        # Format and print each subscription
        for sub in subscriptions:
            # Get the primary filter
            primary_filter = "N/A"

            filter_conditions = sub.get("filter_conditions", {})

            if filter_conditions:
                # Show first filter condition
                key, value = next(iter(filter_conditions.items()))

                primary_filter = f"{key}: {value}"

            print(header_format.format(
                sub.get("subscription_id", "Unknown"),
                sub.get("event_type", "Unknown"),
                primary_filter[:28] + "..." if len(str(primary_filter)) > 30 else str(primary_filter),
                sub.get("process_owner", "Unknown")
            ))

        print(f"\nTotal: {len(subscriptions)} subscriptions")

    def _show_detailed_subscriptions(self, subscriptions):
        """
        Display detailed information for each subscription.

        Keyword arguments:
        subscriptions -- List of subscription dictionaries
        """
        for i, sub in enumerate(subscriptions):
            # Add a separator between subscriptions
            if i > 0:
                print("\n" + "-" * 80)

            print(f"Subscription ID: {sub.get('subscription_id', 'Unknown')}")

            print(f"Event Type: {sub.get('event_type', 'Unknown')}")

            # Show filter conditions
            filter_conditions = sub.get('filter_conditions', {})

            if filter_conditions:
                print(f"Filter Conditions:")

                for key, value in filter_conditions.items():
                    print(f"  {key}: {value}")

            print(f"Agent Definition: {sub.get('agent_definition', 'Unknown')}")

            if "execution_working_directory" in sub and sub["execution_working_directory"]:
                print(f"Working Directory: {sub['execution_working_directory']}")

            print(f"Owner: {sub.get('process_owner', 'Unknown')}")

            # Handle expiration properly
            expiration = sub.get("expiration")

            if expiration is None or expiration == "":
                print("Expiration: Never")

            else:
                print(f"Expiration: {expiration}")

            # Handle single_use properly
            if "single_use" in sub:
                single_use = "Yes" if sub["single_use"] else "No"

                print(f"Single Use: {single_use}")

            # Handle created_on properly
            if "created_on" in sub and sub["created_on"]:
                print(f"Created On: {sub['created_on']}")

            # Handle last_execution properly
            if "last_execution" in sub and sub["last_execution"]:
                print(f"Last Execution: {sub['last_execution']}")

        print(f"\nTotal: {len(subscriptions)} subscriptions")