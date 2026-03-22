# Website Integration - Grimlive ↔ Grimkeeper

## Overview

The grimlive website and grimkeeper Discord bot share the same PostgreSQL database, enabling seamless stat tracking and Discord announcements triggered from the website.

## Architecture

```
┌──────────────────┐
│  grim.hystericca │
│      .dev        │  User clicks "Start Game"
│   (grimlive)     │
└────────┬─────────┘
         │
         │ 1. Insert game record
         │ 2. Insert announcement queue
         ▼
┌─────────────────────────┐
│  PostgreSQL Database    │
│  ┌──────────────────┐   │
│  │ games            │   │  ← Shared data
│  │ announcements    │   │  ← Queue
│  │ sessions         │   │  ← Session codes
│  └──────────────────┘   │
└────────┬────────────────┘
         │
         │ Background task (every 5s)
         │ checks for pending announcements
         ▼
┌──────────────────┐
│  grimkeeper bot  │
│                  │  Sends Discord embed
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Discord Server  │
│  📜┃announcements │  "A New Tale Begins..."
└──────────────────┘
```

## Session Codes

### What are session codes?

Session codes are short identifiers (`s1`, `s2`, `s3`, etc.) that link website games to Discord sessions.

- **Persistent**: Once created, a session code stays the same forever (until session deleted)
- **Sequential per guild**: First session = `s1`, second = `s2`, etc.
- **One-time admin setup**: Created when admin runs `/autosetup` or `/setbotc`
- **Reused for all games**: Same code used for every game in that category
- **Stored in database**: `sessions.session_code` column
- **User-facing**: Displayed in Discord, entered on website

### Where are they shown?

1. **`*game` command** - Shows current session info including code
2. **`/startgame` embed** - Displays as "🔗 Session Code: `s1`"
3. **`/endgame` embed** - Shows in footer "Session: s1"
4. **Website game start** - Auto-announced in Discord with code

### How sessions work:

**One-time setup (Admin):**
1. Admin runs `/autosetup` or `/setbotc <category>` in Discord
2. Bot creates persistent session with code `s1`
3. Session exists forever until manually deleted with `/deletesession`

**Every game (Storyteller):**
1. Storyteller types `*game` → Sees "Session Code: `s1`" (same code every time)
2. Storyteller logs into grim.hystericca.dev with Discord OAuth
3. Storyteller types `s1` in session code input field
4. Website validates: Does this code belong to this Discord user?
5. Game stats tracked to that Discord session ✅
6. Next game? Same code `s1`, same session, different game

## Database Schema

### `announcements` table

Queue for website-triggered Discord notifications.

```sql
CREATE TABLE announcements (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,              -- Discord server ID
    category_id BIGINT,                     -- Discord category ID (session)
    announcement_type VARCHAR(50) NOT NULL, -- 'game_start' or 'game_end'
    game_id INTEGER REFERENCES games(game_id),
    created_at BIGINT NOT NULL,            -- Unix timestamp
    processed BOOLEAN DEFAULT FALSE,        -- Has bot sent this yet?
    processed_at BIGINT                    -- When bot processed it
);

CREATE INDEX idx_announcements_pending ON announcements(guild_id, processed) 
WHERE processed = FALSE;
```

### `games` table (existing, unchanged)

```sql
CREATE TABLE games (
    game_id SERIAL PRIMARY KEY,
    guild_id BIGINT,                       -- Linked to Discord session
    category_id BIGINT,                    -- Discord category (session)
    script VARCHAR(255),
    custom_name VARCHAR(255),
    start_time BIGINT,
    end_time BIGINT,
    players TEXT,                          -- JSON array of player names
    player_count INTEGER,
    storyteller_id BIGINT,                 -- Discord user ID
    winner VARCHAR(50),                    -- 'Good', 'Evil', or NULL
    is_active BOOLEAN DEFAULT TRUE,
    completed_at BIGINT
);
```

### `sessions` table (existing, enhanced)

```sql
CREATE TABLE sessions (
    guild_id BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    destination_channel_id BIGINT,
    grimoire_link TEXT,
    exception_channel_id BIGINT,
    announce_channel_id BIGINT,            -- Where to send announcements
    active_game_id INTEGER,
    storyteller_user_id BIGINT,
    created_at BIGINT,
    last_active BIGINT,
    vc_caps JSONB,
    session_code VARCHAR(10),              -- "s1", "s2", etc.
    PRIMARY KEY (guild_id, category_id)
);
```

## Code Flow

### Website: Start Game

**File:** `grimlive/server/api.js` → `startGame()`

```javascript
// 1. Validate session code (if provided)
if (sessionCode) {
  const sessionData = await pool.query(
    'SELECT guild_id, category_id FROM sessions WHERE session_code = $1 AND storyteller_user_id = $2',
    [sessionCode, session.discord_user_id]
  );
  guildId = sessionData.rows[0].guild_id;
  categoryId = sessionData.rows[0].category_id;
}

// 2. Insert game record
const result = await pool.query(`
  INSERT INTO games (guild_id, category_id, script, custom_name, start_time, players, player_count, storyteller_id, is_active)
  VALUES ($1, $2, $3, $4, $5, $6, $7, $8, true) 
  RETURNING game_id
