# Quick Start - 5 Minute Guide

## ⚡ Fast Track to Recovery

### Step 1: Install (2 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### Step 2: Get API Credentials (3 minutes)

1. Go to https://my.telegram.org
2. Login → API development tools → Create application
3. Copy your `api_id` and `api_hash`

### Step 3: Configure (1 minute)

Edit `.env` file:
```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890
```

### Step 4: Run Scripts (Varies)

```bash
# Option A: Use menu (easiest)
./quick_start.sh

# Option B: Run scripts directly
python 1_retrieve_deleted_messages.py  # Recover deleted (within 48h)
python 2_backup_current_messages.py    # Backup current messages
python 3_restore_messages.py           # Restore to new group
```

---

## 📋 Three Script Workflow

### Script 1: Recover Deleted Messages
**When:** Within 48 hours of deletion
**Input:** Your group username or ID
**Output:** `deleted_messages_backup/deleted_messages_*.json`
**Time:** 5-15 minutes

### Script 2: Backup Current Messages
**When:** Anytime
**Input:** Your group username or ID
**Output:** `current_messages_backup/current_messages_*.json`
**Time:** Depends on message count

### Script 3: Restore to New Group
**When:** After running scripts 1 & 2
**Input:**
- New group username
- Both backup JSON file paths
**Output:** All messages restored with timestamps
**Time:** Depends on message count

---

## 🎯 Your Situation: Complete Recovery

Since messages were deleted within 48 hours, run ALL THREE scripts:

```bash
# 1. Recover what was deleted
python 1_retrieve_deleted_messages.py
# Enter: @yourgroupname

# 2. Backup what remains
python 2_backup_current_messages.py
# Enter: @yourgroupname

# 3. Create new group in Telegram app
# Then restore everything:

python 3_restore_messages.py
# Enter: @newgroupname
# Enter backup file 1: deleted_messages_backup/deleted_messages_20241112_160000.json
# Enter backup file 2: current_messages_backup/current_messages_20241112_161500.json
# (Press Enter on empty line)
# Choose: yes (to merge and sort by date)
```

---

## ⚠️ Important Notes

- **48-hour limit** for deleted message recovery
- **Admin access** required in source group
- **Stable internet** needed throughout process
- **Don't interrupt** scripts while running
- **Keep .env and .session files secure**

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "FloodWaitError" | Script auto-waits, this is normal |
| "Group not found" | Use @username or numeric ID |
| "Not admin" | Need admin rights in source group |
| No deleted messages | Outside 48h window or not admin |
| Session error | Delete `.session` files and retry |

---

## 📁 What You'll Have

```
backup-tg/
├── deleted_messages_backup/
│   ├── deleted_messages_*.json    ← Recovered deleted messages
│   └── deleted_media/              ← Deleted media files
│
├── current_messages_backup/
│   ├── current_messages_*.json    ← Current messages
│   └── current_media/              ← Current media files
│
└── [New Telegram Group]            ← Everything restored!
```

---

## 💡 Pro Tips

1. **Test first**: Use a test group before the real one
2. **Backup originals**: Don't delete original group until verified
3. **Check disk space**: Media files can be large
4. **Use Wi-Fi**: Mobile data may not be sufficient
5. **Read full guide**: See `USAGE_GUIDE.md` for details

---

## Need More Help?

- **Detailed instructions:** Read `USAGE_GUIDE.md`
- **Technical details:** Read `README.md`
- **Common issues:** See troubleshooting sections in guides

---

## Ready? Let's Go! 🚀

```bash
./quick_start.sh
```
