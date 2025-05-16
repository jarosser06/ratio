"""
Proxy Client for interacting with private microservices.
"""
from typing import Dict, Optional, Union

from da_vinci.core.client_base import RESTClientBase, RESTClientResponse
from da_vinci.core.immutable_object import ObjectBody

from ratio.core.core_lib.factories.api import AUTH_HEADER


class RatioInternalClient(RESTClientBase):
    def __init__(self, service_name: str, token: str, app_name: Optional[str] = None, auth_header = AUTH_HEADER,
                 deployment_id: Optional[str] = None):
        """
        Initialize the Ratio client.

        Keyword arguments:
        service_name -- The name of the service to connect to
        token -- The token to use for authentication
        app_name -- The name of the application
        auth_header -- The name of the authentication header
        deployment_id -- The ID of the deployment
        """
        self.service_name = service_name

        super().__init__(resource_name=self.service_name, app_name=app_name, deployment_id=deployment_id)

        self.raise_on_failure = False

        self.auth_header = auth_header

        self._acquired_token = token

    def request(self, path: str, request: Union[Dict, ObjectBody]) -> RESTClientResponse:
        """
        Make a request to the Ratio API.

        Keyword arguments:
        path -- The path to the API endpoint
        request -- The request body to send to the API
        """
        if not self._acquired_token:
            raise ValueError("Token is not set. Please provide a valid token.")

        headers = {self.auth_header: self._acquired_token}

        if isinstance(request, ObjectBody):
            # If the request is an ObjectBody, convert it to a dictionary
            request = request.to_dict()

        print(f"Request to {self.service_name} at {path}: {request}")

        print(f"Headers: {headers}")

        response = self.post(body=request, headers=headers, path=path)

        return response