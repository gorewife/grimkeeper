# Grimkeeper Technical Documentation

## Table of Contents
1. [Architecture](#architecture)
2. [Core Systems](#core-systems)
3. [Command Reference](#command-reference)
4. [Advanced Features](#advanced-features)
5. [Data Persistence](#data-persistence)
6. [Production Deployment](#production-deployment)

---

## Architecture

Grimkeeper manages Blood on the Clocktower sessions on Discord. It handles voice channels, nicknames, and timers. Game mechanics are left to tools like clocktower.live.

**Tech Stack:**
- Python 3.8+
- discord.py (latest)
- PostgreSQL 12+ with asyncpg (connection pooling)
- aiohttp for wiki API requests
- BeautifulSoup4 for HTML parsing
- asyncio for background tasks

**Modular Design:**
This repository has been refactored from a single large `main.py` into a small package (`botc/`) that contains helpers and cogs. Command handlers and long-running systems (polls, timers) are implemented as discord.py Cogs for better lifecycle management and testability.

Key modules:
- `main.py` — entrypoint that wires the `botc` package and exposes a bot contract used by cogs (e.g., `bot.get_active_players`, `bot.timer_manager`, `bot.is_storyteller`, `bot.call_townspeople`, slash command handlers).
- `botc/constants.py` — centralized constants (VERSION, prefixes, delays, poll mappings, script emojis).
- `botc/database.py` — async PostgreSQL operations with connection pooling, game tracking, and storyteller stats.
- `botc/session.py` — Session and SessionManager classes for multi-session support.
- `botc/utils.py` — parsing helpers (duration, timestamp formatting).
- `botc/wiki.py` — BOTC wiki API integration for character lookups.
- `botc/polls.py` — poll creation and completion logic with emoji-based voting.
- `botc/timers.py` — TimerManager class: schedules timers, persists state to database, and restores timers on restart.
- `botc/cogs/slash.py` — slash command registration cog (includes `/character` with button navigation).
- `botc/cogs/polls.py` — message-based `*poll` command handler.
- `botc/cogs/timers.py` — message-based `*call` and `*timer` command handlers.
- `botc/cogs/commands.py` — all message-based prefix commands (`*help`, `*st`, `*g`, etc.).
- `migrations/` — SQL migration files for database schema versioning (001-005).

The remainder of this document describes the same high-level systems (nickname prefixes, voice channel management, shadow follow, timers, game tracking, storyteller stats, multi-session support, wiki integration, etc.) with notes about implementation location.

---

## Core Systems

### 0. The Session-scoped (per-category) system

When you use `/autosetup` or `/setbotc` and choose a category, that category becomes a "session" or a "botc cateogry".
This enables much of the bot's functionality and many of the core features require you to have one set up.
Among these is that it saves such category's voice channel caps to use as a reference for the dynamic vc cap changes
I'll go in depth into what these are more in this document

### 1. Nickname Prefix System

The bot uses nickname prefixes to track user roles and states:

| Prefix | Meaning | Command | Exclusive? |
|--------|---------|---------|------------|
| `(ST) ` | Storyteller | `*st` | Yes (with Co-ST, Spectator) |
| `(Co-ST) ` | Co-Storyteller | `*cost` | Yes (with ST, Spectator) |
| `!` | Spectator | `*!` | Yes (with ST, Co-ST) |
| `[BRB] ` | Away/Break | `*brb` | No (stacks with others) |

**Exclusive Prefixes:** ST, Co-ST, and Spectator cannot coexist. Toggling one removes the others.

**Nickname Trimming:** Discord limits nicknames to 32 characters. If adding prefixes would exceed this, the base nickname is automatically trimmed.

**Storyteller Logic:**
- Multiple storytellers can exist in one server
- Claiming Storyteller (`*st`) removes the prefix of a storyteller if there's one active in the same category
- Claiming Storyteller also clears the grimoire link for that category
- Unclaiming Storyteller keeps the grimoire link

### 2. Voice Channel Cap Management

**Problem Solved:** When Storytellers/Co-Storytellers/Spectators join a voice channel that's at capacity, normal users can't join.

**Solution:** Automatic channel cap adjustment.

**How It Works:**
```
1. When you use `/setbotc` the bot saves a snapshot of the category's vc caps
2. Privileged user joins a capped vc
2. Bot increments the applied count (+1)
3. Bot sets new limit = original + applied
4. When privileged user leaves, decrement applied count
5. When applied count reaches 0, backup data is cleared
```

**Edge Cases Handled:**
- Multiple privileged users stacking increments
- Original cap restored when all privileged users leave
- Requires "Manage Channels" permission

**Technical Details:**
- Tracked caps are stored in the session’s vc_caps snapshot: {channel_id: original_limit, ...}
- Only channels included in the latest /setbotc snapshot are managed
- If you add or change voice channels, run /setbotc <category> again to update the snapshot
- No backup dict or incremental tracking—cap is always recalculated from the snapshot plus current privileged users

### 3. Shadow Follow System

**Purpose:** Allow spectators to automatically follow players between voice channels.

**Components:**
- `shadow_followers`: Maps target user → set of follower user IDs
- `follower_targets`: Maps follower user ID → target user ID (reverse lookup)

**Rules:**
1. Only users with Spectator prefix (`!`) can use `*spec`
2. Users can only follow one person at a time
3. Following a new person automatically unfollows the old target
4. Target users can enable DND (`*dnd`) to prevent being followed
5. Enabling DND automatically removes all current followers
6. When target moves to a new voice channel, all followers move too
7. Followers must be in a voice channel to be moved (checked before move attempt)

**Commands:**
- `*spec @user` - Start following (requires Spectator prefix)
- `*unspec` - Stop following
- `*shadows` - View all active follow relationships (10s auto-delete)
- `*dnd` - Toggle "Do Not Disturb" to prevent followers

**Auto-Cleanup:**
- `clean_followers()` runs after any shadow command to remove stale references
- Removes followers/targets that are no longer server members

**Immediate Following:**
- When you `*spec` someone, if both of you are in voice channels, you're immediately moved to their channel
- No need to wait for them to switch channels first

### 4. Timer System

**Purpose:** Schedule delayed "call to town square" with flexible duration input.

**Requirements:**
- Active game must be started with `/startgame`
- Storyteller or Co-Storyteller prefix required

**Features:**
- Multiple duration formats supported: `5m`, `1h30m`, `90`, `1:30`, `1:02:30`
- Shorthand support: `*5m` works the same as `*timer 5m`
- Persistent announcements that stay until completion/cancellation
- Timer state persists across bot restarts
- Automatic cancellation when `*call` is executed manually
- Discord timestamp formatting (shows end time in each user's local timezone)

**Duration Parser:**
```python
Supported formats:
- Plain seconds: "90" → 90 seconds
- With units: "5m" → 5 minutes
- Combined: "1h30m" → 90 minutes
- Colon (MM:SS): "1:30" → 1 minute 30 seconds
- Colon (HH:MM:SS): "1:02:30" → 1 hour 2 minutes 30 seconds
- Mixed units: "1d2h30m" → 1 day, 2 hours, 30 minutes
```

**Timer Lifecycle:**
1. **Creation:** `*timer <duration>` (ST/Co-ST only)
   - Cancels any existing timer
   - Creates asyncio background task
   - Saves timer state to database
   - Posts persistent announcement with end time

2. **Checking:** `*timer` (anyone)
   - Shows remaining time and end time
   - 8-second auto-delete

3. **Cancellation:** `*timer cancel` (ST/Co-ST only)
   - Stops background task
   - Removes persistent announcement
   - Updates database state
   - 4-second confirmation

4. **Completion:**
   - Calls `call_townspeople()` helper
   - Posts dramatic gold embed: "⏰ TIME'S UP!"
   - Shows count of moved players
   - 15-second auto-delete
   - Cleans up timer state

**Persistence:**
- Active timers saved to database with end_time, creator, and category_id
- On bot restart, `load_timers()` restores unexpired timers
- Remaining time calculated: `end_time - current_time`
- Expired timers discarded during load

**Error Handling:**
- If town square not configured: Error message
- If BOTC category not found: Error message
- If bot lacks Move Members permission: Error message
- All errors auto-delete after 5 seconds

### 5. Town Square System

**Purpose:** Move all players from various voice channels in the BOTC category to a single "Town Square" channel.

**Requirements:**
- Active game must be started with `/startgame`
- Storyteller or Co-Storyteller prefix required

**Configuration:**
- `/setbotc <name|id>` - Set the BOTC category (admin only)
- `/settown #channel` - Set the town square destination (admin only)

**Execution:**
- `*call` - Move everyone immediately (ST/Co-ST only, requires active game)
- `*timer <duration>` or `*<duration>` - Schedule a delayed call (ST/Co-ST only, requires active game)

**Category Matching:**
The bot uses a two-tier matching system:
1. **Configured ID (preferred):** Uses exact category ID from `*setbotc`
2. **Name fallback:** Matches category names: "botc", "bot c", "🩸• blood on the clocktower", "blood on the clocktower"

**Move Logic:**
```python
For each voice channel in BOTC category:
    For each member in that channel:
        Try to move member to town square
        Log failures but continue with others
```

**Exclusions:**
- Bots are not moved (bot accounts are skipped).
- Members who are already in the configured Town Square channel are skipped to avoid redundant moves.

Note: Storytellers, Co-Storytellers, and Spectators are still subject to moves unless they are already in the Town Square channel.

**Permission Check:**
- Requires "Move Members" permission
- Checked before attempting any moves
- Clear error message if missing

### 6. Player List System

**Purpose:** Show active players and track who joined/left since last check.

**Command:** `*players`

**Player Definition:**
A player is anyone in a BOTC category voice channel who is NOT:
- A bot
- Prefixed with `(ST) ` or `(Co-ST) ` (Storytellers)
- Prefixed with `!` (Spectators)
- Note: `[BRB] ` users ARE counted as players

**Snapshot Tracking:**
```python
# Stored per guild
last_player_snapshots[guild_id] = set(player_names)

# On each *players call:
current = set(current_players)
last = last_player_snapshots.get(guild_id, set())

joined = current - last
left = last - current
```

**Display:**
- **First call:** Shows current players, no joined/left (no previous snapshot)
- **Subsequent calls:** Shows current players + joined/left changes
- **No changes:** Shows "No changes since last check"

**Large List Handling:**
- Discord embed limit: 6000 characters
- Player list field limit: ~5500 characters
- If exceeded: Truncates list and shows "...and X more"
- Joined/Left lists also truncated at 1000 chars if needed

**Requirements:**
- BOTC category must be configured first
- Returns error if category not set or not found

### 7. Grimoire Link System

**Purpose:** Store and share grimoire links (typically clocktower.live links).

**Commands:**
- `*g <link>` - Set grimoire link (ST/Co-ST only)
- `*g` - View current grimoire link (anyone)

**Features:**
- **Session-scoped:** Each category has its own independent grimoire link
- Run `*g <link>` from within a category to set that session's grimoire
- Link is cleared when someone new claims Storyteller with `*st` **in that session**
- Link persists when current ST unclaims with `*st` again
- Setting a new link shows permanent embed with clickable link
- Viewing shows simple text message with link

**Multi-Session Example:**
- Category "Blood on the Clocktower 1" has grimoire link A
- Category "Blood on the Clocktower 2" has grimoire link B
- Running `*g` in category 1 shows link A, running it in category 2 shows link B

**Storage:**
- Persisted to `sessions` table
- Format: category-specific grimoire links (guild_id + category_id composite key)

**Embed Display:**
```python
When set:
📜 Grimoire Link Set
<clickable link>

When viewed:
📜 Current grimoire link: <link>
```

### 8. Rate Limiting

**Purpose:** Prevent command spam from overwhelming the bot or Discord API.

**Implementation:**
- 2-second cooldown per user per command
- Tracked in `command_cooldowns` dict: `{user_id: {command: timestamp}}`
- Applied to all commands starting with `*`
- Silently ignores rate-limited commands (no error message)

**Technical:**
```python
def check_rate_limit(user_id, command):
    now = time.time()
    last_used = command_cooldowns[user_id].get(command, 0)
    
    if now - last_used < 2:  # COOLDOWN_SECONDS
        return False  # Rate limited
    
    command_cooldowns[user_id][command] = now
    return True  # Allowed
```

**User Experience:**
- Fast typers or accidental double-sends are ignored
- No spam in chat from error messages

### 9. Wiki Integration & Character Lookup

**Purpose:** Provide instant access to official BOTC character information from the wiki.

**Command:** `/character <name>` (case-insensitive)

**Features:**
- Fetches data from https://wiki.bloodontheclocktower.com/
- Interactive button navigation between sections
- Character icons displayed on summary page
- Team-based color coding (blue for Good, red for Evil)

**Sections:**
1. **Summary** - Character ability and overview (default view)
2. **Tips & Tricks** - Strategy advice for playing the character
3. **Bluffing** - How to bluff as this character (for evil players)
4. **How to Run** - Storyteller guidance and mechanics
5. **Fighting** - How to play against this character

**Implementation (botc/wiki.py):**
- Uses `aiohttp` for async HTTP requests to MediaWiki API
- `BeautifulSoup4` for HTML parsing and content extraction
- Character info parsed from wiki infobox and content sections
- Text cleaning handles wiki formatting tokens (NO ABILITY, YOU ARE, etc.)
- Smart text splitting for Discord's 1024-character field limit

**Button Navigation (botc/cogs/slash.py):**
- `CharacterView` class extends `discord.ui.View`
- 5 navigation buttons for different sections
- Active button highlighted in blue
- 5-minute timeout on interactions
- Embed updates on button click without new message

**Text Processing:**
- Automatic truncation to fit Discord limits
- Paragraph-aware splitting for readability
- Wiki reminder tokens formatted as bold text
- Supports up to 5000 characters per section
- Per-command tracking (running `*help` doesn't block `*players`)

### 9. Game Statistics Tracking

**Purpose:** Track game sessions and maintain server-level statistics.

**Slash Commands:**
- `/startgame <script> [custom_name]` - Start tracking a new game with player confirmation (ST/Co-ST only)
- `/endgame <winner>` - End game and record result (ST/Co-ST only)
- `/addplayer @user` - Add a player to the active game (ST/Co-ST only)
- `/removeplayer @user` - Remove a player from the active game (ST/Co-ST only)
- `/stats` - View server win rates and statistics (everyone)
- `/gamehistory [limit]` - View recent games (everyone, default: 10 games)
- `/deletegame <index>` - Delete a specific game from history (admin only)
- `/clearhistory` - Delete ALL game history (admin only)

**Script Options:**
- 🍺 Trouble Brewing
- 🪻 Sects & Violets
- 🌙 Bad Moon Rising
- ✨ Custom Script (requires custom_name parameter)
- 🏠 Homebrew Script (optional custom_name)

**Game Lifecycle:**
1. **Start:** `/startgame` shows interactive confirmation with player roster
   - Displays current players (anyone in BOTC VCs without spectator prefix)
   - Shows spectators (anyone with spectator prefix)
   - Interactive buttons:
     - ✅ **Confirm** - Start the game with current roster
     - ❌ **Cancel** - Abort game start
     - 🔄 **Refresh** - Re-scan voice channels (updates player list)
   - Validates custom_name required for Custom Script
   - Only storyteller who initiated can confirm/cancel
   - Prevents mistakes from players forgetting to toggle `*!` or being in wrong channels

2. **During Game:** Modify player roster if needed
   - `/addplayer @user` - Manually add a player who joined late or was missed
   - `/removeplayer @user` - Remove a player who left or was added by mistake
   - Updates player count and player list in database
   - Shows confirmation embed with new total

3. **End:** `/endgame` records winner and duration
   - Options: Good, Evil, Cancel
   - Cancel removes game without recording history
   - Creates beautiful public announcement with:
     - Storyteller avatar and name
     - Script name
     - Random flavor text for Good/Evil wins
     - Game duration and player count
     - Color-coded embeds (blue for Good, dark red for Evil)

**Statistics Display:**
- Total games played
- Good/Evil win rates (percentage)
- Most played scripts (top 3)
- Formatted in gold embed

**Storyteller Statistics:**
- Per-storyteller game counts and win rates
- Leaderboard shows guild-specific stats (top 10 storytellers on current server)
- Individual user stats (`/ststats @user`) display as custom-generated stat cards (800x600px images)
- Cards include: avatar, pronouns, favorite script, playing style, bio, games played, win rate, good/evil wins
- Overall Good/Evil win rates for each storyteller
- Script-specific stats with emojis: 🍺 Trouble Brewing, 🪻 Sects & Violets, 🌙 Bad Moon Rising
- Access with `/ststats` (leaderboard) or `/ststats @user` (individual card)
- Legacy `/storytellerstats` command still works as alias
- Automatically tracks storyteller_id on game start
- Updates statistics on game completion

**Storyteller Profiles:**
- Customize your stat card with `/stprofile`
- Optional fields: pronouns (≤15 chars), favorite_script (≤50 chars), style (≤50 chars)
- Profile data displays on your `/ststats` card
- Clear individual fields with `/stprofile` by selecting field and leaving value empty
- Profiles are **bot-wide** (same across all servers, matches bot-wide stats)

**Game History Display:**
- Most recent N games (configurable, default 10)
- Shows: script name, winner, duration
- Emoji indicators: 🏅 (Good), 😈 (Evil), ❌ (Cancel)
- Formatted in blue embed

**Data Storage:**
- PostgreSQL database with asyncpg
- `games` table: Active and completed games with JSONB player data
- `storyteller_stats` table: Per-storyteller statistics and win rates
- Thread-safe database operations with connection pooling

### 10. Script Polling (Enhanced)

**Purpose:** Create timed polls for players to vote on which script to play.

**Commands:** 
- `*poll [123ch] [time]` - Message-based (ST/Co-ST only)
- `/poll <options> [duration]` - Slash command (ST/Co-ST only)

**Options:**
- `1` = Trouble Brewing 🍺
- `2` = Sects & Violets 🪻
- `3` = Bad Moon Rising 🌙
- `c` = Custom Script 🇨
- `h` = Homebrew Script 🇭

**Usage Examples:**
- `*poll 123` or `/poll options:123` - All three base scripts
- `*poll 13c 10m` or `/poll options:13c duration:10m` - TB, BMR, Custom with 10 min timer
- `*poll ch` - Custom and Homebrew only (default 5m)

**Features:**
- Only ST/Co-ST can create polls
- Automatically adds reaction emojis for voting
- Removes duplicate options
- Timed: Auto-announces winner after duration (default: 5 minutes)
- Mentions all active players when poll is created
- Shows poll creator's avatar and name
- Purple embed with gothic formatting
- Discord timestamp shows end time in user's local timezone

**Poll End Behavior:**
- Announces winner after timer expires
- Shows full vote breakdown
- Mentions poll creator
- Handles no-votes gracefully

**Implementation:**
- `botc/polls.py`: `create_poll_internal()` and `_end_poll()` functions
- `botc/cogs/polls.py`: Message command handler
- `botc/cogs/slash.py`: Slash command handler

### 11. Auto-Setup System

**Purpose:** One-command server setup with gothic-themed BOTC structure.

**Command:** `/autosetup` (admin only)

**Multi-Session Support:** You can create multiple independent BOTC sessions on the same server. Each session operates in its own category with isolated channels, timers, games, and configuration.

**Session-Scoped Architecture:**
Each category is a completely independent "session" with its own:
- **Grimoire link** (`*g <link>`) - Set separately per category
- **Town Square** (`*settown #channel`) - Category-specific destination
- **Announcement channel** (`*setannounce #channel`) - Session-specific announcements
- **Exception channel** (`*setexception #channel`) - Private ST channel per category
- **Game history** - Tracked separately per category via `/gamehistory`
- **Active timer** - Each session can have its own countdown

**How It Works:**
All configuration commands (`*g`, `/settown`, `/setannounce`, `/setexception`) must be run **from within** the category they should affect. The bot automatically creates a session for that category when you run the first config command.

**Creating Multiple Sessions:**

**Method 1: Automatic (recommended)**
1. Run `/autosetup` to create your category
2. Run `/autosetup` again to create additional categories
3. Each category is auto-configured with appropriate channels

**Method 2: Manual Setup**
1. Create a Discord category (name it whatever you want)
2. Add text and voice channels inside that category
3. From a channel inside that category, run:
   - `*settown #voice-channel` - Sets town square AND creates session
   - `*setannounce #text-channel` - Sets announcements
   - `*setexception #voice-channel` - Sets private ST channel (optional)
4. Repeat for additional categories

**Recovery from Accidents:**
If you accidentally delete a session or need to reconfigure:
- Just run `*settown` or other config commands again from within the category
- Sessions are automatically created when configuration commands are used
- No need to run `/autosetup` to recreate structure

**Running Multiple Simultaneous Games:**
- Players and storytellers can run completely different games at the same time
- Each category operates independently - configure each one separately
- Use `*sessions` to view all active sessions on your server

**What /autosetup Creates:**
1. **Category:** "🩸• Blood on the Clocktower" (at position 0)
2. **Text Channel:** "📜┃announcements" (with topic)
3. **Voice Channels:**
   - 🏛️┃Town Square (no limit)
   - 🕯️┃Consultation (no limit, exception channel for ST)
   - 🌙┃Private Chamber (2) (2-person cap)
   - ⚰️┃Private Chamber (3) (3-person cap)
   - 🗡️┃Commons (no limit)

**Auto-Configuration:**
- Sets BOTC category
- Sets Town Square as destination channel
- Sets announcements as announce channel
- Sets Consultation as exception channel (excluded from `/call`)

**Setup Complete Embed:**
- Sent to announcements channel
- Shows what was created
- Provides next steps (claim ST, set grimoire, etc.)
- Gothic theme with dark red color (#8B0000)

**Permissions Required:**
- User: Administrator
- Bot: Manage Channels

### 12. Welcome System

**Purpose:** Automatic onboarding when bot joins a new server.

**Trigger:** `on_guild_join` event

**Behavior:**
- Finds first accessible text channel
- Sends comprehensive welcome embed
- Includes:
  - Quick setup options (auto vs manual)
  - Getting started guide
  - Required permissions list
  - Links to documentation

**Welcome Message Content:**
- **Option 1:** Use `/autosetup` for instant gothic setup
- **Option 2:** Manual setup with step-by-step commands
- Lists all essential commands
- Highlights permission requirements:
  - Manage Nicknames
  - Move Members
  - Manage Channels
  - Manage Messages
  - Send Messages & Embed Links
  - Add Reactions

**Theme:** Dark red (#8B0000) for gothic atmosphere

### 13. Exception Channel System

**Purpose:** Exclude specific voice channels from `/call` and timer operations.

**Commands:**
- `*setexception #channel` - Set or replace exception channel (admin only)
- `*setexception clear` - Remove exception channel (admin only)

**Use Case:**
- Consultation channel for storytellers
- Private ST discussion room
- Prevents storytellers from being moved during `/call`

**Implementation:**
- Stored in `sessions` table as `exception_channel_id`
- Used by `call_townspeople()` to skip channels

---

## Command Reference

### Everyone Commands

| Command | Description | Auto-Delete |
|---------|-------------|-------------|
| `*!` | Toggle spectator mode | 2s (confirmation) |
| `*brb` | Toggle away status | 2s (confirmation) |
| `*players` | List active players + joined/left | No |
| `*timer` | Check active timer status | 8s |
| `*help` | Show command reference | No |
| `*consult` | Request ST consultation (requires active game) | 2s |
| `*game` | View active game info for current session | No |
| `/character <name>` | Look up character info (case-insensitive) | No (interactive) |
| `/stats` | View server game statistics | No |
| `/gamehistory [limit]` | View recent games (default: 10) | No |
| `/ststats [@user]` | View ST stats card (optional user filter) | No |
| `/stprofile` | Customize your ST stats card | No |

### Storyteller Commands

| Command | Description | Auto-Delete |
|---------|-------------|-------------|
| `*st` | Claim/unclaim Storyteller | 2s (confirmation) |
| `*cost` | Toggle Co-Storyteller | 2s (confirmation) |
| `*g <link>` | Set grimoire link (session-scoped) | No (shows embed) |
| `*g` | View grimoire link | No |
| `*call` | Move all to town square (requires active game) | 3s (confirmation) |
| `*timer <duration>` | Schedule delayed call (requires active game) | No (persistent) |
| `*<duration>` | Shorthand for timer (e.g., `*5m`, `*1h30m`) | No (persistent) |
| `*timer cancel` | Cancel active timer | 4s (confirmation) |
| `*night` | Announce nighttime (requires active game) | No (permanent) |
| `*day` | Announce morning (requires active game) | No (permanent) |
| `*poll [123ch] [time]` | Create timed script poll (default: 5m) | No (permanent) |
| `/poll <options> [duration]` | Slash version of poll | No (permanent) |
| `/startgame <script> [custom_name]` | Start game tracking (with player confirmation) | No (public embed) |
| `/endgame <winner>` | Record game result | No (public embed) |
| `/addplayer @user` | Add player to active game | No (public embed) |
| `/removeplayer @user` | Remove player from active game | No (public embed) |

### Spectator Commands

| Command | Description | Auto-Delete |
|---------|-------------|-------------|
| `*spec @user` | Shadow follow a player | 2s (confirmation) |
| `*unspec` | Stop following | 2s (confirmation) |
| `*shadows` | View all followers | 10s |
| `*dnd` | Prevent being followed | 2s (confirmation) |
| `*join @user` | Join someone's voice channel (one-time) | 2s (confirmation) |

### Admin Commands

| Command | Description | Auto-Delete |
|---------|-------------|-------------|
| `/setbotc <name\|id>` | **Create/link a session to a category** | Ephemeral |
| `/settown #channel` | Set town square channel (for current session) | Ephemeral |
| `/setannounce #channel` | Set announcement channel (for current session) | Ephemeral |
| `/setexception #channel` | Set exception channel (for current session) | Ephemeral |
| `/setexception` (no arg) | Remove exception channel | Ephemeral |
| `*changelog` | View latest version info (admin-only) | No |
| `/sessions` | List all sessions | Ephemeral |
| `/deletesession <category_id>` | Delete a session | Ephemeral |
| `*config` | View current server settings | No |
| `/deletegame <index>` | Delete specific game (1-based) | Ephemeral |
| `/clearhistory` | Delete all game history | Ephemeral |
| `/autosetup` | Auto-create gothic BOTC structure | Public embed |

---

## Advanced Features

### Permission Checking

The bot includes a helper function to check its own permissions:

```python
def check_bot_permissions(guild):
    """Returns (has_move_members, has_manage_channels)"""
```

**Used by:**
- Voice channel cap adjustments (needs Manage Channels)
- Moving users to town square (needs Move Members)
- `*config` command shows permission status

**User Feedback:**
- Clear error messages when permissions are missing
- `*config` shows ✅ or ❌ for each permission

### Configuration Viewer (`*config`)

**Purpose:** Admin-only command to view all server settings at a glance.

**Shows:**
- BOTC category (name + ID)
- Town square channel (mention + ID)
- Announcement channel (mention + ID)
- Grimoire link (clickable)
- Bot permissions status (Move Members, Manage Channels)

**Security:**
- Restricted to users with Administrator permission
- 3-second error message if non-admin tries to use it

**Announcement System**

**Setup:** `*setannounce #channel` (admin only)

**Triggers:**
- Bot startup/restart
- Shows latest changelog entry from module-level `changelog_data`
- Includes version number and features list

**Embed Format (example):**
```
🔄 Grimkeeper Updated — v1.0.0
🚀 Enhanced onboarding experience for new servers

What's New:
• `/autosetup` command for one-click server configuration
• Welcome message sent to first accessible text channel
• Detailed setup instructions and next steps
• Improved error handling and permission checks
```

**Changelog Management:**
- Centralized `changelog_data` array at module level in `main.py`
- Used by both `*changelog` command and startup announcements
- Single source of truth - update once, used everywhere
- Supports unlimited version history (shows 10 most recent in `*changelog`)

**Version Display:**
- Current version stored in `botc/constants.py`
- Shown in footer of embeds
- Included in help and config commands

### Day/Night Announcements

**Purpose:** Mark day/night transitions with permanent, visible announcements.

**Requirements:**
- Storyteller prefix (ST or Co-ST)
- Active game (must use `/startgame` first)

**Commands:**
- `*night` → Posts "# 🌙 NIGHTTIME"
- `*day` → Posts "# ☀️ MORNING"

**Features:**
- Command message deleted immediately
- Announcement is permanent (doesn't auto-delete)
- Uses Discord's heading markdown for visibility
- Error shown if no active game

**Use Case:** 
Helps track when day/night phases start during gameplay, especially useful for reviewing game flow later or for players who join mid-session.

### Error Handling Strategy

**Principle:** Fail gracefully, log errors, inform users when appropriate.

**Patterns:**

1. **User-facing errors:** 
   ```python
   msg = await channel.send("Clear error message")
   await msg.delete(delay=3)
   ```

2. **Permission errors:**
   ```python
   except discord.errors.Forbidden:
       msg = await channel.send("I don't have permission to do that.")
       await msg.delete(delay=3)
   ```

3. **Background task errors:**
   ```python
   except Exception as e:
       logger.error(f"Detailed error: {e}")
       # Silent failure or generic user message
   ```

4. **Specific exceptions preferred:**
   ```python
   # ❌ Avoid
   except Exception:
       pass
   
   # ✅ Better
   except (asyncpg.PostgresError, asyncio.TimeoutError) as e:
       logger.error(f"Database operation failed: {e}")
   ```

### Logging System

**Configuration:**
```python
logging.basicConfig(
    level=logging.INFO,
    filename='discord.log',
    encoding='utf-8',
    filemode='a'  # Append mode
)
logger = logging.getLogger('botc_bot')
```

**Log Levels:**
- `INFO`: Bot startup, timer restoration, major events
- `WARNING`: Failed move attempts, permission issues, minor failures
- `ERROR`: Database errors, channel edit failures, critical issues

**Log Rotation:**
- Not currently implemented
- File grows indefinitely in append mode
- Consider adding rotation for production

---

## Data Persistence

### Database Architecture

Grimkeeper uses PostgreSQL for all persistent data storage with asyncpg for async database operations and connection pooling.

### Database Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `guilds` | Guild-wide metadata | guild_id (PK), server_name, botc_category_id (default category), is_active |
| `sessions` | Category-scoped game sessions | guild_id + category_id (composite PK), destination_channel_id, grimoire_link, exception_channel_id, announce_channel_id, active_game_id, storyteller_user_id |
| `shadow_followers` | Spectator follow relationships | follower_id + guild_id (composite PK), target_id |
| `dnd_users` | Users with DND mode enabled | user_id (PK) |
| `timers` | Active scheduled timers | guild_id (PK), category_id, end_time, creator_id |
| `channel_limits` | Voice channel cap backups | channel_id (PK), original_limit, added_count |
| `games` | Game tracking (active & history) | game_id (PK), guild_id, category_id, script, custom_name, start_time, end_time, winner, players (JSONB), is_active, storyteller_id |
| `storyteller_stats` | Per-storyteller statistics | guild_id + storyteller_id (composite PK), total_games, good_wins, evil_wins, tb/snv/bmr stats |

### Legacy Storage

The bot previously used JSON files for persistence but has migrated to PostgreSQL. JSON files are no longer used in production.

### Database Operations

**Connection Management:**
- asyncpg connection pooling (min: 2, max: 10 connections)
- Automatic reconnection on connection loss
- Command timeout: 60 seconds
- Query timeout: 5 seconds

**Schema Migrations:**
- Versioned SQL migrations in `migrations/` directory
- `001_initial_schema.sql` - Core tables (guilds, shadow_followers, dnd_users, timers, channel_limits, games)
- `002_storyteller_stats.sql` - Storyteller statistics tracking with script-specific win rates
- `003_sessions_table.sql` - Multi-session support with category-scoped configuration
- `004_add_category_to_timers.sql` - Session-scoped timer persistence
- `005_add_category_to_games.sql` - Session-scoped game history
- `006_add_storyteller_metrics.sql` - Enhanced storyteller stats (avg game length, player count)
- `007_add_storyteller_tracking.sql` - Session-scoped storyteller tracking
- `008_remove_session_fields_from_guilds.sql` - **BREAKING:** Dropped session config from guilds table (grimoire_link, destination_channel_id, announce_channel_id, exception_channel_id)
- Migrations run automatically on bot startup (001-002 only)
- Manual migrations (003-008) must be run via scripts in `scripts/` directory
- Idempotent (safe to run multiple times)

**When database writes happen:**
- `guilds`: After `/autosetup` (sets default botc_category_id only), `*setbotc` (guild-level default category)
- `sessions`: After **all** config commands (`/settown`, `/setannounce`, `/setexception`, `*g <link>`), `/autosetup` (creates session), `/startgame` (sets storyteller_user_id), `/endgame` (clears storyteller_user_id)
- `shadow_followers`: After `*spec`, `*unspec`, `*dnd`, follower cleanup
- `dnd_users`: After `*dnd` toggle
- `timers`: After timer create, cancel, completion (session-scoped)
- `channel_limits`: After voice channel cap adjustments (privileged user joins/leaves)
- `games`: After `/startgame` (is_active=TRUE), `/endgame` (is_active=FALSE) (session-scoped)
- `storyteller_stats`: Automatically updated after successful `/endgame` with Good/Evil winner

### Data Integrity

**JSONB Storage:**
- Player lists in `games.players` stored as JSONB
- Serialized with `json.dumps()` on write
- Automatically deserialized by asyncpg on read
- Allows flexible querying and indexing

**Foreign Keys & Cascading:**
- Guild deletion cascades to all related records (sessions, games, timers, followers)
- Session deletion can optionally cascade to games and timers (configurable)
- Prevents orphaned data
- Maintains referential integrity

**Transaction Safety:**
- Rollback on errors
- Connection pool prevents resource exhaustion
- Errors logged without crashing bot

### Load Strategy

**Startup sequence:**
```python
1. Load environment variables (.env file)
2. Connect to PostgreSQL database
3. Run schema migrations (001-005)
4. Build follower_targets reverse index from shadow_followers table
5. [Bot connects to Discord]
6. on_ready() → Load cogs (slash, polls, timers, commands)
7. on_ready() → Sync slash commands to Discord
8. on_ready() → Restore active timers from database via TimerManager
9. on_ready() → Post startup announcements with latest changelog
```

**Error Handling:**
- Database connection failure: Log and exit (critical failure)
- Migration errors: Log warning but continue (tables may already exist)
- Query errors during operation: Log and return None/empty results
- Follower data corruption: Skip corrupted entries, log warning

### Startup Sequence

```python
1. Load environment variables (.env file)
2. Connect to PostgreSQL database
3. Run schema migrations (001_initial_schema.sql, 002_storyteller_stats.sql)
4. Build follower_targets reverse index from shadow_followers table
5. [Bot connects to Discord]
6. on_ready() → Load cogs (slash, polls, timers)
7. on_ready() → Sync slash commands to Discord
8. on_ready() → Restore active timers from database via TimerManager
9. on_ready() → Post startup announcements with latest changelog
```

**Error Handling:**
- Database connection failure: Log and exit (critical failure)
- Migration errors: Log warning but continue (tables may already exist)
- Query errors during operation: Log and return None/empty results
- Follower data corruption: Skip corrupted entries, log warning

---

## Production Deployment

### AWS EC2 Setup

**Requirements:**
- Python 3.10+
- PostgreSQL 12+ (local or AWS RDS)
- pip packages: discord.py==2.6.4, python-dotenv==1.2.1, asyncpg==0.30.0
- systemd for process management (recommended over screen/tmux)

**Initial Setup:**
```bash
# Clone repository
git clone https://github.com/gorewife/grimkeeper.git ~/grimkeeper
cd ~/grimkeeper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
nano .env  # Add DISCORD_TOKEN

# Run bot
python3 main.py
```

**Running in Background:**
```bash
# Using screen
screen -S botc
python3 main.py
# Ctrl+A, D to detach

# Reattach
screen -r botc

# Using nohup
nohup python3 main.py > output.log 2>&1 &
```

### Configuration After Deploy

**Required steps after fresh deploy:**
1. **Option A - Auto Setup (Recommended):**
   - Invite bot to server
   - Bot sends welcome message automatically
   - Run `/autosetup` in Discord
   - Done! All channels and config created

2. **Option B - Manual Setup:**
   - Run `/setbotc <category>` in Discord (admin) - **Creates a session for that category**
   - Run `/settown #channel` in Discord (admin)
   - Run `/setannounce #channel` in Discord (admin)
   - Optionally: `/setexception #channel` for ST-only channel

**Test the setup:**
```
*config             # View configuration
*st                 # Claim storyteller
*call               # Test moving members
/startgame          # Test game tracking
```

### Git Workflow

**.gitignore includes:**
- `.env` - Bot token and database credentials
- `discord.log` - Runtime logs
- `.venv/` - Virtual environment
- `__pycache__/` - Python cache

**Deployment process:**
```bash
# On local machine
git add main.py
git commit -m "Feature: ..."
git push origin main

# On EC2
cd ~/dweks
git pull

# Restart bot
screen -r botc
# Ctrl+C to stop
python3 main.py
# Ctrl+A, D to detach
```

### Handling Merge Conflicts

**Common scenario:** Local changes on EC2 conflicting with remote updates.

**Quick resolution:**
```bash
# Abort current merge
git merge --abort

# Force update to remote state
git fetch origin
git reset --hard origin/main
```

**Note:** This discards local changes. Config files are safe (in .gitignore).

### Monitoring

**Check if bot is running:**
```bash
ps aux | grep main.py
```

**View logs:**
```bash
tail -f discord.log
```

**Check disk space:**
```bash
df -h
du -sh discord.log  # Log file size
```

### Troubleshooting

**Bot won't start:**
```bash
# Check Python version
python3 --version

# Check dependencies
pip list | grep discord

# Test syntax
python3 -m py_compile main.py
```

**Bot disconnects randomly:**
- Check AWS EC2 instance status
- Review discord.log for errors
- Verify network connectivity
- Check Discord API status

**Commands not working:**
- Verify bot has required permissions in Discord
- Check `*config` to see permission status
- Review server setup (category, channels)

**State not persisting:**
- Check database connection in logs
- Verify `DATABASE_URL` is correct in `.env`
- Check PostgreSQL is running
- Review logs for database errors

### Performance Considerations

**Current scale:**
- Modular bot with cogs: ~2,500 lines total
- PostgreSQL database with connection pooling
- In-memory state for active sessions
- Thread-safe game history with database transactions
- Suitable for: 1-2500 concurrent servers

**Scaling limits:**
- Connection pool limits (default: max 10 connections per bot instance)
- No sharding (single bot instance, <2500 servers)
- Rate limit protection via 2s cooldowns

**If scaling needed:**
- Increase connection pool size in database.py
- Add read replicas for PostgreSQL
- Implement caching layer (Redis) for frequently accessed data
- Consider bot sharding for 2500+ servers
- Queue system for `/call` operations in large servers

### Security Best Practices

**Environment variables:**
- Never commit `.env` file
- Use strong, unique bot token
- Rotate token if exposed

**Admin commands:**
- Restricted by Discord permission checks
- `*config` only for administrators
- No hardcoded admin user IDs (uses Discord roles)

**Data privacy:**
- User IDs stored, not usernames/avatars (except in player snapshots)
- No message content logged
- State files in .gitignore (not committed)
- Game history includes display names at time of game
- No personal data collection beyond Discord's built-in IDs

**Rate limiting:**
- Prevents abuse via command spam
- Protects Discord API quota
- 2-second cooldown per user per command

---

## Version History

See `*changelog` command in Discord for complete version history.

**Current Version:** 1.3.1

**Major Milestones:**
- **1.3.x:** Wiki integration, character lookups, bug fixes
- **1.2.x:** Multi-session support, enhanced stats, PostgreSQL migration
- **1.1.x:** Architecture refactor, cog system, critical bug fixes
- **1.0.x:** Public release, game tracking, autosetup
- **0.9.x:** Enhanced onboarding (auto-setup, welcome messages)
- **0.8.x:** Game statistics tracking, admin management commands
- **0.7.x:** Timed polls, slash commands, performance improvements
- **0.6.x:** Rebranded as Grimkeeper, documentation
- **0.5.x:** Production readiness (timer persistence, rate limiting)
- **0.4.x:** Town square system (call command, player tracking)
- **0.3.x:** Shadow follow system (spectator features)
- **0.2.x:** Core features (grimoire links, prefixes)

---

## Contributing

### Code Style

**Principles:**
- Clear, descriptive variable names
- Comments for complex logic
- Consistent indentation (4 spaces)
- One feature per commit

**Naming Conventions:**
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Classes: `PascalCase` (minimal use)

### Testing

**Before committing:**
```bash
# Syntax check all Python files
python3 -m py_compile main.py botc/*.py botc/cogs/*.py tests/*.py 2>&1 | head -n 50

# Manual testing in test server
# - Create test Discord server
# - Test all modified commands (prefix and slash)
# - Verify error handling
# - Test game tracking flow (/startgame → /endgame)
# - Test auto-setup if modified
```

**Test areas:**
- Prefix commands (`*help`, `*call`, `*timer`, etc.)
- Slash commands (`/startgame`, `/endgame`, `/stats`, etc.)
- Permission checks (ST-only, admin-only)
- State persistence (restart bot, verify data restored)
- Error handling (missing permissions, invalid input)

**Automated tests:**
- Basic tests in `tests/` directory
- Run with: `pytest tests/` (if pytest installed)
- Coverage areas: utils (duration parsing), timer logic

### Documentation

**When adding features:**
1. Update `*help` command text
2. Add to `*changelog` command
3. Update this DOCUMENTATION.md
4. Update README.md if setup changes

---

## FAQ

**Q: Why use both prefix and slash commands?**
A: Prefix commands (`*call`) are faster to type for frequent actions. Slash commands (`/startgame`) provide better discoverability and validation for complex inputs. Best of both worlds!

**Q: Why modular architecture with cogs?**
A: Better separation of concerns, easier testing, cleaner code organization. Cogs can be loaded/unloaded independently and handle their own lifecycle.

**Q: What happens if the bot crashes?**
A: All state persists to PostgreSQL. On restart: migrations run, timers are restored and rescheduled from database, game history intact, active games resume tracking. Voice cap backups cleared intentionally (prevents stale data).

**Q: How do I add a new command?**
A: For prefix commands: Add to `on_message` in main.py or create new cog. For slash commands: Add to `botc/cogs/slash.py` cog_load() and create handler in main.py.

**Q: Can I customize the channels?**
A: Yes! Edit the channel names, emojis, and colors in the `autosetup_handler` function. Currently uses dark red (#8B0000) and gothic emojis (🩸⚰️🕯️🌙🗡️).

**Q: What's the difference between Custom and Homebrew scripts?**
A: In `/startgame`, both allow custom_name input. "Custom Script" requires it, "Homebrew Script" makes it optional. Just semantic distinction for user preference.

**Q: Can I host this on Heroku/Railway/other platforms?**
A: Yes! The bot uses PostgreSQL, so just provision a database addon (Heroku Postgres, Railway PostgreSQL, etc.) and set the DATABASE_URL environment variable.

---

## Support

- **Bug Reports:** Contact `hystericca` on Discord
- **Feature Requests:** Open GitHub issue (gorewife/grimkeeper)
- **Code Review:** Pull requests welcome
- **Documentation:** Available in `/docs` directory

**Version:** 1.3.1  
**Last Updated:** November 30, 2025
