# Dropbox File Recovery Guide

## Overview

This guide explains how to recover file versions from Dropbox programmatically using the Dropbox API.

## When You Need This

- Accidentally deleted files locally before Dropbox synced
- Need to recover specific file versions from a particular date
- Want to check what changes were made on a specific day

## Prerequisites

### 1. Get Dropbox API Token

1. Go to https://www.dropbox.com/developers/apps
2. Click "Create app"
3. Choose:
   - API: Scoped access
   - Access type: Full Dropbox
   - App name: (anything, e.g., "file-recovery-script")
4. After creation, go to the "Permissions" tab
5. Enable these permissions:
   - `files.metadata.read`
   - `files.content.read`
   - `files.content.write` (if you want to restore)
6. Go to "Settings" tab
7. Under "Generated access token", click "Generate"
8. Copy the token (starts with `sl.`)

### 2. Install Dependencies

```bash
pip install dropbox
```

## Usage

### Check File Versions from Specific Date

```bash
python scripts/check_dropbox_versions.py \
  --token YOUR_DROPBOX_TOKEN \
  --date 2025-10-28 \
  --repo-path /github-personal/deep-biblio-tools
```

**Parameters:**
- `--token`: Your Dropbox API access token (required)
- `--date`: Date to check in YYYY-MM-DD format (default: today)
- `--repo-path`: Path to repository in Dropbox (default: /github-personal/deep-biblio-tools)

### Output Example

```
Connected to Dropbox account: John Doe
Checking for file versions from: 2025-10-28
Repository path: /github-personal/deep-biblio-tools
--------------------------------------------------------------------------------

Searching for files with revisions from 2025-10-28...

Found 5 file(s) with revisions from 2025-10-28:
================================================================================

/github-personal/deep-biblio-tools/src/converters/md_to_latex/citation_manager.py
  2 revision(s) from 2025-10-28:
    - 2025-10-28 09:15:23 | 45.2 KB | Rev: abc123def456
    - 2025-10-28 11:30:45 | 46.1 KB | Rev: ghi789jkl012

/github-personal/deep-biblio-tools/docs/ARCHITECTURE.md
  1 revision(s) from 2025-10-28:
    - 2025-10-28 10:22:18 | 12.3 KB | Rev: mno345pqr678

================================================================================

To restore a specific revision:
  dbx.files_restore(path='/path/to/file', rev='revision_id')
```

## Restoring Files

### Option 1: Manual Restore via Web UI

1. Go to https://www.dropbox.com
2. Navigate to the file
3. Click on the file → "Version history"
4. Find the version from the date you want
5. Click "Restore"

### Option 2: Programmatic Restore

Create a restore script:

```python
import dropbox

dbx = dropbox.Dropbox('YOUR_TOKEN')

# Restore specific revision
dbx.files_restore(
    path='/github-personal/deep-biblio-tools/src/file.py',
    rev='abc123def456'  # From check_dropbox_versions.py output
)

print("File restored successfully")
```

### Option 3: Restore to Different Location

```python
import dropbox

dbx = dropbox.Dropbox('YOUR_TOKEN')

# Download specific revision without overwriting
result = dbx.files_download(
    path='/github-personal/deep-biblio-tools/src/file.py',
    rev='abc123def456'
)

# Save to different location
with open('/tmp/recovered_file.py', 'wb') as f:
    f.write(result[1].content)

print("File downloaded to /tmp/recovered_file.py")
```

## Troubleshooting

### "No files found with revisions from [date]"

**Possible causes:**
1. No files were modified on that date
2. Repository path is incorrect (check path in Dropbox web UI)
3. Files were deleted before Dropbox could sync them
4. API token doesn't have access to the path

**Solution:**
- Try checking adjacent dates: `--date 2025-10-27`
- Verify repository path: `--repo-path /Correct/Path/To/Repo`
- Check Dropbox sync status on that date

### "Error connecting to Dropbox"

**Possible causes:**
1. Invalid API token
2. Token expired
3. Network issues

**Solution:**
- Regenerate token at https://www.dropbox.com/developers/apps
- Check internet connection
- Verify token starts with `sl.`

### "Path not found"

**Possible causes:**
1. Repository path doesn't exist in Dropbox
2. Repository is in a different location

**Solution:**
- List root folders: `dbx.files_list_folder('')`
- Check actual path in Dropbox web UI
- Update `--repo-path` parameter

## Dropbox API Limitations

- **Version retention**: Dropbox keeps file versions for 30 days (Basic), 180 days (Plus), or unlimited (Professional/Business)
- **API rate limits**: 600 requests per app per user per day
- **Batch operations**: Script processes one file at a time (could be optimized)

## Security Notes

- **Never commit API tokens** to git repositories
- **Tokens are like passwords** - keep them secret
- **Revoke tokens** after use at https://www.dropbox.com/developers/apps
- **Use short-lived tokens** for one-time operations

## Related Tools

- **Dropbox CLI**: `dropbox` command-line tool (limited version history support)
- **Dropbox Web UI**: Manual version recovery
- **Dropbox API**: Programmatic access (this script)

## See Also

- [Dropbox API Documentation](https://www.dropbox.com/developers/documentation/python)
- [File Versioning API](https://www.dropbox.com/developers/documentation/http/documentation#files-list_revisions)
- [Dropbox Python SDK](https://github.com/dropbox/dropbox-sdk-python)
