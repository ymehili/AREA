"""Gmail plugin for AREA - Implements Gmail triggers and reactions for automation workflows."""

from __future__ import annotations

import asyncio
import base64
import email
import logging
from typing import TYPE_CHECKING, Dict, Any, List

from app.core.encryption import decrypt_token
from app.services.service_connections import get_service_connection_by_user_and_service
from app.integrations.oauth.providers.google import GoogleOAuth2Provider
from app.core.config import settings
from app.integrations.oauth.factory import OAuth2ProviderFactory

if TYPE_CHECKING:
    from app.models.area import Area

logger = logging.getLogger("area")


async def gmail_new_email_handler(area: Area, params: dict, event: dict) -> None:
    """Handle new email trigger for Gmail.
    
    Args:
        area: The Area containing the trigger
        params: Configuration parameters for the trigger, including sender filter
        event: Event data with context about the trigger execution
    """
    logger.info(f"Checking for new emails for Area {area.id}")
    
    # Import the database session
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Get the Gmail connection for the user
        service_connection = get_service_connection_by_user_and_service(db, area.user_id, "gmail")
    finally:
        db.close()
    if not service_connection:
        logger.error(f"No Gmail connection found for user {area.user_id}")
        return
    
    # Decrypt the access token
    access_token = decrypt_token(service_connection.encrypted_access_token)
    
    # Get the provider instance
    provider = OAuth2ProviderFactory.create_provider("gmail")
    
    # Get the filter parameters
    sender_filter = params.get("sender", "") if params else ""
    subject_contains = params.get("subject_contains", "") if params else ""
    
    # Query to find emails from specific sender or with specific subject
    query_parts = []
    if sender_filter:
        query_parts.append(f"from:{sender_filter}")
    if subject_contains:
        query_parts.append(f"subject:({subject_contains})")
    
    query = " ".join(query_parts) or "is:unread"  # Default to unread emails if no specific criteria
    
    try:
        # Get messages from Gmail
        response = await provider.list_gmail_messages(access_token, query=query)
        messages = response.get("messages", [])
        
        # Process new emails
        for msg in messages:
            message_id = msg["id"]
            full_message = await provider.get_gmail_message(access_token, message_id)
            
            # Add the message to the event data for potential use in reactions
            trigger_data = {
                "id": full_message["id"],
                "threadId": full_message["threadId"],
                "snippet": full_message["snippet"],
                "payload": full_message.get("payload", {}),
                "sizeEstimate": full_message.get("sizeEstimate", 0),
                "historyId": full_message.get("historyId", ""),
                "internalDate": full_message.get("internalDate", ""),
            }
            
            # Extract variables for use in reactions
            from app.integrations.variable_extractor import extract_gmail_variables
            variables = extract_gmail_variables(trigger_data)
            
            # Add variables to event for use in subsequent steps
            event.update(variables)
            
            logger.info(f"New email found for Area {area.id}, executing reaction steps")
            break  # Only process the first matching email for now
            
    except Exception as e:
        logger.error(
            f"Error checking for new emails in Area {area.id}: {str(e)}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )


async def gmail_new_unread_email_handler(area: Area, params: dict, event: dict) -> None:
    """Handle new unread email trigger for Gmail.
    
    Args:
        area: The Area containing the trigger
        params: Configuration parameters for the trigger
        event: Event data with context about the trigger execution
    """
    logger.info(f"Checking for new unread emails for Area {area.id}")
    
    # Import the database session
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Get the Gmail connection for the user
        service_connection = get_service_connection_by_user_and_service(db, area.user_id, "gmail")
    finally:
        db.close()
    if not service_connection:
        logger.error(f"No Gmail connection found for user {area.user_id}")
        return
    
    # Decrypt the access token
    access_token = decrypt_token(service_connection.encrypted_access_token)
    
    # Get the provider instance
    provider = OAuth2ProviderFactory.create_provider("gmail")
    
    try:
        # Get unread messages from Gmail
        response = await provider.list_gmail_messages(access_token, query="is:unread")
        messages = response.get("messages", [])
        
        # Process unread emails
        for msg in messages:
            message_id = msg["id"]
            full_message = await provider.get_gmail_message(access_token, message_id)
            
            # Add the message to the event data for potential use in reactions
            trigger_data = {
                "id": full_message["id"],
                "threadId": full_message["threadId"],
                "snippet": full_message["snippet"],
                "payload": full_message.get("payload", {}),
                "sizeEstimate": full_message.get("sizeEstimate", 0),
                "historyId": full_message.get("historyId", ""),
                "internalDate": full_message.get("internalDate", ""),
            }
            
            # Extract variables for use in reactions
            from app.integrations.variable_extractor import extract_gmail_variables
            variables = extract_gmail_variables(trigger_data)
            
            # Add variables to event for use in subsequent steps
            event.update(variables)
            
            logger.info(f"Unread email found for Area {area.id}, executing reaction steps")
            break  # Only process the first unread email for now
            
    except Exception as e:
        logger.error(
            f"Error checking for unread emails in Area {area.id}: {str(e)}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )


async def gmail_email_starred_handler(area: Area, params: dict, event: dict) -> None:
    """Handle email starred trigger for Gmail.
    
    Args:
        area: The Area containing the trigger
        params: Configuration parameters for the trigger
        event: Event data with context about the trigger execution
    """
    logger.info(f"Checking for starred emails for Area {area.id}")
    
    # Import the database session
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Get the Gmail connection for the user
        service_connection = get_service_connection_by_user_and_service(db, area.user_id, "gmail")
    finally:
        db.close()
    
    if not service_connection:
        logger.error(f"No Gmail connection found for user {area.user_id}")
        return
    
    # Decrypt the access token
    access_token = decrypt_token(service_connection.encrypted_access_token)
    
    # Get the provider instance
    provider = OAuth2ProviderFactory.create_provider("gmail")
    
    try:
        # Get starred messages from Gmail (label:STARRED)
        response = await provider.list_gmail_messages(access_token, query="label:STARRED")
        messages = response.get("messages", [])
        
        # Process starred emails
        for msg in messages:
            message_id = msg["id"]
            full_message = await provider.get_gmail_message(access_token, message_id)
            
            # Add the message to the event data for potential use in reactions
            trigger_data = {
                "id": full_message["id"],
                "threadId": full_message["threadId"],
                "snippet": full_message["snippet"],
                "payload": full_message.get("payload", {}),
                "sizeEstimate": full_message.get("sizeEstimate", 0),
                "historyId": full_message.get("historyId", ""),
                "internalDate": full_message.get("internalDate", ""),
            }
            
            # Extract variables for use in reactions
            from app.integrations.variable_extractor import extract_gmail_variables
            variables = extract_gmail_variables(trigger_data)
            
            # Add variables to event for use in subsequent steps
            event.update(variables)
            
            logger.info(f"Starred email found for Area {area.id}, executing reaction steps")
            break  # Only process the first starred email for now
            
    except Exception as e:
        logger.error(
            f"Error checking for starred emails in Area {area.id}: {str(e)}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )


async def gmail_send_email_handler(area: Area, params: dict, event: dict) -> None:
    """Handle send email reaction for Gmail.
    
    Args:
        area: The Area containing the reaction
        params: Configuration parameters for the reaction, including recipient, subject, and body
        event: Event data with context about the execution
    """
    logger.info(f"Sending email for Area {area.id}")
    
    # Validate required parameters
    required_fields = ["to", "subject", "body"]
    for field in required_fields:
        if field not in params:
            raise ValueError(f"Missing required field: {field}")
    
    # Import the database session
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Get the Gmail connection for the user
        service_connection = get_service_connection_by_user_and_service(db, area.user_id, "gmail")
    finally:
        db.close()
    
    if not service_connection:
        logger.error(f"No Gmail connection found for user {area.user_id}")
        return
    
    # Decrypt the access token
    access_token = decrypt_token(service_connection.encrypted_access_token)
    
    # Get the provider instance
    provider = OAuth2ProviderFactory.create_provider("gmail")
    
    # Get parameters with potential variable substitution
    to = params["to"]
    subject = params["subject"]
    body = params["body"]
    cc = params.get("cc", "")
    bcc = params.get("bcc", "")
    
    # Replace any variables in the email content
    for key, value in event.items():
        if isinstance(value, str):
            to = to.replace(f"{{{{{key}}}}}", str(value))
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
            body = body.replace(f"{{{{{key}}}}}", str(value))
        if cc and isinstance(cc, str):
            cc = cc.replace(f"{{{{{key}}}}}", str(value))
        if bcc and isinstance(bcc, str):
            bcc = bcc.replace(f"{{{{{key}}}}}", str(value))
    
    try:
        # Create raw email message
        raw_message = provider.create_raw_email(to, subject, body, cc, bcc)
        
        # Send the email
        response = await provider.send_gmail_message(access_token, raw_message)
        
        logger.info(
            f"Email sent successfully for Area {area.id}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "message_id": response.get("id", "unknown"),
            }
        )
    except Exception as e:
        logger.error(
            f"Error sending email for Area {area.id}: {str(e)}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "error": str(e),
            },
            exc_info=True,
        )


async def gmail_mark_as_read_handler(area: Area, params: dict, event: dict) -> None:
    """Handle mark email as read reaction for Gmail.
    
    Args:
        area: The Area containing the reaction
        params: Configuration parameters for the reaction, including message ID
        event: Event data with context about the execution
    """
    logger.info(f"Marking email as read for Area {area.id}")
    
    # Import the database session
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Get the Gmail connection for the user
        service_connection = get_service_connection_by_user_and_service(db, area.user_id, "gmail")
    finally:
        db.close()
    
    if not service_connection:
        logger.error(f"No Gmail connection found for user {area.user_id}")
        return
    
    # Decrypt the access token
    access_token = decrypt_token(service_connection.encrypted_access_token)
    
    # Get the provider instance
    provider = OAuth2ProviderFactory.create_provider("gmail")
    
    # Get message ID from parameters or from event (if it's a follow-up to a trigger)
    message_id = params.get("message_id", "")
    if not message_id and "gmail.message_id" in event:
        message_id = event["gmail.message_id"]
    
    if not message_id:
        logger.error(
            f"No message ID provided for mark as read action in Area {area.id}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
            }
        )
        return
    
    try:
        # Remove the UNREAD label to mark as read
        response = await provider.modify_gmail_message(
            access_token, 
            message_id, 
            remove_labels=["UNREAD"]
        )
        
        logger.info(
            f"Email marked as read for Area {area.id}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "message_id": message_id,
            }
        )
    except Exception as e:
        logger.error(
            f"Error marking email as read for Area {area.id}: {str(e)}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "message_id": message_id,
                "error": str(e),
            },
            exc_info=True,
        )


