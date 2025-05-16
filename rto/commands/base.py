from argparse import ArgumentParser

from ratio.client.client import Ratio


class RTOErrorMessage(Exception):
    """
    Error message class
    """
    pass


class RTOCommand:
    name = None
    alias = None
    description = None
    requires_authentication = True

    @classmethod
    def configure_parser(cls, parser: ArgumentParser):
        return

    def execute(self, client: Ratio, args):
        raise NotImplementedError

    def ratio_client(self, args):
        """
        Return the ratio client
        """

        return Ratio(
            token=args.token,
            app_name=args.app_name,
            deployment_id=args.deployment_id,
        )