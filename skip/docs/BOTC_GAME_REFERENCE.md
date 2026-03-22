# Blood on the Clocktower - Game Reference for Discord Bot Development

**Purpose**: This document provides comprehensive Blood on the Clocktower game knowledge for bot development, adapted for online/Discord gameplay instead of in-person mechanics.

**Last Updated**: December 30, 2025

---

## Core Game Concepts

### Alignment & Teams
- **Good Team** (Blue): Townsfolk + Outsiders
  - Goal: Execute the Demon to win
  - Majority of players
  - Don't know each other at start
  - Must use abilities and deduction to find evil
  
- **Evil Team** (Red): Minions + Demon
  - Goal: Reduce alive players to 2 (one must be Demon)
  - Know each other from start
  - Demon gets 3 "not in play" characters for bluffing

### Character Types
1. **Townsfolk** - Good characters with helpful abilities
2. **Outsider** - Good characters with harmful/unhelpful abilities
3. **Minion** - Evil characters that support the Demon
4. **Demon** - Evil character whose death ends the game (good wins)
5. **Traveller** - Special characters for late joiners (can be any alignment)
6. **Fabled** - Neutral characters added by Storyteller for special circumstances

### Win Conditions
- **Good wins**: When the Demon dies
- **Evil wins**: When only 2 players remain alive (excluding Travellers)
- All players on a team win/lose together (no individual victories)

---

## Character States

### Drunk
- **What it means**: Player thinks they have a Townsfolk ability, but they don't
- **How it works**: 
  - Player is secretly an Outsider (Drunk character)
  - They receive a Townsfolk token at game start
  - Their ability never works
  - Storyteller may give them false information
  - They do NOT know they are drunk
- **Setup**: Drunk token removed, Townsfolk token added to bag instead
- **Detection**: Characters checking the Drunk see their actual character (Drunk/Outsider), not what they think they are

