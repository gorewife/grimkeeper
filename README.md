# Grimkeeper

![Grimkeeper Banner](https://github.com/gorewife/grimkeeper/blob/main/assets/GRIMKEEPER.png)

<div align="center">

![Version](https://img.shields.io/badge/version-1.7.3-222?style=flat-square&logo=github&logoColor=white)
![Discord](https://img.shields.io/discord/1440582976995069984?style=flat-square&logo=discord&logoColor=white&color=222&label=&labelColor=222)
![GitHub Repo stars](https://img.shields.io/github/stars/gorewife/grimkeeper?style=flat-square&label=&color=222&logo=github&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-222?style=flat-square&logoColor=white)
![Python](https://img.shields.io/badge/python-3.8+-222?style=flat-square&logo=python&logoColor=white)
![Discord.py](https://img.shields.io/badge/discord.py-latest-222?style=flat-square&logo=discord&logoColor=white)

</div>

---

A Discord bot for Blood on the Clocktower games. Manages voice channels, tracks spectators, handles timers, and keeps your grimoire links organized. Made by someone who got tired of manually moving people to Town Square.

## What it does

**Session Management:**
- Run multiple concurrent games in different categories on the same server
- Automatic session detection and isolation
- Session-specific grimoires, timers, and announcements

**Voice & Nickname Management:**
- Adds prefixes to nicknames (ST, Co-ST, spectator, BRB)
- Automatically expands voice channels when storytellers join
- Moves everyone to Town Square with `*call` or schedule with `*timer`
- Spectators can shadow-follow players between voice channels

**Game Tracking & Stats:**
- Track games with `/startgame` and `/endgame`
- Server-wide and per-storyteller statistics
- Game history with win rates and script breakdowns
- Automatic player tracking by Discord ID

**Character Reference:**
- `/character` lookup with full wiki integration
- Interactive sections: Summary, Tips & Tricks, Bluffing, How to Run
- Character icons and team-based color coding

**Utilities:**
- Timers that survive bot restarts
- Script polls with automatic tallying
- Basic rate limiting

---

## Quick Start

### 1. Add the bot

<a href="https://discord.com/oauth2/authorize?client_id=1424573592557064292&permissions=151021648&integration_type=0&scope=bot+applications.commands" target="_blank">
  <img src="https://img.shields.io/badge/Invite%20Grimkeeper%20Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white&labelColor=222&color=5865F2" alt="Invite Grimkeeper"/>
</a>

Permissions needed:
- Manage Nicknames
- Move Members
- Manage Channels
- Manage Messages
- Send Messages
- Embed Links
- Add Reactions
- Read Message History

### 2. Set it up

Run these (admin only):

```
/setbotc Blood on the Clocktower
/settown #town-square
```

**What `/setbotc` does:** Creates a session for that category - this is how the bot knows which categories are used for BOTC games.

Or just use `/autosetup` to create everything automatically.

**💡 Pro Tip:** You can run `/setbotc` on multiple categories to create multiple BOTC sessions on the same server! Each session runs independently with its own channels, timers, and games.

### 3. You're good

Type `*help` to see all commands.

---

## Commands

### 👥 Everyone
- `*!` - Toggle spectator mode
- `*brb` - Toggle away status  
- `*players` - List active players and see who joined/left
- `*timer` - Check active timer status
- `*help` - Show command reference
- `*stguide` - Storyteller's guide to using the bot
- `*consult` - Request ST consultation (active game only)
- `/character <name>` - Look up character info (case-insensitive)
- `/stats` - View server game statistics
- `/gamehistory` - View recent games

### 📋 Storyteller Only
- `*st` - Claim/unclaim Storyteller role
- `*cost` - Toggle Co-Storyteller role
- `*g <link>` - Set grimoire link (session-scoped)
- `*call` - Move everyone to town square (requires active game)
- `*mute` - Server mute all players, excluding storytellers (requires active game)
- `*unmute` - Unmute all players
- `*timer <duration>` - Schedule a delayed call (requires active game)
- `*<duration>` - Shorthand timer (e.g., `*5m`, `*1h30m`)
- `*night` - Announce nighttime (requires active game)
- `*day` - Announce morning (requires active game)
- `*poll [123ch]` - Create script poll
- `/startgame <script>` - Start tracking a game (with player confirmation)
- `/endgame <winner>` - End game and record result
- `/addplayer @user` - Add player to active game
- `/removeplayer @user` - Remove player from active game
- `/storytellerstats [@user]` - View ST stats (user stats are bot-wide)

### 👻 Spectator Only
- `*spec @user` - Shadow follow a player
- `*unspec` - Stop following
- `*shadows` - View all active followers
- `*dnd` - Prevent being followed
- `*join @user` - Join someone's voice channel (one-time)

### ⚙️ Admin Only
- `/setbotc <category>` - Configure BOTC category
- `/settown #channel` - Set town square channel
- `/setexception #channel` - Set private ST channel
- `*changelog` - View version history
- `/sessions` - List all active sessions
- `/sessions cleanup` - Remove inactive sessions
- `/autosetup` - Auto-create gothic server structure (can run multiple times for multiple sessions)
- `/deletegame <number>` - Delete specific game from history
- `/clearhistory` - Clear all game history

---
## Documentation

- [📖 DOCUMENTATION.md](docs/DOCUMENTATION.md) - User guide and command reference

## Support

- Bug reports & feature requests: [Open an issue](https://github.com/gorewife/grimkeeper/issues)
- Questions: Contact `hystericca` on Discord

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimers

Bot profile image and artwork © Riot Games, Inc. Grimkeeper is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties.

Grimkeeper is a community-created Discord bot and is not affiliated with or endorsed by Blood on the Clocktower or The Pandemonium Institute.

---

**Version**: 1.7.3 | **Maintainer**: hystericca

pip install asyncpg