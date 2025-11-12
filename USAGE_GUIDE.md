# Telegram Group Recovery - Complete Usage Guide

## Your Situation

You are the owner of a Telegram group where another admin has accidentally deleted all your messages. You need to:
1. Recover the recently deleted messages (if within 48 hours)
2. Backup remaining current messages
3. Restore everything to a new group

## Quick Start

### Option 1: Use the Quick Start Script (Easiest)

**On Linux/macOS:**
```bash
./quick_start.sh
```

**On Windows:**
```
quick_start.bat
```

### Option 2: Manual Setup

Follow the steps below for complete control.

---

## Step-by-Step Guide

### Part 1: Initial Setup (One-time)

#### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Get Telegram API Credentials

1. Open your browser and go to: https://my.telegram.org
2. Log in with your Telegram phone number
3. Click **"API development tools"**
4. Fill in the form:
   - App title: `Backup Tool` (or any name)
   - Short name: `backup` (or any short name)
   - Platform: Select your platform
5. Click **"Create application"**
6. Save the `api_id` and `api_hash` values

#### 3. Configure Environment Variables

Create a `.env` file in the project directory:

```bash
cp .env.example .env
```

Edit the `.env` file and add your credentials:

```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+1234567890
```

**Important:** Replace the values with your actual credentials!

---

### Part 2: Recover Deleted Messages

**⏰ Time-sensitive: This must be done within 48 hours of deletion!**

#### Step 1: Run the Recovery Script

```bash
python 1_retrieve_deleted_messages.py
```

Or with quick start:
```bash
./quick_start.sh
# Select option 1
```

#### Step 2: Provide Group Information

When prompted, enter your group identifier. You can use:

- **Group username** (if public): `@yourgroupname`
- **Group invite link**: `https://t.me/joinchat/XXXXX`
- **Group ID** (if you know it): `-1001234567890`

**How to find your group identifier:**
1. Open Telegram Desktop
2. Right-click on the group
3. Select "Copy Link" (for public groups) or use group ID

#### Step 3: Authenticate

On first run, you'll be asked to:
1. Enter the verification code sent to your Telegram
2. Optionally enter 2FA password if enabled

This creates a session file, so you won't need to do this again.

#### Step 4: Wait for Completion

The script will:
- Connect to Telegram
- Retrieve the admin log
- Find all deleted messages
- Download any media files
- Save everything to JSON

**Output:**
- `deleted_messages_backup/deleted_messages_YYYYMMDD_HHMMSS.json`
- `deleted_messages_backup/deleted_media/` (if messages had media)

---

### Part 3: Backup Current Messages

Now backup all remaining messages that weren't deleted.

#### Step 1: Run the Backup Script

```bash
python 2_backup_current_messages.py
```

Or with quick start:
```bash
./quick_start.sh
# Select option 2
```

#### Step 2: Provide Group Information

Enter the same group identifier as before.

#### Step 3: Set Message Limit (Optional)

- Press **Enter** to backup ALL messages (recommended)
- Or enter a number to limit (e.g., `1000` for last 1000 messages)

#### Step 4: Wait for Completion

This may take a while depending on:
- Number of messages
- Amount of media files
- Internet speed

The script shows progress every message.

**Output:**
- `current_messages_backup/current_messages_YYYYMMDD_HHMMSS.json`
- `current_messages_backup/current_media/` (downloaded media files)

---

### Part 4: Create New Group

Before restoring, you need a new group:

1. Open Telegram
2. Create a new group:
   - Tap the menu icon (☰)
   - Select "New Group"
   - Add a name (e.g., "Restored Group")
   - Add members if desired
3. Make the group a **supergroup** (required):
   - Go to group settings
   - Edit → Group Type → Supergroup
4. Set a username (recommended):
   - Go to group settings
   - Edit → Username
   - Set username (e.g., `restoredgroup`)

---

### Part 5: Restore Messages to New Group

#### Step 1: Run the Restore Script

```bash
python 3_restore_messages.py
```

Or with quick start:
```bash
./quick_start.sh
# Select option 3
```

#### Step 2: Provide Target Group

Enter your NEW group's identifier:
- Username: `@restoredgroup`
- Or group ID

#### Step 3: Provide Backup Files

Enter the paths to backup JSON files. You should enter BOTH:

**First backup file:**
```
deleted_messages_backup/deleted_messages_20241112_160000.json
```

**Second backup file:**
```
current_messages_backup/current_messages_20241112_160100.json
```

*Note: Your filenames will have different timestamps*

Press **Enter** on an empty line when done.

#### Step 4: Choose Merge Option

When asked "Merge and sort messages by date?"
- Type `yes` (recommended) - This will combine both files and sort chronologically
- Type `no` - Messages will be sent in the order of files provided

#### Step 5: Confirm

Review the summary:
- Total messages to send
- Target group name

Type `yes` to proceed.

#### Step 6: Wait for Restoration

The script will:
- Send each message with timestamp and author
- Upload media files
- Show progress every 10 messages
- Automatically handle rate limits

