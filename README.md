# Telegram Group Backup and Recovery Tool

A set of Python scripts to backup, recover, and restore Telegram group messages and media using the Telegram MTProto API.

## Features

- **Recover recently deleted messages** (within 48 hours) using Admin Log API
- **Backup current group messages** and media to JSON format
- **Restore messages** to a new group with timestamps and author names
- **Download media files** (photos, videos, documents, etc.)
- **Rate limiting protection** with automatic retry

## Prerequisites

1. **Python 3.7+** installed on your system
2. **Telegram API credentials** (API ID and API Hash)
3. **Admin access** to the group you want to backup/recover

## Setup Instructions

### Step 1: Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click on "API development tools"
4. Fill in the form to create a new application
5. Save your `api_id` and `api_hash`

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install telethon cryptg
```

### Step 3: Set Environment Variables

Set the following environment variables:

**On Linux/macOS:**
```bash
export TELEGRAM_API_ID="your_api_id"
export TELEGRAM_API_HASH="your_api_hash"
export TELEGRAM_PHONE="your_phone_number"  # e.g., +1234567890
```

**On Windows (Command Prompt):**
```cmd
set TELEGRAM_API_ID=your_api_id
set TELEGRAM_API_HASH=your_api_hash
set TELEGRAM_PHONE=your_phone_number
```

**On Windows (PowerShell):**
```powershell
$env:TELEGRAM_API_ID="your_api_id"
$env:TELEGRAM_API_HASH="your_api_hash"
$env:TELEGRAM_PHONE="your_phone_number"
```

Alternatively, you can create a `.env` file in the project directory:
```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890
```

## Usage

### Script 1: Retrieve Deleted Messages

**Purpose:** Recover messages deleted within the last 48 hours from the Admin Log.

**Important:** This only works if:
- Messages were deleted within the last 48 hours
- You have admin access to the group
- The group is a supergroup (not a basic group)

**Run:**
```bash
python 1_retrieve_deleted_messages.py
```

**Input:**
- Group username (e.g., `@yourgroup`) or group ID

**Output:**
- `deleted_messages_backup/deleted_messages_YYYYMMDD_HHMMSS.json`
- `deleted_messages_backup/deleted_media/` (media files)

### Script 2: Backup Current Messages

**Purpose:** Backup all current messages and media from a group.

**Run:**
```bash
python 2_backup_current_messages.py
```

**Input:**
- Group username (e.g., `@yourgroup`) or group ID
- Message limit (optional, press Enter for all messages)

**Output:**
- `current_messages_backup/current_messages_YYYYMMDD_HHMMSS.json`
- `current_messages_backup/current_media/` (media files)

### Script 3: Restore Messages to New Group

**Purpose:** Restore backed up messages to a new group with timestamps and author names.

**Prerequisites:**
- Create a new Telegram group
- Add the bot/account to the new group
- Make sure you have permission to send messages

**Run:**
```bash
python 3_restore_messages.py
```

**Input:**
- Target group username or ID (e.g., `@newgroup`)
- Paths to backup JSON files (one per line, empty line to finish)
- Whether to merge and sort messages by date

**Output:**
- Messages sent to the target group with formatted headers

### Example: Complete Recovery Workflow

1. **Recover deleted messages** (if within 48 hours):
   ```bash
   python 1_retrieve_deleted_messages.py
   ```

2. **Backup current messages**:
   ```bash
   python 2_backup_current_messages.py
   ```

3. **Create a new group** in Telegram

4. **Restore all messages**:
   ```bash
   python 3_restore_messages.py
   ```
   Enter both backup file paths when prompted:
   - `deleted_messages_backup/deleted_messages_20241112_160000.json`
   - `current_messages_backup/current_messages_20241112_160100.json`

## Message Format

Restored messages will have the following format:

```
📅 2024-11-12 15:30:45 | 👤 John Doe | 📎 Photo
--------------------------------------------------
This is the message text content
```

For deleted messages:
```
📅 2024-11-12 15:30:45 | 👤 John Doe | 🗑️ DELETED
--------------------------------------------------
This message was deleted
```

## File Structure

```
backup-tg/
├── 1_retrieve_deleted_messages.py   # Script to recover deleted messages
├── 2_backup_current_messages.py     # Script to backup current messages
├── 3_restore_messages.py            # Script to restore messages
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── deleted_messages_backup/         # Output from script 1
│   ├── deleted_messages_*.json
│   └── deleted_media/
├── current_messages_backup/         # Output from script 2
│   ├── current_messages_*.json
│   └── current_media/
└── telegram_*_session.session       # Telethon session files
```

## Backup File Format

Backup files are stored in JSON format with the following structure:

```json
{
  "group_id": 123456789,
  "group_title": "My Group",
  "backed_up_at": "2024-11-12T16:00:00",
  "total_messages": 1000,
  "messages": [
    {
      "message_id": 1,
      "date": "2024-01-01T12:00:00",
      "sender_id": 987654321,
      "sender_name": "John Doe",
      "text": "Hello world",
      "media_type": "MessageMediaPhoto",
      "media_path": "deleted_media/photo_1.jpg",
      "reply_to_msg_id": null,
      "forward_info": null
    }
  ]
}
```

## Limitations

1. **48-hour window for deleted messages**: The Admin Log API only retains deleted messages for 48 hours
2. **Rate limiting**: Telegram has rate limits. The scripts include delays to avoid hitting limits
3. **Media files**: Large media files may take time to download
4. **Slow mode**: If the target group has slow mode enabled, restoration will be slower
5. **Group type**: Some features only work with supergroups, not basic groups

## Troubleshooting

### "FloodWaitError"
- The script will automatically wait and retry
- This happens when you send too many messages too quickly

### "You must be an admin"
- Make sure you have admin privileges in the source group
- For deleted messages recovery, admin access is required

### "Could not find the group"
- Make sure the group username is correct (include the @ symbol)
- Alternatively, use the numeric group ID
- Ensure you're a member of the group

### "Session file not found" on first run
- This is normal - you'll be asked to enter a verification code sent to your Telegram
- The session will be saved for future runs

### Media files not uploading
- Check that the media files exist in the backup directory
- Large files may fail due to Telegram size limits (2GB for regular users, 4GB for Premium)
- Check your internet connection

## Security Notes

1. **Keep your API credentials secure** - Never share your API ID and API Hash
2. **Session files contain authentication** - Protect `.session` files
3. **Backup files may contain sensitive data** - Store them securely
4. **Be careful with rate limits** - Avoid modifying delay settings unless necessary

## Rate Limiting

The restoration script includes rate limiting protection:
- 1 second delay between text messages
- 2 seconds delay for messages with media
- Automatic retry on FloodWaitError
- Automatic handling of slow mode

## Tips

1. **Test with a small backup first** - Use the message limit option to test with a few messages
2. **Keep original groups** - Don't delete the original group until restoration is verified
3. **Check media files** - Verify that media files are properly downloaded before restoring
4. **Use message limits** - For large groups, consider backing up in batches
5. **Monitor progress** - The scripts show progress updates every 10 messages

## Support

If you encounter issues:
1. Check that all environment variables are set correctly
2. Verify you have the necessary permissions
3. Check your internet connection
4. Review the error messages for specific details

## License

This tool is provided as-is for personal use. Make sure to comply with Telegram's Terms of Service when using the API.