`, [...]);

// 3. Queue Discord announcement (if session linked)
if (guildId && categoryId) {
  await pool.query(`
    INSERT INTO announcements (guild_id, category_id, announcement_type, game_id, created_at)
    VALUES ($1, $2, 'game_start', $3, $4)
  `, [guildId, categoryId, gameId, timestamp]);
}
```

### Website: End Game

**File:** `grimlive/server/api.js` → `endGame()`

```javascript
// 1. Get game details for announcement
const gameData = await pool.query(
  'SELECT guild_id, category_id, script, custom_name, start_time, player_count FROM games WHERE game_id = $1',
  [gameId]
);

// 2. Update game record
await pool.query(`
  UPDATE games 
  SET end_time = $1, winner = $2, is_active = false, completed_at = $3
  WHERE game_id = $4
`, [endTime, winningTeam, endTime, gameId]);

// 3. Queue Discord announcement (if session linked)
if (gameData.rows.length && gameData.rows[0].guild_id) {
  await pool.query(`
    INSERT INTO announcements (guild_id, category_id, announcement_type, game_id, created_at)
    VALUES ($1, $2, 'game_end', $3, $4)
  `, [guild_id, category_id, gameId, timestamp]);
}
```

### Bot: Process Announcements

**File:** `grimkeeper/botc/announcements.py` → `AnnouncementProcessor`

```python
# Background loop (every 5 seconds)
async def _process_loop(self):
    while self.running:
        await self._process_pending_announcements()
        await asyncio.sleep(5)

# Fetch pending announcements
async def _process_pending_announcements(self):
    announcements = await conn.fetch("""
        SELECT id, guild_id, category_id, announcement_type, game_id
        FROM announcements 
        WHERE processed = FALSE 
        ORDER BY created_at ASC
        LIMIT 10
    """)
    
    for announcement in announcements:
        await self._process_announcement(announcement)
        # Mark as processed
        await conn.execute(
            "UPDATE announcements SET processed = TRUE, processed_at = $1 WHERE id = $2",
            timestamp, announcement['id']
        )

# Process individual announcement
async def _process_announcement(self, announcement):
    # 1. Get guild, session, announce channel
    guild = self.bot.get_guild(guild_id)
    session = await self.session_manager.get_session(guild_id, category_id)
    announce_channel = await self._get_announce_channel(guild, session, category_id)
    
    # 2. Get game data from database
    game = await conn.fetchrow("SELECT * FROM games WHERE game_id = $1", game_id)
    
    # 3. Create embed (reuses logic similar to handlers.py)
    if announcement_type == 'game_start':
        embed = await self._create_game_start_embed_from_website(guild, game, session)
    elif announcement_type == 'game_end':
        embed = await self._create_game_end_embed_from_website(guild, game, session)
    
    # 4. Send to Discord
    await announce_channel.send(embed=embed)
```

### Bot: Announce Channel Selection

**File:** `grimkeeper/botc/announcements.py` → `_get_announce_channel()`

Priority order:
1. **Session announce channel** - Set by `/setbotc` or `/autosetup` (`sessions.announce_channel_id`)
2. **First text channel in category** - Any text channel bot can send to

Each category (session) has its own announcements - completely isolated.

## User Workflows

### Manual Discord Game (Original)

```
1. ST: /startgame trouble-brewing
2. Bot: "Are you sure? 15 players..."
3. ST: Clicks ✅ Confirm
4. Bot: "🎊 A New Tale Begins" embed in #announcements
5. ST: Plays game in Discord
6. ST: /endgame Good
7. Bot: "☀️ The Dawn Breaks" embed
```

### Website Game with Discord Stats

```
1. ADMIN (one-time setup): /autosetup or /setbotc in Discord
2. Bot: Creates persistent session with code "s1"
3. ST: Types *game to see the session code (same "s1" every time)
4. ST: Logs into grim.hystericca.dev with Discord OAuth
5. ST: Enters "s1" in session code field on website
6. ST: Clicks "Start Game" on website
7. Bot: "🎊 A New Tale Begins" embed in #announcements (no confirmation!)
8. ST: Plays game using website grimoire
9. ST: Clicks "End Game - Good" on website
10. Bot: "☀️ The Dawn Breaks" embed in Discord
11. Stats: Tracked in grimkeeper database ✅

--- Next game in same session ---

12. ST: Enters same "s1" code on website (session persists!)
13. ST: Plays another game, stats tracked to same Discord session
```

### Website Game without Discord (Also supported)

```
1. User: Visits grim.hystericca.dev (no Discord login)
2. User: Plays game using website grimoire
3. User: Ends game
4. Stats: Tracked locally only (no Discord announcements)
```

