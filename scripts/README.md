## Workshop Scripts

This folder now includes a single weekly workflow script:

- `workshop_manager.py`: manage weekly workshop room rotation.
  - Pick top `N` unique usernames from a source list.
  - Skip usernames that were already invited in past runs.
  - Auto-detect private group vs public channel and call correct APIs.
  - Move previous week's invited users to an archive room (or kick if archive room is not set).
  - Optionally clear room messages.
  - Invite the new batch.
  - Post a default onboarding welcome message after successful invites.
  - Persist history in `workshop_state.json`.

## Setup

1. Install dependencies:
   ```bash
   cd scripts
   pip install -r requirements.txt
   ```
2. Configure environment variables:
   - Copy `.env.example` to `.env` and fill:
     - `RC_TOKEN`
     - `RC_UID`
     - `RC_RID`
     - optionally `RC_URL`
3. Configure workshop defaults:
   - Copy `workshop_config.example.json` to `workshop_config.json`.
   - Optional:
     - `archive_room_id` (if set, old batch is moved here before new invites)
     - `send_welcome_message` (`true`/`false`)
     - `welcome_message` (custom message text)

## Username Source File

`workshop_manager.py` accepts:

- `.txt`: one username per line (with or without `@`)
- `.csv`: first column usernames (header optional)
- `.json`: list of usernames, or objects containing `username` / `usernames` / `entries`

## Weekly Workflow

1. Preview selected users:
   ```bash
   python workshop_manager.py preview --source ./weekly_usernames.txt --limit 15
   ```
2. Rotate weekly batch (move previous to archive if configured, then invite new):
   ```bash
   python workshop_manager.py rotate --source ./weekly_usernames.txt --limit 15
   ```
3. Rotate and also clear room messages:
   ```bash
   python workshop_manager.py rotate --source ./weekly_usernames.txt --limit 15 --clear-messages --max-messages 1000
   ```
4. Dry run (no server mutations, no state updates):
   ```bash
   python workshop_manager.py rotate --source ./weekly_usernames.txt --limit 15 --dry-run
   ```

## Cleanup Only

Move previous batch to archive room (or kick if not configured), without inviting:

```bash
python workshop_manager.py cleanup
```

Kick previous batch and clear messages:

```bash
python workshop_manager.py cleanup --clear-messages --max-messages 1000
```

## State Tracking

The script stores run history in `workshop_state.json`:

- `batches`: each invite run with week label, invited users, failures, cleanup results
- `invited_index`: lookup of previously invited usernames with timestamps and invite count

This state is used to filter out already invited users on future weeks.

## Legacy Scripts

Older scripts are still in this folder (`invite.py`, `kick_users.py`, etc.) but the recommended weekly flow is `workshop_manager.py`.
