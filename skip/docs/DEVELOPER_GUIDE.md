# Grimkeeper Developer Guide

Technical reference for developers working on Grimkeeper.

---

## Table of Contents

1. [Quick Start for New Developers](#quick-start-for-new-developers)
2. [Architecture Overview](#architecture-overview)
3. [Codebase Organization](#codebase-organization)
4. [Session Architecture Deep Dive](#session-architecture-deep-dive)
5. [Database Patterns](#database-patterns)
6. [Command Implementation Patterns](#command-implementation-patterns)
7. [State Management](#state-management)
8. [Card Generation System](#card-generation-system)
9. [Color Theme System](#color-theme-system)
10. [Error Handling Philosophy](#error-handling-philosophy)
11. [Testing Strategy](#testing-strategy)
12. [Performance Considerations](#performance-considerations)
13. [Common Development Tasks](#common-development-tasks)
14. [Debugging Strategies](#debugging-strategies)
15. [Migration Guide](#migration-guide)
16. [Common Pitfalls](#common-pitfalls)

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Discord bot token
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/gorewife/grimkeeper.git
cd grimkeeper

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env: add DISCORD_TOKEN and DATABASE_URL

# Run
python3 main.py
```

### Development Workflow

```bash
# Feature branch
git checkout -b feature/name

# Test
python3 -m pytest tests/ -v

# Verify compilation
python3 -m py_compile main.py botc/*.py botc/cogs/*.py

# Commit
git add -A
git commit -m "Feature: description"
git push origin feature/name
```

---

## Architecture

### Design Principles

1. **Session-scoped architecture**: Each Discord category = one persistent game session
2. **Cog-based modularity**: Commands organized into discord.py Cogs
3. **PostgreSQL as source of truth**: All state persists across bot restarts
4. **Async-first**: All I/O operations are async
5. **Graceful degradation**: Missing permissions fail gracefully

### Session Architecture Explained

**What is a session?**
- A session = Discord category (e.g., "🩸• Blood on the Clocktower")
- Sessions are **persistent infrastructure** created once by admins
- Each session has a unique code (`s1`, `s2`, `s3`) that never changes
- Sessions exist until manually deleted with `/deletesession`

**Session creation:**
- Admin runs `/autosetup` → Creates category + channels + session record
- OR admin runs `/setbotc <category>` → Links existing category to new session
- Session gets auto-generated sequential code (s1, s2, etc.)
- Code stored in `sessions.session_code` column

**Session lifecycle:**
```
[Admin creates session]     →  [Session exists with code "s1"]
         ↓                              ↓
[ST plays Game #1 in s1]          [ST plays Game #2 in s1]
         ↓                              ↓
[Stats tracked to s1]            [Stats tracked to s1]
         ↓                              ↓
[Game ends]                      [Game ends]
         ↓                              ↓
    [Session "s1" still exists - same code, ready for Game #3]
```

**Key insight:** Sessions are like "game rooms" - once set up, they're permanent. Storytellers never create sessions; they just use existing ones.

**Multi-session support:**
- One guild can have multiple sessions (multiple categories)
- Each session is completely independent:
  - Own grimoire link (`*g` command)
  - Own town square channel (`/settown`)
  - Own game history (`*history`)
  - Own active game state
  - Own session code (s1, s2, s3...)
- Commands automatically scope to the session based on which channel they're used in

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Discord API                         │
│              (User commands, events, messages)              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       main.py (Bot Core)                    │
│  - Event handlers (on_ready, on_message, on_voice_update)  │
│  - Bot contract (helper methods exposed to cogs)           │
│  - Slash command registration                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────┬──────────────────┬──────────────────────┐
│  Cogs Layer      │   Core Modules   │   Utilities          │
├──────────────────┼──────────────────┼──────────────────────┤
│ cogs/slash.py    │ session.py       │ utils.py             │
│ cogs/polls.py    │ database.py      │ constants.py         │
│ cogs/timers.py   │ timers.py        │ wiki.py              │
│ cogs/commands.py │ polls.py         │ discord_utils.py     │
│ cogs/events.py   │ handlers.py      │ exceptions.py        │
└──────────────────┴──────────────────┴──────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                      │
│  - sessions (category-scoped config)                        │
│  - guilds (server-level metadata)                           │
│  - games (game tracking & history)                          │
│  - timers (scheduled announcements)                         │
│  - shadow_followers (spectator system)                      │
│  - storyteller_stats (ST performance metrics)               │
└─────────────────────────────────────────────────────────────┘
```

### Request Flow Example

**User runs `/startgame Trouble Brewing` in #announcements:**

```
1. Discord API → Bot receives interaction event
2. main.py → Dispatches to slash command handler
3. slash.py → Calls start_game_handler() in handlers.py
4. handlers.py → Resolves session from channel's category
5. session.py → Checks cache, queries database if needed
6. handlers.py → Validates config (ST role, players present)
7. database.py → Inserts new game record
8. session.py → Updates session.active_game_id
9. handlers.py → Creates embed, sends to channel
10. Discord API → User sees game start announcement
```

---

## Codebase Organization

### File Structure

```
grimkeeper/
├── main.py                    # Bot entry point, event handlers, bot contract
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (NOT committed)
├── .env.example              # Template for .env
├── .gitignore                # Git exclusions
├── grimkeeper.service        # systemd service file (production)
├── changelog.json            # Version history (for *changelog command)
│
├── botc/                     # Core package
│   ├── __init__.py          # Package marker
│   ├── constants.py         # VERSION, emojis, delays, prefixes
│   ├── database.py          # PostgreSQL operations (asyncpg)
│   ├── session.py           # Session dataclass & SessionManager
│   ├── utils.py             # Duration parsing, timestamp formatting
│   ├── wiki.py              # BOTC wiki API integration
│   ├── polls.py             # Poll creation logic
│   ├── timers.py            # TimerManager class
│   ├── handlers.py          # Business logic for slash commands
│   ├── discord_utils.py     # Discord helper functions
│   ├── exceptions.py        # Custom exception classes
│   │
│   └── cogs/                # Discord.py cogs (command handlers)
│       ├── __init__.py
│       ├── slash.py         # Slash command registration (/character, /startgame, etc.)
│       ├── polls.py         # *poll command
│       ├── timers.py        # *timer and *call commands
│       ├── commands.py      # All other prefix commands (*help, *st, *g, etc.)
│       └── events.py        # Event handlers (on_ready, etc.)
│
├── docs/                    # Documentation
│   ├── DOCUMENTATION.md     # User/admin guide
│   ├── SESSION_ARCHITECTURE.md  # Session system deep dive
│   ├── TESTING_PROTOCOL.md      # Testing procedures
│   ├── DEVELOPER_GUIDE.md       # This file
│   ├── QUICKSTART.md            # Quick setup guide
│   ├── DEPLOYMENT.md            # Production deployment
│   ├── DATABASE_SETUP.md        # Database configuration
│   └── (other docs)
│
├── migrations/              # SQL migration files
│   ├── 001_initial_schema.sql
│   ├── 002_storyteller_stats.sql
│   ├── 003_sessions_table.sql
│   ├── 004_add_category_to_timers.sql
│   ├── 005_add_category_to_games.sql
│   ├── 006_add_storyteller_metrics.sql
│   ├── 007_add_storyteller_tracking.sql
│   └── 008_remove_session_fields_from_guilds.sql
│
├── scripts/                 # Maintenance scripts
│   ├── apply_migrations.py
│   ├── deploy.sh
│   ├── setup_database.sh
│   └── (other scripts)
│
└── tests/                   # Test suite
    ├── test_session_scenarios.py  # Session architecture tests
    ├── test_utils.py              # Utility function tests
    ├── test_timers.py             # Timer logic tests
    └── test_start_end_flow.py     # Game lifecycle tests
```

### Module Responsibilities

#### `main.py`
- **Bot initialization:** Create bot instance, load .env
- **Event handlers:** `on_ready`, `on_message`, `on_voice_state_update`, `on_member_update`, `on_guild_join`
- **Bot contract:** Helper methods exposed to cogs (`bot.is_storyteller()`, `bot.get_active_players()`, etc.)
- **Slash command wiring:** Registers handlers from `handlers.py` as bot methods
- **Cog loading:** Loads all cogs from `botc/cogs/`
- **Voice channel cap management:** Adjusts user_limit for storytellers/spectators

#### `botc/constants.py`
- **Version:** `VERSION = "1.5.0"`
- **Emojis:** Custom Discord emoji IDs (`EMOJI_GOOD`, `EMOJI_EVIL`, etc.)
- **Prefixes:** Nickname prefixes (`PREFIX_ST = "(ST) "`)
- **Delays:** Auto-delete timers (`DELETE_DELAY_QUICK = 2`)
- **Script mappings:** Poll options → script names

#### `botc/database.py`
- **Connection pool:** asyncpg connection management (min: 2, max: 10)
- **CRUD operations:** All database queries
- **Migrations:** Auto-run migrations 001-002 on startup
- **Game tracking:** Start, end, add/remove players
- **Stats aggregation:** Storyteller performance metrics
- **Session persistence:** Session CRUD (via SessionManager)

#### `botc/session.py`
- **Session dataclass:** Immutable session representation
- **SessionManager:** Session lifecycle (create, read, update, delete)
- **Cache:** In-memory session cache (dict)
- **Resolution:** Use `get_session_from_channel()` for all commands. Sessions should only be created by `/setbotc` and `/autosetup`
- **Cleanup:** Inactive session removal

#### `botc/handlers.py`
- **Business logic:** Separated from Discord interaction handling
- **Game lifecycle:** `start_game_handler()`, `end_game_handler()`
- **Validation:** Checks for ST role, active game, player presence
- **Embed creation:** Rich Discord embeds for announcements

#### `botc/cogs/slash.py`
- **Slash commands:** `/character`, `/startgame`, `/endgame`, `/addplayer`, `/removeplayer`, `/stats`, `/gamehistory`, `/storytellerstats`, `/poll`, `/autosetup`, `/deletegame`, `/clearhistory`
- **Interactive views:** Button navigation for `/character`
- **Confirmation flows:** Player roster confirmation before `/startgame`

#### `botc/cogs/commands.py`
- **Prefix commands:** `*help`, `*st`, `*cost`, `*!`, `*brb`, `*g`, `*players`, `*shadows`, `*spec`, `*unspec`, `*dnd`, `*join`, `*night`, `*day`, `*consult`, `*changelog`, `*game`
- **Admin slash commands:** `/setbotc`, `/settown`, `/setannounce`, `/setexception`, `/sessions`

#### `botc/cogs/timers.py`
- **Timer commands:** `*timer`, `*call`, `*<duration>` (shorthand)
- **Town square calling:** Move all players to town square
- **Duration parsing:** Flexible time format support

#### `botc/cogs/polls.py`
- **Poll creation:** `*poll [123ch] [duration]`
- **Timed voting:** Auto-announce winner after duration

#### `botc/cogs/events.py`
- **Startup announcements:** Send changelog to configured channels
- **Event forwarding:** Delegates to main.py handlers

---

## Session Architecture Deep Dive

### Core Concept

**Sessions = Category-Scoped Game Instances**

Each Discord category becomes an isolated session with its own:
- Grimoire link
- Town Square (destination channel for `*call`)
- Exception channel (excluded from `*call`)
- Announcement channel
- Active game tracking
- Timer state
- Storyteller assignment

### The Session Object

```python
@dataclass
class Session:
    guild_id: int                           # Discord server ID
    category_id: int                        # Discord category ID
    destination_channel_id: Optional[int]   # Town Square
    grimoire_link: Optional[str]            # Grimoire URL
    exception_channel_id: Optional[int]     # ST-only channel
    announce_channel_id: Optional[int]      # Bot announcements
    active_game_id: Optional[int]           # FK to games table
    storyteller_user_id: Optional[int]      # Current ST
    created_at: Optional[float]             # Unix timestamp
    last_active: Optional[float]            # Unix timestamp
    
    @property
    def session_id(self) -> tuple[int, int]:
        """Composite primary key: (guild_id, category_id)"""
        return (self.guild_id, self.category_id)
```

### SessionManager: The Resolution Engine

> **⚠️ IMPORTANT SESSION CREATION POLICY (Updated Dec 2024)**
> 
> **Sessions should ONLY be created by:**
> - `/setbotc` command (explicit admin setup)
> - `/autosetup` command (auto-creates categories + sessions)
>
> **All other commands MUST use `get_session_from_channel()` (read-only) and fail gracefully if no session exists.**
>
> Commands that previously auto-created sessions (`/settown`, `/setannounce`, `/setexception`, `*g`) now require an existing session. This prevents accidental session creation in wrong categories.

**Two resolution methods:**

#### 1. `get_session_from_channel()` - Read-Only
Used by **ALL commands** except `/setbotc` and `/autosetup`.

**Logic:**
1. Extract category from channel
2. Check cache for `(guild_id, category_id)`
3. If cache miss, query database
4. If DB miss, return `None`
5. **No auto-creation** - sessions must be explicitly created via `/setbotc`

**Example usage:**
```python
session = await session_manager.get_session_from_channel(message.channel, guild)
if not session:
    await message.channel.send("⚠️ This category is not set up as a BOTC session. Use `/setbotc` to set it up first.")
    return
```

#### 2. `get_or_create_session_from_channel()` - DEPRECATED
**⚠️ WARNING: This method is deprecated and should NOT be used in new code.**

This method auto-creates sessions and was causing issues where commands like `*g`, `/settown`, etc. would accidentally create sessions in random categories.

**NEW APPROACH:** All commands should use `get_session_from_channel()` (read-only) and require users to explicitly run `/setbotc` or `/autosetup` to create sessions.

**Only these commands should create sessions:**
- `/setbotc` - Explicitly creates a session for a category
- `/autosetup` - Creates categories and sessions together

**Example (OLD - DO NOT USE):**
```python
# ❌ WRONG - Do not use this pattern
session = await session_manager.get_or_create_session_from_channel(ctx.channel, guild)
```

**Example (NEW - USE THIS):**
```python
# ✅ CORRECT - Require explicit session creation
session = await session_manager.get_session_from_channel(ctx.channel, guild)
if not session:
    await ctx.send("⚠️ No session found in this category. Run `/setbotc` first to create a session.")
    return

session.grimoire_link = new_link
await session_manager.update_session(session)
```

### Session Resolution Flow

```
User runs command in #announcements (inside "BOTC Tournament" category)
    ↓
Bot extracts category: category_id = 987654321
    ↓
Build session key: (guild_id=123456789, category_id=987654321)
    ↓
Check cache: session_key in _cache?
    ↓          ↓
   Yes        No → Query database
    ↓              ↓          ↓
Return cached   Found     Not found
                  ↓          ↓
              Cache it   Auto-create (if applicable)
                  ↓          ↓
              Return     Return
```

### Cache Strategy

**Why cache?**
- Sessions accessed on **every command** that needs context
- Avoids database query per command
- Reduces latency

**Implementation:**
```python
self._cache: dict[tuple[int, int], Session] = {}
```

**Cache operations:**
- **Read:** O(1) dict lookup
- **Write:** Update DB first, then cache
- **Invalidate:** Remove from cache on delete

**Cache consistency:**
- Single bot instance = single cache (no distributed cache needed)
- Always write to database before updating cache
- If DB write fails, cache isn't updated

### Multi-Session Isolation Example

```python
# Server "BOTC Community" has two categories:
# - "Tournament Finals" (category_id: 111)
# - "Beginner's Night" (category_id: 222)

# In Tournament Finals:
session_A = await session_manager.get_or_create_session_from_channel(
    channel_in_category_111, guild
)
session_A.grimoire_link = "clocktower.live/tournament"
await session_manager.update_session(session_A)

# In Beginner's Night:
session_B = await session_manager.get_or_create_session_from_channel(
    channel_in_category_222, guild
)
session_B.grimoire_link = "clocktower.live/beginners"
await session_manager.update_session(session_B)

# Result: Two independent sessions
# session_A.session_id = (guild_123, 111)
# session_B.session_id = (guild_123, 222)
```

### Session Lifecycle

**Creation:**
- `/setbotc <category>` → **Primary method** - creates session for specified category
- `/autosetup` → Auto-creates session with all channels configured (convenience)
- Session-scoped config commands (`/settown`, `/setannounce`, `/setexception`) → Auto-create session if needed
- Manual: `*g <link>` in a category → Auto-creates session with only grimoire set

**Philosophy:** Explicit over implicit. Sessions are created intentionally, not automatically.

**Updates:**
- Any config command updates `session.last_active`
- Changes written to database immediately
- Cache refreshed

**Deletion:**
- Manual: Admin runs cleanup command
- Automatic: Cleanup job removes sessions inactive >30 days
- Cache invalidated immediately

---

## Database Patterns

### Connection Management

**asyncpg connection pool:**
```python
self.pool = await asyncpg.create_pool(
    connection_string=DATABASE_URL,
    min_size=2,
    max_size=10,
    command_timeout=60
)
```

**Key characteristics:**
- **Connection pooling:** Reuses connections across requests
- **Automatic reconnection:** Handles transient network issues
- **Transaction support:** Proper ACID compliance
- **Async-first:** All queries are async, no blocking I/O

**Usage pattern:**
```python
async with self.pool.acquire() as conn:
    result = await conn.fetchrow("SELECT * FROM sessions WHERE guild_id = $1", guild_id)
    return dict(result) if result else None
```

### Schema Organization

**Core tables:**

#### `guilds`
- **Purpose:** Server-level metadata (language preferences, default category)
- **Primary Key:** `guild_id` (BIGINT)
- **Fields:** `botc_category_id` (deprecated, use sessions), `language` (VARCHAR)

#### `sessions`
- **Purpose:** Category-scoped game configuration
- **Primary Key:** `(guild_id, category_id)` composite
- **Fields:**
  - `destination_channel_id`: Town Square (for `*call`)
  - `grimoire_link`: Session-specific grimoire URL
  - `exception_channel_id`: Excluded from `*call` operations
  - `announce_channel_id`: Bot announcements
  - `active_game_id`: FK to current game
  - `storyteller_user_id`: Current ST for this session
  - `created_at`, `last_active`: Timestamps
  - `vc_caps`: JSONB storing voice channel user_limit snapshots

#### `games`
- **Purpose:** Individual game tracking and history
- **Primary Key:** `game_id` (SERIAL)
- **Fields:**
  - `guild_id`, `category_id`: Session identification
  - `script`, `custom_name`: What was played
  - `start_time`, `end_time`: Game duration (Unix timestamps as FLOAT)
  - `players`: JSONB array of player user IDs
  - `player_count`: Denormalized count for queries
  - `storyteller_id`: Who ran the game
  - `winner`: 'Good', 'Evil', or NULL
  - `is_active`: TRUE if game is ongoing
  - `completed_at`: TIMESTAMP when game ended

#### `storyteller_stats`
- **Purpose:** Aggregate performance metrics per guild
- **Primary Key:** `(guild_id, storyteller_id)`
- **Fields:**
  - `total_games`, `good_wins`, `evil_wins`: Counters
  - `tb_games`, `tb_good_wins`, `tb_evil_wins`: Trouble Brewing stats
  - `snv_games`, `snv_good_wins`, `snv_evil_wins`: Sects & Violets stats
  - `bmr_games`, `bmr_good_wins`, `bmr_evil_wins`: Bad Moon Rising stats
  - `total_game_duration`: Cumulative seconds
  - `total_player_count`: Cumulative player count
  - `storyteller_name`: Display name (updated on game end)
  - `last_game_at`: TIMESTAMP of last game
  - `created_at`, `updated_at`: Audit timestamps

#### `storyteller_profiles_global`
- **Purpose:** Bot-wide storyteller customization
- **Primary Key:** `user_id` (BIGINT)
- **Fields:**
  - `pronouns`: User pronouns (max 15 chars)
  - `custom_title`: Card title (max 15 chars, e.g., "Gamer", "Farmer")
  - `color_theme`: Theme name (gold, silver, crimson, emerald, amethyst, sapphire, rose, copper, midnight, jade)
  - `created_at`, `updated_at`: TIMESTAMP

#### `timers`
- **Purpose:** Scheduled timer tasks (for delayed `*call`)
- **Primary Key:** `guild_id` (one timer per guild)
- **Fields:**
  - `end_time`: FLOAT Unix timestamp when timer expires
  - `creator_id`: User who set the timer
  - `category_id`: Session scope for timer

#### `shadow_followers`
- **Purpose:** Spectator shadow-follow relationships
- **Primary Key:** `(follower_id, guild_id)`
- **Fields:**
  - `target_id`: User being followed
  - Auto-moves follower to target's voice channel

#### `dnd_users`
- **Purpose:** Do-not-disturb preference (prevents shadow-following)
- **Primary Key:** `(user_id)`
- **Fields:** Just existence check

#### `admin_roles`
- **Purpose:** Custom admin roles per guild
- **Primary Key:** `(guild_id, role_id)`
- **Fields:** Role IDs that grant admin permissions

### Query Patterns

**1. Session resolution:**
```python
async def get_session(self, guild_id: int, category_id: int):
    """Most common query - always check cache first."""
    session_key = (guild_id, category_id)
    if session_key in self._cache:
        return self._cache[session_key]
    
    async with self.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM sessions WHERE guild_id = $1 AND category_id = $2",
            guild_id, category_id
        )
    # ...
```

**2. Game tracking:**
```python
async def start_game(self, guild_id, script, custom_name, start_time, players, storyteller_id, category_id):
    """Start tracking a new game - atomic with session update."""
    async with self.pool.acquire() as conn:
        # End any existing active game first
        await conn.execute(
            "UPDATE games SET is_active = FALSE WHERE guild_id = $1 AND category_id = $2 AND is_active = TRUE",
            guild_id, category_id
        )
        
        # Create new game
        row = await conn.fetchrow(
            "INSERT INTO games (...) VALUES (...) RETURNING game_id",
            guild_id, category_id, script, custom_name, start_time, json.dumps(players), len(players), storyteller_id
        )
        return row['game_id']
```

**3. Stats aggregation:**
```python
async def _update_storyteller_stats(self, guild_id, storyteller_id, script, winner, game_duration, player_count):
    """Update aggregate stats after game ends - uses ON CONFLICT for UPSERT."""
    script_type = self._determine_script_type(script)  # 'tb', 'snv', 'bmr', or None
    
    async with self.pool.acquire() as conn:
        await conn.execute(f"""
            INSERT INTO storyteller_stats (
                guild_id, storyteller_id, total_games, good_wins, evil_wins,
                {script_type}_games, {script_type}_good_wins, {script_type}_evil_wins,
                total_game_duration, total_player_count, last_game_at
            ) VALUES ($1, $2, 1, ...) 
            ON CONFLICT (guild_id, storyteller_id) DO UPDATE SET
                total_games = storyteller_stats.total_games + 1,
                good_wins = storyteller_stats.good_wins + CASE WHEN $3 = 'Good' THEN 1 ELSE 0 END,
                ...
        """, guild_id, storyteller_id, winner, game_duration, player_count)
```

### Migration System

**Auto-run migrations:**
- `migrations/001_complete_schema.sql` - Base schema (runs if `guilds` table doesn't exist)
- `migrations/002-009_*.sql` - Incremental migrations (checked via table existence)

**Migration application:**
```python
async def initialize_schema(self):
    """Run on bot startup."""
    # Check if base schema exists
    schema_exists = await conn.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'guilds')"
    )
    
    if not schema_exists:
        # Run complete schema
        with open(migrations_dir / "001_complete_schema.sql") as f:
            await conn.execute(f.read())
    
    # Run additional migrations (002+)
    await self._run_migrations(migrations_dir, conn)
```

**Creating new migrations:**
1. Create `migrations/XXX_description.sql`
2. Include idempotent checks (IF NOT EXISTS, CREATE TABLE IF NOT EXISTS)
3. Test on fresh database AND existing database
4. Update `_run_migrations()` if needed for table existence checks

---

## Card Generation System

### Architecture

**Stack:**
- **Jinja2:** HTML templating
- **Playwright:** Headless Chromium for rendering
- **HTML/CSS:** Gothic-themed card design with 10 color themes

**Process flow:**
```
1. Fetch stats from database (total_games, good_wins, evil_wins, script breakdown)
2. Fetch profile (pronouns, custom_title, color_theme)
3. Load Jinja2 template (botc/templates/stats_card.html)
4. Inject data + color theme variables
5. Launch Playwright headless browser
6. Render HTML at 400x750px viewport
7. Screenshot to PNG
8. Return BytesIO buffer
9. Upload to Discord as file attachment
```

### Template System

**File:** `botc/templates/stats_card.html`

**Key features:**
- **CSS custom properties:** Colors injected via `{{ primary_color }}`, `{{ secondary_color }}`, etc.
- **Base64 assets:** Icons embedded directly to avoid file I/O
- **Responsive layout:** Flexbox-based stat cards
- **Ornate borders:** 4-layer border system with corner decorations, gradient lines, ornamental dots
- **Sparkle effects:** 22 dynamically positioned sparkles with varied sizes (9px-40px)

**Template structure:**
```html
<!DOCTYPE html>
<html>
<head>
    <style>
        :root {
            --primary-color: {{ primary_color }};
            --secondary-color: {{ secondary_color }};
            --accent-color: {{ accent_color }};
            --text-color: {{ text_color }};
            --background-color: {{ background_color }};
        }
        
        body {
            margin: 0;
            padding: 0;
            width: 400px;
            height: 750px;
            background: var(--background-color);
            color: var(--text-color);
            font-family: 'Cinzel', serif;
        }
        
        .card-border {
            /* 4 nested border layers */
            border: 2px solid var(--primary-color);
            box-shadow: 
                0 0 10px var(--primary-color),
                inset 0 0 20px rgba(201, 168, 117, 0.3);
        }
        
        .sparkle {
            position: absolute;
            width: {{ sparkle_size }}px;
            opacity: 0.6;
            pointer-events: none;
            /* Dynamic positioning via inline styles */
        }
    </style>
</head>
<body>
    <div class="card-container">
        <!-- Header: Avatar + Name + Title -->
        <div class="header">
            <img src="{{ avatar_url }}" class="avatar">
            <h1>{{ username }}</h1>
            {% if custom_title %}
            <p class="title">The {{ custom_title }}</p>
            {% endif %}
        </div>
        
        <!-- Stats Grid -->
        <div class="stats-body">
            <div class="stat-card">
                <span class="stat-label">Total Games</span>
                <span class="stat-value">{{ total_games }}</span>
            </div>
            <!-- ... more stat cards ... -->
        </div>
        
        <!-- Sparkles -->
        {% for sparkle in sparkles %}
        <img src="{{ sparkle_icon }}" class="sparkle" style="left: {{ sparkle.x }}%; top: {{ sparkle.y }}%; width: {{ sparkle.size }}px;">
        {% endfor %}
    </div>
</body>
</html>
```

### Color Theme Implementation

**Defined in:** `botc/card_generator.py`

```python
COLOR_THEMES = {
    'gold': {
        'primary_color': '#c9a875',
        'secondary_color': '#8b7355',
        'accent_color': '#c9a875',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'silver': { ... },
    'crimson': { ... },
    # ... 7 more themes
}
```

**Usage:**
```python
theme_colors = COLOR_THEMES.get(color_theme, COLOR_THEMES['gold'])
html_content = template.render(
    username=username,
    avatar_url=avatar_url,
    total_games=total_games,
    **theme_colors  # Unpack colors as template variables
)
```

**User selection:**
```python
# User sets theme via /stprofile
await db.set_storyteller_profile(user_id, color_theme='emerald')

# Retrieved when generating card
profile = await db.get_storyteller_profile(user_id)
card_buffer = await generate_stats_card(
    ...,
    color_theme=profile.get('color_theme')  # 'emerald'
)
```

### Playwright Rendering

**Requirements:**
- Install Playwright: `pip install playwright`
- Install browsers: `playwright install chromium`

**Rendering code:**
```python
async with async_playwright() as p:
    browser = await p.chromium.launch(
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    
    page = await browser.new_page(
        viewport={'width': CARD_WIDTH, 'height': CARD_HEIGHT}
    )
    
    await page.set_content(html_content)
    await page.wait_for_load_state('networkidle')
    
    screenshot_bytes = await page.screenshot(type='png')
    return io.BytesIO(screenshot_bytes)
```

**Performance:**
- **Cold start:** ~2-3 seconds (browser launch)
- **Warm render:** ~500ms (reuse browser)
- **Memory:** ~100-200MB per browser instance

**Production tips:**
- Use browser pool for concurrent requests
- Set `--disable-gpu` for headless servers
- Monitor memory usage (browsers can leak)
- Timeout renders (5-10 seconds max)

### Stats Card Data Flow

```
User runs /ststats @user
    ↓
storytellerstats_handler(interaction, user)
    ↓
db.get_storyteller_stats(None)  # Bot-wide stats
    ↓
Filter for specific user
    ↓
db.get_storyteller_profile(user_id)  # Get customization
    ↓
generate_stats_card(
    username=user.display_name,
    avatar_url=user.display_avatar.url,
    total_games=stats['total_games'],
    good_wins=stats['good_wins'],
    evil_wins=stats['evil_wins'],
    pronouns=profile.get('pronouns'),
    custom_title=profile.get('custom_title'),
    color_theme=profile.get('color_theme'),
    tb_games=stats['tb_games'],
    snv_games=stats['snv_games'],
    bmr_games=stats['bmr_games'],
    avg_duration_minutes=stats['total_game_duration'] / stats['total_games'] / 60,
    avg_players=stats['total_player_count'] / stats['total_games']
)
    ↓
Template rendering + Playwright screenshot
    ↓
Upload to Discord as file attachment
```

### Troubleshooting Card Generation

**Common issues:**

1. **"Playwright not installed"**
   - Solution: `pip install playwright && playwright install chromium`

2. **Fonts not rendering correctly**
   - Solution: Install system fonts (Cinzel, etc.) or use web fonts with CDN fallback

3. **Unicode username characters render as boxes**
   - Solution: `normalize_username()` converts fancy Unicode to ASCII equivalents

4. **Card generation timeout**
   - Solution: Increase `command_timeout` in Playwright, check headless mode

5. **Memory leak (bot memory grows)**
   - Solution: Ensure `browser.close()` is called in finally block

---

## Color Theme System

### User Customization Flow

**1. User sets theme:**
```
/stprofile color_theme:emerald
```

**2. Database storage:**
```sql
INSERT INTO storyteller_profiles_global (user_id, color_theme, updated_at)
VALUES (123456789, 'emerald', CURRENT_TIMESTAMP)
ON CONFLICT (user_id) DO UPDATE SET
    color_theme = 'emerald',
    updated_at = CURRENT_TIMESTAMP;
```

**3. Card generation:**
```python
# Retrieve profile
profile = await db.get_storyteller_profile(user_id)
theme = profile.get('color_theme') or 'gold'  # Default to gold

# Generate card with theme
card_buffer = await generate_stats_card(
    ...,
    color_theme=theme
)
```

**4. Template injection:**
```html
<style>
    :root {
        --primary-color: {{ primary_color }};  /* #50c878 for emerald */
        --secondary-color: {{ secondary_color }};  /* #2e8b57 */
        /* ... */
    }
</style>
```

### Available Themes

| Theme | Primary | Secondary | Use Case |
|-------|---------|-----------|----------|
| gold | `#c9a875` | `#8b7355` | Default, classic look |
| silver | `#c0c0c0` | `#808080` | Elegant, neutral |
| crimson | `#dc143c` | `#8b0000` | Bold, evil-themed |
| emerald | `#50c878` | `#2e8b57` | Vibrant, good-themed |
| amethyst | `#9966cc` | `#663399` | Mystical, purple |
| sapphire | `#0f52ba` | `#082567` | Deep blue, regal |
| rose | `#ff69b4` | `#c71585` | Bright, playful |
| copper | `#b87333` | `#8b4513` | Earthy, warm |
| midnight | `#4169e1` | `#191970` | Dark, mysterious |
| jade | `#00a86b` | `#006400` | Natural, balanced |

### Adding New Themes

**Step 1: Define colors**
```python
# botc/card_generator.py
COLOR_THEMES = {
    # ... existing themes ...
    'your_theme': {
        'primary_color': '#RRGGBB',
        'secondary_color': '#RRGGBB',
        'accent_color': '#RRGGBB',
        'text_color': '#ffffff',  # Usually white
        'background_color': '#000000'  # Usually black
    }
}
```

**Step 2: Update validation**
```python
# botc/cogs/slash.py in stprofile_slash command
valid_themes = ['gold', 'silver', ..., 'your_theme']
if color_theme and color_theme.lower() not in valid_themes:
    await interaction.response.send_message(
        f"❌ Invalid color theme. Choose from: {', '.join(valid_themes)}",
        ephemeral=True
    )
    return
```

**Step 3: Document**
- Add to docs/COLOR_THEMES.md
- Update `/stprofile` command description
- Update developer guide (here)

**Step 4: Test**
```bash
python3 generate_preview_card.py your_theme
```

---

## Command Implementation Patterns

### Slash Commands vs Prefix Commands

**Slash commands** (`/startgame`, `/endgame`):
- **Pros:** Autocomplete, type validation, UI-driven
- **Cons:** Slower to type, requires interaction.response.defer() for long operations
- **Use for:** Admin commands, game lifecycle, structured data entry

**Prefix commands** (`*st`, `*call`, `*g`):
- **Pros:** Fast to type, familiar to power users
- **Cons:** No autocomplete, manual parsing, harder discoverability
- **Use for:** Quick actions, role toggles, simple lookups

### Slash Command Pattern

**File:** `botc/cogs/slash.py`

```python
@app_commands.command(name="startgame", description="Start a new game")
@app_commands.describe(
    script="Script being played",
    custom_name="Custom script name (required for Custom Script)"
)
@app_commands.choices(
    script=[
        app_commands.Choice(name="🍺 Trouble Brewing", value="Trouble Brewing"),
        app_commands.Choice(name="🪻 Sects & Violets", value="Sects & Violets"),
        # ...
    ]
)
async def startgame_slash(interaction: discord.Interaction, script: app_commands.Choice[str], custom_name: str = ""):
    # 1. Permission check
    member = interaction.guild.get_member(interaction.user.id)
    if not getattr(self.bot, "is_storyteller", lambda m: False)(member):
        await interaction.response.send_message("Only storytellers can start games.", ephemeral=True)
        return
    
    # 2. Validation
    if not interaction.channel.category:
        await interaction.response.send_message("⚠️ Must be run in a category.", ephemeral=True)
        return
    
    session = await session_manager.get_session(guild_id, category_id)
    if not session:
        await interaction.response.send_message("⚠️ No session found. Run `/setbotc` first.", ephemeral=True)
        return
    
    # 3. Defer for long operation
    await interaction.response.defer(ephemeral=False)
    
    # 4. Delegate to business logic
    try:
        embed = await self.bot.start_game_handler(interaction, script, custom_name)
        await interaction.followup.send(embed=embed, ephemeral=False)
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        await interaction.followup.send("❌ Failed to start game.", ephemeral=True)
```

### Prefix Command Pattern

**File:** `botc/cogs/commands.py`

```python
@commands.Cog.listener()
async def on_message(self, message: discord.Message):
    if message.author.bot:
        return
    
    content = message.content.strip()
    first_word = content.split()[0] if content else ""
    
    # Example: *g <link> (set grimoire)
    if first_word == "*g" or content.startswith("*g "):
        args = content.split(maxsplit=1)
        
        # Get session (read-only)
        session_manager = getattr(self.bot, "session_manager", None)
        session = await session_manager.get_session_from_channel(message.channel, message.guild)
        
        if not session:
            await message.channel.send("⚠️ No session found. Run `/setbotc` first.")
            return
        
        if len(args) > 1:
            # Set grimoire link (ST only)
            if not self.bot.is_storyteller(message.author):
                await message.channel.send("Only storytellers can set grimoire.")
                return
            
            session.grimoire_link = args[1].strip()
            await session_manager.update_session(session)
            await message.channel.send(f"{EMOJI_SCROLL} Grimoire link set.")
        else:
            # Display current link
            if session.grimoire_link:
                await message.channel.send(f"{EMOJI_SCROLL} {session.grimoire_link}")
            else:
                await message.channel.send("No grimoire link set.")
        return
```

### Business Logic Handlers

**File:** `botc/handlers.py`

**Why separate?**
- **Testability:** Business logic isolated from Discord API
- **Reusability:** Same handler for slash and prefix commands
- **Clarity:** Interaction handling vs game logic

**Pattern:**
```python
async def start_game_handler(
    interaction: discord.Interaction,
    bot,
    db: Database,
    script: object,
    custom_name: str = ""
) -> discord.Embed:
    """Pure business logic - no Discord interaction calls except final response."""
    
    # 1. Extract context
    guild = interaction.guild
    member = interaction.user
    
    # 2. Validate business rules
    if not main_st:
        raise ValueError("No main Storyteller found")
    
    # 3. Database operations
    game_id = await db.start_game(...)
    
    # 4. Build response
    embed = discord.Embed(title="Game Started", ...)
    return embed
```

### Session-Scoped Command Pattern

**All commands that modify session state:**

```python
# 1. Get session (fail if not found)
session = await session_manager.get_session_from_channel(channel, guild)
if not session:
    await channel.send("⚠️ No session found. Run `/setbotc` first.")
    return

# 2. Modify session
session.grimoire_link = new_link
session.last_active = time.time()

# 3. Persist changes
await session_manager.update_session(session)

# 4. Confirm to user
await channel.send(f"✅ Updated session in {session.category.name}")
```

### Rate Limiting Pattern

**Implementation:**
```python
# Global dict: user_id -> {command: last_timestamp}
command_cooldowns: dict[int, dict[str, float]] = {}

def check_rate_limit(user_id: int, command: str, cooldown_seconds: int = 2) -> bool:
    """Returns True if command allowed, False if on cooldown."""
    now = time.time()
    if user_id not in command_cooldowns:
        command_cooldowns[user_id] = {}
    
    last_used = command_cooldowns[user_id].get(command, 0)
    if now - last_used < cooldown_seconds:
        return False  # Rate limited
    
    command_cooldowns[user_id][command] = now
    return True  # Allowed
```

**Usage:**
```python
if not self.bot.check_rate_limit(interaction.user.id, "stats", COMMAND_COOLDOWN_LONG):
    await interaction.response.send_message("⏳ Please wait before using this command again.", ephemeral=True)
    return
```

---

## State Management

### In-Memory State

**What's cached:**
1. **Sessions:** `SessionManager._cache` (dict)
2. **Shadow followers:** `bot.follower_targets` (dict)
3. **Player snapshots:** `bot.last_player_snapshots` (dict)
4. **Rate limits:** `command_cooldowns` (dict)
5. **Nick change tracking:** `bot.bot_initiated_nick_changes` (set)

**Why cache?**
- **Sessions:** Accessed on every command
- **Followers:** Real-time voice channel moves
- **Snapshots:** Detect roster changes for warnings
- **Rate limits:** Prevent spam
- **Nick changes:** Avoid false warnings for bot-initiated changes

### Persistence Strategy

**Rule:** All persistent state MUST be in PostgreSQL.

**Cache invalidation:**
- **Session updates:** Write to DB first, then cache
- **Game start/end:** Update active_game_id in DB and session cache
- **Follower changes:** Write to DB immediately, update in-memory dict

**Startup recovery:**
```python
@bot.event
async def on_ready():
    # 1. Connect to database
    await db.connect()
    await db.initialize_schema()
    
    # 2. Load shadow followers
    for guild in bot.guilds:
        followers = await db.get_all_followers_for_guild(guild.id)
        for target_id, follower_ids in followers.items():
            for follower_id in follower_ids:
                bot.follower_targets[follower_id] = target_id
    
    # 3. Restore timers
    await timer_manager.load_timers()
    
    # Session cache is empty on startup - populated on first command
```

### Voice Channel Cap Management

**Problem:** STs and spectators need to join full channels.

**Solution:** Dynamic user_limit adjustment.

**Algorithm:**
1. **Snapshot on `/startgame`:**
   ```python
   for vc in category.voice_channels:
       if vc.user_limit > 0:
           session.vc_caps[vc.id] = vc.user_limit
   await session_manager.update_session(session)
   ```

2. **Increase on privileged join:**
   ```python
   async def _handle_vc_cap_join(member, channel):
       if not has_st_or_spec_prefix(member):
           return
       
       original_cap = session.vc_caps.get(channel.id)
       if not original_cap:
           return
       
       new_cap = channel.user_limit + 1
       await channel.edit(user_limit=new_cap)
   ```

3. **Restore on privileged leave:**
   ```python
   async def _handle_vc_cap_leave(member, channel):
       privileged_count = count_privileged_in_channel(channel)
       target_cap = session.vc_caps[channel.id] + privileged_count
       await channel.edit(user_limit=target_cap)
   ```

4. **Reset on `/endgame`:**
   ```python
   for channel_id, original_cap in session.vc_caps.items():
       channel = guild.get_channel(channel_id)
       await channel.edit(user_limit=original_cap)
   session.vc_caps = {}
   await session_manager.update_session(session)
   ```

---

##

**Best practices:**
- Always use `async with self.pool.acquire() as conn:`
- Never hold connections longer than necessary
- Handle `asyncpg.PostgresError` explicitly
- Use connection pool, not individual connections

### Query Patterns

#### Simple SELECT
```python
async def get_guild(self, guild_id: int) -> dict:
    async with self.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM guilds WHERE guild_id = $1",
            guild_id
        )
        return dict(row) if row else None
```

#### INSERT with RETURNING
```python
async def create_session(self, session: Session) -> Session:
    async with self.pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO sessions (
                guild_id, category_id, destination_channel_id, ...
            ) VALUES ($1, $2, $3, ...)
            ON CONFLICT (guild_id, category_id) 
            DO UPDATE SET last_active = $10
            RETURNING *
        """, session.guild_id, session.category_id, ...)
        
        return Session(**dict(row))
```

**Note:** `ON CONFLICT` prevents race conditions when two users configure same session simultaneously.

#### UPDATE
```python
async def update_session(self, session: Session):
    async with self.pool.acquire() as conn:
        await conn.execute("""
            UPDATE sessions SET
                destination_channel_id = $3,
                grimoire_link = $4,
                last_active = $5
            WHERE guild_id = $1 AND category_id = $2
        """, session.guild_id, session.category_id, ...)
```

#### Transaction (Multiple Operations)
```python
async def end_game(self, guild_id, end_time, winner, category_id=None):
    async with self.pool.acquire() as conn:
        async with conn.transaction():
            # 1. Mark game as ended
            await conn.execute("""
                UPDATE games SET 
                    end_time = $1, 
                    winner = $2, 
                    is_active = FALSE
                WHERE guild_id = $3 AND is_active = TRUE
            """, end_time, winner, guild_id)
            
            # 2. Update storyteller stats
            await conn.execute("""
                UPDATE storyteller_stats SET
                    total_games = total_games + 1,
                    good_wins = good_wins + CASE WHEN $1 = 'Good' THEN 1 ELSE 0 END,
                    evil_wins = evil_wins + CASE WHEN $1 = 'Evil' THEN 1 ELSE 0 END
                WHERE guild_id = $2 AND storyteller_id = $3
            """, winner, guild_id, storyteller_id)
```

**Transaction guarantees:**
- All operations succeed, or none do (atomicity)
- Automatic rollback on exception
- Use for multi-step operations that must be consistent

### JSONB Storage

**Player lists stored as JSONB:**
```python
# Writing
players_json = json.dumps(player_ids)  # [123, 456, 789]
await conn.execute("""
    INSERT INTO games (players, ...)
    VALUES ($1::jsonb, ...)
""", players_json)

# Reading (automatic deserialization by asyncpg)
row = await conn.fetchrow("SELECT players FROM games WHERE game_id = $1", game_id)
players = row['players']  # Already a Python list!
```

### Migration Pattern

**Idempotent migrations:**
```sql
-- 003_sessions_table.sql
CREATE TABLE IF NOT EXISTS sessions (...);

-- Safe to run multiple times
```

**Data migrations:**
```sql
-- Move data from old table to new table
INSERT INTO sessions (guild_id, category_id, ...)
SELECT guild_id, server_name, ...
FROM guilds
WHERE guild_id = $1
ON CONFLICT (guild_id, category_id) DO NOTHING;
```

**Breaking migrations (like 008):**
```sql
-- Must be run manually via script
-- Requires code changes first
ALTER TABLE guilds DROP COLUMN grimoire_link;
```

---

## Command Implementation Patterns

### Pattern 1: Simple Prefix Command

```python
# In botc/cogs/commands.py

@commands.command(name="help")
async def help_command(self, ctx):
    """Show help message."""
    embed = discord.Embed(
        title="Grimkeeper Commands",
        description="...",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)
```

### Pattern 2: Session-Scoped Command

```python
@commands.command(name="g")
async def grimoire(self, ctx, link: str = None):
    """Get or set grimoire link."""
    # Resolve session
    if link:
        # Setting link - use get_or_create
        session = await self.bot.session_manager.get_or_create_session_from_channel(
            ctx.channel, ctx.guild
        )
    else:
        # Viewing link - use get_session
        session = await self.bot.session_manager.get_session_from_channel(
            ctx.channel, ctx.guild
        )
    
    if not session:
        await ctx.send("No session found for this category")
        return
    
    # Business logic
    if link:
        session.grimoire_link = link
        await self.bot.session_manager.update_session(session)
        embed = discord.Embed(title="📜 Grimoire Link Set", description=link)
        await ctx.send(embed=embed)
    else:
        if session.grimoire_link:
            await ctx.send(f"📜 Current grimoire link: {session.grimoire_link}")
        else:
            await ctx.send("No grimoire link set")
```

### Pattern 3: Role-Restricted Command

```python
@commands.command(name="call")
async def call_command(self, ctx):
    """Move all players to town square (ST only)."""
    # Check ST role
    if not self.bot.is_storyteller(ctx.author):
        msg = await ctx.send("Only storytellers can use this command")
        await msg.delete(delay=3)
        return
    
    # Check active game
    session = await self.bot.session_manager.get_session_from_channel(
        ctx.channel, ctx.guild
    )
    if not session or not session.active_game_id:
        msg = await ctx.send("No active game. Use /startgame first")
        await msg.delete(delay=3)
        return
    
    # Execute
    await self.bot.call_townspeople(ctx.guild, category_id=session.category_id)
    msg = await ctx.send("📯 Called players to town square!")
    await msg.delete(delay=3)
```

### Pattern 4: Slash Command with Interaction

```python
# In botc/cogs/slash.py

@app_commands.command(name="startgame", description="Start tracking a game")
@app_commands.describe(
    script="Which script are you running?",
    custom_name="Custom script name (required for Custom Script)"
)
async def startgame(
    self,
    interaction: discord.Interaction,
    script: ScriptChoice,
    custom_name: str = ""
):
    """Slash command wrapper - delegates to handler."""
    # Show confirmation view first
    view = StartGameConfirmView(self.bot, interaction, script, custom_name)
    
    embed = discord.Embed(
        title="🎲 Start New Game?",
        description="Review the player roster and confirm",
        color=discord.Color.gold()
    )
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
```

**Handler in `botc/handlers.py`:**
```python
async def start_game_handler(
    interaction: discord.Interaction,
    bot,
    db: 'Database',
    script: object,
    custom_name: str = ""
) -> None:
    """Business logic separated from Discord interaction."""
    # Validate input
    # Resolve session
    # Collect players
    # Record game
    # Create announcement
    # Return embed for confirmation view to send
```

### Pattern 5: Interactive View (Buttons)

```python
class CharacterView(discord.ui.View):
    def __init__(self, char_info):
        super().__init__(timeout=300)  # 5 minute timeout
        self.char_info = char_info
        self.current_section = "summary"
    
    @discord.ui.button(label="Summary", style=discord.ButtonStyle.primary)
    async def summary_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_section = "summary"
        embed = self.create_embed("summary")
        await interaction.response.edit_message(embed=embed, view=self)
    
    # More buttons...
    
    def create_embed(self, section):
        """Build embed for section."""
        embed = discord.Embed(title=self.char_info.name)
        if section == "summary":
            embed.description = self.char_info.ability
        # ...
        return embed
```

### Pattern 6: Rate Limited Command

```python
from botc.constants import COMMAND_COOLDOWN_LONG

def check_rate_limit(user_id, command_name, cooldown=2):
    """Check if user is rate limited."""
    now = time.time()
    last_used = command_cooldowns.get(user_id, {}).get(command_name, 0)
    
    if now - last_used < cooldown:
        return False  # Rate limited
    
    command_cooldowns.setdefault(user_id, {})[command_name] = now
    return True  # Allowed

# Usage in command:
if not check_rate_limit(ctx.author.id, "players"):
    return  # Silently ignore (no error message)
```

---

## State Management

### What Lives Where

| State Type | Storage Location | Lifetime | Persistence |
|------------|------------------|----------|-------------|
| Session config | Database + cache | Until deleted | Persistent |
| Active game | Database (games table) | Until /endgame | Persistent |
| Active timer | Database + memory | Until completion | Persistent across restarts |
| Shadow followers | Database | Until *unspec | Persistent |
| Player snapshots | Memory (dict) | Until bot restart | Ephemeral |
| Voice cap backups | Memory (dict) | Cleared on restart | Ephemeral |
| Command cooldowns | Memory (dict) | Until bot restart | Ephemeral |
| Cache (sessions) | Memory (dict) | Until invalidation | Ephemeral |

### State Synchronization

**Database is source of truth:**
- All persistent state written to database immediately
- Cache is read-through (query DB on cache miss)
- Cache is write-through (update DB first, then cache)

**Memory state rebuilding:**
```python
async def on_ready():
    # Rebuild shadow followers from database
    followers = await db.get_all_shadow_followers()
    for follower_id, target_id, guild_id in followers:
        shadow_followers[target_id].add(follower_id)
        follower_targets[follower_id] = target_id
    
    # Restore timers
    await timer_manager.load_timers()
    
    # Cache starts empty, populated on demand
```

### State Cleanup Strategies

**Automatic cleanup:**
```python
# Cleanup shadow followers when user leaves server
@bot.event
async def on_member_remove(member):
    await db.remove_shadow_follower(member.id, member.guild.id)
    # Also update in-memory state
    follower_targets.pop(member.id, None)
    for followers_set in shadow_followers.values():
        followers_set.discard(member.id)
```

**Periodic cleanup:**
```python
# Every 24 hours, remove sessions inactive >30 days
@tasks.loop(hours=24)
async def cleanup_sessions():
    deleted = await session_manager.cleanup_inactive_sessions(max_age_days=30)
    logger.info(f"Cleaned up {deleted} inactive sessions")
```

**Manual cleanup:**
```python
# Admin command to clean up specific session
@commands.command(name="sessions")
async def sessions_command(self, ctx, action: str = None, session_id: int = None):
    if action == "cleanup" and session_id:
        await self.bot.session_manager.delete_session(guild_id, category_id)
```

---

## Error Handling Philosophy

### Principles

1. **Fail gracefully:** No uncaught exceptions that crash the bot
2. **Helpful errors:** Tell users what went wrong AND how to fix it
3. **Silent failures for spam:** Rate-limited commands fail silently
4. **Log everything:** Errors logged even if not shown to user
5. **Auto-delete errors:** Temporary error messages delete after 3-5 seconds

### Error Handling Patterns

#### Pattern 1: User Input Validation
```python
async def settown(self, ctx, channel: discord.VoiceChannel):
    # Type validation via discord.py converter
    # If channel isn't a VoiceChannel, discord.py handles error
    
    # Business logic validation
    if not channel.category:
        msg = await ctx.send(
            "❌ Town Square must be in a category.\n"
            "Move the channel into a category first."
        )
        await msg.delete(delay=5)
        return
    
    # Proceed with valid input
```

#### Pattern 2: Permission Errors
```python
try:
    await member.edit(nick=new_nick)
except discord.Forbidden:
    msg = await ctx.send(
        "❌ I don't have permission to change nicknames.\n"
        "Grant me 'Manage Nicknames' permission."
    )
    await msg.delete(delay=5)
except discord.HTTPException as e:
    logger.error(f"Failed to edit nickname: {e}")
    msg = await ctx.send("❌ Failed to update nickname. Check bot permissions.")
    await msg.delete(delay=5)
```

#### Pattern 3: Database Errors
```python
from botc.exceptions import DatabaseError

try:
    await db.start_game(guild_id, script, ...)
except DatabaseError as e:
    logger.error(f"Database error in start_game: {e}")
    await interaction.response.send_message(
        "❌ Database error. Please try again.",
        ephemeral=True
    )
    return
except Exception as e:
    logger.exception(f"Unexpected error in start_game: {e}")
    await interaction.response.send_message(
        "❌ Unexpected error. Contact administrator.",
        ephemeral=True
    )
    return
```

#### Pattern 4: Graceful Degradation
```python
# If announce channel deleted, don't crash - just skip announcement
session = await session_manager.get_session_from_channel(channel, guild)
if session and session.announce_channel_id:
    announce_channel = guild.get_channel(session.announce_channel_id)
    if announce_channel:
        try:
            await announce_channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.warning(f"Failed to send announcement: {e}")
            # Continue execution - announcement is optional
    else:
        logger.warning(f"Announce channel {session.announce_channel_id} not found")
        # Continue - channel may have been deleted
```

### Error Message Guidelines

**Bad error:**
```
❌ Error
```

**Good error:**
```
❌ No town square configured

Run `*settown #channel-name` to set it up.
```

**Great error:**
```
❌ Cannot start game - no players found

Make sure players are in voice channels in the BOTC category.
Storytellers (ST) and spectators (!) are not counted as players.

Need help? Run `*help` for setup guide.
```

**Template:**
```
[Emoji] [What went wrong]

[Why it happened / What's missing]

[How to fix it]
```

---

## Testing Strategy

### Test Pyramid

```
     /\        Unit Tests (test_utils.py, test_timers.py)
    /  \       - Fast, isolated, many
   /    \      
  /------\     Integration Tests (test_session_scenarios.py)
 /        \    - Medium speed, test interactions
/----------\   
  Manual      End-to-End Tests (TESTING_PROTOCOL.md)
   Tests      - Slow, realistic, few
```

### Automated Tests

**Run all tests:**
```bash
python3 -m pytest tests/ -v
```

**Run specific test file:**
```bash
python3 -m pytest tests/test_session_scenarios.py -v
```

**Run specific test:**
```bash
python3 -m pytest tests/test_session_scenarios.py::test_fresh_autosetup -v
```

**Coverage report:**
```bash
python3 -m pytest tests/ --cov=botc --cov-report=html
open htmlcov/index.html
```

### Test Database Setup

**Use separate test database:**
```python
# In tests/conftest.py
@pytest.fixture
async def test_db():
    db = Database(database_url="postgresql://localhost/grimkeeper_test")
    await db.connect()
    
    # Run migrations
    await db.run_migrations()
    
    yield db
    
    # Cleanup
    await db.pool.close()
```

### Writing New Tests

**Test structure:**
```python
import pytest
from botc.session import Session, SessionManager

@pytest.mark.asyncio
async def test_session_creation(test_db):
    """Test that sessions are created correctly."""
    # Arrange
    session_manager = SessionManager(test_db)
    guild_id = 123456789
    category_id = 987654321
    
    # Act
    session = await session_manager.create_session(
        guild_id=guild_id,
        category_id=category_id
    )
    
    # Assert
    assert session.guild_id == guild_id
    assert session.category_id == category_id
    assert session.session_id == (guild_id, category_id)
    assert session.created_at is not None
```

### Manual Testing Checklist

Before committing major changes:

- [ ] Code compiles without syntax errors
- [ ] Automated tests pass
- [ ] Test in Discord test server:
  - [ ] Run changed command(s) successfully
  - [ ] Verify error handling (wrong input, missing permissions)
  - [ ] Check multi-session isolation (if session-related)
  - [ ] Verify database persistence (restart bot)
- [ ] Check logs for errors/warnings
- [ ] Review error messages for clarity

---

## Performance Considerations

### Database Query Optimization

**Use indexes:**
```sql
CREATE INDEX idx_sessions_guild ON sessions(guild_id);
CREATE INDEX idx_sessions_last_active ON sessions(last_active);
```

**Batch queries instead of N+1:**
```python
# ❌ Bad - N+1 queries
for session in sessions:
    game = await db.get_game(session.active_game_id)

# ✅ Good - Single query
game_ids = [s.active_game_id for s in sessions if s.active_game_id]
games = await db.get_games_by_ids(game_ids)
```

**Use connection pooling:**
- Already configured (min: 2, max: 10)
- Don't create new connections manually
- Always use `async with self.pool.acquire()`

### Caching Strategy

**What to cache:**
- ✅ Sessions (accessed every command)
- ✅ Guild config (accessed frequently)
- ❌ Game history (infrequent, large)
- ❌ Storyteller stats (computed on-demand)

**Cache invalidation:**
```python
# Invalidate immediately on update
async def update_session(self, session):
    await self.db.update_session(session)
    self._cache[session.session_id] = session  # Refresh cache
```

### Discord API Rate Limits

**Best practices:**
- **Delete messages after delay** instead of immediately (fewer API calls)
- **Batch edits** if editing multiple messages
- **Use ephemeral messages** for temporary info (slash commands)
- **Don't spam announcements** (one per session, not per channel)

**Example:**
```python
# ❌ Bad - Multiple API calls
msg = await channel.send("Starting game...")
await asyncio.sleep(1)
await msg.delete()

# ✅ Good - Single API call with delay
msg = await channel.send("Starting game...")
await msg.delete(delay=3)
```

### Memory Management

**Current footprint (estimates):**
- Session cache: ~250 KB for 1000 sessions
- Command cooldowns: ~100 KB for 1000 users
- Shadow followers: ~50 KB for 500 relationships
- Voice cap backups: ~20 KB for 100 channels

**Total: <1 MB** - No memory concerns for foreseeable scale

---

## Common Development Tasks

### Adding a New Prefix Command

1. **Choose the right cog:**
   - Generic commands → `botc/cogs/commands.py`
   - Timer-related → `botc/cogs/timers.py`
   - Poll-related → `botc/cogs/polls.py`

2. **Add command handler:**
```python
# In botc/cogs/commands.py

@commands.command(name="mycommand")
async def mycommand(self, ctx, arg1: str, arg2: int = 10):
    """My new command description."""
    # Rate limiting
    if not check_rate_limit(ctx.author.id, "mycommand"):
        return
    
    # Permission check (if needed)
    if not self.bot.is_storyteller(ctx.author):
        msg = await ctx.send("ST only")
        await msg.delete(delay=3)
        return
    
    # Session resolution (if needed)
    session = await self.bot.session_manager.get_session_from_channel(
        ctx.channel, ctx.guild
    )
    
    # Business logic
    result = do_something(arg1, arg2)
    
    # Response
    await ctx.send(f"Result: {result}")
```

3. **Update help text:**
```python
# In botc/cogs/commands.py help_command()
# Add to appropriate section
```

4. **Test:**
```bash
# In Discord: *mycommand test 5
```

### Adding a New Slash Command

1. **Define in `botc/cogs/slash.py`:**
```python
@app_commands.command(name="myslash", description="My new slash command")
@app_commands.describe(
    param1="Description of param1",
    param2="Description of param2"
)
async def myslash(
    self,
    interaction: discord.Interaction,
    param1: str,
    param2: int = 10
):
    """Slash command wrapper."""
    # Simple logic - handle inline
    await interaction.response.send_message(f"Got {param1} and {param2}")
    
    # OR complex logic - delegate to handler
    await my_handler(interaction, self.bot, self.bot.db, param1, param2)
```

2. **Create handler (if complex) in `botc/handlers.py`:**
```python
async def my_handler(
    interaction: discord.Interaction,
    bot,
    db: 'Database',
    param1: str,
    param2: int
) -> None:
    """Business logic separated from Discord interaction."""
    # Validation, session resolution, database ops, etc.
    # ...
    
    await interaction.response.send_message("Done!")
```

3. **Sync commands:**
```bash
# Restart bot - slash commands auto-sync in on_ready()
```

4. **Test:**
```bash
# In Discord: /myslash param1:test param2:5
```

### Adding a Database Migration

1. **Create migration file:**
```bash
# migrations/009_my_feature.sql
CREATE TABLE IF NOT EXISTS my_new_table (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    data TEXT
);

CREATE INDEX idx_my_new_table_guild ON my_new_table(guild_id);
```

2. **Add to auto-run (if safe) in `botc/database.py`:**
```python
async def run_migrations(self):
    migrations = [
        "001_initial_schema.sql",
        "002_storyteller_stats.sql",
        # ...
        "009_my_feature.sql",  # Add here
    ]
    # ...
```

**OR create manual migration script:**
```bash
# scripts/apply_migration_009.sh
#!/bin/bash
psql $DATABASE_URL -f migrations/009_my_feature.sql
```

3. **Add database methods in `botc/database.py`:**
```python
async def insert_my_data(self, guild_id: int, data: str):
    async with self.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO my_new_table (guild_id, data)
            VALUES ($1, $2)
        """, guild_id, data)
```

4. **Test migration:**
```bash
# On fresh test database
python3 main.py  # Runs migrations
# Verify table created
psql $DATABASE_URL -c "\dt"
```

### Adding a Custom Emoji

1. **Upload emoji to Discord server:**
   - Server Settings → Emoji → Upload Image
   - Copy emoji ID (right-click emoji → Copy Link, extract ID)

2. **Add to `botc/constants.py`:**
```python
# Custom Discord emojis (from server ID: YOUR_SERVER_ID)
EMOJI_MY_NEW_EMOJI = "<:my_emoji:1234567890123456789>"
```

3. **Use in code:**
```python
from botc.constants import EMOJI_MY_NEW_EMOJI

embed.add_field(name=f"{EMOJI_MY_NEW_EMOJI} My Field", value="...")
```

### Updating the Changelog

1. **Edit `changelog.json`:**
```json
[
  {
    "version": "1.5.1",
    "date": "2025-12-02",
    "title": "My New Feature",
    "description": "Added cool new functionality",
    "features": [
      "New command: *mycommand",
      "Improved error handling",
      "Bug fix: fixed issue with X"
    ]
  },
  // ... older versions
]
```

2. **Update `botc/constants.py`:**
```python
VERSION = "1.5.1"
```

3. **Test:**
```bash
# In Discord: *changelog
# Should show latest version
```

---

## Debugging Strategies

### Reading Logs

**Log file location:** `discord.log` (in project root)

**Tail logs in real-time:**
```bash
tail -f discord.log
```

**Search for errors:**
```bash
grep ERROR discord.log
grep "Failed to" discord.log
```

**Filter by session:**
```bash
grep "category_id=123456" discord.log
```

### Common Issues

#### Issue: Command not responding

**Checklist:**
- [ ] Is bot online in Discord?
- [ ] Does bot have Read Messages permission?
- [ ] Is command rate-limited? (wait 2 seconds, try again)
- [ ] Check logs for errors

**Debug:**
```python
# Add debug logging to command
logger.info(f"Command invoked: {ctx.command.name} by {ctx.author}")
```

#### Issue: Session not found

**Checklist:**
- [ ] Is channel in a category?
- [ ] Was session created? Check database:
```sql
SELECT * FROM sessions WHERE guild_id = YOUR_GUILD_ID;
```
- [ ] Is cache stale? Restart bot to rebuild cache

**Debug:**
```python
# Add logging to session resolution
logger.info(f"Resolving session for guild={guild.id}, category={channel.category.id if channel.category else None}")
session = await session_manager.get_session_from_channel(channel, guild)
logger.info(f"Session found: {session}")
```

#### Issue: Database connection failure

**Symptoms:**
- Commands hang
- Errors: `asyncpg.exceptions.TooManyConnectionsError`

**Solution:**
```python
# Check connection pool status
logger.info(f"Pool size: {db.pool.get_size()}, Free: {db.pool.get_idle_size()}")

# Increase pool size if needed (in database.py)
self.pool = await asyncpg.create_pool(..., max_size=20)
```

#### Issue: Bot crashes on startup

**Checklist:**
- [ ] `.env` file exists with valid `DISCORD_TOKEN`?
- [ ] Database accessible? Test:
```bash
psql $DATABASE_URL -c "SELECT 1"
```
- [ ] Python dependencies installed?
```bash
pip install -r requirements.txt
```

**Debug:**
```python
# Add try/except around bot.run()
try:
    bot.run(DISCORD_TOKEN)
except Exception as e:
    logger.exception(f"Bot failed to start: {e}")
```

### Interactive Debugging

**Use ipdb (interactive Python debugger):**

1. **Install:**
```bash
pip install ipdb
```

2. **Add breakpoint:**
```python
import ipdb; ipdb.set_trace()
```

3. **Run bot:**
```bash
python3 main.py
# Bot will pause at breakpoint
# Use commands: n (next), s (step), c (continue), p (print)
```

**Use Discord test server:**
- Create private server for testing
- Invite bot with all permissions
- Test commands in isolation
- Use ephemeral messages to avoid clutter

---

## Migration Guide

### Migrating from Pre-Session Architecture

**Old code (guild-scoped):**
```python
guild_config = await db.get_guild(guild_id)
grimoire_link = guild_config.get("grimoire_link")
```

**New code (session-scoped):**
```python
session = await session_manager.get_session_from_channel(channel, guild)
if session:
    grimoire_link = session.grimoire_link
```

### Breaking Changes in v1.5.0

**Migration 008 removed these fields from `guilds` table:**
- `grimoire_link` → Moved to `sessions.grimoire_link`
- `destination_channel_id` → Moved to `sessions.destination_channel_id`
- `announce_channel_id` → Moved to `sessions.announce_channel_id`
- `exception_channel_id` → Moved to `sessions.exception_channel_id`

**Update code:**
```python
# ❌ Old (breaks after migration 008)
guild = await db.get_guild(guild_id)
await channel.send(guild["grimoire_link"])

# ✅ New
session = await session_manager.get_session_from_channel(channel, guild)
if session and session.grimoire_link:
    await channel.send(session.grimoire_link)
```

### Session Creation Philosophy (v1.5.1+)

**Explicit Session Setup:**
As of v1.5.1, all sessions must be explicitly created. The old `guild.botc_category_id` backward compatibility auto-creation has been removed.

**Creation Methods:**
1. **Primary:** `/setbotc <category>` - Admin explicitly designates a category as a BOTC session
2. **Convenience:** `/autosetup` - Creates category + channels + session in one command
3. **Implicit:** Session-scoped config commands (`/settown`, etc.) auto-create if run in a category

**Validation:**
All session-dependent commands (`/startgame`, `/endgame`, `*call`, `*timer`, `*night`, `*day`, `*consult`) now validate:
1. Channel is in a category
2. Session exists for that category
3. Show clear error: "⚠️ This category is not set up as a BOTC session. Use `/setbotc` to set it up first."

**Why the change?**
- **Clarity:** Users know exactly when a session is created
- **Control:** No surprise auto-creation from legacy guild config
- **Modularity:** Each category is independently configured
- **Simplicity:** One less code path to maintain

---

## Common Pitfalls

### Pitfall 1: Forgetting to Update Cache

**Problem:**
```python
# Update database but forget cache
await db.update_session(session)
# Cache still has old data!
```

**Solution:**
```python
# SessionManager.update_session() handles both
await session_manager.update_session(session)
```

### Pitfall 2: Not Handling None Session

**Problem:**
```python
session = await session_manager.get_session_from_channel(channel, guild)
grimoire = session.grimoire_link  # Crashes if session is None!
```

**Solution:**
```python
session = await session_manager.get_session_from_channel(channel, guild)
if not session:
    await channel.send("⚠️ This category is not set up as a BOTC session. Use `/setbotc` to set it up first.")
    return

grimoire = session.grimoire_link  # Safe
```

### Pitfall 3: Using Wrong Resolution Method

**Problem:**
```python
# User wants to VIEW grimoire but command auto-creates session
session = await session_manager.get_or_create_session_from_channel(channel, guild)
```

**Solution:**
```python
# Use get_session for read-only operations
session = await session_manager.get_session_from_channel(channel, guild)

# Use get_or_create only for config commands
session = await session_manager.get_or_create_session_from_channel(channel, guild)
```

### Pitfall 4: Holding Database Connections Too Long

**Problem:**
```python
conn = await db.pool.acquire()
# ... lots of code ...
await do_slow_operation()
# ... more code ...
await conn.release()  # Connection held for too long!
```

**Solution:**
```python
async with db.pool.acquire() as conn:
    # Only hold connection for queries
    await conn.execute(...)
# Connection auto-released
```

### Pitfall 5: Not Awaiting Async Functions

**Problem:**
```python
session = session_manager.get_session(guild_id, category_id)  # Forgot await!
print(session.grimoire_link)  # Crashes - session is a coroutine, not Session object
```

**Solution:**
```python
session = await session_manager.get_session(guild_id, category_id)
print(session.grimoire_link)  # Works
```

### Pitfall 6: SQL Injection (Avoided with Parameterized Queries)

**Problem:**
```python
# ❌ NEVER do this
query = f"SELECT * FROM sessions WHERE guild_id = {guild_id}"
await conn.execute(query)
```

**Solution:**
```python
# ✅ Always use parameterized queries
await conn.execute(
    "SELECT * FROM sessions WHERE guild_id = $1",
    guild_id
)
```

### Pitfall 7: Forgetting Transaction for Multi-Step Operations

**Problem:**
```python
# Step 1 succeeds
await db.end_game(...)

# Step 2 fails - game ended but stats not updated!
await db.update_stats(...)
```

**Solution:**
```python
async with db.pool.acquire() as conn:
    async with conn.transaction():
        await conn.execute("UPDATE games ...")
        await conn.execute("UPDATE storyteller_stats ...")
# Both succeed or both roll back
```

---

## Best Practices Summary

### Code Organization
- ✅ Business logic in handlers, not cogs
- ✅ Reusable functions in utils
- ✅ Constants in constants.py
- ✅ Database operations in database.py

### Error Handling
- ✅ Always handle exceptions explicitly
- ✅ Log errors even if not shown to user
- ✅ Provide actionable error messages
- ✅ Auto-delete temporary errors

### Database
- ✅ Use connection pool (`async with self.pool.acquire()`)
- ✅ Use parameterized queries (prevent SQL injection)
- ✅ Use transactions for multi-step operations
- ✅ Index frequently queried columns

### Session Management
- ✅ Use `get_session` for read-only operations
- ✅ Use `get_or_create` for config commands
- ✅ Always check if session is None before using
- ✅ Update via SessionManager (handles cache)

### Testing
- ✅ Write tests for new features
- ✅ Test edge cases (None, empty, invalid)
- ✅ Manual test in Discord before committing
- ✅ Check logs for warnings/errors

### Documentation
- ✅ Update help text when adding commands
- ✅ Update changelog for every release
- ✅ Document breaking changes clearly
- ✅ Keep this guide up-to-date

---

## Getting Help

### Resources

- **Documentation:** `/docs` folder
- **Code examples:** Look at existing commands in `botc/cogs/`
- **Database schema:** See migration files in `migrations/`
- **Testing examples:** See `tests/` folder

### Debugging Steps

1. **Check logs:** `tail -f discord.log`
2. **Check database:** Query relevant tables
3. **Test in isolation:** Create minimal reproduction
4. **Add debug logging:** Use `logger.info()` liberally
5. **Ask for help:** Contact project maintainer

### Contributing

When submitting code:
1. **Follow existing patterns** (look at similar commands)
2. **Write tests** for new functionality
3. **Update documentation** (help text, changelog)
4. **Test manually** in Discord test server
5. **Check logs** for warnings/errors
6. **Use descriptive commit messages**

---

## Appendix: Quick Reference

### Common Bot Methods

```python
# Session resolution
session = await bot.session_manager.get_session_from_channel(channel, guild)
session = await bot.session_manager.get_or_create_session_from_channel(channel, guild)

# Role checks
is_st = bot.is_storyteller(member)

# Player collection
players = await bot.get_active_players(guild, category_id)

# Town square call
await bot.call_townspeople(guild, category_id)

# Channel retrieval
category = await bot.get_botc_category(guild, db)
```

### Common Database Methods

```python
# Sessions
session = await db.get_session(guild_id, category_id)
await db.create_session(session)
await db.update_session(session)
await db.delete_session(guild_id, category_id)

# Games
await db.start_game(guild_id, script, start_time, players, storyteller_id, category_id)
await db.end_game(guild_id, end_time, winner, category_id)
game = await db.get_active_game(guild_id, category_id)
history = await db.get_game_history(guild_id, limit, category_id)

# Guilds
guild = await db.get_guild(guild_id)
await db.upsert_guild(guild_id, server_name=name)

# Stats
stats = await db.get_storyteller_stats(guild_id, storyteller_id)
await db.update_storyteller_stats(guild_id, storyteller_id, winner, ...)
```

### Common Imports

```python
# Core Discord
import discord
from discord import app_commands
from discord.ext import commands

# Grimkeeper modules
from botc.constants import VERSION, EMOJI_*, PREFIX_*, DELETE_DELAY_*
from botc.database import Database
from botc.session import Session, SessionManager
from botc.utils import parse_duration, format_timestamp
from botc.handlers import start_game_handler, end_game_handler
from botc.discord_utils import safe_send_interaction
from botc.exceptions import DatabaseError

# Standard library
import asyncio
import logging
import time
import json
from typing import Optional
from dataclasses import dataclass
```

---

**This guide should be updated as the codebase evolves. When in doubt, look at existing code for patterns.**

**Last updated:** December 1, 2025 (v1.5.0)