### Poisoned
- **What it means**: Player's ability temporarily doesn't work
- **How it works**:
  - Same as drunk (no ability, may get false info, doesn't know)
  - BUT it's temporary - typically lasts one night + following day
  - Applied by evil characters (Poisoner ability)
- **Key difference from drunk**: Poisoning can start/stop, drunk is permanent

### Alive vs Dead
- **Alive players**:
  - Have their ability (unless drunk/poisoned)
  - Can vote unlimited times
  - Can nominate once per day
  - Game continues while 3+ alive

- **Dead players**:
  - Immediately lose ability
  - Can vote only ONCE for rest of game
  - Cannot nominate
  - Persistent effects of their ability end

### Ability States
- **Characters have NO ability when**:
  - Dead
  - Drunk
  - Poisoned

---

## Game Flow (Adapted for Discord)

### Setup Phase
1. Storyteller determines player count and character distribution
2. Characters assigned privately (DM/private channels)
3. Evil team learns each other's identities
4. Demon receives "not in play" characters for bluffing

### Night Phase
- Players "close eyes" (private DMs/channels)
- Storyteller wakes characters in specific order
- Characters use their abilities
- Demon kills (usually)
- Phase ends at "dawn"

### Day Phase
- Public discussion in main channel
- Players share information and strategize
- **Nominations**: Alive players can nominate once per day
- **Voting**: Alive players vote unlimited times, dead vote once total
- **Execution**: Player with most votes (≥50% of alive) dies
- Maximum one execution per day (may be zero)

### Timing Keywords
- **First night**: The initial night phase only
- **Each night**: Every night phase
- **Each night***: Every night EXCEPT the first
- **Once per game**: Ability can only be used once, even if drunk/poisoned when used
- **Dusk**: Start of night (before most abilities)
- **Dawn**: End of night (after most abilities)

---

## Critical Mechanics

### Registration
- Players can "register as" a different character/alignment
- This affects how other abilities see them
- Does NOT give them that character's ability
- Example: Good player registering as evil still wins with good team, but appears evil to detection abilities

### Information Reliability
- **True info**: Always given for game rules
- **False info**: May be given when ability malfunctions (drunk/poisoned)
- **"May/Might"**: Storyteller chooses whether effect happens

### Execution vs Exile
- **Execution**: Voting process for normal players, max 1 per day
- **Exile**: Separate process for Travellers, unlimited per day
- Exile is NOT a vote and abilities don't affect it

### Nomination & Voting Rules
- Alive players nominate once per day
- Players can be nominated once per day
- Alive players vote unlimited times
- Dead players vote exactly once (entire game)
- Execution requires ≥50% of alive players AND most votes
- Votes counted clockwise, ending with nominee

---

## Alignment Changes (RARE)

Only specific characters can change alignment during the game:

### Politician
- Starts good
- Can become evil during game (via ability)

### Goon  
- Starts good (Outsider)
- Becomes evil if drunk or poisoned

**Important**: 
- Alignment change ≠ character change
- A player's character stays the same when alignment changes
- Alignment and character are separate properties
- Most characters NEVER change alignment

---

## Discord/Online Adaptations

### In-Person → Discord Translations

| In-Person Mechanic | Discord Equivalent |
|-------------------|-------------------|
| Eyes closed | Private DMs/hidden channels |
| Whispering | Private DMs between players |
| Physical tokens | Bot commands/embeds |
| Storyteller waking players | Bot DMs with prompts |
| Town Square | Main game channel |
| Showing character tokens | Sending images/embeds |
| Grimoire | Bot's database state |
| Voting with hands | React with emojis or bot commands |

### Key Discord Considerations

1. **Privacy**: Use DMs or private channels for night actions
2. **Timing**: Async or scheduled phases (not instant like in-person)
3. **Information**: Embeds and formatted messages replace physical tokens
4. **Voting**: Reactions or commands replace hand-raising
5. **Nominations**: Commands or reactions replace verbal declarations
6. **Death**: Role changes, muting, or channel permissions
7. **Game State**: All tracked in bot database (replaces physical Grimoire)

---

## Common Ability Patterns

### Information-Gathering
- **Start knowing**: Info given first night OR when character created
- **Each night**: Repeated info every night
- **Learn**: Player gains specific knowledge
- **Choose**: Player decides; if absent, Storyteller decides

### Active Abilities
- **Choose a player**: Ability targets someone
- **Might**: Storyteller decides if effect occurs
- **Once per game**: Single use, even if drunk/poisoned

### Persistent Effects
- End immediately when player dies
- Continue while alive (unless ability states otherwise)

---

## Character Distribution by Player Count

Grimkeeper tracks character counts automatically, but for reference:

| Players | Townsfolk | Outsiders | Minions | Demons |
|---------|-----------|-----------|---------|--------|
| 5 | 3 | 0 | 1 | 1 |
| 6 | 3 | 1 | 1 | 1 |
| 7 | 5 | 0 | 1 | 1 |
| 8 | 5 | 1 | 1 | 1 |
| 9 | 5 | 2 | 1 | 1 |
| 10 | 7 | 0 | 2 | 1 |
| 11 | 7 | 1 | 2 | 1 |
| 12 | 7 | 2 | 2 | 1 |
| 13 | 9 | 0 | 3 | 1 |
| 14 | 9 | 1 | 3 | 1 |
| 15 | 9 | 2 | 3 | 1 |

**Modifiers**: Some characters (like Baron) change Outsider count

---

## Important for Stats Tracking

### What to Track
- **Role**: Character name (e.g., "Washerwoman", "Imp")
- **Team**: Character's default team (townsfolk/outsider/minion/demon)
- **Alignment**: Player's actual alignment at game end (good/evil)
- **Survived**: Did player survive to end?
- **Winning Team**: Was player on winning team?

### Alignment vs Team
- **Team** = Character type category (never changes)
- **Alignment** = Good or evil (rarely changes: Politician, Goon)
- Track BOTH for accurate statistics

### Special Cases
- Drunk: Sees Townsfolk, but actually Outsider
- Travellers: Don't count toward win conditions
- Fabled: Neutral, don't count for any team
- Dead players: Still win/lose with their team

---

## Bot Command Considerations

### Game Start
- Validate character distribution
- Track starting roles and alignments
- Initialize night action queues
- Set up private channels/DMs

### Game End
- Record final roles (may differ from start)
- Record final alignments (may differ from start) 
- Calculate winning team
- Mark survivors
- Store all player stats

### During Game
- Track deaths and ability status
- Handle drunk/poisoned states
- Manage night action order
- Validate nominations/votes
- Process executions

---

## Edge Cases & Jinxes

**Jinxes**: Special rules that apply when certain character combinations exist in the same game. These prevent broken interactions.

**Example Jinx**: Some characters interact in ways that would break the game, so official rules modify how they work together.

**For Bot Development**: 
- Store jinx rules in database
- Check active characters against jinx list
- Display relevant jinxes to Storyteller at game start
- Reference: https://wiki.bloodontheclocktower.com/Jinxes

---

## Quick Reference

### Core Rules
1. Good wins when Demon dies
2. Evil wins at 2 alive players
3. Max 1 execution per day
4. Dead players vote once (total)
5. Abilities don't work when dead/drunk/poisoned

### States to Track
- Alive/Dead
- Drunk/Sober  
- Poisoned/Healthy
- Character
- Alignment
- Team

### Information Flow
- Evil knows each other from start
- Good must discover information
- Drunk/poisoned may receive false info
- Dead players lose abilities immediately

---

## Resources

- **Official Wiki**: https://wiki.bloodontheclocktower.com/
- **Wiki API**: https://wiki.bloodontheclocktower.com/api.php
- **Glossary**: https://wiki.bloodontheclocktower.com/Glossary
- **Character Database**: Stored locally in `assets/wiki_images/_metadata.json`
- **Script Tool**: https://script.bloodontheclocktower.com/

---

## Notes for Future Features

### Potential Tracking Enhancements
- [ ] Starting vs ending alignment (for Politician/Goon)
- [ ] Night-by-night ability usage logs
- [ ] Information received by each player
- [ ] Nomination/voting history
- [ ] Death details (who killed who, when, how)

### Deferred Complexity
- Mid-game role changes (rare, complex)
- Day-by-day state tracking
- Traveller special mechanics
- Fabled interactions

---

# CHARACTER COMPENDIUM

This section documents every character's ability, mechanical interactions, and storyteller tool implementation considerations.

---

## TROUBLE BREWING (Beginner Edition)

### Townsfolk (13 characters)

#### Washerwoman
**Ability**: "You start knowing that 1 of 2 players is a particular Townsfolk."

**Mechanics**:
- Triggers first night only
- Shown 2 players and 1 Townsfolk character
- One of the 2 players must have that character (unless drunk/poisoned)
- Can show dead players

**Key interactions**:
- **Spy registration**: May register as Townsfolk, allowing Spy to be shown
- **Recluse registration**: May register as Townsfolk, allowing Recluse to be shown  
- **Drunk**: Gets false info (neither player is that Townsfolk, OR both are, OR shown non-Townsfolk)
- **Pit-Hag**: If player's character changes after N1, Washerwoman info doesn't update
- **Philosopher**: If Philosopher gains Washerwoman ability, doesn't trigger (not "start")

**Storyteller tool implementation**:
- **Setup phase**: Auto-mark for Night 1 wake
- **Night 1 prompt**: "Select Townsfolk character → Select 2 players (one must be that character)"
- **Validation checks**: 
  - Verify one selected player actually has that character (unless Washerwoman drunk/poisoned)
  - If drunk/poisoned: Allow storyteller to provide completely false info
  - Flag if Spy in play (offer registration override)
  - Flag if Recluse in play (offer registration override)
- **State tracking**: Log given info {player1, player2, character} for storyteller reference
- **Character change handling**: If Pit-Hag changes either shown player, display reminder to storyteller that Washerwoman info is now potentially incorrect

---

#### Librarian
**Ability**: "You start knowing that 1 of 2 players is a particular Outsider. (Or that zero are in play.)"

**Mechanics**:
- Triggers first night only
- If 0 Outsiders in play: Shown "0"
- If 1+ Outsiders in play: Shown 2 players and 1 Outsider character, one of the 2 players must have that character (unless drunk/poisoned)
- Can show dead players

**Key interactions**:
- **Baron**: Adds +2 Outsiders at setup, makes "0" result impossible
- **Spy registration**: May register as Outsider, allowing Spy to be shown
- **Recluse registration**: May register as Outsider, allowing Recluse to be shown
- **Drunk**: Gets false info ("0" when Outsiders exist, OR shown players who aren't that Outsider, OR shown non-Outsider character)
- **Pit-Hag**: If creates Outsider after N1, Librarian info doesn't update
- **Godfather**: Modifies Outsider count at setup (+1 or -1)
- **Fang Gu/Vigormortis**: Modify Outsider count at setup

**Storyteller tool implementation**:
- **Setup phase**: Calculate Outsider count with setup modifications, auto-mark for Night 1 wake
- **Night 1 prompt**: 
  - If 0 Outsiders: "Show Librarian: 0 Outsiders in play"
  - If 1+ Outsiders: "Select Outsider character → Select 2 players (one must be that character)"
- **Validation checks**:
  - Verify Outsider count calculation includes Baron/Godfather/Demon setup modifiers
  - If drunk/poisoned: Allow storyteller to show "0" when Outsiders exist, or false players
  - Flag if Spy/Recluse in play (offer registration override)
- **State tracking**: Log given info for reference, display Outsider count vs expected count

---

#### Investigator
**Ability**: "You start knowing that 1 of 2 players is a particular Minion."

**Mechanics**:
- Triggers first night only
- Shown 2 players and 1 Minion character
- One of the 2 players must have that character (unless drunk/poisoned)
- Can show dead players

**Key interactions**:
- **Recluse registration**: May register as Minion, allowing Recluse to be shown
- **Spy registration**: Does NOT register as Minion (registers as good/Townsfolk/Outsider only)
- **Drunk**: Gets false info (neither player is that Minion, OR both are, OR shown non-Minion)
- **Pit-Hag**: If changes Minion's character after N1, Investigator info doesn't update
- **Vigormortis**: Dead Minions killed by Vigormortis keep abilities, still Minions for Investigator

**Storyteller tool implementation**:
- **Setup phase**: Auto-mark for Night 1 wake
- **Night 1 prompt**: "Select Minion character → Select 2 players (one must be that character)"
- **Validation checks**:
  - Verify one selected player is actually that Minion (unless Investigator drunk/poisoned)
  - If drunk/poisoned: Allow completely false info
  - Flag if Recluse in play (offer registration override)
  - Note: Spy should NOT be offered as registration option (can't register as Minion)
- **State tracking**: Log given info {player1, player2, character}
- **Character change handling**: Display reminder if Pit-Hag changes either shown player

---

#### Chef
**Ability**: "You start knowing how many pairs of evil players there are."

**Mechanics**:
- Triggers first night only
- "Pair" = 2 evil players sitting adjacent to each other
- Counts pairs, not individuals (3 evil in a row = 2 pairs)
- Dead players count for adjacency
- Travelers do NOT count for adjacency

**Key interactions**:
- **Spy registration**: If Spy registers as good, not counted as evil for pairs
- **Recluse registration**: If Recluse registers as evil, counted for pairs
- **Goon alignment change**: Uses alignment at N1, not later changes
- **Snake Charmer**: Uses alignment at N1, not later swaps
- **Drunk**: Gets false number (any number, not necessarily accurate)
- **Seating changes**: Uses setup seating only, not mid-game changes

**Storyteller tool implementation**:
- **Setup phase**: Auto-calculate evil pairs from seating order at game start
- **Night 1 prompt**: "Show Chef: [number] pairs of evil players" (auto-calculated)
- **Validation checks**:
  - Count adjacencies: Evil player next to evil player = pair
  - Exclude Travelers from calculation
  - Include dead players (if dead at setup, edge case)
  - If Spy: Offer option to have Spy register as good (reduces count)
  - If Recluse: Offer option to have Recluse register as evil (increases count)
  - If drunk/poisoned: Allow manual override of number
- **State tracking**: Display calculation breakdown for storyteller reference
- **Reminder**: Chef number never updates after N1, even if alignments/seating changes

---

#### Empath
**Ability**: "Each night, you learn how many of your 2 alive neighbors are evil."

**Mechanics**:
- Triggers every night (including first)
- "Neighbors" = closest alive player in each direction (clockwise/counterclockwise)
- Dead players are skipped when determining neighbors
- Travelers count as neighbors
- Returns number 0, 1, or 2

**Key interactions**:
- **Spy registration**: If Spy registers as good, counted as good neighbor
- **Recluse registration**: If Recluse registers as evil, counted as evil neighbor
- **Drunk**: Gets false number (any of 0, 1, 2)
- **Goon/Snake Charmer**: Alignment changes affect count
- **Deaths**: Neighbor calculation updates when players die (skips to next alive)
- **Seating changes**: Uses current seating (if rules allow mid-game seating changes)
- **Pit-Hag**: If neighbor's character changes, may affect alignment → affects count

**Storyteller tool implementation**:
- **Each night prompt**: "Empath info: [auto-calculated number]" (display neighbors for verification)
- **Validation checks**:
  - Auto-calculate living neighbors from current game state
  - Count evil alignments among those 2 neighbors
  - Display neighbor names and alignments for storyteller verification
  - If Spy neighbor: Offer registration override (count as good)
  - If Recluse neighbor: Offer registration override (count as evil)
  - If drunk/poisoned: Allow manual override of number
- **State tracking**: Log nightly info {night#, left_neighbor, right_neighbor, evil_count}
- **Visual aid**: Highlight Empath and their 2 living neighbors in seating display
- **Night timing**: Calculate AFTER all deaths/resurrections resolve for that night

---

#### Fortune Teller
**Ability**: "Each night, choose 2 players: you learn if either is a Demon. There is a good player that registers as a Demon to you."

**Mechanics**:
- Triggers every night (including first)
- Chooses 2 players (can be alive or dead)
- Returns YES (at least one is Demon) or NO (neither is Demon)
- Red Herring: One good player chosen at setup who always registers as Demon
- Red Herring never changes throughout game

**Key interactions**:
- **Red Herring**: Fixed at setup, doesn't change if player dies/character changes
- **Recluse registration**: May ALSO register as Demon (separate from Red Herring)
- **Imp/Scarlet Woman**: If Demon changes players, FT detects new Demon
- **Fang Gu**: If Fang Gu jumps to Outsider, new player is Demon, old player is not
- **Snake Charmer**: If swap occurs, former Demon no longer registers, new Demon does
- **Drunk**: Still gets Red Herring false positives PLUS may get other false results
- **Spy registration**: Does NOT register as Demon (only good/Townsfolk/Outsider)
- **Philosopher**: If gains FT ability, DOES get Red Herring assigned

**Storyteller tool implementation**:
- **Setup phase**: "Select Red Herring player" (must be good, locks for entire game)
- **Each night prompt**: "Fortune Teller selects 2 players → Show result"
- **Auto-calculation**:
  - Check if either player is current Demon → YES
  - Check if either player is Red Herring → YES
  - Check if Recluse chosen: Offer registration override → YES
  - Otherwise → NO
  - If drunk/poisoned: Allow manual override
- **State tracking**: 
  - Display Red Herring player prominently
  - Log nightly choices {player1, player2, result}
  - Show current Demon for storyteller reference
- **Reminders**: 
  - Red Herring persists if they die/character changes
  - If Demon changes (Imp starpass, Fang Gu jump, Scarlet Woman), update current Demon marker
- **Visual aid**: Highlight Red Herring and current Demon in player list

---

#### Undertaker
**Ability**: "Each night*, you learn which character died by execution today."

**Mechanics**:
- Triggers every night EXCEPT first
- Shows character of player executed during the previous day
- If no execution occurred that day: No info (or "no execution")
- If multiple executions (Virgin trigger): Shows most recent execution
- Shows actual character, not what player claims

**Key interactions**:
- **Spy registration**: May register as ANY character when executed
- **Recluse registration**: May register as evil character when executed
- **Drunk**: Shows the character Drunk thinks they are, NOT "Drunk"
- **Pit-Hag**: Shows character player had when executed, not original character
- **Barber/Philosopher**: Shows current character at time of execution
- **Poisoned**: Gets false character (any character, not necessarily in play)
- **Multiple executions**: If Virgin kills nominator, then Virgin executed → show Virgin

**Storyteller tool implementation**:
- **Each night* prompt**: "Show Undertaker: [executed character]" (auto-fill if execution occurred)
- **Auto-calculation**:
  - Check if execution occurred today → retrieve executed player's character
  - If Spy executed: Offer registration override (select any character)
  - If Recluse executed: Offer registration override (select Minion/Demon)
  - If Drunk executed: Show character Drunk THINKS they are
  - If no execution: Show "No execution today" or skip prompt
  - If drunk/poisoned: Allow manual character selection
- **State tracking**: 
  - Log {day#, executed_player, character_shown}
  - Link to day phase execution record
- **Validation**: Verify execution occurred before showing Undertaker prompt
- **Edge case**: If player's character changed before execution (Pit-Hag), show NEW character not old

---

#### Monk
**Ability**: "Each night*, choose a player (not yourself): they are safe from the Demon tonight."

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses one player (cannot choose self)
- Protected player cannot be killed by Demon ability this night
- Demon's ability "doesn't work" if targeting protected player
- No indication to Monk or protected player if protection triggered

**Key interactions**:
- **Imp starpass**: If Imp kills self to pass Demonhood, Monk protection does NOT prevent (self-targeting bypass)
- **Other deaths**: Does NOT protect from execution, Assassin, Witch, Godfather, Gossip, etc.
- **Drunk**: Provides no protection
- **Poisoned**: Provides no protection
- **Multiple Demons**: Protects from all Demon kills (Po, Shabaloth, etc.)
- **Tinker**: Does NOT protect Tinker from Storyteller arbitrary death
- **Assassin**: Does NOT block Assassin kill (bypasses protection)

**Storyteller tool implementation**:
- **Each night* prompt**: "Monk selects player to protect"
- **State tracking**: Mark selected player as "Monk-protected" for this night
- **Demon kill resolution**: 
  - When Demon chooses target, check if target has Monk protection
  - If protected AND Monk is sober/healthy: Demon kill fails (no death)
  - If Monk drunk/poisoned: Protection inactive, kill succeeds
  - If Imp targeting self: Bypass protection (starpass succeeds)
- **No feedback**: Do NOT indicate to Monk whether protection triggered
- **Validation**:
  - Prevent Monk from selecting self
  - Check Monk alive/sober/healthy status before applying protection
- **Visual aid**: Display Monk-protected player marker during night phase
- **Cross-edition**: If Po/Shabaloth, protection blocks ALL chosen targets for that Demon

---

#### Ravenkeeper
**Ability**: "If you die at night, you are woken to choose a player: you learn their character."

**Mechanics**:
- Triggers only on night death
- Immediately woken after dying (during same night phase)
- Chooses one player (can be alive or dead)
- Learns chosen player's actual character
- One-time ability (if resurrected and killed again, does NOT retrigger)

**Key interactions**:
- **Execution death**: Does NOT trigger (only night deaths)
- **Assassin/Godfather/Gossip**: These are night deaths, DO trigger
- **Tinker**: Night death, triggers Ravenkeeper
- **Spy registration**: May register as any character to Ravenkeeper
- **Recluse registration**: May register as Minion/Demon to Ravenkeeper
- **Drunk Ravenkeeper**: Triggers, but gets false character
- **Poisoned Ravenkeeper**: Triggers, but gets false character
- **Drunk target**: Shows character Drunk THINKS they are, not "Drunk"
- **Professor resurrection**: If Ravenkeeper resurrected after triggering, ability doesn't reset
- **Shabaloth regurgitation**: If killed and regurgitated, ability already used

**Storyteller tool implementation**:
- **Death detection**: If Ravenkeeper dies at night, flag for immediate wake
- **Immediate prompt**: "Ravenkeeper has died. They select a player → Show character"
- **Auto-calculation**:
  - Retrieve selected player's current character
  - If Spy: Offer registration override (select any character)
  - If Recluse: Offer registration override (select Minion/Demon)
  - If target is Drunk: Show character Drunk thinks they are
  - If Ravenkeeper drunk/poisoned: Allow manual character selection
- **State tracking**: 
  - Mark Ravenkeeper ability as "used" (prevents retriggering)
  - Log {died_night#, selected_player, character_shown}
- **Night order**: Ravenkeeper wake happens in night phase after death occurs
- **Visual aid**: Highlight that Ravenkeeper is dead but still acting this night
- **Edge case**: If resurrected (Professor/Shabaloth), ability remains "used" status

---

#### Virgin
**Ability**: "The 1st time you are nominated, if the nominator is a Townsfolk, they are executed immediately."

**Mechanics**:
- Triggers on first nomination of Virgin only
- If nominator is Townsfolk (or registers as Townsfolk): Nominator immediately executed
- Execution happens instantly, no trial or voting
- After first nomination, ability is spent (subsequent nominations don't trigger)
- Traveller nominations do NOT count/trigger

**Key interactions**:
- **Spy**: CAN trigger Virgin (Spy may register as Townsfolk)
- **Recluse**: Cannot trigger (registers as evil, not Townsfolk)
- **Drunk**: Does NOT trigger (not actually Townsfolk, despite thinking they are)
- **Poisoned Virgin**: Does NOT trigger when nominated
- **Drunk Virgin**: Ability doesn't work
- **Pacifist**: May prevent nominator's execution (Storyteller choice)
- **Devil's Advocate**: May prevent nominator's execution if protected
- **After trigger**: Virgin still alive, can still be nominated/executed normally

**Storyteller tool implementation**:
- **Setup**: Mark Virgin as "first nomination pending"
- **Day phase - Nomination event**: 
  - If Virgin nominated AND "first nomination" flag active:
    - Check nominator's character type
    - If Townsfolk OR (Spy registering as Townsfolk): Trigger execution
    - If Spy: Offer registration prompt "Does Spy register as Townsfolk?"
    - If other: No trigger
    - Mark Virgin "first nomination used"
  - If Virgin drunk/poisoned: Skip trigger, but mark "first nomination used"
- **Immediate execution**:
  - Execute nominator without trial
  - Check Pacifist/Devil's Advocate interactions
  - Process as normal execution for other abilities (Undertaker, Saint, etc.)
- **State tracking**: Log {nominator, was_townsfolk, execution_occurred}
- **Visual alert**: Display "Virgin ability triggered!" notification to storyteller
- **Traveller handling**: Exclude Travellers from trigger eligibility

---

#### Slayer
**Ability**: "Once per game, during the day, publicly choose a player: if they are the Demon, they die."

**Mechanics**:
- One-time use during any day phase
- Must be publicly announced
- If target is Demon: Target dies immediately
- If target is not Demon: Nothing happens
- Does NOT kill Minions, only Demons

**Key interactions**:
- **Recluse**: May register as Demon and DIE from Slayer
- **Spy**: Does NOT register as Demon, safe from Slayer
- **Scarlet Woman**: Does NOT register as Demon until transformation, safe from Slayer before becoming Demon
- **Drunk/Poisoned Slayer**: Ability fails (no kill even if target is Demon)
- **Dead Slayer**: Cannot use ability while dead
- **Pacifist**: Does NOT prevent Slayer kill (not an execution)
- **Fang Gu/Snake Charmer**: If Demon changes, new Demon can be Slayer-killed

**Storyteller tool implementation**:
- **Setup**: Mark Slayer ability as "unused"
- **Day phase - Slayer use**:
  - Prompt: "Slayer targets [player] → Verify Demon/Not Demon"
  - Auto-check: Is target current Demon?
  - If Recluse targeted: Offer registration prompt "Does Recluse register as Demon?"
  - If Slayer drunk/poisoned: Force "No effect" result
  - If target is Demon (or Recluse registering): Immediate death
  - Mark ability as "used"
- **State tracking**: Log {day#, target, result, was_sober}
- **Validation**:
  - Prevent use if Slayer dead
  - Prevent use if ability already used
  - Check Slayer drunk/poisoned status
- **Visual feedback**: Display result to storyteller ("Demon killed" or "No effect")
- **No public reveal**: Game does NOT announce whether target was Demon

---

#### Soldier
**Ability**: "You are safe from the Demon."

**Mechanics**:
- Passive protection, always active
- Demon's kill ability "doesn't work" when targeting Soldier
- No indication to Soldier when protection triggers
- No indication to Demon that protection occurred
- Works even if Soldier is dead

**Key interactions**:
- **Execution**: Does NOT protect from execution
- **Witch**: Does NOT protect from Witch curse
- **Assassin**: Does NOT protect from Assassin (bypasses protection)
- **Godfather/Gossip/Tinker**: Does NOT protect from non-Demon deaths
- **Drunk Soldier**: Can be killed by Demon
- **Poisoned Soldier**: Can be killed by Demon
- **Imp starpass**: Imp CAN kill self to pass Demonhood (self-targeting bypass)
- **Dead Soldier**: Protection still works while dead (Demon can't kill Soldier's "ghost")

**Storyteller tool implementation**:
- **Setup**: Mark Soldier with "Demon-proof" status
- **Night phase - Demon kill**:
  - When Demon selects target, auto-check if target is Soldier
  - If Soldier AND sober/healthy: Block kill (no death occurs)
  - If Soldier drunk/poisoned: Kill succeeds normally
  - If Imp targeting self: Bypass protection (starpass succeeds)
- **No feedback**: Do NOT indicate to Demon or Soldier that protection triggered
- **State tracking**: Log attempted Demon kills on Soldier (for storyteller reference)
- **Visual aid**: Display "Soldier - Demon Proof" indicator in player list
- **Validation**: Check Soldier sober/healthy status before blocking kill
- **Dead player handling**: Protection persists even if Soldier dead

---

#### Mayor
**Ability**: "If only 3 players live & no execution occurs, your team wins. If you die at night, another player might die instead."

**Mechanics**:
- Two separate abilities:
  1. **Win condition**: At end of day with exactly 3 alive + no execution = good team wins
  2. **Bounce**: When killed at night, death may bounce to different player (Storyteller choice)
- Travelers do NOT count toward "3 players"
- Bounce target can be anyone (good or evil, alive player)

**Key interactions**:
- **Drunk Mayor**: Both abilities lost
- **Poisoned Mayor**: Both abilities lost
- **Win condition**: Checks at dusk (end of day before night)
- **Bounce**: Only triggers on night deaths (not execution)
- **Assassin**: Death can still bounce even if "can't be prevented"
- **Imp bounce**: If death bounces to Imp, good can win early
- **Multiple deaths**: If 3-kill night (Po), Mayor bounce still only affects Mayor's death
- **Traveller count**: Exclude from 3-player calculation

**Storyteller tool implementation**:
- **End of day check**:
  - Count alive players (exclude Travellers)
  - If exactly 3 AND no execution occurred AND Mayor alive/sober/healthy:
    - Prompt: "Mayor win condition triggered - Good team wins?"
    - Allow storyteller to confirm/override
- **Night phase - Mayor death**:
  - If Mayor killed at night AND sober/healthy:
    - Prompt: "Bounce Mayor's death? Select target player"
    - If yes: Original target (Mayor) survives, bounce target dies instead
    - If no: Mayor dies normally
  - Death bounce is Storyteller choice ("might")
- **State tracking**: Log {3-player days, bounce occurrences, bounce targets}
- **Visual alerts**:
  - At 3 players: Display "Mayor win condition possible" reminder
  - When Mayor killed: Display "Bounce available" prompt
- **Validation**:
  - Verify Mayor sober/healthy before applying abilities
  - Ensure bounce target is alive (can't bounce to dead player)
- **Traveller handling**: Auto-exclude Travellers from 3-player count

---

### Outsiders (4 characters)

#### Butler
**Ability**: "Each night, choose a player (not yourself): tomorrow, you may only vote if they are voting too."

**Mechanics**:
- Triggers every night (including first)
- Chooses one player (cannot choose self), called "master"
- Next day: Butler can only vote when master has already voted in that specific vote
- Restriction applies to all votes (nominations, on execution, tied votes)
- Master doesn't know they were chosen

**Key interactions**:
- **Drunk Butler**: Has no voting restriction
- **Dead Butler**: Restriction still applies (dead voting once rule + Butler restriction)
- **Master voting order**: Butler must vote after master votes in each individual vote
- **Nomination votes**: Butler can't vote unless master already voted in that nomination
- **Master dead**: If master can't vote (dead token used), Butler can never vote that day
- **Character changes**: If master's character changes (Pit-Hag), doesn't affect Butler

**Storyteller tool implementation**:
- **Each night prompt**: "Butler selects master for tomorrow"
- **State tracking**: Mark {night#, selected_master} - applies to next day
- **Day phase - Voting**:
  - For each vote: Track master's vote status
  - If master hasn't voted yet: Disable Butler's vote button/option
  - If master has voted: Enable Butler's vote
  - Display reminder to storyteller: "Butler can only vote after [master name]"
- **Visual aid**: Highlight Butler's master for the day in voting interface
- **Validation**:
  - Prevent Butler from selecting self
  - Check Butler drunk status (if drunk, no restrictions apply)
- **Dead Butler**: Apply both dead voting restriction AND Butler restriction (very limited voting)

---

#### Drunk
**Ability**: "You do not know you are the Drunk. You think you are a Townsfolk character, but you are not."

**Mechanics**:
- Setup character: Drunk token removed from bag, replaced with random Townsfolk token
- Player thinks they are that Townsfolk
- Player IS the Drunk (Outsider), not the Townsfolk
- Ability never works (permanently drunk state)
- Cannot become sober through any means

**Key interactions**:
- **Information abilities**: Storyteller provides false or no information
- **One-time abilities**: Wasted when used (Slayer, Ravenkeeper, etc.)
- **Passive abilities**: Don't function (Soldier, Saint, etc.)
- **Detection**: Other abilities see "Drunk" not the fake character
- **Baron**: May add extra Drunk (second Drunk token becomes Townsfolk)
- **Undertaker**: If Drunk executed, shows fake character (what Drunk thinks they are)
- **Philosopher**: Cannot make Drunk sober

**Storyteller tool implementation**:
- **Setup phase**: 
  - Assign Drunk player
  - Select fake Townsfolk character for Drunk
  - Store: {actual: "Drunk", perceived: "Fake Townsfolk"}
- **Night/Day prompts**: 
  - When Drunk's fake character would act: Prompt storyteller to give false info or skip
  - Display: "Drunk (thinks: [Fake Character]) - Ability doesn't work"
- **Info generation**: Provide options for false information appropriate to fake character
- **State tracking**: Log all false info given to Drunk for consistency checking
- **Detection abilities**: When others detect Drunk, show "Drunk" not fake character
- **Visual reminder**: Display "DRUNK" status prominently on player token
- **Undertaker special case**: If Drunk executed, automatically suggest showing fake character

---

#### Recluse
**Ability**: "You might register as evil & as a Minion or Demon, even if dead."

**Mechanics**:
- Storyteller chooses when/if Recluse registers as evil
- Can register as specific Minion or Demon character
- Registration can change between different ability checks
- No consistency required (can register different each time)
- Works even if Recluse is dead

**Key interactions**:
- **Detection abilities**: May trigger false positives (Empath, Fortune Teller, Washerwoman, Investigator, etc.)
- **Kill abilities**: May be killed by Slayer, may trigger Virgin
- **Spy**: Separate mechanic (Spy is evil registering good, Recluse is good registering evil)
- **Drunk**: Recluse who is Drunk still has registration ability
- **Every ability**: Storyteller can choose registration for each individual check

**Storyteller tool implementation**:
- **Global setting**: Mark Recluse with "Registration Override Available" flag
- **Detection prompts**: When any ability checks Recluse:
  - Display: "Recluse detected - Register as evil/Minion/Demon?"
  - Options: [Normal (good), Register as Evil, Register as specific character]
  - Allow character selection if registering as Minion/Demon
- **Common triggers**:
  - Empath checking neighbors: "Count Recluse as evil?"
  - Fortune Teller checking: "Recluse register as Demon?"
  - Washerwoman/Librarian/Investigator: "Show Recluse as [Townsfolk/Outsider/Minion]?"
  - Slayer targeting: "Recluse register as Demon (will die)?"
- **State tracking**: Log each registration decision {ability, night/day#, registered_as}
- **No consistency**: Don't enforce consistency between registrations
- **Visual reminder**: Display "Recluse - Can register as evil" indicator
- **Dead Recluse**: Registration still works after death

---

#### Saint
**Ability**: "If you die by execution, your team loses."

**Mechanics**:
- Instant loss condition for good team if Saint executed
- Only triggers on execution, not other deaths
- No trial/voting phase after trigger - immediate loss
- Does not prevent Saint's death, just triggers loss

**Key interactions**:
- **Drunk Saint**: Can be executed safely (no loss)
- **Poisoned Saint**: Can be executed safely (no loss)
- **Pacifist**: If Pacifist prevents Saint execution, loss doesn't trigger
- **Virgin trigger**: If Townsfolk nominates Virgin and dies, then Saint executed = still triggers loss
- **Double execution**: If both Virgin nominator and Saint executed same day, Saint loss still triggers
- **Mayor**: Saint execution prevents Mayor 3-player win

**Storyteller tool implementation**:
- **Execution phase**: 
  - When Saint is executed AND Saint sober/healthy:
    - Immediate prompt: "Saint executed - Good team loses!"
    - Trigger game end (Evil wins)
  - If Saint drunk/poisoned: Normal execution (no loss)
- **Validation**:
  - Check Saint sober/healthy status before triggering loss
  - Don't trigger if Pacifist prevents execution
- **Visual alert**: Display prominent "SAINT EXECUTED - EVIL WINS" notification
- **State tracking**: Log {day#, saint_executed, game_ended}
- **Reminder**: Display "Saint in play - execution = good loses" warning during day phase
- **Pre-execution check**: Optional storyteller confirm: "Execute Saint? (Good team will lose)"

---

### Minions (4 characters)

#### Poisoner
**Ability**: "Each night, choose a player: they are poisoned tonight and tomorrow day."

**Mechanics**:
- Triggers every night (including first)
- Chooses one player to poison
- Poison lasts: current night + following day (until next dusk)
- Poisoned player's ability doesn't work during this time
- Player doesn't know they're poisoned

**Key interactions**:
- **Info abilities**: Storyteller provides false information
- **Passive abilities**: Stop working (Soldier, Saint, etc.)
- **One-time abilities**: Wasted if used while poisoned (Slayer, etc.)
- **Can poison Demon**: Legal but risky for evil team
- **Can poison self**: Legal
- **Drunk Poisoner**: Doesn't poison anyone
- **Poisoned Poisoner**: Can still poison others
- **Scarlet Woman**: Can poison to prevent transformation
- **Multiple nights**: Can poison same player multiple nights in a row

**Storyteller tool implementation**:
- **Each night prompt**: "Poisoner selects player to poison"
- **State tracking**:
  - Mark selected player as "Poisoned" (duration: until next dusk)
  - Display poison duration timer
  - Track {night#, poisoned_player, expires: next_dusk}
- **Ability resolution**:
  - When poisoned player's ability triggers: Provide false info or disable ability
  - Display to storyteller: "[Player] is POISONED - ability doesn't work"
- **Auto-expiry**: Remove poison status at dusk
- **Visual indicators**:
  - Poison icon on affected player
  - Duration countdown
  - List of currently poisoned players
- **Info generation**: Provide false info options appropriate to poisoned character
- **Validation**: Check Poisoner drunk status before applying poison
- **Reminder**: Track when each poison expires to remove status

---

#### Spy
**Ability**: "Each night, you see the Grimoire. You might register as good & as a Townsfolk or Outsider, even if dead."

**Mechanics**:
- Triggers every night (including first)
- Sees all player tokens, characters, statuses (drunk/poisoned), reminders
- Storyteller chooses when/if Spy registers as good
- Can register as specific Townsfolk or Outsider character
- Can trigger Virgin (only evil player who can)

**Key interactions**:
- **Virgin**: CAN trigger (can register as Townsfolk)
- **Washerwoman/Librarian**: Can be shown as Townsfolk/Outsider
- **Empath**: Can register as good (not counted as evil neighbor)
- **Fortune Teller**: Does NOT register as Demon
- **Chef**: Can register as good (not counted in evil pairs)
- **Recluse**: Opposite mechanic (Recluse is good registering evil)
- **Sees everything**: Drunk status, poison status, Red Herring, all tokens
- **Dead Spy**: Registration still works after death

**Storyteller tool implementation**:
- **Each night prompt**: "Show Grimoire to Spy"
- **Grimoire display**: Full game state view including:
  - All player characters
  - Drunk/poisoned statuses
  - Reminder tokens (Red Herring, protected players, etc.)
  - Dead/alive status
  - NOT-IN-PLAY characters
- **Registration overrides**: When Spy is checked by detection ability:
  - Display: "Spy detected - Register as good/Townsfolk/Outsider?"
  - Options: [Normal (evil), Register as Good, Register as specific character]
  - Allow character selection if registering as Townsfolk/Outsider
- **Common triggers**:
  - Empath checking: "Count Spy as good?"
  - Washerwoman checking: "Show Spy as [Townsfolk]?"
  - Librarian checking: "Show Spy as [Outsider]?"
  - Virgin nomination: "Spy register as Townsfolk (will execute Spy)?"
- **State tracking**: Log {night#, saw_grimoire: true, registrations: [...]}
- **Dead Spy**: Still sees Grimoire and registration works
- **Visual aid**: Provide clean, comprehensive Grimoire view for Spy player

---

#### Baron
**Ability**: "There are extra Outsiders in play. [+2 Outsiders]"

**Mechanics**:
- Setup ability only (not night/day triggered)
- Adds 2 Outsiders to game, removes 2 Townsfolk
- Effect permanent even if Baron dies
- Modifies character distribution before game starts

**Key interactions**:
- **Librarian**: Cannot see "0" if Baron in play (always 2+ Outsiders)
- **May add Drunk**: One of the +2 Outsiders might be Drunk
- **Character count**: Changes game setup (2 fewer Townsfolk, 2 more Outsiders)
- **Death**: Baron dying doesn't revert Outsider count
- **Drunk Baron**: Still adds Outsiders (setup completed before drunk state)
- **Poisoned Baron**: Irrelevant (setup already completed)

**Storyteller tool implementation**:
- **Setup phase**: 
  - When Baron assigned: Automatically adjust character counts
  - Display: "Baron in play - Adding +2 Outsiders, removing -2 Townsfolk"
  - Modify player distribution: Original Townsfolk count -2, Original Outsider count +2
- **Character selection**:
  - Update character bag/pool automatically
  - Ensure 2 additional Outsiders selected
  - Reduce Townsfolk by 2
- **Validation**:
  - Verify Outsider count matches expected (base + 2)
  - Check that Librarian cannot receive "0" info
- **State tracking**: Mark "Baron setup modifier applied" flag
- **Visual reminder**: Display Outsider count vs. expected baseline
- **Script info**: Show expected vs. actual Outsider count for verification
- **Multiple modifiers**: If other setup modifiers exist (Godfather, Fang Gu), calculate cumulative

---

#### Scarlet Woman
**Ability**: "If there are 5 or more players alive & the Demon dies, you become the Demon. (Travellers don't count.)"

**Mechanics**:
- Triggers when Demon dies (execution or night death)
- Requires 5+ players alive (excluding Travellers) at moment of Demon death
- Scarlet Woman becomes same Demon type as dead Demon
- Does NOT register as Demon until transformation occurs
- After transformation, is full Demon with all abilities

**Key interactions**:
- **Drunk Scarlet Woman**: Cannot transform
- **Poisoned Scarlet Woman**: Cannot transform
- **Dead Scarlet Woman**: Cannot transform (must be alive)
- **4 or fewer alive**: No transformation
- **Slayer**: Before transformation, Slayer doesn't work on Scarlet Woman
- **Fortune Teller**: Before transformation, doesn't register as Demon
- **Imp starpass**: Scarlet Woman transforms before Imp passes to other Minion (if 5+ alive)
- **Multiple Demons**: Becomes same type as dying Demon
- **Travellers**: Excluded from 5-player count

**Storyteller tool implementation**:
- **Demon death event**:
  - Count alive players (exclude Travellers)
  - Check Scarlet Woman status (alive, sober, healthy)
  - If 5+ players AND Scarlet Woman eligible:
    - Prompt: "Scarlet Woman becomes [Demon type]"
    - Transform Scarlet Woman character to Demon
    - Update alignment if needed (should already be evil)
    - Game continues
  - If <5 players OR Scarlet Woman ineligible:
    - Normal Demon death (good wins)
- **State tracking**:
  - Mark Scarlet Woman pre-transformation status
  - Log transformation {night/day#, became: Demon_type, player_count}
- **Visual alert**: Display "Scarlet Woman transformed!" notification
- **New Demon setup**:
  - Scarlet Woman gets Demon wake order
  - Knows Minions (already knew as Minion)
  - Retains bluffs from original Demon setup
- **Validation**:
  - Auto-count excluding Travellers
  - Check Scarlet Woman alive/sober/healthy
  - Verify Demon actually died (not fake Zombuul death)
- **Night order**: If transformation happens during day, update night order for next night

---

### Demons (1 character)

#### Imp
**Ability**: "Each night*, choose a player: they die. If you kill yourself this way, a Minion becomes the Imp."

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses one player (can be alive or dead)
- If chooses living player: They die
- If chooses dead player: Nothing happens
- If chooses self ("starpass"): Imp dies, random Minion becomes new Imp
- New Imp doesn't kill same night (transformation happens after kill phase)

**Key interactions**:
- **Scarlet Woman starpass**: If 5+ alive, Scarlet Woman becomes Imp (priority over other Minions)
- **Monk/Soldier protection**: Can't kill protected player (but CAN kill self for starpass)
- **Dead target**: Can choose dead players safely (no effect)
- **Drunk Imp**: Kill fails
- **Poisoned Imp**: Kill fails
- **Scarlet Woman poisoned**: If SW poisoned during starpass, doesn't transform (passes to other Minion)
- **No Minions alive**: Starpass fails (Imp dies, good wins)
- **Multiple Minions**: Storyteller chooses which becomes new Imp

**Storyteller tool implementation**:
- **Each night* prompt**: "Imp selects kill target"
- **Kill resolution**:
  - If target is self: Trigger starpass sequence
  - If target is living player: Check protections (Monk, Soldier, etc.)
    - If protected/immune: Kill fails (no death)
    - If not protected: Kill succeeds
  - If target is dead player: No effect
  - If Imp drunk/poisoned: No kill
- **Starpass sequence** (if Imp kills self):
  1. Imp dies
  2. Count alive players (exclude Travellers)
  3. If 5+ alive AND Scarlet Woman alive/sober/healthy: Scarlet Woman becomes Imp
  4. Else: Select living Minion to become Imp
  5. If no living Minions: Game ends (good wins)
  6. New Imp doesn't kill this night
  7. Update character tokens and night order
- **State tracking**: Log {night#, target, kill_succeeded, starpass: true/false}
- **Visual alerts**:
  - Display Imp's target
  - If starpass: "Imp killed self - [player] becomes new Imp"
- **Validation**:
  - Check Imp sober/healthy status
  - Check target protections
  - If starpass: Verify Minions available
- **New Imp setup**:
  - Transfer Demon abilities to new Imp
  - New Imp knows Minions
  - Update night order position

---

## BAD MOON RISING (Intermediate Edition)

### Townsfolk (13 characters)

#### Grandmother
**Ability**: "You start knowing a good player & their character. If the Demon kills them, you die too."

**Mechanics**:
- Triggers first night only (learns grandchild)
- Shown one good player and their character
- If that player dies from Demon kill: Grandmother dies too (linked death)
- Linked death is NOT a Demon kill, it's indirect
- Linked death occurs immediately after Demon kill resolves

**Key interactions**:
- **Protection bypass**: Linked death bypasses ALL protection (Fool, Tea Lady, Sailor, etc.)
- **Drunk Grandmother**: Gets false grandchild, linked death doesn't trigger
- **Poisoned Grandmother**: Linked death doesn't trigger
- **Non-Demon deaths**: If grandchild dies from execution/Assassin/etc., no linked death
- **Exorcist**: If Exorcist prevents Demon wake, no kill = no linked death
- **Grandchild character change**: If Pit-Hag changes grandchild, doesn't affect Grandmother info
- **Shabaloth regurgitation**: If grandchild regurgitated after death, doesn't retrigger

**Storyteller tool implementation**:
- **Setup phase**: Auto-mark for Night 1 wake
- **Night 1 prompt**: "Select good player as grandchild → Show character"
- **Validation**: Verify selected player is actually good and show their actual character (unless drunk/poisoned)
- **State tracking**: Mark grandchild with permanent "Grandmother's grandchild" reminder token
- **Demon kill resolution**: 
  - After Demon kills, check if victim is marked grandchild
  - If yes AND Grandmother alive/sober/healthy: Kill Grandmother immediately
  - Linked death bypasses all protection
- **Visual aid**: Highlight grandchild in player list with Grandmother link icon
- **Death notification**: Display "Grandmother dies (linked to grandchild)" when triggered
- **Edge case**: If grandchild drunk/poisoned when killed, still triggers (it's about the player, not their ability)

---

#### Sailor
**Ability**: "Each night, choose an alive player: either you or they are drunk until dusk. You can't die."

**Mechanics**:
- Triggers every night (including first)
- Chooses one alive player
- Storyteller chooses which one becomes drunk (Sailor or chosen player)
- Drunk lasts until dusk (end of next day)
- "Can't die" is passive protection from ALL sources while sober

**Key interactions**:
- **Protection**: While sober and healthy, immune to execution, Demon, Assassin, everything
- **Drunk Sailor**: Can die (loses protection)
- **Poisoned Sailor**: Can die (loses protection)
- **Sailor gets drunk**: If storyteller drunks Sailor, becomes vulnerable that day
- **Assassin**: Does NOT bypass (but if Sailor drunk, Assassin works)
- **Can choose self**: Legal, essentially asking to be drunk
- **Drunk duration**: Until dusk, so protection resumes at dusk

**Storyteller tool implementation**:
- **Each night prompt**: "Sailor selects player → Choose who gets drunk [Sailor / Selected player]"
- **State tracking**: 
  - Mark drunk player (Sailor or target) with drunk status until dusk
  - Track {night#, selected_player, who_drunk}
- **Death protection**:
  - Check Sailor drunk/poisoned status before allowing ANY death
  - If sober/healthy: Block ALL deaths (execution, Demon, Assassin, etc.)
  - If drunk/poisoned: Deaths proceed normally
- **Visual aid**: 
  - Display "SAILOR - CAN'T DIE" indicator when sober/healthy
  - Show drunk status duration
- **Execution handling**: If village tries to execute Sailor, block and notify storyteller
- **Validation**: Sailor can only select alive players
- **Auto-expire**: Remove drunk status at dusk

---

#### Chambermaid
**Ability**: "Each night, choose 2 alive players (not yourself): you learn how many woke tonight due to their ability."

**Mechanics**:
- Triggers every night (including first)
- Chooses 2 alive players (cannot choose self)
- Returns number 0, 1, or 2
- Only counts if player woke because of THEIR ability
- Does NOT count being woken by other players' abilities

**Key interactions**:
- **Drunk/poisoned players**: Don't wake (count as 0)
- **Dead players**: Never wake (count as 0)
- **Minions/Demons**: Wake every night from their own ability (usually)
- **Godfather**: Only wakes if Outsider died today
- **Passive abilities**: Don't wake (Soldier, Sailor protection, etc.)
- **Once-per-game abilities**: Only wake when used
- **Being targeted**: Doesn't count (Monk choosing player doesn't make them wake)

**Storyteller tool implementation**:
- **Each night prompt**: "Chambermaid selects 2 alive players → Calculate wake count"
- **Auto-calculation**:
  - For each selected player: Check if they woke due to their own ability this night
  - Count: 0, 1, or 2
  - If either drunk/poisoned: They didn't wake (don't count)
  - If either dead: Don't count (can only select alive but validate)
- **Wake tracking**: Maintain log of which characters woke each night
- **State tracking**: Log {night#, player1, player2, wake_count}
- **Visual aid**: Display wake history for storyteller reference
- **Validation**: 
  - Prevent selecting self
  - Verify both selections are alive
  - Check Chambermaid drunk/poisoned (if yes, give false count)
- **Character-specific**: Display which characters typically wake (help storyteller)

---

#### Exorcist
**Ability**: "Each night*, choose a player (different to last night): the Demon, if chosen, learns who you are then doesn't wake tonight."

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses one player (must be different from previous night)
- If chosen player is Demon: Demon learns Exorcist identity, Demon doesn't wake (no kill)
- If chosen player is NOT Demon: Nothing happens
- Demon stays alive, just prevented from acting

**Key interactions**:
- **Demon learns identity**: Demon is told "You were Exorcisted by [player]"
- **Drunk Exorcist**: No effect, Demon wakes normally
- **Poisoned Exorcist**: No effect, Demon wakes normally
- **Pukka**: Exorcist does NOT prevent poison/death from PREVIOUS night
- **Multiple kills**: If Demon kills multiple (Shabaloth, Po), all kills prevented
- **Godfather**: If Outsider died, Godfather still prevented if Demon Exorcised
- **Assassination**: Doesn't prevent Assassin kill (not Demon ability)

**Storyteller tool implementation**:
- **Each night* prompt**: "Exorcist selects player (must differ from last night)"
- **Validation**: 
  - Check previous night's choice, prevent selecting same player
  - Verify Exorcist alive
  - If Exorcist drunk/poisoned: Skip effect but track choice
- **Demon check**:
  - If selected player is current Demon AND Exorcist sober/healthy:
    - Notify Demon: "You were Exorcisted by [Exorcist name]"
    - Skip Demon's wake/action this night
    - Mark Demon as "Exorcised" for this night
  - If not Demon: No effect
- **State tracking**: Log {night#, selected_player, was_demon: true/false, prevented_kill: true/false}
- **Visual aid**: Display previous night's choice as unavailable option
- **Night order**: Exorcist acts before Demon, so Demon prevention happens before Demon would wake

---

#### Innkeeper
**Ability**: "Each night*, choose 2 players: they can't die tonight, but 1 is drunk until dusk."

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses 2 players (can choose self)
- Both protected from ALL death tonight
- Storyteller chooses which one is drunk until dusk
- Protection lasts one night, drunk lasts until dusk

**Key interactions**:
- **Protection**: Blocks execution, Demon, Assassin, everything
- **Drunk effect**: Protected drunk player's ability doesn't work
- **Can protect Demon**: Legal and interesting
- **Can protect self**: Legal
- **Drunk Innkeeper**: No protection or drunkenness applied
- **Poisoned Innkeeper**: No protection or drunkenness applied
- **Assassin**: Protection DOES block Assassin (unlike most protection)
- **Sailor**: Can protect Sailor (redundant but legal)

**Storyteller tool implementation**:
- **Each night* prompt**: "Innkeeper selects 2 players → Choose who gets drunk"
- **State tracking**:
  - Mark both players as "Innkeeper-protected" for this night
  - Mark one player as drunk until dusk
  - Track {night#, protected1, protected2, who_drunk}
- **Death protection**:
  - Check protected status before allowing any death
  - If protected AND Innkeeper sober/healthy: Block death
  - If Innkeeper drunk/poisoned: No protection
- **Drunk application**: Apply drunk status to selected player until dusk
- **Visual aid**:
  - Display protection icons on both players
  - Show drunk status with duration
- **Validation**: Check Innkeeper sober/healthy before applying effects
- **Auto-expire**: Remove drunk at dusk, protection at dawn

---

#### Gambler
**Ability**: "Each night*, choose a player & guess their character: if you guess wrong, you die."

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses one player and guesses their character
- If guess is CORRECT: Nothing happens
- If guess is WRONG: Gambler dies immediately
- Death is NOT a Demon kill

**Key interactions**:
- **Drunk Gambler**: Wrong guess doesn't kill
- **Poisoned Gambler**: Wrong guess doesn't kill
- **Character changes**: Guess checked against current character at resolution
- **Pit-Hag**: If character changed this night, Gambler sees new character
- **Drunk target**: Gambler guesses actual character (Drunk), not what Drunk thinks
- **Protection**: Gambler death CAN be prevented (Fool, Innkeeper, Sailor, Tea Lady)
- **Assassination**: Separate from Gambler wrong guess

**Storyteller tool implementation**:
- **Each night* prompt**: "Gambler selects player and guesses character"
- **Validation**:
  - Retrieve target player's actual current character
  - Compare guess to actual character
  - If match: No effect
  - If no match AND Gambler sober/healthy: Kill Gambler
  - If Gambler drunk/poisoned: No death even if wrong
- **State tracking**: Log {night#, target, guess, actual_character, result: correct/wrong/died}
- **Visual feedback**: Display to storyteller "Correct" or "Wrong - Gambler dies"
- **Death resolution**: Process Gambler death (check protections, trigger other abilities)
- **Character selection**: Provide dropdown of all possible characters for guess
- **Edge case**: If target character changed during night (Pit-Hag before Gambler), use new character

---

#### Gossip
**Ability**: "Each day, you may make a public statement. Tonight, if it was true, a player dies."

**Mechanics**:
- Triggers each day phase (player makes statement)
- Statement can be about anything
- That night: Storyteller evaluates if statement was true
- If true: Storyteller kills one player (Storyteller choice)
- Death is NOT a Demon kill

**Key interactions**:
- **Drunk Gossip**: Statement doesn't cause death
- **Poisoned Gossip**: Statement doesn't cause death
- **Truth evaluation**: Storyteller interprets truth
- **Kill choice**: Storyteller chooses who dies (can kill anyone, even Demon)
- **Multiple statements**: If Gossip makes multiple, only first counts (or none if unclear)
- **Vague statements**: Storyteller interpretation crucial
- **Protection**: Death CAN be prevented by protections

**Storyteller tool implementation**:
- **Day phase**: 
  - Provide "Log Gossip statement" button
  - Record statement text
  - Track {day#, statement, evaluation_pending}
- **Night phase**:
  - Prompt: "Evaluate Gossip statement: [statement text] - True or False?"
  - If True AND Gossip sober/healthy: "Select player to die"
  - If False OR Gossip drunk/poisoned: No death
- **State tracking**: Log {day#, statement, truth_value, killed_player}
- **Kill resolution**: Process death (check protections, can be prevented)
- **Visual aid**: Display pending Gossip evaluation reminder
- **Multiple statements**: Only evaluate most recent or first statement per day
- **Storyteller guidance**: Allow storyteller notes on interpretation

---

#### Courtier
**Ability**: "Once per game, at night, choose a character: they are drunk for 3 nights & 3 days."

**Mechanics**:
- One-time use ability
- Triggers at night (any night including first)
- Chooses a CHARACTER type (not a specific player)
- ALL players with that character become drunk for 3 nights + 3 days
- Duration: 3 full day/night cycles

**Key interactions**:
- **Can drunk Demon**: Extremely powerful
- **Multiple players**: If multiple players have that character (Pit-Hag), all drunk
- **Drunk Courtier**: Ability wasted (no one drunk)
- **Poisoned Courtier**: Ability wasted (no one drunk)
- **Character changes**: If player's character changes during duration, drunk ends for them
- **Duration counting**: Night used + 3 more nights = 4 nights total drunk
- **Travellers**: Can be drunked if Courtier selects Traveller character

**Storyteller tool implementation**:
- **Setup**: Mark Courtier ability as "unused"
- **Any night prompt** (if unused): "Courtier chooses character to drunk (3 nights + 3 days)"
- **Character selection**: Provide list of all characters in script
- **Application**:
  - Find all players with selected character
  - Apply drunk status to all found players
  - Set duration: Current night + 3 more nights + days
  - Mark ability as "used"
- **State tracking**: 
  - Log {night_used, character, affected_players, expires: night#+3}
  - Display duration countdown
- **Auto-expire**: Remove drunk from all affected at expiration
- **Visual aid**: 
  - Display "Courtier drunk: [Character]" with timer
  - Show affected players list
- **Validation**: 
  - Prevent use if already used
  - Check Courtier sober/healthy before applying
- **Character change handling**: If affected player's character changes, remove their drunk status

---

#### Professor
**Ability**: "Once per game, at night*, choose a dead player: if they are a Townsfolk, they are resurrected."

**Mechanics**:
- One-time use ability
- Triggers any night EXCEPT first
- Chooses one dead player
- If player is Townsfolk: They return to life
- If player is NOT Townsfolk: Nothing happens
- Resurrection is permanent

**Key interactions**:
- **Drunk Professor**: Ability wasted (no resurrection)
- **Poisoned Professor**: Ability wasted (no resurrection)
- **Execution/night death**: Can resurrect from either
- **Outsiders**: Not resurrected
- **Minions/Demons**: Not resurrected
- **Character changes**: Checks current character at time of use
- **Pit-Hag**: If dead Townsfolk changed to non-Townsfolk, can't be resurrected

**Storyteller tool implementation**:
- **Setup**: Mark Professor ability as "unused"
- **Each night* prompt** (if unused): "Professor selects dead player"
- **Validation**:
  - Verify selected player is actually dead
  - Check player's current character
  - If Townsfolk AND Professor sober/healthy: Resurrect
  - If not Townsfolk: No effect
  - Mark ability as "used"
- **Resurrection**:
  - Change player status to alive
  - Reset vote token (can vote again)
  - Can nominate again
  - Ability starts working (if sober/healthy)
- **State tracking**: Log {night#, selected_player, was_townsfolk, resurrected: true/false}
- **Visual alert**: Display "Professor resurrects [player]" notification
- **Game state update**: Update all tracking (alive count, seating neighbors, etc.)
- **Validation**: Prevent use if already used

---

#### Minstrel
**Ability**: "When a Minion dies by execution, all other players (except Travellers) are drunk until dusk tomorrow."

**Mechanics**:
- Triggers when Minion executed (not night death)
- ALL players except Minstrel and Travellers become drunk
- Drunk lasts until dusk next day
- Affects both good and evil players

**Key interactions**:
- **Only execution**: Night deaths don't trigger
- **Drunk Minstrel**: Doesn't trigger
- **Poisoned Minstrel**: Doesn't trigger
- **Multiple triggers**: Each Minion execution triggers new drunk period
- **Vigormortis dead Minions**: Still count as Minions for trigger
- **Pit-Hag**: If Minion changed to non-Minion before execution, doesn't trigger
- **Mass disruption**: Extremely powerful, affects everyone

**Storyteller tool implementation**:
- **Execution resolution**:
  - Check if executed player is Minion
  - If yes AND Minstrel alive/sober/healthy:
    - Prompt: "Minstrel triggered - All players drunk until dusk tomorrow"
    - Apply drunk status to all players except Minstrel and Travellers
    - Set duration: Until dusk next day
- **State tracking**: Log {day#, executed_minion, drunk_duration: until_next_dusk}
- **Visual alert**: Display "MINSTREL TRIGGERED - MASS DRUNK" notification
- **Drunk application**:
  - Auto-select all players except Minstrel and Travellers
  - Apply drunk markers
  - Show duration countdown
- **Auto-expire**: Remove drunk from all at dusk
- **Validation**: Check Minstrel alive/sober/healthy status
- **Multiple triggers**: Can stack durations if multiple Minions executed

---

#### Tea Lady
**Ability**: "If both your alive neighbors are good, they can't die."

**Mechanics**:
- Passive ability, always checking
- "Neighbors" = closest alive player in each direction
- Both alive neighbors must be good for protection to work
- Protected neighbors immune to ALL death sources
- Dead players skipped when determining neighbors

**Key interactions**:
- **Drunk Tea Lady**: No protection
- **Poisoned Tea Lady**: No protection
- **Evil neighbor**: Breaks protection (need BOTH good)
- **Dead neighbors**: Skipped to next alive player
- **Goon/Snake Charmer**: Alignment changes affect protection
- **Protection**: Blocks execution, Demon, Assassin, everything
- **Travellers**: Count as neighbors if adjacent
- **Dynamic**: Protection updates as neighbors die/alignments change

**Storyteller tool implementation**:
- **Continuous monitoring**:
  - Calculate Tea Lady's living neighbors (left and right)
  - Check both neighbors' alignments
  - If both good AND Tea Lady sober/healthy: Apply protection to both neighbors
  - If either evil OR Tea Lady drunk/poisoned: Remove protection
- **Death prevention**:
  - Before processing any death, check if target has Tea Lady protection
  - If protected: Block death
  - Update protection status after each death (neighbors may change)
- **State tracking**: Log current protection status and protected players
- **Visual aid**:
  - Highlight Tea Lady's living neighbors
  - Display protection icons on protected neighbors
  - Show alignment status affecting protection
- **Dynamic updates**: Recalculate neighbors after each death
- **Validation**: Check Tea Lady sober/healthy before applying protection
- **Neighbor calculation**: Auto-find closest alive in each direction

---

#### Pacifist
**Ability**: "Executed good players might not die."

**Mechanics**:
- Passive ability, triggers on executions
- When good player executed: Storyteller chooses whether they die
- Only affects executions, not other deaths
- No indication when ability triggers
- Can save good players from execution

**Key interactions**:
- **Drunk Pacifist**: Doesn't protect
- **Poisoned Pacifist**: Doesn't protect
- **Evil players**: Always die from execution (Pacifist doesn't protect evil)
- **Saint**: Can prevent Saint execution (no loss if Pacifist saves)
- **Virgin trigger**: Pacifist can prevent nominator death
- **Traveller executions**: Separate from nominations, Pacifist might work (unclear rule)
- **"Might"**: Storyteller's choice each time

**Storyteller tool implementation**:
- **Execution resolution**:
  - Check executed player's alignment
  - If good AND Pacifist alive/sober/healthy:
    - Prompt: "Pacifist can save [player] - Prevent execution death?"
    - Options: [Let die, Pacifist saves]
  - If evil: Normal death (no prompt)
  - If Pacifist drunk/poisoned: Normal death
- **State tracking**: Log {day#, executed_player, pacifist_saved: true/false}
- **No indication**: Don't publicly announce Pacifist saved (appears like normal survival)
- **Visual aid**: Display Pacifist decision prompt to storyteller only
- **Saint interaction**: If Saint executed and Pacifist saves, good team doesn't lose
- **Validation**: Check Pacifist alive/sober/healthy before offering save

---

#### Fool
**Ability**: "The 1st time you die, you don't."

**Mechanics**:
- One-time protection from death
- Triggers on ANY death (execution, Demon, Assassin, etc.)
- No indication to Fool or anyone when triggered
- After first death prevented, dies normally on subsequent deaths
- Cannot be bypassed except by drunk/poisoned status

**Key interactions**:
- **Drunk Fool**: Dies on first death (no protection)
- **Poisoned Fool**: Dies on first death (no protection)
- **Assassin**: Fool protection DOES work (Assassin says "even if for some reason they could not" but Fool says they "don't die")
- **All deaths**: Works on execution, Demon, Godfather, Gossip, Gambler, everything
- **Resurrection**: If resurrected, ability already used (doesn't reset)
- **One-time**: After first trigger, no more protection

**Storyteller tool implementation**:
- **Setup**: Mark Fool ability as "unused"
- **Death processing**:
  - When Fool would die AND ability unused AND Fool sober/healthy:
    - Prevent death
    - Mark ability as "used"
    - No announcement (silent save)
  - If ability used: Fool dies normally
  - If Fool drunk/poisoned: Fool dies, don't mark ability used
- **State tracking**: Log {death_attempt#, prevented: true/false, ability_remaining: true/false}
- **Visual aid**: Display "Fool - 1st death protected" indicator, update to "used" after trigger
- **No feedback**: Don't indicate to players that protection triggered
- **Validation**: Check Fool sober/healthy before applying protection
- **Assassin interaction**: Fool protection overrides Assassin bypass (official ruling)

---

### Outsiders (4 characters)

#### Goon
**Ability**: "Each night, the 1st player to choose you with their ability is drunk until dusk. You become their alignment."

**Mechanics**:
- Triggers every night (including first)
- First player each night whose ability targets Goon: Gets drunk until dusk
- Goon changes to that player's alignment (good or evil)
- Alignment change persists (doesn't revert)
- Can flip back and forth between alignments

**Key interactions**:
- **Drunk Goon**: Doesn't drunk others, doesn't change alignment
- **Poisoned Goon**: Doesn't drunk others, doesn't change alignment
- **Win condition**: Uses alignment at game end for winning team
- **Only first chooser**: If multiple abilities target Goon same night, only first counts
- **Night order**: Matters for determining "first"
- **Politician**: Both can change alignment mid-game
- **Oracle**: Goon's alignment change affects count
- **Detection**: Goon registers as current alignment, not original

**Storyteller tool implementation**:
- **Each night monitoring**:
  - Track ability uses in night order
  - When first ability targets Goon AND Goon sober/healthy:
    - Apply drunk to chooser until dusk
    - Change Goon's alignment to match chooser's alignment
    - Mark Goon as "triggered" for this night (block further triggers)
- **State tracking**: Log {night#, first_chooser, chooser_alignment, goon_new_alignment}
- **Visual aid**: 
  - Display Goon's current alignment prominently
  - Show alignment history
  - Highlight "First to choose Goon" during night
- **Alignment tracking**: Update Goon's alignment immediately, persist through game
- **Win condition**: Check Goon's final alignment at game end
- **Validation**: Check Goon sober/healthy before applying effects
- **Night order**: Display night order to help determine "first"

---

#### Lunatic
**Ability**: "You think you are a Demon, but you are not. The Demon knows who you are & who you choose at night."

**Mechanics**:
- Setup: Player thinks they are Demon
- Shown fake Minions at start
- Makes "kills" each night, but they're fake
- Real Demon is told Lunatic identity and sees Lunatic's choices
- Player completely unaware they're Lunatic

**Key interactions**:
- **Drunk Lunatic**: Still thinks they're Demon (doesn't change)
- **Poisoned Lunatic**: Demon stops seeing choices while poisoned
- **Slayer**: Lunatic is NOT Demon, doesn't die to Slayer
- **Fortune Teller**: Lunatic does NOT register as Demon
- **Detection**: Shown as Lunatic, not as Demon
- **Demon coordination**: Helps Demon with bluffs and target selection
- **Setup modifier**: One of two Outsiders in setup (base +1 or -1 from Baron/Godfather)

**Storyteller tool implementation**:
- **Setup phase**:
  - Assign Lunatic
  - Select Demon type for Lunatic to "be"
  - Select 2-3 players to show as fake Minions
  - Reveal to real Demon: "Lunatic is [player]"
- **Each night**: 
  - Prompt Lunatic: "[Demon type] select player to kill"
  - Log fake choice (doesn't actually kill)
  - Show real Demon: "Lunatic chose [player]"
- **State tracking**: Log {night#, lunatic_choice, shown_to_demon}
- **Grimoire**: Show Lunatic as Lunatic (not Demon) to Spy
- **Info for Demon**: Provide ongoing updates of Lunatic's fake actions
- **Visual aid**: Display "LUNATIC (thinks: [Demon type])" clearly
- **Fake Minions**: Track who was shown as fake Minions to maintain consistency
- **No death**: Lunatic's choices never cause death

---

#### Tinker
**Ability**: "You might die at any time."

**Mechanics**:
- Storyteller can kill Tinker at any time (day or night)
- No warning, no trigger condition
- Used for game balance
- Death is NOT from Demon or other characters

**Key interactions**:
- **Drunk Tinker**: Can still be killed by Storyteller
- **Poisoned Tinker**: Can still be killed by Storyteller
- **Protection**: Doesn't prevent Storyteller kill (bypasses all protection)
- **Monk/Sailor/Innkeeper**: Doesn't prevent Tinker death
- **Fool**: Doesn't prevent Tinker death (Storyteller kill is absolute)
- **Used for balance**: Kill when needed to balance game or create confusion

**Storyteller tool implementation**:
- **Global button**: "Kill Tinker" available at any time (day or night)
- **No conditions**: Can trigger regardless of Tinker's status
- **Instant death**: Process death immediately when triggered
- **State tracking**: Log {time_of_death: day/night#, reason: "Storyteller arbitrary"}
- **Visual aid**: Display "Tinker - Can die anytime" reminder
- **Storyteller guidance**: Suggest times to consider: "Game stalled? Kill Tinker"
- **Bypasses all**: Death processing skips all protection checks
- **No prevention**: Cannot be stopped by any ability

---

#### Moonchild
**Ability**: "When you learn that you died, publicly choose 1 alive player. Tonight, if it was a good player, they die."

**Mechanics**:
- Triggers when Moonchild learns they died (day or night death)
- Immediately makes public choice of one alive player
- That night: If chosen player is good, they die
- If chosen player is evil: Nothing happens
- Death is NOT from Demon

**Key interactions**:
- **Drunk Moonchild**: Doesn't trigger
- **Poisoned Moonchild**: Doesn't trigger
- **Execution death**: Triggers (makes choice immediately after execution)
- **Night death**: Triggers (woken to make choice)
- **Good choice**: Accidentally kills good player that night
- **Evil choice**: No death (safe)
- **Protection**: Death CAN be prevented (Fool, protections work)
- **One-time**: Only triggers on first death

**Storyteller tool implementation**:
- **Death trigger**:
  - When Moonchild dies AND Moonchild sober/healthy:
    - If day death: Prompt immediately "Moonchild publicly chooses alive player"
    - If night death: Wake Moonchild "Choose alive player (will be public)"
- **Night resolution**:
  - Check chosen player's alignment
  - If good: Kill chosen player that night
  - If evil: No effect
- **State tracking**: Log {died: day/night#, chosen_player, alignment, killed: true/false}
- **Visual aid**: Display "Moonchild choice pending resolution" during day
- **Public announcement**: Moonchild's choice must be made publicly
- **Validation**: Verify Moonchild sober/healthy at death
- **Protection check**: Chosen player's death can be prevented by protections

---

### Minions (4 characters)

#### Godfather
**Ability**: "You start knowing which Outsiders are in play. If 1 died today, choose a player tonight: they die. [-1 or +1 Outsider]"

**Mechanics**:
- Night 1: Learn all Outsiders in play
- Each night: If Outsider died today (execution or other), Godfather kills additional player
- Setup: Modifies Outsider count by -1 or +1 (Storyteller choice)
- Conditional extra kills

**Key interactions**:
- **Drunk Godfather**: Doesn't get Outsider info, can't kill
- **Poisoned Godfather**: Can't kill even if Outsider died
- **Multiple Outsiders**: Killing multiple Outsiders same day only gives one kill
- **Night death**: Outsider dying at night counts for next night
- **Setup modification**: Permanent even if Godfather dies
- **Chambermaid**: Godfather only wakes if Outsider died

**Storyteller tool implementation**:
- **Setup phase**:
  - Godfather in play: Choose +1 or -1 Outsider modifier
  - Apply to character distribution
  - Track which Outsiders are in play
- **Night 1**: Show Godfather list of all Outsiders in play
- **Each night**:
  - Check if any Outsider died since last dusk
  - If yes AND Godfather alive/sober/healthy:
    - Prompt: "Godfather selects player to kill"
  - If no Outsider died: Godfather doesn't wake
- **State tracking**: Log {night#, outsider_died: true/false, kill_target, kill_succeeded}
- **Visual aid**: 
  - Display "Outsider died - Godfather can kill" indicator
  - Show Outsider list for reference
- **Validation**: Check Godfather sober/healthy before granting kill
- **Chambermaid**: Godfather only "woke" if actually made choice

---

#### Devil's Advocate
**Ability**: "Each night, choose a living player (different to last night): if executed tomorrow, they don't die."

**Mechanics**:
- Triggers every night (including first)
- Chooses one living player (must differ from previous night)
- Next day: If chosen player executed, they survive
- No indication ability triggered
- Protection only against execution, not other deaths

**Key interactions**:
- **Drunk Devil's Advocate**: No protection applied
- **Poisoned Devil's Advocate**: No protection applied
- **Can protect anyone**: Demon, Minions, or good players
- **Saves from execution**: Doesn't save from Demon, Assassin, etc.
- **Pacifist**: Can both trigger (Pacifist also saves, redundant)
- **Saint**: If Devil's Advocate saves Saint, good team doesn't lose
- **Virgin trigger**: Doesn't prevent Virgin immediate execution

**Storyteller tool implementation**:
- **Each night prompt**: "Devil's Advocate selects player to protect (must differ from last night)"
- **Validation**:
  - Check previous night's choice
  - Prevent selecting same player
  - Verify player is alive
- **State tracking**: Mark protected player, track {night#, protected_player}
- **Execution resolution**:
  - If protected player executed AND Devil's Advocate sober/healthy:
    - Player survives execution (no death)
  - If Devil's Advocate drunk/poisoned: Normal death
- **Visual aid**: Display previous night's choice as unavailable
- **No indication**: Don't announce Devil's Advocate saved (appears like normal survival)
- **Protection duration**: One day only (next day after choice)

---

#### Assassin
**Ability**: "Once per game, at night*, choose a player: they die, even if for some reason they could not."

**Mechanics**:
- One-time use ability
- Triggers any night EXCEPT first
- Chooses one player
- Bypasses ALL protection and immunities
- Kills "can't die" characters (Sailor, protected players, etc.)

**Key interactions**:
- **Drunk Assassin**: Ability wasted (no kill)
- **Poisoned Assassin**: Ability wasted (no kill)
- **Sailor**: Kills through Sailor protection
- **Innkeeper**: Kills through Innkeeper protection
- **Tea Lady**: Kills through Tea Lady protection
- **Fool**: DOES NOT bypass Fool (Fool explicitly says they "don't die", official ruling)
- **Soldier**: Kills through Soldier protection
- **Mayor**: Death can still bounce (Mayor's ability, not protection)

**Storyteller tool implementation**:
- **Setup**: Mark Assassin ability as "unused"
- **Each night* prompt** (if unused): "Assassin selects player to kill"
- **Kill resolution**:
  - If Assassin sober/healthy: Kill target (bypass all protections)
  - Exception: Check Fool ability (Fool protection still works)
  - If Assassin drunk/poisoned: No kill
  - Mark ability as "used"
- **State tracking**: Log {night#, target, bypassed_protections, killed: true/false}
- **Visual alert**: Display "ASSASSIN KILL - Bypasses protection"
- **Fool exception**: Even Assassin must check Fool's first-death protection
- **Validation**: Prevent use if already used, check Assassin sober/healthy

---

#### Mastermind
**Ability**: "If the Demon dies by execution (ending the game), play for 1 more day. If a player is then executed, their team loses."

**Mechanics**:
- Triggers when Demon executed
- Game continues 1 more day instead of ending
- Next execution (of any player): That player's TEAM loses
- If no execution next day: Good team can win normally

**Key interactions**:
- **Drunk Mastermind**: Game ends normally when Demon executed
- **Poisoned Mastermind**: Game ends normally when Demon executed
- **Good executed**: Good team loses
- **Evil executed**: Evil team loses
- **No execution**: Game continues, good can still win
- **Zombuul fake death**: Doesn't trigger Mastermind (Demon didn't really die)
- **Scarlet Woman**: If transforms, Demon didn't die (Mastermind doesn't trigger)

**Storyteller tool implementation**:
- **Demon execution event**:
  - Check if would end game (Demon actually died, not Zombuul fake)
  - If yes AND Mastermind alive/sober/healthy:
    - Prevent game end
    - Display: "MASTERMIND - Game continues 1 more day"
    - Mark "Mastermind extension active"
  - If Mastermind drunk/poisoned: Normal game end
- **Next day execution**:
  - If Mastermind extension active:
    - When player executed, check their team
    - That team LOSES (opposite team wins)
    - End game
  - If no execution: Good team wins at dusk (or evil if 2 alive)
- **State tracking**: Log {demon_died: day#, extension_active, next_execution_result}
- **Visual alert**: Display "MASTERMIND DAY - Next execution = team loss"
- **Validation**: Check Mastermind sober/healthy at Demon death
- **Game end**: Process team loss correctly based on executed player's team

---

### Demons (4 characters)

#### Zombuul
**Ability**: "Each night*, if no-one died today, choose a player: they die. The 1st time you die, you live but register as dead."

**Mechanics**:
- Triggers every night EXCEPT first
- Only kills if NO daytime death occurred (any death cancels kill)
- First death: Zombuul appears dead but is actually alive
- "Dead" Zombuul still votes, acts at night, and all abilities work
- Second death: Zombuul dies for real

**Key interactions**:
- **Drunk Zombuul**: Can't kill, fake death doesn't work
- **Poisoned Zombuul**: Can't kill, fake death doesn't work
- **No day death**: Execution, Tinker, Gossip, etc. all count as day deaths
- **Night death**: Doesn't prevent Zombuul kill
- **Fake death**: Good team may think they won
- **Detection**: While "dead", still registers as alive Demon to abilities
- **Voting**: Can vote while "dead" (obvious tell)
- **Protection**: Doesn't prevent Zombuul fake death (not real death)

**Storyteller tool implementation**:
- **Setup**: Mark Zombuul "Fake death available"
- **Each night* prompt**:
  - Check if anyone died during previous day
  - If no day deaths AND Zombuul sober/healthy:
    - "Zombuul selects player to kill"
  - If day death occurred: Zombuul doesn't wake
- **Kill condition tracking**: Monitor day deaths carefully
- **First death event**:
  - When Zombuul would die first time AND sober/healthy:
    - Fake death: Change appearance to "dead" but keep alive internally
    - Zombuul still wakes at night
    - Zombuul can still vote
    - Mark "Fake death used"
  - If drunk/poisoned at death: Real death (no fake)
- **State tracking**: Log {night#, day_deaths, killed: player/none, fake_death_active}
- **Visual aid**: 
  - Display "Zombuul - APPEARS DEAD" prominently
  - Show "Actually alive" status to storyteller
- **Second death**: Normal death, game ends (good wins)
- **Detection abilities**: Zombuul registers as alive Demon even while "dead"

---

#### Pukka
**Ability**: "Each night, choose a player: they are poisoned. The previously poisoned player dies then becomes healthy."

**Mechanics**:
- Triggers every night (including first)
- Poison new player each night
- Previous night's poisoned player dies then becomes healthy
- Always exactly one player poisoned
- 1-night delay on deaths

**Key interactions**:
- **Drunk Pukka**: Doesn't poison or kill
- **Poisoned Pukka**: Doesn't poison or kill
- **Night 1**: Poisons player, no death (no previous)
- **Night 2+**: Previous poisoned player dies, new player poisoned
- **Exorcist**: Doesn't prevent previous night's death, only current poison
- **Protection**: Can prevent death, but player already gave false info
- **Death pattern**: Delayed by 1 night (identifiable signature)

**Storyteller tool implementation**:
- **Setup**: Track "Currently poisoned" player (none at start)
- **Each night prompt**: "Pukka selects player to poison"
- **Resolution sequence**:
  1. If player was poisoned last night: Kill them, remove poison
  2. If Pukka sober/healthy: Poison newly selected player
  3. Update "Currently poisoned" tracker
- **State tracking**: Log {night#, new_poison, died_from_previous, currently_poisoned}
- **Visual aid**:
  - Display "Poisoned by Pukka - Dies next night" on poisoned player
  - Show countdown timer
- **Night 1**: Only poison (no death to resolve)
- **Poison duration**: Lasts until death next night
- **Validation**: Check Pukka sober/healthy before poisoning

---

#### Shabaloth
**Ability**: "Each night*, choose 2 players: they die. A dead player you chose last night might be regurgitated."

**Mechanics**:
- Triggers every night EXCEPT first
- Kills 2 players per night
- Previous night's victim might be resurrected (Storyteller choice)
- Resurrection happens before new kills
- High kill rate

**Key interactions**:
- **Drunk Shabaloth**: Can't kill or regurgitate
- **Poisoned Shabaloth**: Can't kill or regurgitate
- **Protection**: Can prevent kills
- **Regurgitation**: Brings back one of last night's kills (Storyteller choice)
- **Regurgitated player**: Remembers dying, comes back to life
- **"Might"**: Storyteller decides if/when to regurgitate
- **Protected targets**: Don't die, can't be regurgitated later

**Storyteller tool implementation**:
- **Each night* prompt**: "Shabaloth selects 2 players to kill"
- **Resolution sequence**:
  1. Check previous night's kills
  2. If available: Prompt "Regurgitate one of last night's victims?"
  3. If yes: Select which victim to resurrect
  4. Process resurrection
  5. Process new 2 kills (check protections)
- **State tracking**: Log {night#, kill1, kill2, regurgitated_player}
- **Visual aid**: 
  - Display "Shabaloth - 2 kills per night"
  - Show "Available for regurgitation" on previous victims
- **Regurgitation option**: Storyteller choice ("might")
- **Resurrection**: Full return to life (can vote, nominate, ability works)
- **Validation**: Check Shabaloth sober/healthy, check kill protections

---

#### Po
**Ability**: "Each night*, you may choose a player: they die. If your last choice was no-one, choose 3 players tonight."

**Mechanics**:
- Triggers every night EXCEPT first
- Can choose 1 player OR choose nobody
- If previous night was nobody: MUST choose 3 players this night
- Alternating pattern: 0→3, or consistent 1s
- Cannot choose dead players for 3-kill

**Key interactions**:
- **Drunk Po**: Can't kill
- **Poisoned Po**: Can't kill
- **Skip night**: Choosing nobody sets up 3-kill next night
- **3-kill obvious**: Very identifiable pattern
- **Exorcist**: Prevents all kills (0 or 3)
- **Protection**: Each kill checked separately
- **Night 2**: Po can skip or kill 1 (hasn't skipped yet)

**Storyteller tool implementation**:
- **Setup**: Track "Previous choice" (none at start)
- **Each night* prompt**:
  - If previous was nobody: "Po MUST select 3 players"
  - If previous was 1 or start: "Po selects 1 player OR nobody"
- **Kill resolution**:
  - If 1 kill: Process normally (check protection)
  - If 0 kills: Mark "Previous = nobody"
  - If 3 kills: Process each separately (check protections for each)
- **State tracking**: Log {night#, choice: 0/1/3, targets, previous_choice}
- **Visual aid**: 
  - Display "Po previous choice: [0/1]"
  - If previous=0: "MUST choose 3 tonight"
- **Validation**: 
  - Check Po sober/healthy
  - If must choose 3, enforce exactly 3 selections
  - Can only select alive players
- **Strategy tracking**: Show kill pattern for storyteller (0-3-1-1-0-3...)

---

## SECTS & VIOLETS (Intermediate/Advanced Edition)

Chaos edition. Characters change alignment, change characters, get tons of info but it's crazy unreliable. Madness mechanic adds mandatory lying.

### Townsfolk (13 characters)

#### Clockmaker
**Ability**: "You start knowing how many steps from the Demon to its nearest Minion."

**Mechanics**:
- Night 1 only: Learn number of seats between Demon and closest Minion
- Counts shortest path around circle (clockwise or counterclockwise)
- 0 = Demon adjacent to Minion
- Number fixed at game start, doesn't update

**Key interactions**:
- **Drunk Clockmaker**: Gets false number
- **Poisoned Clockmaker**: Gets false number
- **Demon/Minion death**: Number doesn't change (based on setup positions)
- **Pit-Hag**: Creating new Demon doesn't update Clockmaker's number
- **Fang Gu transformation**: Number based on original Demon position
- **No Minions**: Depends on script setup (usually N/A or high number)

**Storyteller tool implementation**:
- **Setup phase**:
  - Calculate shortest distance between Demon and each Minion
  - Select minimum distance
  - Store number
- **Night 1**: Show Clockmaker the distance number
- **Distance calculation**:
  - Count seats in both directions around circle
  - Use minimum of two counts
  - Display visual aid showing paths
- **State tracking**: Log {setup_distance, shown_number}
- **Visual aid**: Highlight Demon and closest Minion positions, show both path lengths
- **Validation**: Check Clockmaker sober/healthy before showing accurate number
- **One-time**: Only provides info on Night 1, doesn't update

---

#### Dreamer
**Ability**: "Each night, choose a player (not yourself or Travellers): you learn 1 good & 1 evil character, 1 of which is correct."

**Mechanics**:
- Triggers every night (including first)
- Chooses one player (not self, not Travellers)
- Shown 2 characters: one good alignment, one evil alignment
- Exactly one of the two matches chosen player's actual character
- Order is random

**Key interactions**:
- **Drunk Dreamer**: Both characters can be false (or both true, Storyteller choice)
- **Poisoned Dreamer**: Both characters can be false (or both true)
- **Can't choose Travellers**: Validation prevents this
- **Demon detection**: Can identify Demon type
- **Character changes**: Shows current character at resolution time
- **Pit-Hag**: If target changed during night, Dreamer sees new character
- **Drunk target**: Dreamer sees actual character (Drunk), not what Drunk thinks

**Storyteller tool implementation**:
- **Each night prompt**: "Dreamer selects player (exclude self and Travellers)"
- **Info generation**:
  - Get target's actual current character
  - If Dreamer sober/healthy:
    - Generate one good character
    - Generate one evil character
    - Ensure one matches target's actual character
    - Randomize order
  - If Dreamer drunk/poisoned:
    - Generate any two characters (one good, one evil)
    - Neither needs to match (or both match, Storyteller choice)
- **State tracking**: Log {night#, target, actual_character, shown_good, shown_evil}
- **Visual aid**: Display target's character highlighted with correct one
- **Validation**: Prevent selecting self or Travellers
- **Character selection**: Provide dropdowns with all good/evil characters for generation

---

#### Snake Charmer
**Ability**: "Each night, choose an alive player: a chosen Demon swaps characters & alignments with you & is then poisoned."

**Mechanics**:
- Triggers every night (including first)
- Chooses one alive player
- If chosen player is Demon: Complete swap occurs
  - Snake Charmer becomes evil Demon
  - Former Demon becomes good poisoned Snake Charmer
- If chosen player is NOT Demon: Nothing happens
- Can choose self (guarantees no swap)

**Key interactions**:
- **Drunk Snake Charmer**: No swap occurs
- **Poisoned Snake Charmer**: No swap occurs
- **Former Demon**: Becomes good, is poisoned (ability doesn't work)
- **New Demon**: Doesn't learn Minions, starts fresh
- **Alignment swap**: Both players swap teams
- **Can choose self**: Safe play to avoid swapping
- **Multiple swaps**: Can swap back if chosen again
- **Win condition**: New Demon wins with evil, former Demon wins with good

**Storyteller tool implementation**:
- **Each night prompt**: "Snake Charmer selects alive player"
- **Swap resolution**:
  - Check if chosen player is current Demon
  - If yes AND Snake Charmer sober/healthy:
    - Swap characters: Snake Charmer ↔ Demon
    - Swap alignments: Snake Charmer becomes evil, Demon becomes good
    - Apply poison to new Snake Charmer (former Demon)
    - Mark swap in game state
  - If no: No effect
- **State tracking**: Log {night#, chosen_player, is_demon, swapped: true/false}
- **Visual aid**:
  - Display "SNAKE CHARMER SWAP" alert if swap occurs
  - Show alignment changes prominently
  - Mark new Snake Charmer as poisoned
- **Validation**: Check Snake Charmer sober/healthy, verify chosen player alive
- **Info for players**: New Demon doesn't get Minion info (disadvantaged)
- **Poison tracking**: New Snake Charmer poisoned (ability doesn't work)

---

#### Mathematician
**Ability**: "Each night, you learn how many players' abilities worked abnormally (since dawn) due to another character's ability."

**Mechanics**:
- Triggers every night (including first)
- Counts players whose abilities malfunctioned since dawn
- "Abnormally" means: didn't work as expected due to another ability
- Only counts changes caused by other characters, not setup conditions
- Drunk/poisoned count as abnormal

**Key interactions**:
- **Drunk Mathematician**: Gets false number
- **Poisoned Mathematician**: Gets false number
- **What counts**:
  - Poisoner poisoning someone
  - No Dashii poisoning neighbors
  - Vigormortis poisoning
  - Cerenovus madness preventing ability
  - Philosopher drunk original character
  - Drunk/poisoned players (ability doesn't work normally)
- **What doesn't count**:
  - Setup drunk (Drunk character, Sailor's drunk choice, Innkeeper's drunk choice)
  - Pit-Hag changing character (not "abnormal", new character works normally)
  - Abilities that failed due to being dead
- **Timing**: Counts from dawn to dusk (full day + night)

**Storyteller tool implementation**:
- **Each night tracking**:
  - Monitor all abilities that trigger since dawn
  - Track which abilities are modified by other characters:
    - Poisoner targets
    - No Dashii neighbors
    - Vigormortis poisoned Townsfolk
    - Cerenovus madness victims (if prevents ability)
    - Philosopher source character
    - Any drunk/poisoned players
  - Count unique players affected
- **State tracking**: Log {night#, affected_players: [list], count}
- **Visual aid**: Display list of "abnormal" players for Storyteller reference
- **Count calculation**: Unique players whose abilities didn't work normally
- **Validation**: Check Mathematician sober/healthy before showing accurate count
- **Reset**: Clear tracking list at dawn each day

---

#### Flowergirl
**Ability**: "Each night*, you learn if a Demon voted today."

**Mechanics**:
- Triggers every night EXCEPT first
- Learn YES or NO: Did current Demon vote today?
- Any vote counts (nomination vote, execution vote, hand raise)
- Tracks current Demon only

**Key interactions**:
- **Drunk Flowergirl**: Gets false info
- **Poisoned Flowergirl**: Gets false info
- **Fang Gu transformation**: Tracks new Demon after transformation
- **Snake Charmer swap**: Tracks current Demon (may change during day)
- **Dead Demon**: If Demon died during day, usually NO (wasn't Demon when voted)
- **Demon can avoid**: Demon can choose not to vote
- **All votes count**: Nomination, execution, any hand raise during day

**Storyteller tool implementation**:
- **Day vote tracking**:
  - Monitor all votes during day phase
  - Track which player is current Demon at each vote
  - Flag if Demon voted at any point
- **Night* prompt**: Automatic info generation
- **Info generation**:
  - Check if current Demon voted during previous day
  - If Flowergirl sober/healthy: Show accurate YES/NO
  - If Flowergirl drunk/poisoned: Show false info
- **State tracking**: Log {night#, demon_voted: true/false, shown_info}
- **Visual aid**: Display vote tracking with Demon indicator
- **Edge case**: If Demon changed during day (Snake Charmer), track all players who were Demon
- **Validation**: Check Flowergirl sober/healthy before providing accurate info

---

#### Town Crier
**Ability**: "Each night*, you learn if a Minion nominated today."

**Mechanics**:
- Triggers every night EXCEPT first
- Learn YES or NO: Did any Minion nominate today?
- Only nominations count (not votes on nominations)
- Any Minion nominating triggers YES

**Key interactions**:
- **Drunk Town Crier**: Gets false info
- **Poisoned Town Crier**: Gets false info
- **Dead Minions**: Count if they nominated
- **Pit-Hag created Minions**: Count if they nominated
- **Vigormortis killed Minions**: Still count as Minions
- **Only nomination**: Voting on nominations doesn't count, must nominate someone
- **Multiple Minions**: If any Minion nominated = YES

**Storyteller tool implementation**:
- **Day nomination tracking**:
  - Monitor all nominations during day
  - Track which players are Minions at time of nomination
  - Flag if any Minion nominated
- **Night* prompt**: Automatic info generation
- **Info generation**:
  - Check if any Minion nominated during previous day
  - If Town Crier sober/healthy: Show accurate YES/NO
  - If Town Crier drunk/poisoned: Show false info
- **State tracking**: Log {night#, minion_nominated: true/false, which_minions, shown_info}
- **Visual aid**: Display nomination tracking with Minion indicators
- **Validation**: Check Town Crier sober/healthy before providing accurate info
- **Character changes**: If player became Minion during day (Pit-Hag), check if they nominated AFTER becoming Minion

---

#### Oracle
**Ability**: "Each night*, you learn how many dead players are evil."

**Mechanics**:
- Triggers every night EXCEPT first
- Counts dead evil players
- Includes all evil alignments: Demons, Minions, evil Outsiders (Goon), evil Townsfolk (Snake Charmer)
- Updates nightly as deaths and alignment changes occur

**Key interactions**:
- **Drunk Oracle**: Gets false number
- **Poisoned Oracle**: Gets false number
- **Goon alignment change**: If Goon dead, count updates as alignment changes
- **Snake Charmer swap**: Former Demon now good (doesn't count), former Snake Charmer now evil (counts if dead)
- **Fang Gu transformation**: Demon jumps to Outsider, new Demon counts as evil
- **Pit-Hag**: Alignment changes affect count
- **All dead evil**: Includes players who died any time, not just tonight

**Storyteller tool implementation**:
- **Each night* tracking**:
  - Count all dead players
  - Check current alignment of each dead player
  - Count how many are evil
- **Info generation**:
  - If Oracle sober/healthy: Show accurate count
  - If Oracle drunk/poisoned: Show false number
- **State tracking**: Log {night#, dead_evil_count, dead_players: [list with alignments]}
- **Visual aid**: Display dead players with current alignments highlighted
- **Dynamic updates**: Recalculate each night (alignment changes persist)
- **Validation**: Check Oracle sober/healthy before providing accurate count
- **Endgame value**: Very powerful for determining if evil players were executed

---

#### Savant
**Ability**: "Each day, you may visit the Storyteller to learn 2 things in private: 1 is true & 1 is false."

**Mechanics**:
- Triggers each day (may request, not required)
- Storyteller provides 2 statements
- Exactly one statement is true, one is false
- Order is random (Storyteller choice)
- Completely open-ended (can be about anything)

**Key interactions**:
- **Drunk Savant**: Both statements can be false (or both true, Storyteller choice)
- **Poisoned Savant**: Both statements can be false (or both true)
- **Vortox**: Info still inverted (normal for Vortox)
- **Can ask about**: Characters, alignments, Demon identity, Minion count, anything
- **Storyteller discretion**: Storyteller chooses what 2 statements to provide
- **Strategic questioning**: Savant should guide what info they want

**Storyteller tool implementation**:
- **Day prompt** (optional): "Savant requests info"
- **Statement generation**:
  - Storyteller creates 2 statements about game state
  - If Savant sober/healthy:
    - One statement must be true
    - One statement must be false
    - Randomize order
  - If Savant drunk/poisoned:
    - Both can be false (or both true)
- **State tracking**: Log {day#, statement1, statement2, which_true, shown_to_savant}
- **Visual aid**: Display statement generator interface for Storyteller
- **Private delivery**: Statements shown only to Savant, not public
- **Validation**: Check Savant sober/healthy to determine if 1T/1F rule applies
- **Flexibility**: Storyteller has complete freedom in statement content

---

#### Seamstress
**Ability**: "Once per game, at night, choose 2 players (not yourself): you learn if they are the same alignment."

**Mechanics**:
- One-time use ability
- Triggers any night (Storyteller choice when to offer)
- Chooses 2 players (can't choose self)
- Learn YES (same alignment) or NO (different alignments)
- Checks alignment at resolution time

**Key interactions**:
- **Drunk Seamstress**: Gets false info
- **Poisoned Seamstress**: Gets false info
- **Alignment changes**: Goon, Snake Charmer changes affect result if occur before resolution
- **Timing**: Checks alignments at time of ability resolution
- **Both good or both evil**: YES
- **One good, one evil**: NO
- **Can't choose self**: Validation prevents this
- **One-time**: After use, ability is exhausted

**Storyteller tool implementation**:
- **Setup**: Mark Seamstress ability as "unused"
- **Night prompt** (if unused): "Seamstress selects 2 players (not self)"
- **Validation**: Prevent selecting self, require exactly 2 different players
- **Alignment check**:
  - Get both players' current alignments
  - If both good OR both evil: YES
  - If one good, one evil: NO
  - If Seamstress sober/healthy: Show accurate result
  - If Seamstress drunk/poisoned: Show false result
- **State tracking**: Log {night#, player1, player2, actual_alignments, same: true/false, shown_result}
- **Visual aid**: Display both players with alignments highlighted
- **Mark used**: After use, mark ability as "used" (can't use again)
- **Validation**: Check Seamstress sober/healthy before providing accurate info

---

#### Philosopher
**Ability**: "Once per game, at night, choose a good character: gain that ability. If this character is in play, they are drunk."

**Mechanics**:
- One-time use ability
- Triggers any night (Storyteller choice when to offer)
- Chooses any good character (Townsfolk or Outsider)
- Gains that character's ability
- If chosen character is in play, that player becomes drunk
- Philosopher remains Philosopher (character doesn't change)

**Key interactions**:
- **Drunk Philosopher**: Ability wasted, no gain, no drunk applied
- **Poisoned Philosopher**: Ability wasted, no gain, no drunk applied
- **Gained ability**: Works as if Philosopher has that character's ability
- **Original character drunk**: If character in play, they're drunk (ability doesn't work)
- **Character stays Philosopher**: Detection sees Philosopher, not gained ability
- **Multiple characters**: If 2 of same character, both get drunk
- **Can gain**: Slayer, Ravenkeeper, powerful abilities
- **Mathematician**: Philosopher gaining ability counts as "abnormal"

**Storyteller tool implementation**:
- **Setup**: Mark Philosopher ability as "unused"
- **Night prompt** (if unused): "Philosopher selects good character to gain"
- **Ability gain**:
  - If Philosopher sober/healthy:
    - Grant Philosopher the chosen character's ability
    - Check if that character is in play
    - If yes: Apply drunk to that player
    - Mark ability as "used"
  - If Philosopher drunk/poisoned: No effect, ability wasted
- **State tracking**: Log {night#, chosen_character, in_play: true/false, drunk_applied_to, gained_ability}
- **Visual aid**: 
  - Display "Philosopher has [character] ability"
  - Mark original character as drunk if applicable
- **Ability tracking**: Philosopher now uses gained ability each night/day
- **Validation**: Check Philosopher sober/healthy before applying effect
- **One-time**: After use (successful or wasted), can't use again

---

#### Artist
**Ability**: "Once per game, during the day, privately ask the Storyteller any yes/no question."

**Mechanics**:
- One-time use ability
- Triggers during any day phase
- Ask any yes/no question
- Storyteller answers truthfully
- Question and answer are private

**Key interactions**:
- **Drunk Artist**: May get false answer (Storyteller choice)
- **Poisoned Artist**: May get false answer (Storyteller choice)
- **Vortox**: Answer inverted (lies)
- **Any question**: Can ask about Demon identity, Minion identity, character types, alignments, anything
- **Completely flexible**: No restrictions on question content
- **Private**: Nobody else hears question or answer
- **One-time**: After asking, ability exhausted

**Storyteller tool implementation**:
- **Setup**: Mark Artist ability as "unused"
- **Day prompt** (if unused): "Artist asks yes/no question (private)"
- **Question interface**: Text input for Artist's question
- **Answer generation**:
  - Storyteller determines truthful answer to question
  - If Artist sober/healthy: Provide truthful answer
  - If Artist drunk/poisoned: Storyteller may lie (optional)
  - If Vortox: Invert answer
- **State tracking**: Log {day#, question, actual_answer, given_answer}
- **Private delivery**: Show answer only to Artist
- **Mark used**: After asking, mark ability as "used"
- **Validation**: Check Artist sober/healthy, note if answer may be false
- **Storyteller guidance**: Provide context for answering complex questions

---

#### Juggler
**Ability**: "On your 1st day, publicly guess up to 5 players' characters. That night, you learn how many you got correct."

**Mechanics**:
- Day 1 only: Make public guesses (0-5 players)
- Must be public (announced to all players)
- Can guess up to 5 players' characters
- Night 1: Learn number correct (0-5)
- One-time ability

**Key interactions**:
- **Drunk Juggler**: Gets false number
- **Poisoned Juggler**: Gets false number
- **Must be public**: Guesses announced to all, not private
- **Character accuracy**: Checked against actual characters at Night 1
- **Can guess 0-5**: Doesn't have to guess all 5
- **Drunk target**: Juggler guesses actual character (Drunk), not what Drunk thinks
- **Travellers**: Can guess Travellers

**Storyteller tool implementation**:
- **Day 1 prompt**: "Juggler publicly guesses up to 5 players' characters"
- **Guess recording**:
  - Log each guess: {player, guessed_character}
  - Must be public (announce to all players)
  - Maximum 5 guesses
- **Night 1 calculation**:
  - For each guess, check if guessed_character matches player's actual character
  - Count number of correct guesses
  - If Juggler sober/healthy: Show accurate count
  - If Juggler drunk/poisoned: Show false count
- **State tracking**: Log {guesses: [{player, guess, actual, correct}], total_correct, shown_count}
- **Visual aid**: Display guesses with checkmarks/X for Storyteller reference
- **Validation**: Check Juggler sober/healthy at Night 1 before providing accurate count
- **Public requirement**: Ensure guesses are announced to all players
- **One-time**: Only Day 1, only get count Night 1

---

#### Sage
**Ability**: "If the Demon kills you, you learn that it is 1 of 2 players."

**Mechanics**:
- Triggers only when Demon kills Sage at night
- Immediately learn 2 players
- Exactly one of the 2 is the Demon
- The other is not the Demon
- Sage learns this before dying (can share info)

**Key interactions**:
- **Drunk Sage**: Doesn't trigger (both players can be false)
- **Poisoned Sage**: Doesn't trigger (both players can be false)
- **Only Demon kill**: Execution, Assassin, Godfather, etc. don't trigger
- **Imp starpass**: Doesn't trigger (not a kill)
- **Other deaths**: Don't trigger
- **Can share info**: Sage learns before dying (can whisper, claim, etc.)
- **Night wake**: Sage woken to receive info

**Storyteller tool implementation**:
- **Demon kill event**:
  - When Demon kills Sage at night:
    - Check if Sage sober/healthy
    - If yes:
      - Select Demon
      - Select one other player (not Demon)
      - Wake Sage
      - Show Sage both players: "One of these is the Demon"
      - Randomize order
    - If Sage drunk/poisoned: No info (or false info)
- **State tracking**: Log {night#, shown_player1, shown_player2, which_is_demon}
- **Visual aid**: Display 2 players shown to Sage with Demon marked for Storyteller
- **Timing**: Sage learns info before dying (can attempt to share)
- **Validation**: Check Sage sober/healthy before triggering
- **Death types**: Only Demon kill triggers (not execution, Assassin, etc.)

---

### Outsiders (4 characters)

#### Mutant
**Ability**: "If you are "mad" about being an Outsider, you might be executed."

**Mechanics**:
- Madness requirement: Must convincingly act like NOT Mutant
- If Storyteller judges madness insufficient, Mutant can be executed
- Judgment is Storyteller's discretion
- Creates pressure to appear as non-Outsider

**Key interactions**:
- **Drunk Mutant**: Still subject to execution (madness still required)
- **Poisoned Mutant**: Still subject to execution
- **Madness definition**: Acting like you're not an Outsider (claiming Townsfolk, etc.)
- **Storyteller judgment**: Subjective call on sufficient madness
- **Execution trigger**: Storyteller may choose to execute if madness fails
- **Can execute anytime**: Day or night, Storyteller choice

**Storyteller tool implementation**:
- **Setup**: Mark Mutant with "Madness: Outsider" requirement
- **Madness tracking**:
  - Monitor Mutant's claims and behavior
  - Assess if acting "mad about being Outsider" (claiming non-Outsider)
  - Storyteller judgment interface: "Is Mutant sufficiently mad?"
- **Execution option**: "Execute Mutant for insufficient madness" button available anytime
- **State tracking**: Log {madness_assessment, execution_triggered: true/false}
- **Visual aid**: Display madness requirement reminder
- **Judgment guidance**: Provide examples of sufficient/insufficient madness
- **Discretionary**: Storyteller choice whether to execute ("might")

---

#### Sweetheart
**Ability**: "When you die, 1 player is drunk from now on."

**Mechanics**:
- Triggers when Sweetheart dies (any death type)
- Storyteller chooses one player
- That player becomes drunk permanently (rest of game)
- Cannot be undone

**Key interactions**:
- **Drunk Sweetheart**: Doesn't trigger (no permanent drunk applied)
- **Poisoned Sweetheart**: Doesn't trigger
- **Death type**: Any death triggers (execution, Demon, etc.)
- **Permanent**: Drunk lasts entire rest of game
- **Can drunk Demon**: Legal and powerful
- **Can drunk key Townsfolk**: Can disrupt good team
- **Storyteller choice**: Who gets drunk is strategic decision

**Storyteller tool implementation**:
- **Death trigger**:
  - When Sweetheart dies AND Sweetheart sober/healthy:
    - Prompt: "Sweetheart died - Select player to drunk permanently"
    - Storyteller selects one player
    - Apply permanent drunk status
- **State tracking**: Log {died: day/night#, drunk_player, permanent: true}
- **Visual aid**: Display "SWEETHEART DRUNK - PERMANENT" on affected player
- **Permanent marker**: Different visual from temporary drunk
- **Validation**: Check Sweetheart sober/healthy at death
- **Cannot remove**: Drunk status persists rest of game

---

#### Barber
**Ability**: "If you died today or tonight, the Demon may choose 2 players (not another Demon) to swap characters."

**Mechanics**:
- If Barber died since last dusk: Demon gets option to swap characters
- Demon chooses 2 players
- Those 2 players swap characters completely
- Alignments stay with original players (don't swap)
- Can't create duplicate Demons

**Key interactions**:
- **Drunk Barber**: Doesn't offer swap option
- **Poisoned Barber**: Doesn't offer swap option
- **Characters swap**: Players exchange character abilities
- **Alignments stay**: Good stays good, evil stays evil
- **Can't choose Demon**: Prevents creating 2 Demons
- **Optional**: Demon can decline to swap
- **Powerful chaos**: Can move Demon character, disrupt good abilities

**Storyteller tool implementation**:
- **Death tracking**: Monitor if Barber died since last dusk
- **Night prompt** (if Barber died):
  - Ask Demon: "Barber died - Choose 2 players to swap characters (optional)"
  - Validation: Can't select another Demon (only 1 Demon allowed)
- **Character swap**:
  - If Demon chooses AND Barber sober/healthy:
    - Swap player1's character with player2's character
    - Alignments remain unchanged
    - Both players now use new character abilities
- **State tracking**: Log {died: day/night#, swap_offered, players_swapped, characters}
- **Visual aid**: Display "BARBER SWAP" with character changes highlighted
- **Validation**: Check Barber sober/healthy at death, prevent Demon selection
- **Grimoire update**: Show new characters clearly

---

#### Klutz
**Ability**: "When you learn that you died, publicly choose 1 alive player: if they are evil, your team loses."

**Mechanics**:
- Triggers when Klutz learns they died
- Must immediately make public choice of one alive player
- Check chosen player's alignment
- If evil: Good team loses instantly, game ends
- If good: No effect

**Key interactions**:
- **Drunk Klutz**: Doesn't trigger (no choice required)
- **Poisoned Klutz**: Doesn't trigger
- **Timing**: "Learn that you died" (day or night)
- **Public choice**: Must announce choice to all players
- **Evil choice**: Instant good team loss
- **Good choice**: Safe, no penalty
- **High stakes**: Can lose game for good team with wrong choice

**Storyteller tool implementation**:
- **Death trigger**:
  - When Klutz dies AND Klutz sober/healthy:
    - If day death: Prompt immediately "Klutz publicly chooses alive player"
    - If night death: Wake Klutz "Choose alive player (will be public)"
- **Choice resolution**:
  - Check chosen player's alignment
  - If evil: Good team loses, evil team wins, end game
  - If good: No effect
- **State tracking**: Log {died: day/night#, chosen_player, alignment, game_ended: true/false}
- **Visual aid**: Display "KLUTZ CHOICE - High stakes" warning
- **Public announcement**: Klutz's choice must be made publicly
- **Validation**: Verify Klutz sober/healthy at death, verify chosen player alive
- **Game end**: Immediate loss processing if evil chosen

---

### Minions (4 characters)

#### Evil Twin
**Ability**: "You & an opposing player know each other. If the good player is executed, evil wins. Good can't win if you both live."

**Mechanics**:
- Setup: Evil Twin paired with one good player
- Both players learn each other's identity
- Special win conditions:
  - If good twin executed: Evil team wins immediately
  - If both alive at end: Good team cannot win (must kill one)
- Alignment known to each other

**Key interactions**:
- **Drunk Evil Twin**: Both players still know each other (setup info persists)
- **Poisoned Evil Twin**: Win conditions still active
- **Good twin must die**: For good to win, usually good twin dies at night
- **Evil twin execution**: Doesn't cause evil win (only good twin execution)
- **Both alive**: Good cannot win final vote even if Demon dead
- **Claims**: Evil Twin can claim to be the good twin

**Storyteller tool implementation**:
- **Setup phase**:
  - Select one good player as "good twin"
  - Pair with Evil Twin
  - Reveal identities to each other: "You are paired with [player]"
- **Win condition tracking**:
  - Monitor if good twin executed
  - If yes: Evil team wins immediately, end game
  - Monitor if both twins alive at potential good win
  - If both alive: Good cannot win (prevent good victory)
- **State tracking**: Log {good_twin_player, both_alive, good_twin_executed}
- **Visual aid**: Display "EVIL TWIN PAIRING" with both players highlighted
- **Win check**: Always check twin status before declaring good win
- **Execution trigger**: Immediate evil win if good twin executed

---

#### Witch
**Ability**: "Each night, choose a player: if they nominate tomorrow, they die. If just 3 players live, you lose this ability."

**Mechanics**:
- Triggers every night (including first)
- Chooses one player to curse
- Next day: If cursed player nominates anyone, they die immediately
- Ability lost when only 3 players alive (including dead)
- Death is NOT from Demon

**Key interactions**:
- **Drunk Witch**: No curse applied
- **Poisoned Witch**: No curse applied
- **Vigormortis**: If Witch killed by Vigormortis, ability persists when dead
- **3 players**: Ability lost (curse still active from previous night)
- **Nomination = death**: Happens immediately when cursed player nominates
- **Can curse Demon**: Legal but risky
- **Multiple curses**: Only most recent curse active

**Storyteller tool implementation**:
- **Each night prompt**: "Witch selects player to curse"
- **Curse tracking**:
  - Mark cursed player
  - Track {night#, cursed_player}
  - Replace previous curse with new curse
- **Day nomination monitoring**:
  - When any player nominates:
    - Check if they are currently cursed
    - If yes AND Witch sober/healthy when cursed:
      - Kill cursed player immediately
      - Clear curse
- **Player count check**:
  - Monitor living player count
  - If only 3 alive: Disable Witch ability
  - Mark "Witch ability lost - 3 players"
- **State tracking**: Log {cursed_player, curse_active, ability_active}
- **Visual aid**: Display curse icon on cursed player
- **Validation**: Check Witch sober/healthy when curse applied

---

#### Cerenovus
**Ability**: "Each night, choose a player & a good character: they are "mad" they are this character tomorrow, or might be executed."

**Mechanics**:
- Triggers every night (including first)
- Chooses one player and one good character (Townsfolk or Outsider)
- Next day: Chosen player must act "mad" they are that character
- If madness insufficient, Storyteller may execute them
- Forces player to lie convincingly

**Key interactions**:
- **Drunk Cerenovus**: No madness applied
- **Poisoned Cerenovus**: No madness applied
- **Madness definition**: Player must convincingly act as if they are the assigned character
- **Storyteller judgment**: Subjective assessment of madness quality
- **Can make evil mad**: Evil players can be forced to claim good characters
- **Execution optional**: Storyteller discretion ("might")
- **Mathematician**: Cerenovus madness preventing ability counts as "abnormal"

**Storyteller tool implementation**:
- **Each night prompt**: "Cerenovus selects player and good character"
- **Madness assignment**:
  - Mark player with "Mad: [character]"
  - Track {night#, mad_player, mad_character, duration: next_day}
- **Day madness tracking**:
  - Monitor mad player's claims and behavior
  - Storyteller judgment interface: "Is [player] sufficiently mad as [character]?"
  - If insufficient madness: "Execute [player]" button available
- **State tracking**: Log {mad_assignments, madness_assessment, executions}
- **Visual aid**: Display "MAD: [character]" on affected player
- **Validation**: Check Cerenovus sober/healthy when applying madness
- **Duration**: Madness lasts one day (next day after assignment)
- **Judgment guidance**: Examples of sufficient/insufficient madness for different characters

---

#### Pit-Hag
**Ability**: "Each night*, choose a player & a character they become (if not in play). If a Demon is made, deaths tonight are arbitrary."

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses one player and one character
- If chosen character NOT currently in play: Player becomes that character
- If character already in play: No change
- Alignment doesn't change (good stays good, evil stays evil)
- If creating Demon: Storyteller balances with arbitrary deaths

**Key interactions**:
- **Drunk Pit-Hag**: No transformation
- **Poisoned Pit-Hag**: No transformation
- **Can't duplicate**: If character already exists, transformation fails
- **Alignment preserved**: Good player becoming Imp is still good (usually loses immediately)
- **Creating Demons**: Storyteller kills players arbitrarily to balance
- **Character abilities**: Player immediately uses new character's ability
- **Philosopher**: Can transform Philosopher (gains new character)
- **Detection**: Player registers as new character immediately

**Storyteller tool implementation**:
- **Each night* prompt**: "Pit-Hag selects player and character"
- **Validation**:
  - Check if chosen character currently in play
  - If in play: Transformation fails (notify Storyteller)
  - If not in play: Proceed with transformation
- **Transformation**:
  - If Pit-Hag sober/healthy AND character not in play:
    - Change player's character to chosen character
    - Player's alignment stays same
    - Player immediately gains new character's ability
    - Mark transformation in game state
- **Demon creation**:
  - If new character is Demon:
    - Display "DEMON CREATED - Balance with deaths"
    - Storyteller selects players for arbitrary deaths tonight
- **State tracking**: Log {night#, target_player, new_character, old_character, transformation_succeeded, demon_created}
- **Visual aid**: Display "PIT-HAG TRANSFORMATION" with character change
- **Character list**: Show which characters currently in play for validation
- **Validation**: Check Pit-Hag sober/healthy, verify character availability
- **Grimoire update**: Update character tokens immediately

---

### Demons (4 characters)

#### Fang Gu
**Ability**: "Each night*, choose a player: they die. The 1st Outsider this kills becomes an evil Fang Gu & you die instead. [+1 Outsider]"

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses one player to kill
- First time kills an Outsider: Transformation occurs
  - Killed Outsider becomes evil Fang Gu
  - Original Fang Gu dies
- Setup: +1 Outsider to character distribution

**Key interactions**:
- **Drunk Fang Gu**: Can't kill, can't transform
- **Poisoned Fang Gu**: Can't kill, can't transform
- **Outsider protection**: If protected, transformation doesn't occur
- **New Fang Gu**: Doesn't learn Minions, starts fresh
- **Alignment change**: Outsider becomes evil
- **One-time**: Only first Outsider killed triggers transformation
- **Setup modifier**: Permanent +1 Outsider even if Fang Gu dies
- **Fortune Teller**: Tracks new Fang Gu after transformation

**Storyteller tool implementation**:
- **Setup phase**: Add +1 Outsider to character distribution
- **Setup tracking**: Mark Fang Gu "Transformation available"
- **Each night* prompt**: "Fang Gu selects player to kill"
- **Kill resolution**:
  - Process kill normally
  - Check if killed player is Outsider
  - If yes AND Fang Gu sober/healthy AND transformation available:
    - Transform killed Outsider into evil Fang Gu
    - Kill original Fang Gu
    - Mark "Transformation used"
    - Update Demon tracking
  - If killed player protected: No death, no transformation
- **State tracking**: Log {night#, kill_target, is_outsider, transformation_occurred, new_fang_gu}
- **Visual aid**: Display "FANG GU JUMP" when transformation occurs
- **Demon tracking**: Update who is current Demon
- **Validation**: Check Fang Gu sober/healthy, check if transformation already used

---

#### Vigormortis
**Ability**: "Each night*, choose a player: they die. Minions you kill keep their ability & poison 1 Townsfolk neighbor. [-1 Outsider]"

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses one player to kill
- Special effects for killing Minions:
  - Dead Minion keeps ability (works while dead)
  - Dead Minion poisons one Townsfolk neighbor (closest living)
- Setup: -1 Outsider from character distribution

**Key interactions**:
- **Drunk Vigormortis**: Can't kill, Minion effects don't apply
- **Poisoned Vigormortis**: Can't kill, Minion effects don't apply
- **Dead Minion abilities**: Witch, Cerenovus, Pit-Hag all work when dead if killed by Vigormortis
- **Townsfolk neighbor**: Closest living Townsfolk in either direction
- **Poison permanent**: Lasts rest of game (unlike Poisoner)
- **Multiple Minions**: Each killed Minion poisons a neighbor independently
- **Setup modifier**: -1 Outsider permanent
- **Mathematician**: Dead Minion poisoning counts as "abnormal"

**Storyteller tool implementation**:
- **Setup phase**: Remove 1 Outsider from character distribution
- **Each night* prompt**: "Vigormortis selects player to kill"
- **Kill resolution**:
  - Process kill normally
  - Check if killed player is Minion
  - If yes AND Vigormortis sober/healthy:
    - Mark Minion as "Keeps ability when dead"
    - Calculate closest living Townsfolk neighbor
    - Apply permanent poison to that Townsfolk
    - Mark poison as "Vigormortis - Permanent"
- **State tracking**: Log {night#, kill_target, is_minion, neighbor_poisoned, permanent_poison}
- **Visual aid**: 
  - Display "VIGORMORTIS MINION" on killed Minion
  - Show "Ability persists" marker
  - Display permanent poison on Townsfolk neighbor
- **Neighbor calculation**: Auto-find closest living Townsfolk in each direction
- **Dead Minion abilities**: Enable ability for dead Minion (special)
- **Validation**: Check Vigormortis sober/healthy

---

#### No Dashii
**Ability**: "Each night*, choose a player: they die. Your 2 Townsfolk neighbors are poisoned."

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses one player to kill
- Passive effect: No Dashii's 2 closest Townsfolk neighbors are poisoned
- "Neighbors" = closest Townsfolk in each direction (skips non-Townsfolk)
- Poison is permanent while No Dashii alive

**Key interactions**:
- **Drunk No Dashii**: Can't kill, doesn't poison neighbors
- **Poisoned No Dashii**: Can't kill, doesn't poison neighbors
- **Neighbor calculation**: Skips Outsiders, Minions, Demons, dead players
- **Can poison 0, 1, or 2**: Depends on Townsfolk proximity
- **Seating fixed**: Neighbors determined by seating at setup, doesn't change
- **Permanent poison**: Lasts while No Dashii alive and sober/healthy
- **Mathematician**: No Dashii poisoning counts as "abnormal"

**Storyteller tool implementation**:
- **Setup phase**:
  - Calculate No Dashii's position
  - Find closest Townsfolk in clockwise direction (skip non-Townsfolk)
  - Find closest Townsfolk in counterclockwise direction
  - Mark both as "Poisoned by No Dashii"
- **Each night* prompt**: "No Dashii selects player to kill"
- **Kill resolution**: Process kill normally
- **Poison tracking**:
  - Poison active while No Dashii alive/sober/healthy
  - If No Dashii drunk/poisoned: Remove neighbor poison temporarily
  - If No Dashii dies: Remove neighbor poison permanently
- **State tracking**: Log {night#, kill_target, poisoned_neighbors: [left, right]}
- **Visual aid**: 
  - Display "NO DASHII POISON" on both Townsfolk neighbors
  - Show seating diagram with poisoned neighbors highlighted
- **Neighbor calculation**: Auto-find closest Townsfolk, skip dead/non-Townsfolk
- **Validation**: Check No Dashii sober/healthy for poison effect

---

#### Vortox
**Ability**: "Each night*, choose a player: they die. Townsfolk abilities yield false info. Each day, if no-one is executed, evil wins."

**Mechanics**:
- Triggers every night EXCEPT first
- Chooses one player to kill
- Passive effect 1: All Townsfolk abilities get false information
- Passive effect 2: If day ends with no execution, evil team wins immediately

**Key interactions**:
- **Drunk Vortox**: Can't kill, Townsfolk get true info, no execution requirement
- **Poisoned Vortox**: Can't kill, Townsfolk get true info, no execution requirement
- **Info inversion**: All Townsfolk get false info (YES becomes NO, numbers wrong, etc.)
- **Drunk Townsfolk**: Get true info (double negative: Vortox inverts, drunk inverts = true)
- **Poisoned Townsfolk**: Get true info (same double negative)
- **Outsiders not affected**: Sweetheart, Klutz, etc. still work normally
- **Execution requirement**: MUST execute someone each day or evil wins
- **Mathematician**: Vortox inversion doesn't count as "abnormal" (is normal for Vortox)

**Storyteller tool implementation**:
- **Each night* prompt**: "Vortox selects player to kill"
- **Info generation** (all game):
  - For every Townsfolk ability that gives info:
    - If Vortox alive/sober/healthy:
      - Generate false information
      - If Townsfolk drunk/poisoned: Give true info (double negative)
    - If Vortox drunk/poisoned/dead: Normal info
- **Day execution tracking**:
  - Monitor if execution occurred during day
  - At dusk: Check if anyone was executed
  - If no execution AND Vortox alive/sober/healthy:
    - Evil team wins immediately
    - End game
- **State tracking**: Log {night#, kill_target, info_inverted: true, execution_occurred}
- **Visual aid**: 
  - Display "VORTOX - All Townsfolk info FALSE" prominently
  - Show "MUST EXECUTE TODAY" warning during day
  - Countdown/reminder for execution requirement
- **Validation**: Check Vortox sober/healthy for both effects
- **Game end**: Immediate evil win if no execution
