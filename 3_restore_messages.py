#!/usr/bin/env python3
"""
Telegram Message Restoration Script
Restores messages from backup JSON files to a new Telegram group.
Messages are sent with timestamp prefix and author name.
"""

import asyncio
import json
import os
import hashlib
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import InputMediaUploadedDocument, DocumentAttributeFilename
from telethon.errors import FloodWaitError, SlowModeWaitError
import time

# Load environment variables from .env file
load_dotenv()

# Configuration
API_ID = os.getenv('TELEGRAM_API_ID')  # Get from https://my.telegram.org
API_HASH = os.getenv('TELEGRAM_API_HASH')  # Get from https://my.telegram.org
PHONE = os.getenv('TELEGRAM_PHONE')  # Your phone number with country code
SESSION_NAME = 'sessions/telegram_restore_session'

# Rate limiting configuration: 15 requests per minute = 1 request every 4 seconds
MESSAGE_DELAY = 4.0  # Delay between messages (seconds) - 15 req/min
MEDIA_DELAY = 4.0  # Delay for messages with media (seconds) - 15 req/min

# Checkpoint configuration
CHECKPOINT_FILE = Path(__file__).parent / '.restore_checkpoint.json'
CHECKPOINT_VERSION = 1
CHECKPOINT_MODE = os.getenv('CHECKPOINT_MODE', 'prompt')  # 'prompt', 'resume', 'restart'


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file for integrity checking."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def compute_operation_hash(backup_files: list, target_group_id: int, merge: bool) -> str:
    """Compute a unique hash identifying this restore operation."""
    data = {
        'files': sorted([str(Path(f).resolve()) for f in backup_files]),
        'target': target_group_id,
        'merge': merge
    }
    content = json.dumps(data, sort_keys=True)
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def load_checkpoint() -> dict | None:
    """Load existing checkpoint if it exists."""
    if not CHECKPOINT_FILE.exists():
        return None
    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
        if checkpoint.get('version') != CHECKPOINT_VERSION:
            print(f"Warning: Checkpoint version mismatch (found v{checkpoint.get('version')}, expected v{CHECKPOINT_VERSION})")
            return None
        return checkpoint
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not read checkpoint: {e}")
        return None


def save_checkpoint(checkpoint: dict) -> None:
    """Atomically save checkpoint to disk using temp file + rename."""
    checkpoint['updated_at'] = datetime.now().isoformat()

    temp_fd, temp_path = tempfile.mkstemp(
        suffix='.json',
        prefix='.restore_checkpoint_',
        dir=CHECKPOINT_FILE.parent
    )
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2)
        shutil.move(temp_path, CHECKPOINT_FILE)
    except Exception:
        if Path(temp_path).exists():
            os.unlink(temp_path)
        raise


