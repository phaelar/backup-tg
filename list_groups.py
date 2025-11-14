#!/usr/bin/env python3
"""
Helper script to list all groups/channels you're a member of.
"""

import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient

# Load environment variables
load_dotenv()

# Configuration
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE = os.getenv('TELEGRAM_PHONE')
SESSION_NAME = 'telegram_backup_session'


async def list_groups():
    """List all groups and channels."""
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    try:
        await client.start(phone=PHONE)
        print("Connected to Telegram\n")
        print("=" * 80)
        print("Your Groups and Channels:")
        print("=" * 80)

        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                from telethon.tl.types import Chat, Channel

                # Determine the type
                if isinstance(dialog.entity, Chat):
                    group_type = "Regular Chat (no admin log support)"
                elif isinstance(dialog.entity, Channel):
                    if dialog.entity.megagroup:
                        group_type = "Supergroup (supports admin log)"
                    elif dialog.entity.broadcast:
                        group_type = "Channel (supports admin log)"
                    else:
                        group_type = "Channel/Group"
                else:
                    group_type = "Unknown"

                print(f"\nName: {dialog.name}")
                print(f"ID: {dialog.id}")
                if hasattr(dialog.entity, 'username') and dialog.entity.username:
                    print(f"Username: @{dialog.entity.username}")
                print(f"Type: {group_type}")
                print("-" * 80)

    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(list_groups())
