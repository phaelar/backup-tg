#!/usr/bin/env python3
"""
Telegram Deleted Messages Recovery Script
Retrieves recently deleted messages (within 48 hours) from a Telegram group via Admin Log.
Outputs to JSON format for backup.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.channels import GetAdminLogRequest
from telethon.tl.types import (
    ChannelAdminLogEventActionDeleteMessage,
    InputChannel,
    Message
)

# Load environment variables from .env file
load_dotenv()

# Configuration
API_ID = os.getenv('TELEGRAM_API_ID')  # Get from https://my.telegram.org
API_HASH = os.getenv('TELEGRAM_API_HASH')  # Get from https://my.telegram.org
PHONE = os.getenv('TELEGRAM_PHONE')  # Your phone number with country code
SESSION_NAME = 'telegram_recovery_session'

# Output configuration
OUTPUT_DIR = Path('deleted_messages_backup')
OUTPUT_FILE = OUTPUT_DIR / f'deleted_messages_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
MEDIA_DIR = OUTPUT_DIR / 'deleted_media'


async def get_group_entity(client, group_identifier):
    """
    Get the group entity from username, invite link, or group ID.

    Args:
        client: TelegramClient instance
        group_identifier: Group username (e.g., @groupname), invite link, or group ID

    Returns:
        Group entity
    """
    try:
        # If it looks like a numeric ID, convert to int
        if isinstance(group_identifier, str) and group_identifier.lstrip('-').isdigit():
            group_identifier = int(group_identifier)
            print(f"Converted to integer: {group_identifier}")

        entity = await client.get_entity(group_identifier)
        return entity
    except ValueError as e:
        # If get_entity fails, try searching through dialogs
        print(f"Direct lookup failed, searching through your groups...")
        target_id = int(group_identifier) if isinstance(group_identifier, str) and group_identifier.lstrip('-').isdigit() else None

        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                if target_id and dialog.id == target_id:
                    print(f"Found group in dialogs: {dialog.name}")
                    return dialog.entity

        print(f"Error getting group entity: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're a member of the group")
        print("2. Try using the group's @username instead of ID")
        print("3. Run 'python3 list_groups.py' to see all your groups")
        print("4. Try getting an invite link from the group and use that")
        raise
    except Exception as e:
        print(f"Error getting group entity: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're a member of the group")
        print("2. Try using the group's @username instead of ID")
        print("3. Run 'python3 list_groups.py' to see all your groups")
        raise


async def download_media(client, message, media_dir):
    """
    Download media from a message if it exists.

    Args:
        client: TelegramClient instance
        message: Message object
        media_dir: Directory to save media files

    Returns:
        Path to downloaded file or None
    """
    if not message.media:
        return None

    try:
        # Create unique filename using message ID and date
        file_path = await client.download_media(
            message.media,
            file=media_dir
        )
        return str(file_path) if file_path else None
    except Exception as e:
        print(f"Error downloading media for message {message.id}: {e}")
        return None


async def extract_message_data(client, message, media_dir, event_date):
    """
    Extract relevant data from a message object.

    Args:
        client: TelegramClient instance
        message: Message object
        media_dir: Directory to save media files
        event_date: Date when the message was deleted

    Returns:
        Dictionary with message data
    """
    media_path = None
    if message.media:
        media_path = await download_media(client, message, media_dir)

    # Get sender information
    sender_name = "Unknown"
    sender_id = None
    sender_username = None
    if message.sender:
        sender_id = message.sender.id
        if hasattr(message.sender, 'username') and message.sender.username:
            sender_username = message.sender.username
        if hasattr(message.sender, 'first_name'):
            sender_name = message.sender.first_name
            if hasattr(message.sender, 'last_name') and message.sender.last_name:
                sender_name += f" {message.sender.last_name}"
        elif hasattr(message.sender, 'title'):
            sender_name = message.sender.title

    return {
        'message_id': message.id,
        'date': message.date.isoformat() if message.date else None,
        'deleted_date': event_date.isoformat() if event_date else None,
        'sender_id': sender_id,
        'sender_name': sender_name,
        'sender_username': sender_username,
        'text': message.message or "",
        'media_type': message.media.__class__.__name__ if message.media else None,
        'media_path': media_path,
        'reply_to_msg_id': message.reply_to.reply_to_msg_id if message.reply_to else None,
        'forward_info': {
            'from_id': message.forward.from_id.user_id if message.forward and hasattr(message.forward.from_id, 'user_id') else None,
            'from_name': message.forward.from_name if message.forward else None,
            'date': message.forward.date.isoformat() if message.forward and message.forward.date else None
        } if message.forward else None
    }


async def retrieve_deleted_messages(group_identifier):
    """
    Main function to retrieve deleted messages from a Telegram group.

    Args:
        group_identifier: Group username, invite link, or group ID
    """
    # Validate configuration
    if not API_ID or not API_HASH or not PHONE:
        print("ERROR: Please set the following environment variables:")
        print("  - TELEGRAM_API_ID")
        print("  - TELEGRAM_API_HASH")
        print("  - TELEGRAM_PHONE")
        print("\nYou can get API_ID and API_HASH from https://my.telegram.org")
        return

    # Create output directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    MEDIA_DIR.mkdir(exist_ok=True)

    # Initialize Telegram client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    try:
        await client.start(phone=PHONE)
        print(f"Connected to Telegram as {PHONE}")

        # Get the group entity
        print(f"Getting group entity for: {group_identifier}")
        group = await get_group_entity(client, group_identifier)
        print(f"Group found: {group.title} (ID: {group.id})")

        # Check if it's a channel/supergroup (required for admin log)
        from telethon.tl.types import Chat, Channel
        if isinstance(group, Chat):
            print("\n" + "=" * 80)
            print("ERROR: This is a regular group chat, not a supergroup or channel.")
            print("=" * 80)
            print("\nAdmin log (for retrieving deleted messages) only works with:")
            print("  - Supergroups")
            print("  - Channels")
            print("\nYour group is a regular chat (limited to 200 members).")
            print("\nOptions:")
            print("  1. Convert your group to a supergroup in Telegram settings")
            print("     (Group Info -> Edit -> Group Type -> Supergroup)")
            print("  2. Use script 2 (backup_current_messages.py) to backup current messages")
            print("     (This won't recover deleted messages, only current ones)")
            print("\nNote: Once converted to a supergroup, you cannot convert back.")
            return

        # Retrieve admin log events
        print("\nRetrieving admin log (deleted messages)...")
        deleted_messages = []

        # Paginate through all admin log events
        max_id = 0
        total_events_fetched = 0
        processed = 0

        while True:
            # Get admin log with filter for deleted messages
            admin_log = await client(GetAdminLogRequest(
                channel=group,
                q='',  # No search query
                max_id=max_id,
                min_id=0,
                limit=100,  # Retrieve up to 100 events at a time
            ))

            if not admin_log.events:
                break  # No more events to fetch

            total_events_fetched += len(admin_log.events)
            print(f"Fetched {total_events_fetched} admin log events...", end='\r')

            for event in admin_log.events:
                # Filter for message deletion events
                if isinstance(event.action, ChannelAdminLogEventActionDeleteMessage):
                    processed += 1
                    print(f"Processing deleted message {processed}...", end='\r')

                    message = event.action.message
                    if isinstance(message, Message):
                        message_data = await extract_message_data(
                            client,
                            message,
                            MEDIA_DIR,
                            event.date
                        )
                        message_data['deleted_by_user_id'] = event.user_id
                        deleted_messages.append(message_data)

            # Get the last event's ID for pagination
            max_id = admin_log.events[-1].id

        print(f"\nFound {len(deleted_messages)} deleted messages from {total_events_fetched} total admin log events")

        # Save to JSON file
        output_data = {
            'group_id': group.id,
            'group_title': group.title,
            'retrieved_at': datetime.now().isoformat(),
            'total_deleted_messages': len(deleted_messages),
            'messages': deleted_messages
        }

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Deleted messages saved to: {OUTPUT_FILE}")
        print(f"✓ Media files saved to: {MEDIA_DIR}")
        print(f"\nSummary:")
        print(f"  - Total deleted messages: {len(deleted_messages)}")
        print(f"  - Messages with media: {sum(1 for m in deleted_messages if m['media_path'])}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


def main():
    """Entry point for the script."""
    print("=" * 60)
    print("Telegram Deleted Messages Recovery Tool")
    print("=" * 60)
    print("\nThis script retrieves deleted messages from a Telegram group")
    print("using the Admin Log API (messages deleted within 48 hours).")
    print()

    # Get group identifier from user
    group_identifier = input("Enter group username (e.g., @groupname) or group ID: ").strip()

    if not group_identifier:
        print("Error: Group identifier is required")
        return

    # Run the async function
    asyncio.run(retrieve_deleted_messages(group_identifier))


if __name__ == '__main__':
    main()