**This will take time!** For example:
- 100 messages: ~2-5 minutes
- 1,000 messages: ~20-50 minutes
- 10,000 messages: ~3-8 hours

**Important:** Don't close the script while running!

---

## Message Format in Restored Group

Messages will appear like this:

```
📅 2024-11-12 15:30:45 | 👤 John Doe
--------------------------------------------------
This is the original message text
```

Deleted messages will be marked:
```
📅 2024-11-12 15:30:45 | 👤 Jane Doe | 🗑️ DELETED
--------------------------------------------------
This message was deleted
```

Messages with media:
```
📅 2024-11-12 16:00:00 | 👤 Bob Smith | 📎 Photo
--------------------------------------------------
Check out this photo!
[Photo will be attached]
```

---

## Troubleshooting

### "FloodWaitError: Too many requests"

**Solution:** The script will automatically wait and retry. This is normal.

### "Admin privileges required"

**Solution:** Make sure you're an admin in the source group with "Delete messages" permission.

### "Group not found"

**Solutions:**
- Check the username spelling (include @)
- Make sure the group is a supergroup, not a basic group
- Try using the numeric group ID instead

To get group ID:
```python
# Run this temporarily in any script:
async with client:
    entity = await client.get_entity('@yourgroupname')
    print(f"Group ID: {entity.id}")
```

### No Deleted Messages Found

**Possible reasons:**
- Messages were deleted more than 48 hours ago
- You don't have admin access
- Messages weren't actually deleted (check the group)

### Media Files Not Downloading

**Solutions:**
- Check your internet connection
- Some media may have expired (very old messages)
- Ensure you have enough disk space

### "Cannot write to auth key file"

**Solution:** Delete the `.session` files and run again:
```bash
rm telegram_*_session.session*
```

### Script Stops or Crashes

**Solutions:**
- Check your internet connection
- Restart the script (it will resume from where it stopped for restore)
- Check the error message for specific issues

---

## Tips for Best Results

### Before Starting

1. ✅ Make sure you have admin access to the original group
2. ✅ Check that messages were deleted within 48 hours (for recovery)
3. ✅ Have stable internet connection
4. ✅ Free up disk space (for media files)
5. ✅ Set up API credentials correctly

### During Backup

1. ✅ Don't close the terminal window
2. ✅ Keep your computer from sleeping
3. ✅ Monitor progress messages
4. ✅ Wait for completion confirmation

### During Restoration

1. ✅ Don't send any messages to the new group manually during restoration
2. ✅ Keep the script running (don't interrupt)
3. ✅ If you must stop, you can run it again later
4. ✅ Monitor for error messages

### After Restoration

1. ✅ Verify messages in the new group
2. ✅ Check that media files are present
3. ✅ Keep backup files safe (don't delete immediately)
4. ✅ You can delete the old group once verified

---

## File Reference

After running all scripts, you'll have:

```
backup-tg/
├── 1_retrieve_deleted_messages.py
├── 2_backup_current_messages.py
├── 3_restore_messages.py
├── quick_start.sh (or .bat)
├── requirements.txt
├── README.md
├── USAGE_GUIDE.md (this file)
├── .env (your credentials - keep secret!)
│
├── deleted_messages_backup/
│   ├── deleted_messages_20241112_160000.json  ← Deleted messages data
│   └── deleted_media/
│       ├── photo_1.jpg
│       ├── video_2.mp4
│       └── ...
│
├── current_messages_backup/
│   ├── current_messages_20241112_160100.json  ← Current messages data
│   └── current_media/
│       ├── photo_100.jpg
│       ├── document_101.pdf
│       └── ...
│
└── telegram_*_session.session (authentication - keep secret!)
```

---

## Security Reminders

🔒 **Keep these files SECRET:**
- `.env` (contains your API credentials)
- `telegram_*_session.session` (authentication tokens)
- Backup JSON files (may contain private messages)

🚫 **Never share:**
- Your API_ID and API_HASH
- Your session files
- Backup files with sensitive content

---

## Getting Help

If you encounter issues:

1. **Read error messages carefully** - they often explain the problem
2. **Check this guide** - most issues are covered above
3. **Verify credentials** - make sure .env is set up correctly
4. **Check permissions** - ensure you have admin access
5. **Internet connection** - verify you're online

---

## Summary of Your Recovery Process

1. ✅ **Setup** (10 minutes)
   - Install dependencies
   - Get API credentials
   - Configure .env file

2. ✅ **Recover Deleted** (5-15 minutes)
   - Run script 1
   - Provide group info
   - Wait for completion

3. ✅ **Backup Current** (varies by size)
   - Run script 2
   - Provide group info
   - Wait for all messages to backup

4. ✅ **Create New Group** (2 minutes)
   - Create in Telegram
   - Make it a supergroup
   - Set username

5. ✅ **Restore Everything** (varies by size)
   - Run script 3
   - Provide both backup files
   - Wait for restoration

6. ✅ **Verify** (5 minutes)
   - Check messages in new group
   - Verify media files
   - Confirm everything is there

---

Good luck with your recovery! 🚀
