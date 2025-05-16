"""
Scheduler API Proxy
"""
from typing import Dict

from da_vinci.core.immutable_object import ObjectBody

from ratio.core.core_lib.client import RatioInternalClient

from ratio.core.core_lib.factories.api import ChildAPI, Route

from ratio.core.services.scheduler.request_definitions import (
    CreateSubscriptionRequest,
    DeleteSubscriptionRequest,
    DescribeSubscriptionRequest,
    ListSubscriptionsRequest,
)


class SchedulerAPI(ChildAPI):
    """
    Scheduler API Proxy for managing agent execution subscriptions.
    """
    routes = [
        Route(
            path="/scheduler/create_subscription",
            method_name="scheduler_request",
            request_body_schema=CreateSubscriptionRequest,
        ),
        Route(
            path="/scheduler/delete_subscription",
            method_name="scheduler_request",
            request_body_schema=DeleteSubscriptionRequest,
        ),
        Route(
            path="/scheduler/describe_subscription",
            method_name="scheduler_request",
            request_body_schema=DescribeSubscriptionRequest,
        ),
        Route(
            path="/scheduler/list_subscriptions",
            method_name="scheduler_request",
            request_body_schema=ListSubscriptionsRequest,
        ),
    ]

    def __init__(self):
        """
        Initialize the ScehdulerAPI
        """
        super().__init__()

    def scheduler_request(self, request_body: ObjectBody, request_context: Dict) -> Dict:
        """
        Handle requests to the scheduler API.

        Keyword arguments:
        request_body -- The request body containing the subscription details.
        request_context -- The context of the request, including authentication details.
        """
        storage_client = RatioInternalClient(
            service_name="scheduler",
            token=request_context["signed_token"]
        )

        path = request_context["path"].replace("/scheduler", "")

        response = storage_client.request(path=path, request=request_body)

        return self.respond(
            body=response.response_body,
            status_code=response.status_code,
        )