## Key Design Decisions

### Why a queue instead of webhooks?

**Pros:**
- ✅ No exposed endpoints on the bot
- ✅ Works even if bot temporarily offline
- ✅ Database already shared
- ✅ Reliable delivery (retries built-in)
- ✅ Simple to debug (can query the table)

**Cons:**
- ⏱️ 5-second delay (acceptable for announcements)

### Why not call Discord API directly from website?

Would require:
- Bot token exposed to website (security risk)
- Complex error handling for Discord API
- No retry logic if Discord down
- Tight coupling between systems

Current design keeps separation of concerns:
- Website: Web stuff + database writes
- Bot: Discord stuff + database reads

### Why store minimal data in announcements?

Queue only stores:
- Which guild/session (routing info)
- Which game (reference to full data)
- What type (start/end)

Full game data already in `games` table. No duplication = no sync issues.

## Deployment Checklist

### 1. Database Migration

```bash
cd grimkeeper
psql $DATABASE_URL < migrations/017_add_announcements_queue.sql
```

Verify:
```sql
SELECT * FROM announcements LIMIT 1;
```

### 2. Deploy Website

```bash
cd grimlive/grimlive
bun run vite build
# Deploy to Cloudflare Pages
scp server/api.js server/index.js ubuntu@3.101.142.133:/home/ubuntu/grimlive-server/server/
ssh ubuntu@3.101.142.133 'cd /home/ubuntu/grimlive-server/server && systemctl restart grimlive-server'
```

### 3. Deploy Bot

```bash
cd grimkeeper
# Commit changes
git add .
git commit -m "Add website announcement processor"
git push

# On server
ssh your-bot-server
cd grimkeeper
git pull
pm2 restart grimkeeper
# or
systemctl restart grimkeeper
```

### 4. Verify

Test sequence:
1. Run `/setbotc` in Discord → Check session code appears
2. Log into website with Discord OAuth
3. Enter session code on website
4. Click "Start Game"
5. **Within 5 seconds:** Announcement appears in Discord ✅

Check logs:
```bash
# Bot logs
tail -f grimkeeper/discord.log | grep "announcement"

# Website logs  
journalctl -u grimlive-server -f | grep "announcement"
```

## Troubleshooting

### Announcements not appearing

**Check 1:** Is announcement processor running?
```python
# In bot logs, should see:
# "Announcement processor started"
```

**Check 2:** Are announcements being queued?
```sql
SELECT * FROM announcements WHERE processed = FALSE ORDER BY created_at DESC;
```

**Check 3:** Can bot send to announce channel?
```sql
-- Get session announce channel
SELECT announce_channel_id FROM sessions WHERE session_code = 's1';
```
Verify bot has "Send Messages" permission in that channel.

**Check 4:** Is session linked correctly?
```sql
-- Does session exist with correct storyteller?
SELECT * FROM sessions WHERE session_code = 's1';
```

### Announcements delayed

- Normal: Up to 5 seconds delay (background task interval)
- If longer: Check bot connectivity to database
- Check bot CPU/memory (background task may be blocked)

### Duplicate announcements

Should never happen (processed flag prevents it), but if it does:
```sql
-- Find duplicates
SELECT game_id, COUNT(*) FROM announcements 
GROUP BY game_id HAVING COUNT(*) > 1;

-- Mark duplicates as processed
UPDATE announcements SET processed = TRUE 
WHERE id IN (
    SELECT id FROM announcements WHERE game_id = X AND processed = FALSE
    ORDER BY created_at ASC OFFSET 1
);
```

### Wrong channel

Announcement going to wrong text channel?

**Solution:** Set proper announce channel with `/setbotc`:
```
/setbotc
> Announce Channel: #game-announcements
```

This sets `sessions.announce_channel_id` to ensure announcements go to the right place.

## Future Enhancements

### Possible additions:

1. **Player join/leave notifications** - Website → Discord when players added/removed mid-game
2. **Timer sync** - Website sets timer → Bot announces in Discord
3. **Role reveals** - End game with role list → Bot shows in rich embed
4. **Grimoire link in website announcements** - Click to view on website
5. **Reaction controls** - React to announcement to end game, add player, etc.

### Performance considerations:

- Current: 5-second polling
- If high volume: Consider PostgreSQL NOTIFY/LISTEN for instant updates
- If many guilds: Consider per-guild announcement channels to reduce query load

## Related Files

- `grimlive/server/api.js` - Website API endpoints
- `grimkeeper/botc/announcements.py` - Announcement processor
- `grimkeeper/botc/handlers.py` - Discord /startgame and /endgame handlers
- `grimkeeper/botc/session.py` - Session management
- `grimkeeper/botc/cogs/commands.py` - *game command (shows session code)
- `grimkeeper/migrations/017_add_announcements_queue.sql` - Database schema
- `grimkeeper/main.py` - Bot initialization
- `grimkeeper/botc/cogs/events.py` - Bot startup (starts announcement processor)
