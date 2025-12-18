# Translation Guide for Grimkeeper

## How to Translate

1. **Copy `en.json`** to a new file named with your language code (e.g., `es.json` for Spanish, `fr.json` for French)
2. **Translate only the values** (text after the `:`) - do NOT change the keys (text before the `:`)
3. **Keep special characters** like emojis (🍺, 🪻, etc.) and formatting markers (**, `, etc.)
4. **Keep placeholders** if you see any (they'll look like `{variable}`)

## Example

**English (en.json):**
```json
"good_win": "Good triumphs! The town is safe... for now."
```

**Spanish (es.json):**
```json
"good_win": "¡El bien triunfa! La ciudad está a salvo... por ahora."
```

## What NOT to Change

❌ Don't translate:
- Key names (left side of `:`)
- File structure (`{`, `}`, `,`)
- Command names in descriptions (like `/startgame`, `*call`)
- Technical terms (BOTC, grimoire)

✅ Do translate:
- All user-facing text
- Button labels
- Error messages
- Descriptions

## Supported Languages

Current translations:
- `en.json` - English (default)

To add your language, copy `en.json` and translate all the values!

## Testing

Once you create a translation file, send it to the developer and they'll add language selection to the bot.

## Questions?

If you're unsure about translating something, leave it in English with a comment like:
```json
"_comment": "Not sure how to translate 'grimoire' - is there a Spanish equivalent?",
"grimoire": "grimoire"
```
