# Contributing

Thanks for checking this out. Here's how you can help:

## How to Contribute

### Bug Reports

Check existing issues first to avoid duplicates. Include these details:

**Bug Report Template:**
```
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. Do action '...'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- Bot version: [e.g. 1.3.1]
- Python version: [e.g. 3.10]
- Database: [e.g. PostgreSQL 15 local/RDS]
- Discord server size: [e.g. 50 members]
- Hosting: [e.g. AWS EC2, local]

**Additional context**
Any other context about the problem.
```

### Feature Requests

Before suggesting something:

1. Check if someone already asked for it
2. Make sure it actually fits a BOTC utility bot
3. Think about how it'd work with what's already there

**Feature Request Template:**
```
**Is your feature related to a problem?**
A clear description of the problem. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Any other context, screenshots, or examples.
```

### Pull Requests

1. Fork the repo and create your branch from `main`
2. Test your changes thoroughly
3. Follow the existing code style
4. Update docs if needed
5. Write clear commit messages

**Process:**

1. **Test your changes**
   ```bash
   python3 -m py_compile main.py  # Syntax check
   # Test all modified commands in a Discord server
   ```

2. **Update version and changelog**
   - Increment version appropriately (see Versioning below)
   - Add entry to `changelog.json`
   - Update `VERSION` in `botc/constants.py`

3. **Code style**
   - Use 4 spaces for indentation
   - Follow existing naming conventions (`snake_case` for functions)
   - Add comments for complex logic
   - Keep functions focused and readable

4. **Commit messages**
   ```
   Good: "Fix: Timer persistence not saving on cancel"
   Good: "Feature: Add *night and *day announcements"
   Bad: "fixed stuff"
   Bad: "update"
   ```

## Development Setup

1. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/grimkeeper.git
   cd grimkeeper
   ```

2. **Create a test Discord server**
   - Create a fresh server for testing
   - Create BOTC category and channels
   - Invite your bot

3. **Set up environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Add your test bot token to .env
   ```

4. **Run the bot**
   ```bash
   python3 main.py
   ```

5. **Test thoroughly**
   - Test all modified commands
   - Test edge cases (missing permissions, invalid input, etc.)
   - Check logs for errors

## Code Organization

### File Structure
- `main.py` - Bot entrypoint and event handlers
- `botc/` - Core bot package
  - `constants.py` - Version and constants
  - `database.py` - PostgreSQL operations
  - `session.py` - Multi-session management
  - `wiki.py` - BOTC wiki integration
  - `polls.py` - Poll creation logic
  - `timers.py` - Timer management
  - `utils.py` - Helper functions
  - `cogs/` - Command handlers (slash, polls, timers, commands)
- `migrations/` - Database schema migrations (001-005)
- `docs/` - Documentation
- `tests/` - Test files

### Key Sections in main.py
1. **Imports and setup** - Dependencies and bot initialization
2. **Helper functions** - Utility functions used by commands
3. **Event handlers** - `on_ready`, `on_message`, `on_voice_state_update`, etc.
4. **Cog loading** - Loads command cogs on startup

### Adding a New Command

1. **Add command to delete list**
   ```python
   if content_lower.split()[0] in ["*!", "*st", ..., "*yourcommand"]:
   ```

2. **Add command handler**
   ```python
   if content_lower.startswith("*yourcommand"):
       # Your logic here
       msg = await message.channel.send("Response")
       await msg.delete(delay=3)
       return
   ```

3. **Add to help command**
   ```python
   embed.add_field(
       name="Section",
       value=(
           ...
           "`*yourcommand` — description\n"
       )
   )
   ```

4. **Update changelog**

## Versioning

We use semantic versioning: `MAJOR.MINOR.PATCH`.

- **PATCH** (bug fixes, small improvements) - e.g., 1.3.0 → 1.3.1
- **MINOR** (new features, backward compatible) - e.g., 1.2.0 → 1.3.0  
- **MAJOR** (breaking changes) - e.g., 1.x.x → 2.0.0

Current version: 1.3.1

## Testing Checklist

Before submitting a PR, verify:

- [ ] Code passes syntax check: `python3 -m py_compile main.py botc/*.py botc/cogs/*.py`
- [ ] All modified commands tested in Discord
- [ ] Error cases handled (missing permissions, invalid input, database errors)
- [ ] Logs checked for errors
- [ ] Database migrations tested if schema changed
- [ ] Documentation updated if needed
- [ ] `changelog.json` updated
- [ ] Version bumped in `botc/constants.py`
- [ ] No sensitive data in commits (tokens, IDs, passwords, etc.)

## Style Guide

### Python Style
- Follow PEP 8 where reasonable
- Use descriptive variable names
- Add docstrings to complex functions
- Keep functions under 50 lines when possible

### Discord Messages
- Use embeds for structured data
- Auto-delete temporary messages (2-5s)
- Keep permanent messages for important info
- Use clear language

### Error Messages
- Tell users what went wrong
- Suggest how to fix it
- Auto-delete after 3-5 seconds
- Log detailed errors for debugging

### Comments
```python
# Good: Explain WHY, not WHAT
# We clear backups on startup because caps might have been manually
# adjusted while bot was offline, preventing incorrect restoration
channel_limit_backups.clear()

# Bad: Obvious comments
# Clear the channel limit backups
channel_limit_backups.clear()
```

## Questions?

- Open an issue for discussion
- Contact `hystericca` on Discord
- Check existing issues and docs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
