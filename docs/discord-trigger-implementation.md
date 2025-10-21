# Discord Trigger Implementation Summary

## Overview
Added a new Discord trigger: **"New Message in Channel"** that triggers when a new message is received in a specific Discord channel.

## Changes Made

### 1. Backend Changes

#### a. Discord Scheduler (`apps/server/app/integrations/simple_plugins/discord_scheduler.py`)
- Created new polling scheduler similar to Gmail scheduler
- Polls Discord channels every 10 seconds for new messages
- Tracks seen messages per area to avoid duplicate triggers
- Extracts message data including:
  - Message ID, content, timestamp, channel ID
  - Author information (ID, username, discriminator, global name)
  - Attachments and embeds
- Provides variables for use in actions:
  - `{{discord.message.id}}`
  - `{{discord.message.content}}`
  - `{{discord.message.timestamp}}`
  - `{{discord.message.channel_id}}`
  - `{{discord.author.id}}`
  - `{{discord.author.username}}`
  - `{{discord.author.discriminator}}`
  - `{{discord.author.global_name}}`
  - `{{discord.attachments}}`
  - `{{discord.embeds}}`

#### b. Service Catalog (`apps/server/app/integrations/catalog.py`)
- Added new action to Discord service integration:
  ```python
  AutomationOption(
      key="new_message_in_channel",
      name="New Message in Channel",
      description="Triggers when a new message is received in a specific Discord channel.",
  )
  ```

#### c. Main Application (`apps/server/main.py`)
- Added Discord scheduler imports
- Started Discord scheduler in application lifespan startup
- Stopped Discord scheduler in application lifespan shutdown

#### d. Tests (`apps/server/tests/test_discord_scheduler.py`)
- Created comprehensive test suite covering:
  - Message fetching functionality
  - Message data extraction
  - Area fetching from database
  - Trigger processing
  - Scheduler lifecycle management
  - Error handling and cancellation

### 2. Frontend Changes

#### a. Controls Panel (`apps/web/src/components/area-builder/ControlsPanel.tsx`)
- Added Discord trigger parameter input section
- Allows users to specify the Discord channel ID to monitor
- Input field with proper validation and placeholder
- Help text explaining the parameter

## Configuration Required

### Environment Variables
The Discord trigger requires the following environment variable to be set:
```bash
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

This is the same bot token used for Discord actions (send_message, create_channel).

## How It Works

1. **Scheduler Startup**: When the application starts, the Discord scheduler task begins running
2. **Polling**: Every 10 seconds, the scheduler:
   - Fetches all enabled areas with `trigger_service='discord'` and `trigger_action='new_message_in_channel'`
   - For each area, retrieves the configured `channel_id` from `trigger_params`
   - Fetches recent messages from that Discord channel using the bot token
   - Compares fetched messages against previously seen messages
3. **Trigger Execution**: When a new message is detected:
   - Creates an execution log entry
   - Extracts message data into variables
   - Executes the area's workflow using `execute_area()`
   - Updates the execution log with success/failure status
   - Marks the message as seen

## Usage Example

**Automation**: "When a new message is posted in #general, send it to Gmail"

1. **Trigger**: Discord - "New Message in Channel"
   - Channel ID: `123456789012345678` (your #general channel ID)

2. **Action**: Gmail - "Send Email"
   - To: `your-email@example.com`
   - Subject: `New Discord message from {{discord.author.username}}`
   - Body: `{{discord.message.content}}`

## Testing

Run tests with:
```bash
cd apps/server
python -m pytest tests/test_discord_scheduler.py -v
```

Or run all tests:
```bash
make test
```

## Rate Limiting Considerations

- The scheduler polls every 10 seconds to respect Discord API rate limits
- Uses the same bot token as Discord actions
- Fetches up to 10 messages per poll by default
- Tracks seen messages in memory to avoid duplicate processing

## Variables Available in Workflows

When a Discord message trigger fires, the following variables are available for use in subsequent actions:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{discord.message.id}}` | Unique message ID | `987654321098765432` |
| `{{discord.message.content}}` | Message text content | `Hello world!` |
| `{{discord.message.timestamp}}` | ISO timestamp of message | `2023-01-01T12:00:00.000000+00:00` |
| `{{discord.message.channel_id}}` | Channel where message was sent | `123456789012345678` |
| `{{discord.author.id}}` | Message author's user ID | `111222333444555666` |
| `{{discord.author.username}}` | Author's username | `cooluser` |
| `{{discord.author.discriminator}}` | Author's discriminator (legacy) | `1234` |
| `{{discord.author.global_name}}` | Author's display name | `Cool User` |
| `{{discord.attachments}}` | Array of attachment objects | `[{id, filename, url, content_type}]` |
| `{{discord.embeds}}` | Array of embed objects | `[{...}]` |

## Architecture Notes

- Follows the same pattern as Gmail scheduler
- Uses in-memory storage for tracking seen messages (resets on server restart)
- Scheduler runs as an async background task
- Each area is processed with its own database session
- Graceful shutdown handling with proper cleanup
