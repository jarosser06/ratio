"""
File system generated events
"""
import logging
import os

from typing import Dict, Optional, Union

from da_vinci.core.immutable_object import (
    ObjectBody,
)

from da_vinci.event_bus.client import EventPublisher
from da_vinci.event_bus.event import Event as EventBusEvent

from ratio.core.core_lib.definitions.events import FileEventType
from ratio.core.services.storage_manager.request_definitions import FileUpdateEvent
from ratio.core.services.storage_manager.tables.files.client import File

from ratio.core.services.scheduler.request_definitions import (
    GeneralSystemEvent,
)


def publish_file_update_event(file: File, file_event_type: Union[str, FileEventType], requestor: str,
                              details: Optional[Dict] = None) -> None:
    """
    Publish a file update event to the event bus.

    Keyword arguments:
    file -- The file that was updated.
    file_event_type -- The type of the file event.
    requestor -- The entity that requested the file update.
    details -- The details of the file update.
    """
    # Construct the event body
    event_body = ObjectBody(
        body={
            "details": details,
            "file_path": os.path.join(file.file_path, file.file_name),
            "file_type": file.file_type,
            "file_event_type": file_event_type,
            "is_directory": file.is_directory,
            "requestor": requestor,
        },
        schema=FileUpdateEvent,
    )

    event_publisher = EventPublisher()

    event_publisher.submit(
        event=EventBusEvent(
            body=event_body,
            event_type=event_body["system_event_type"],
        ),
    )

    logging.debug(f"File update event published: {event_body['file_event_type']} for file {file.file_name} at {file.file_path}")


def publish_file_type_update_event(file_type: str, requestor: str, details: Optional[Dict] = None) -> None:
    """
    Publish a file type update event to the event bus.

    Keyword arguments:
    file_type -- The file type that was updated.
    event_type -- The type of the file type event.
    requestor -- The entity that requested the file type update.
    details -- The details of the file type update.
    """
    event_details = {
        "file_type": file_type,
        "requestor": requestor,
        **details,
    }

    # Construct the event body
    event_body = ObjectBody(
        body={
            "event_details": event_details,
            "system_event_type": "file_types_update",
            "source_system": "storage_manager",
        },
        schema=GeneralSystemEvent,
    )

    event_publisher = EventPublisher()

    event_publisher.submit(
        event=EventBusEvent(
            body=event_body,
            event_type=event_body["event_type"],
        ),
    )

    logging.debug(f"File type update event published: {event_body['event_type']} for file type {file_type}")