# Grimkeeper Technical Cheat Sheet

Quick reference for explaining the bot's architecture and implementation.

---

## High-Level Architecture

**Pattern**: Event-driven microservice using Discord.py framework
**Structure**: Cog-based modular architecture with async I/O throughout
**State**: PostgreSQL as source of truth, in-memory caching for hot paths

```
Discord API → Bot Core → Cogs (Commands/Events) → Business Logic → Database
```

---

## Key Technical Concepts

### 1. Async/Await Pattern
**Why**: Discord API is I/O-bound - async prevents blocking on network calls
**Example**: `async def call_townspeople()` - moves users in parallel batches
**Optimization**: `asyncio.gather()` for concurrent operations (15 users/batch, 80ms delay)

### 2. Session Management
**Problem**: Multiple games per server need isolation
**Solution**: Category-scoped sessions (each Discord category = independent game)
**Data Structure**: SessionManager with cache: `{(guild_id, category_id): Session}`
**Persistence**: Database-backed with lazy loading

### 3. Database Layer
**Stack**: asyncpg (connection pooling), PostgreSQL 12+
**Pattern**: Connection pool (min: 2, max: 10 connections)
**Why async**: Non-blocking queries during Discord API calls
**Migration system**: Versioned SQL files, auto-applied on startup

### 4. Cog Architecture
**Purpose**: Modular command handling with lifecycle management
**Structure**:
- `events.py` - Voice state changes, member updates
- `slash.py` - Slash command registration
- `commands.py` - Prefix commands (*help, *st, etc.)
- `timers.py` - Scheduled operations

**Loading**: `bot.load_extension()` in setup_hook (pre-connection)

---

## Core Systems Explained

### Rate Limiting
```python
command_cooldowns: dict[int, dict[str, float]]  # user_id -> {command: timestamp}
```
Per-user, per-command cooldowns using `time.time()` timestamps. O(1) lookup.

### Shadow Following (Spectator System)
```python
follower_targets: dict[int, int]  # follower_id -> target_id
```
Event-driven: `on_voice_state_update` triggers follower moves. Database-persisted for crash recovery.

### Batch User Movement
**Challenge**: Discord rate limits (can't move 20 users instantly)
**Solution**: Async batching with `asyncio.gather()`
```python
BATCH_SIZE = 15
results = await asyncio.gather(*[move_member(m) for m in batch])
```
Processes moves concurrently within rate limit constraints.

### Timer Persistence
**Storage**: Database with Unix timestamps
**Recovery**: On restart, calculate remaining time: `end_time - current_time`
**Execution**: asyncio.sleep() with background tasks

---

## Data Flow Examples

### Starting a Game:
```
User: /startgame
→ SlashCog receives interaction
→ start_game_handler() validates session
→ Database: INSERT game record
→ SessionManager: update active_game_id
→ Discord: Send embed
```

### Moving Users (*call):
```
User: *call
→ TimersCog receives message
→ call_townspeople() gets session config
→ Collect members from voice channels (filter bots/STs)
→ asyncio.gather() moves in parallel batches
→ Return count
```

---

## Performance Optimizations

1. **Dictionary.setdefault()** instead of manual key checks
2. **Single-pass aggregation** for stats (was O(n²), now O(n))
3. **List comprehensions** over nested loops where possible
4. **Connection pooling** prevents per-query connection overhead
5. **In-memory caching** for session lookups (fallback to DB)

---

## Error Handling Strategy

**Custom exceptions**: `ConfigurationError`, `DatabaseError`, `ValidationError`
**Pattern**: Try/catch at API boundaries, log all errors, graceful degradation
**Example**: Missing permissions → helpful error message, don't crash

---

## Production Considerations

**Deployment**: systemd service on Linux
**Logging**: File-based (`discord.log`) with level-based filtering
**Environment**: `.env` file for secrets (never committed)
**Migrations**: Automatic version tracking, idempotent SQL

---

## Quick Talking Points

**"Why async Python?"**
→ I/O-bound application (Discord API, database). Async allows handling multiple requests without blocking. Single-threaded but concurrent.

**"How do you handle crashes?"**
→ Timers and follower state are database-persisted. On restart, reconstruct in-memory state from DB.

**"Why PostgreSQL over SQLite?"**
→ Connection pooling, concurrent writes, JSONB support, better for production deployment.

**"How do you prevent race conditions?"**
→ Database transactions, immutable dataclasses, single event loop (no threading).

**"Biggest challenge?"**
→ Managing multi-session state isolation while keeping data consistent across crashes/restarts.

---

## Code Metrics

- **Lines of code**: ~1,560 (main.py), ~5,000+ total
- **Modules**: 12+ (cogs, database, session, timers, utils, handlers, etc.)
- **Database tables**: 9 (sessions, games, timers, followers, etc.)
- **Concurrent operations**: Batch processing, connection pooling, async everywhere
- **Error handling**: Custom exception hierarchy, comprehensive logging

---

## If Asked to Explain a Function

**Pick `call_townspeople()`**:
1. Get session config from database (which category, which destination)
2. Check permissions (can bot move users?)
3. Collect members from voice channels (filter bots/STs/already-in-destination)
4. Define async helper: `move_member()` with error handling
5. Process in batches of 15 with `asyncio.gather()`
6. Return move count

**Why interesting**: Demonstrates async patterns, error handling, batch processing, database interaction, Discord API usage.