def clear_checkpoint() -> None:
    """Remove checkpoint file after successful completion."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("Checkpoint cleared.")


def validate_checkpoint(checkpoint: dict, backup_files: list, target_group_id: int, merge: bool) -> tuple[bool, str]:
    """
    Validate if checkpoint matches current operation.
    Returns (is_valid, reason_if_invalid).
    """
    current_hash = compute_operation_hash(backup_files, target_group_id, merge)
    if checkpoint.get('operation_hash') != current_hash:
        return False, "Operation parameters differ (different files, target, or merge setting)"

    for filepath, expected_hash in checkpoint.get('source_files_hashes', {}).items():
        if not Path(filepath).exists():
            return False, f"Source file no longer exists: {filepath}"
        actual_hash = compute_file_hash(Path(filepath))
        if actual_hash != expected_hash:
            return False, f"Source file was modified: {filepath}"

    return True, ""


def create_checkpoint(
    backup_files: list,
    target_group_id: int,
    target_group_title: str,
    merge: bool,
    total_messages: int
) -> dict:
    """Create a new checkpoint for this restore operation."""
    resolved_files = [str(Path(f).resolve()) for f in backup_files]
    file_hashes = {f: compute_file_hash(Path(f)) for f in resolved_files}

    return {
        'version': CHECKPOINT_VERSION,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'operation_hash': compute_operation_hash(backup_files, target_group_id, merge),
        'target_group_id': target_group_id,
        'target_group_title': target_group_title,
        'source_files': resolved_files,
        'source_files_hashes': file_hashes,
        'merge_enabled': merge,
        'total_messages': total_messages,
        'last_successful_index': -1,
        'last_message_id': None,
        'success_count': 0,
        'failed_count': 0,
        'failed_message_ids': [],
        'elapsed_seconds': 0.0
    }


def prompt_resume_or_restart(checkpoint: dict) -> str:
    """
    Ask user whether to resume, restart, or cancel.
    Returns: 'resume', 'restart', or 'cancel'
    """
    print("\n" + "=" * 60)
    print("EXISTING CHECKPOINT FOUND")
    print("=" * 60)
    print(f"Target group: {checkpoint['target_group_title']} (ID: {checkpoint['target_group_id']})")
    print(f"Progress: {checkpoint['last_successful_index'] + 1}/{checkpoint['total_messages']} messages sent")
    print(f"Success: {checkpoint['success_count']} | Failed: {checkpoint['failed_count']}")
    print(f"Started: {checkpoint['created_at']}")
    print(f"Last update: {checkpoint['updated_at']}")

    elapsed = checkpoint.get('elapsed_seconds', 0)
    print(f"Time spent: {int(elapsed / 60)}m {int(elapsed % 60)}s")

    remaining = checkpoint['total_messages'] - (checkpoint['last_successful_index'] + 1)
    est_remaining = remaining * MESSAGE_DELAY
    print(f"Estimated time remaining: {int(est_remaining / 3600)}h {int((est_remaining % 3600) / 60)}m")

    print("\nOptions:")
    print("  [r]esume  - Continue from where you left off")
    print("  [s]tart   - Start over from the beginning (clears checkpoint)")
    print("  [c]ancel  - Exit without making changes")

    while True:
        choice = input("\nYour choice (r/s/c): ").strip().lower()
        if choice in ('r', 'resume'):
            return 'resume'
        elif choice in ('s', 'start'):
            confirm = input("Are you sure you want to restart? This will clear progress. (yes/no): ").strip().lower()
            if confirm == 'yes':
                return 'restart'
            print("Restart cancelled. Please choose again.")
        elif choice in ('c', 'cancel'):
            return 'cancel'
        else:
            print("Invalid choice. Please enter 'r', 's', or 'c'.")


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


def format_message_header(message_data):
    """
    Format the message header with timestamp and author.

    Args:
        message_data: Dictionary containing message data

    Returns:
        Formatted header string
    """
    date_str = "Unknown date"
    if message_data.get('date'):
        try:
            date = datetime.fromisoformat(message_data['date'])
            date_str = date.strftime("%Y-%m-%d %H:%M:%S")
        except:
            date_str = message_data['date']

    sender_name = message_data.get('sender_name', 'Unknown')
    header = f"📅 {date_str} | 👤 {sender_name}"

    # Add deleted indicator if from deleted messages backup
    if message_data.get('deleted_date'):
        header += " | 🗑️ DELETED"

    return header


def format_message_text(message_data):
    """
    Format the complete message text with header and content.

    Args:
        message_data: Dictionary containing message data

    Returns:
        Formatted message string
    """
    header = format_message_header(message_data)
    text = message_data.get('text', '')

    # Add media indicator if present
    if message_data.get('media_type'):
        media_type = message_data['media_type'].replace('MessageMedia', '')
        header += f" | 📎 {media_type}"

    # Add forward indicator if present
    if message_data.get('forward_info'):
        forward_info = message_data['forward_info']
        if forward_info.get('from_name'):
            header += f" | ↩️ Forwarded from: {forward_info['from_name']}"

    separator = "-" * 50
    return f"{header}\n{separator}\n{text}" if text else f"{header}\n{separator}\n[No text content]"


async def send_message_with_retry(client, target_group, message_text, media_path=None, max_retries=3):
    """
    Send a message with automatic retry on rate limiting.

    Args:
        client: TelegramClient instance
        target_group: Target group entity
        message_text: Message text to send
        media_path: Optional path to media file
        max_retries: Maximum number of retries

    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries):
        try:
            if media_path and Path(media_path).exists():
                await client.send_file(
                    target_group,
                    media_path,
                    caption=message_text
                )
            else:
                await client.send_message(
                    target_group,
                    message_text
                )
            return True

        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"\n⚠️  Rate limited. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)

        except SlowModeWaitError as e:
            wait_time = e.seconds
            print(f"\n⚠️  Slow mode active. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)

        except Exception as e:
            print(f"\n✗ Error sending message (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                return False

    return False


async def restore_messages(backup_files, target_group_identifier, merge=True):
    """
    Restore messages from backup files to a target group.
    Supports checkpoint/resume functionality.

    Args:
        backup_files: List of paths to backup JSON files
        target_group_identifier: Target group username, invite link, or group ID
        merge: If True, merge and sort messages from all files
    """
    # Validate configuration
    if not API_ID or not API_HASH or not PHONE:
        print("ERROR: Please set the following environment variables:")
        print("  - TELEGRAM_API_ID")
        print("  - TELEGRAM_API_HASH")
        print("  - TELEGRAM_PHONE")
        print("\nYou can get API_ID and API_HASH from https://my.telegram.org")
        return

    # Load all messages from backup files
    all_messages = []
    for backup_file in backup_files:
        backup_path = Path(backup_file)
        if not backup_path.exists():
            print(f"⚠️  Warning: Backup file not found: {backup_file}")
            continue

        print(f"Loading messages from: {backup_file}")
        with open(backup_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = data.get('messages', [])
            print(f"  Loaded {len(messages)} messages")
            all_messages.extend(messages)

    if not all_messages:
        print("✗ No messages to restore")
        return

    # Sort messages by date if merging
    if merge:
        print(f"\nMerging and sorting {len(all_messages)} messages by date...")
        all_messages.sort(key=lambda x: x['date'] if x.get('date') else '')

    print(f"\nTotal messages to restore: {len(all_messages)}")

    # Initialize Telegram client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    try:
        await client.start(phone=PHONE)
        print(f"Connected to Telegram as {PHONE}")

        # Get the target group entity
        print(f"\nGetting target group entity for: {target_group_identifier}")
        target_group = await get_group_entity(client, target_group_identifier)
        print(f"Target group found: {target_group.title} (ID: {target_group.id})")

        # === CHECKPOINT HANDLING ===
        start_index = 0
        success_count = 0
        failed_count = 0
        failed_message_ids = []
        prior_elapsed = 0.0
        checkpoint = load_checkpoint()

        if checkpoint:
            is_valid, reason = validate_checkpoint(
                checkpoint, backup_files, target_group.id, merge
            )

            if is_valid:
                if CHECKPOINT_MODE == 'resume':
                    choice = 'resume'
                    print(f"\nAuto-resuming from message {checkpoint['last_successful_index'] + 2}...")
                elif CHECKPOINT_MODE == 'restart':
                    choice = 'restart'
                    print("\nAuto-restarting (clearing checkpoint)...")
                else:
                    choice = prompt_resume_or_restart(checkpoint)

                if choice == 'cancel':
                    print("Restoration cancelled.")
                    return
                elif choice == 'resume':
                    start_index = checkpoint['last_successful_index'] + 1
                    success_count = checkpoint['success_count']
                    failed_count = checkpoint['failed_count']
                    failed_message_ids = checkpoint.get('failed_message_ids', [])
                    prior_elapsed = checkpoint.get('elapsed_seconds', 0)
                    print(f"\nResuming from message {start_index + 1}...")
                else:  # restart
                    clear_checkpoint()
                    checkpoint = None
            else:
                print(f"\nExisting checkpoint is invalid: {reason}")
                print("A new checkpoint will be created.")
                clear_checkpoint()
                checkpoint = None

        # Create new checkpoint if needed
        if checkpoint is None:
            checkpoint = create_checkpoint(
                backup_files, target_group.id, target_group.title,
                merge, len(all_messages)
            )
            save_checkpoint(checkpoint)

        # === CONFIRMATION (only for new restores starting from beginning) ===
        if start_index == 0:
            print("\n" + "=" * 60)
            print(f"Ready to send {len(all_messages)} messages to: {target_group.title}")
            print("=" * 60)
            confirm = input("\nProceed? (yes/no): ").strip().lower()

            if confirm != 'yes':
                print("Restoration cancelled")
                return

        # Send messages
        print("\nRestoring messages...")
        start_time = time.time()

        for idx in range(start_index, len(all_messages)):
            message_data = all_messages[idx]
            display_num = idx + 1

            print(f"\nSending message {display_num}/{len(all_messages)} (ID: {message_data.get('message_id', 'unknown')})", end='')

            # Format message
            message_text = format_message_text(message_data)

            # Get media path (relative to backup directory)
            media_path = None
            if message_data.get('media_path'):
                # Try to resolve media path relative to backup file
                for backup_file in backup_files:
                    backup_dir = Path(backup_file).parent
                    potential_path = backup_dir / message_data['media_path']
                    if potential_path.exists():
                        media_path = str(potential_path)
                        break

            # Send message
            success = await send_message_with_retry(
                client,
                target_group,
                message_text,
                media_path
            )

            if success:
                success_count += 1
                print(" ✓")
            else:
                failed_count += 1
                failed_message_ids.append(message_data.get('message_id'))
                print(" ✗")

            # === UPDATE CHECKPOINT AFTER EACH MESSAGE ===
            elapsed = prior_elapsed + (time.time() - start_time)
            checkpoint['last_successful_index'] = idx
            checkpoint['last_message_id'] = message_data.get('message_id')
            checkpoint['success_count'] = success_count
            checkpoint['failed_count'] = failed_count
            checkpoint['failed_message_ids'] = failed_message_ids
            checkpoint['elapsed_seconds'] = elapsed
            save_checkpoint(checkpoint)

            # Rate limiting delay
            delay = MEDIA_DELAY if media_path else MESSAGE_DELAY
            await asyncio.sleep(delay)

            # Progress update every 10 messages
            if display_num % 10 == 0:
                total_elapsed = prior_elapsed + (time.time() - start_time)
                messages_sent_this_session = idx - start_index + 1
                if messages_sent_this_session > 0:
                    avg_time = (time.time() - start_time) / messages_sent_this_session
                    remaining = (len(all_messages) - display_num) * avg_time
                    print(f"  Progress: {display_num}/{len(all_messages)} | Success: {success_count} | Failed: {failed_count}")
                    print(f"  Estimated time remaining: {int(remaining / 60)}m {int(remaining % 60)}s")

        # === SUCCESSFUL COMPLETION ===
        clear_checkpoint()

        elapsed = prior_elapsed + (time.time() - start_time)
        print("\n" + "=" * 60)
        print("Restoration Complete")
        print("=" * 60)
        print(f"Total messages: {len(all_messages)}")
        print(f"Successfully sent: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Time taken: {int(elapsed / 60)}m {int(elapsed % 60)}s")

    except KeyboardInterrupt:
        print("\n\nInterrupted! Progress has been saved.")
        print("Run the script again to resume from where you left off.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("Progress has been saved. Run the script again to resume.")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


def main():
    """Entry point for the script."""
    print("=" * 60)
    print("Telegram Message Restoration Tool")
    print("=" * 60)
    print("\nThis script restores messages from backup JSON files")
    print("to a new Telegram group with timestamps and author names.")
    print()

    # Get target group from environment or prompt
    target_group = os.getenv('TARGET_GROUP')
    if target_group:
        print(f"Target group (from env): {target_group}")
    else:
        target_group = input("Enter target group username (e.g., @newgroup) or group ID: ").strip()
        if not target_group:
            print("Error: Target group is required")
            return

    # Get backup files from environment or prompt
    backup_files_env = os.getenv('BACKUP_FILES')
    if backup_files_env:
        backup_files = [f.strip() for f in backup_files_env.split(',') if f.strip()]
        print(f"Backup files (from env): {len(backup_files)} file(s)")
        for f in backup_files:
            print(f"  - {f}")
    else:
        print("\nEnter backup file paths (one per line, empty line to finish):")
        backup_files = []
        while True:
            file_path = input(f"Backup file {len(backup_files) + 1}: ").strip()
            if not file_path:
                break
            backup_files.append(file_path)

    if not backup_files:
        print("Error: At least one backup file is required")
        return

    # Get merge setting from environment or prompt
    merge_env = os.getenv('MERGE_MESSAGES')
    if merge_env:
        merge = merge_env.lower() in ('yes', 'true', '1')
        print(f"Merge and sort messages (from env): {'yes' if merge else 'no'}")
    else:
        merge = input("\nMerge and sort messages by date? (yes/no) [yes]: ").strip().lower()
        merge = merge != 'no'

    # Run the async function
    asyncio.run(restore_messages(backup_files, target_group, merge))


if __name__ == '__main__':
    main()
