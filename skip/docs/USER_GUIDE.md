# User Guide

Complete command reference and setup guide for Grimkeeper.

## Setup

### Initial Configuration (Admin Only - One Time)

1. Invite the bot to your server
2. **Admin** runs `/autosetup` to create channels automatically, or:
   - `/setbotc <category>` - Create a session for a specific category
   - `/settown #channel` - Set town square channel for that session

**Important:** Sessions are persistent infrastructure. Once created, they exist forever until deleted. You never need to run `/setbotc` again for that category.

### Multiple Sessions

To run multiple simultaneous games:
- **Option 1:** Run `/autosetup` again (creates another gothic-themed category)
- **Option 2:** Create a new category manually, then run `/setbotc <new-category>` from a channel inside it

Each session has its own:
- Session code (s1, s2, s3...)
- Grimoire link
- Town square channel
- Game history
- Active timers

---

## Commands

### Everyone

**Basic:**
- `*!` - Toggle spectator mode
- `*brb` - Toggle away status
- `*players` - List active players
- `*timer` - Check timer status
- `*help` - Command reference
- `*stguide` - Storyteller guide

**Game:**
- `*consult` - Request ST consultation (during game)
- `/character <name>` - Look up character info
- `/stats` - Server statistics
- `/gamehistory` - Recent games

### Storyteller

**Session:**
- `*st` - Claim/unclaim Storyteller role
- `*cost` - Toggle Co-Storyteller role
- `*g <link>` - Set grimoire link

**Game Control:**
- `*call` - Move everyone to town square
- `*mute` - Server mute all players
- `*unmute` - Unmute all players
- `*night` - Announce nighttime
- `*day` - Announce morning

**Timers:**
- `*timer <duration>` - Schedule delayed call
- `*5m` - Shorthand (also `*1h30m`, etc.)

**Voting:**
- `*poll [123ch]` - Create script poll

**Tracking:**
- `/startgame <script>` - Start tracking game
- `/endgame <winner>` - End game, record result
- `/addplayer @user` - Add player to active game
- `/removeplayer @user` - Remove player from game
- `/ststats [@user]` - View ST statistics

### Spectator

- `*spec @user` - Shadow follow a player
- `*unspec` - Stop following
- `*shadows` - View all followers
- `*dnd` - Prevent being followed
- `*join @user` - Join someone's voice channel once

### Admin

**Configuration:**
- `/setbotc <category>` - Configure BOTC category
- `/settown #channel` - Set town square
- `/setexception #channel` - Set private ST channel
- `/autosetup` - Auto-create server structure
- `/setadmin <role>` - Add admin role

**Management:**
- `/sessions` - List active sessions
- `/sessions cleanup` - Remove inactive sessions
- `/deletegame <number>` - Delete specific game
- `/clearhistory` - Clear all game history
- `*changelog` - View version history

---

## How It Works

### Sessions

Sessions are tied to categories. Each session has:
- Independent grimoire links
- Separate timers
- Own game tracking
- Session-specific settings

Multiple sessions per server are supported.

### Prefixes

The bot adds prefixes to nicknames:
- `(ST)` - Storyteller
- `(Co-ST)` - Co-Storyteller  
- `!` - Spectator
- `[BRB]` - Away

Spectator, ST, and Co-ST are mutually exclusive. BRB stacks with others.

### Voice Channels

When ST/Co-ST/Spectators join a capped voice channel, the bot increases the limit so players aren't blocked. Limits reset when privileged users leave.

### Shadow Following

Spectators can follow players between voice channels:
1. Use `*spec @player`
2. When player moves, you move automatically
3. Use `*unspec` to stop
4. Players can use `*dnd` to prevent followers

### Timers

Schedule automatic town square calls:
- `*timer 5m` - Call everyone in 5 minutes
- `*1h30m` - Shorthand format
- `*timer` - Check status
- `*timer cancel` - Cancel timer

Timers persist across bot restarts.

### Game Tracking

Track games for statistics:
1. `/startgame <script>` - Start tracking (requires active session)
2. Game runs
3. `/endgame Good/Evil/Cancelled` - Record result

Stats tracked:
- Games played
- Win rates
- Script breakdowns
- Player participation

---

## Troubleshooting

**Bot doesn't respond:**
- Check bot has message permissions
- Verify bot is online

**Can't move users:**
- Bot needs "Move Members" permission
- Users must be in voice channels

**Commands fail:**
- Ensure session is configured (`/setbotc`)
- Check you have required role (ST/Admin)
- Verify active game exists (for game commands)

**Voice caps not adjusting:**
- Bot needs "Manage Channels" permission
- Run `/setbotc` again to update snapshot

---

## Support

- Bug reports: [GitHub Issues](https://github.com/gorewife/grimkeeper/issues)
- Questions: Contact `hystericca` on Discord