async def gmail_forward_email_handler(area: Area, params: dict, event: dict) -> None:
    """Handle forward email reaction for Gmail.
    
    Args:
        area: The Area containing the reaction
        params: Configuration parameters for the reaction, including forward recipient
        event: Event data with context about the execution
    """
    logger.info(f"Forwarding email for Area {area.id}")
    
    # Validate required parameters
    if "to" not in params:
        raise ValueError("Missing required field: to")
    
    # Import the database session
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Get the Gmail connection for the user
        service_connection = get_service_connection_by_user_and_service(db, area.user_id, "gmail")
    finally:
        db.close()
    
    if not service_connection:
        logger.error(f"No Gmail connection found for user {area.user_id}")
        return
    
    # Decrypt the access token
    access_token = decrypt_token(service_connection.encrypted_access_token)
    
    # Get the provider instance
    provider = OAuth2ProviderFactory.create_provider("gmail")
    
    # Get the original message ID from event (this should come from a trigger)
    original_message_id = event.get("gmail.message_id", "")
    if not original_message_id:
        logger.error(
            f"No original message ID found in event for forwarding in Area {area.id}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
            }
        )
        return
    
    try:
        # Get the original message
        original_message = await provider.get_gmail_message(access_token, original_message_id)
        
        # Extract the original email data
        payload = original_message.get("payload", {})
        headers = payload.get("headers", [])
        
        # Get original subject and sender
        original_subject = ""
        original_from = ""
        for header in headers:
            name = header.get("name", "").lower()
            value = header.get("value", "")
            if name == "subject":
                original_subject = value
            elif name == "from":
                original_from = value
        
        # Create a forwarded message with "Fwd:" prefix
        forward_to = params["to"]
        forward_subject = f"Fwd: {original_subject}"
        
        # Get the original body content
        body_content = ""
        if "body" in original_message:
            body_data = original_message["body"].get("data", "")
            if body_data:
                # Decode base64 content
                decoded_bytes = base64.urlsafe_b64decode(body_data)
                body_content = decoded_bytes.decode('utf-8')
        
        # Build forwarded message body
        forward_body = f"---------- Forwarded message ---------\n"
        forward_body += f"From: {original_from}\n"
        forward_body += f"Subject: {original_subject}\n\n"
        forward_body += f"{body_content}\n"
        
        # Create raw email message for forwarding
        raw_message = provider.create_raw_email(forward_to, forward_subject, forward_body)
        
        # Send the forwarded email
        response = await provider.send_gmail_message(access_token, raw_message)
        
        logger.info(
            f"Email forwarded successfully for Area {area.id}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "original_message_id": original_message_id,
                "forwarded_message_id": response.get("id", "unknown"),
            }
        )
    except Exception as e:
        logger.error(
            f"Error forwarding email for Area {area.id}: {str(e)}",
            extra={
                "area_id": str(area.id),
                "user_id": str(area.user_id),
                "original_message_id": original_message_id,
                "error": str(e),
            },
            exc_info=True,
        )


__all__ = [
    "gmail_new_email_handler",
    "gmail_new_unread_email_handler", 
    "gmail_email_starred_handler",
    "gmail_send_email_handler",
    "gmail_mark_as_read_handler",
    "gmail_forward_email_handler"
]