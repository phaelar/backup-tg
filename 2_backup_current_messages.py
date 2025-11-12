#!/usr/bin/env python3
"""
Telegram Current Messages Backup Script
Retrieves all current messages from a Telegram group and saves them to JSON format.
Downloads all media files associated with messages.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.types import Message

# Configuration
API_ID = os.getenv('TELEGRAM_API_ID')  # Get from https://my.telegram.org
API_HASH = os.getenv('TELEGRAM_API_HASH')  # Get from https://my.telegram.org
PHONE = os.getenv('TELEGRAM_PHONE')  # Your phone number with country code
SESSION_NAME = 'telegram_backup_session'

# Output configuration
OUTPUT_DIR = Path('current_messages_backup')
OUTPUT_FILE = OUTPUT_DIR / f'current_messages_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
MEDIA_DIR = OUTPUT_DIR / 'current_media'

# Batch size for saving progress
SAVE_BATCH_SIZE = 100


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
        entity = await client.get_entity(group_identifier)
        return entity
    except Exception as e:
        print(f"Error getting group entity: {e}")
        print("Make sure you provide the correct group username, invite link, or ID")
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
        # Create unique filename using message ID
        file_path = await client.download_media(
            message.media,
            file=media_dir
        )
        return str(file_path) if file_path else None
    except Exception as e:
        print(f"Error downloading media for message {message.id}: {e}")
        return None


async def extract_message_data(client, message, media_dir):
    """
    Extract relevant data from a message object.

    Args:
        client: TelegramClient instance
        message: Message object
        media_dir: Directory to save media files

    Returns:
        Dictionary with message data
    """
    media_path = None
    if message.media:
        media_path = await download_media(client, message, media_dir)

    # Get sender information
    sender_name = "Unknown"
    sender_id = None
    if message.sender:
        sender_id = message.sender.id
        if hasattr(message.sender, 'first_name'):
            sender_name = message.sender.first_name
            if hasattr(message.sender, 'last_name') and message.sender.last_name:
                sender_name += f" {message.sender.last_name}"
        elif hasattr(message.sender, 'title'):
            sender_name = message.sender.title
        elif hasattr(message.sender, 'username'):
            sender_name = message.sender.username

    # Get edit date if message was edited
    edit_date = message.edit_date.isoformat() if message.edit_date else None

    # Get reactions if any
    reactions = []
    if message.reactions:
        for reaction_count in message.reactions.results:
            reactions.append({
                'emoticon': reaction_count.reaction.emoticon if hasattr(reaction_count.reaction, 'emoticon') else None,
                'count': reaction_count.count
            })

    return {
        'message_id': message.id,
        'date': message.date.isoformat() if message.date else None,
        'edit_date': edit_date,
        'sender_id': sender_id,
        'sender_name': sender_name,
        'text': message.message or "",
        'media_type': message.media.__class__.__name__ if message.media else None,
        'media_path': media_path,
        'reply_to_msg_id': message.reply_to.reply_to_msg_id if message.reply_to else None,
        'forward_info': {
            'from_id': message.forward.from_id.user_id if message.forward and hasattr(message.forward.from_id, 'user_id') else None,
            'from_name': message.forward.from_name if message.forward else None,
            'date': message.forward.date.isoformat() if message.forward and message.forward.date else None
        } if message.forward else None,
        'reactions': reactions if reactions else None,
        'views': message.views if hasattr(message, 'views') else None,
        'pinned': message.pinned if hasattr(message, 'pinned') else False
    }


async def backup_current_messages(group_identifier, limit=None):
    """
    Main function to backup all current messages from a Telegram group.

    Args:
        group_identifier: Group username, invite link, or group ID
        limit: Maximum number of messages to retrieve (None for all)
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

        # Retrieve all messages
        print("\nRetrieving messages from the group...")
        print("This may take a while depending on the number of messages...")

        all_messages = []
        message_count = 0

        async for message in client.iter_messages(group, limit=limit):
            if isinstance(message, Message):
                message_count += 1
                print(f"Processing message {message_count} (ID: {message.id})...", end='\r')

                message_data = await extract_message_data(client, message, MEDIA_DIR)
                all_messages.append(message_data)

                # Save progress in batches
                if message_count % SAVE_BATCH_SIZE == 0:
                    print(f"\nSaved progress: {message_count} messages processed")

        print(f"\n\nTotal messages retrieved: {len(all_messages)}")

        # Sort messages by date (oldest first)
        all_messages.sort(key=lambda x: x['date'] if x['date'] else '')

        # Save to JSON file
        output_data = {
            'group_id': group.id,
            'group_title': group.title,
            'backed_up_at': datetime.now().isoformat(),
            'total_messages': len(all_messages),
            'messages': all_messages
        }

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Messages saved to: {OUTPUT_FILE}")
        print(f"✓ Media files saved to: {MEDIA_DIR}")
        print(f"\nSummary:")
        print(f"  - Total messages: {len(all_messages)}")
        print(f"  - Messages with media: {sum(1 for m in all_messages if m['media_path'])}")
        print(f"  - Messages with text: {sum(1 for m in all_messages if m['text'])}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


def main():
    """Entry point for the script."""
    print("=" * 60)
    print("Telegram Current Messages Backup Tool")
    print("=" * 60)
    print("\nThis script backs up all current messages from a Telegram group")
    print("including text, media, and metadata.")
    print()

    # Get group identifier from user
    group_identifier = input("Enter group username (e.g., @groupname) or group ID: ").strip()

    if not group_identifier:
        print("Error: Group identifier is required")
        return

    # Ask about message limit
    limit_input = input("Enter message limit (or press Enter for all messages): ").strip()
    limit = int(limit_input) if limit_input.isdigit() else None

    # Run the async function
    asyncio.run(backup_current_messages(group_identifier, limit))


if __name__ == '__main__':
    main()
