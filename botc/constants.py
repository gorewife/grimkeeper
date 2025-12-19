"""Constants for Grimkeeper (extracted from main.py).

This module centralizes configuration values and mappings so they can be
imported by other modules as part of a gradual refactor.
"""
from __future__ import annotations

VERSION = "1.7.3"

# ============================================================================
# COLOR PALETTE - Grimkeeper Theme
# ============================================================================
# Primary colors for consistent visual identity across all embeds

# Main bot color - deep purple, evocative of mystery and night
COLOR_PRIMARY = 0x4A235A

# Team colors (official BOTC)
COLOR_GOOD = 0x5DADE2      # Townsfolk blue - good team wins
COLOR_EVIL = 0x641E16      # Blood red - evil team wins, errors
COLOR_TIE = 0x566573       # Moonlight silver - tie games

# Accent colors
COLOR_GOLD = 0x7D6608      # Clocktower gold - important announcements, highlights
COLOR_SHADOW = 0x1C2833    # Shadow gray - secondary info, muted content
COLOR_SPECTRAL = 0x6C3483  # Spectral purple - special events, dramatic moments

# Status colors
COLOR_SUCCESS = 0x27AE60   # Green - confirmations, success messages
COLOR_WARNING = 0xE67E22   # Orange - warnings, alerts
COLOR_ERROR = 0x641E16     # Blood red - errors, failures
COLOR_INFO = 0x566573      # Silver - neutral information

# ============================================================================
# NICKNAME PREFIX CONSTANTS
# ============================================================================

# Nickname prefix constants
PREFIX_ST = "(ST) "
PREFIX_COST = "(Co-ST) "
PREFIX_SPEC = "!"
PREFIX_BRB = "[BRB] "

# Message deletion delays (in seconds)
DELETE_DELAY_QUICK = 2      # Quick confirmations
DELETE_DELAY_NORMAL = 3     # Normal feedback messages
DELETE_DELAY_MEDIUM = 4     # Medium-length messages
DELETE_DELAY_CONFIRMATION = 4  # Action confirmations (timer cancel, etc.)
DELETE_DELAY_ERROR = 5      # Error messages
DELETE_DELAY_INFO = 8       # Informational messages
DELETE_DELAY_LONG = 10      # Long-form content
DELETE_DELAY_DRAMATIC = 15  # Timer completions, dramatic announcements

# Duration limits
MAX_DURATION_SECONDS = 86400  # 24 hours - cap for timers and polls

# Poll defaults
DEFAULT_POLL_DURATION = 300  # 5 minutes in seconds
MAX_POLL_DURATION = MAX_DURATION_SECONDS  # 24 hours in seconds

# Rate limiting
COMMAND_COOLDOWN_SECONDS = 2  # Minimum seconds between commands per user
COMMAND_COOLDOWN_LONG = 30  # Longer cooldown for heavy info commands

# Discord limits
MAX_NICK_LENGTH = 32  # Maximum length for Discord nicknames

# Commands that should be deleted for cleaner chat
DELETABLE_COMMANDS = [
    "*!", "*st", "*cost", "*brb", "*help", "*g", "*spec", "*unspec",
    "*shadows", "*dnd", "*settown", "*setbotc", "*setannounce", "*call",
    "*players", "*timer", "*changelog", "*config", "*night", "*day", "*poll",
    "*mute", "*unmute"
]

# Script emojis
SCRIPT_EMOJI_TB = "🍺"  # Beer mug for Trouble Brewing
SCRIPT_EMOJI_SNV = "🪻"  # Violet for Sects & Violets
SCRIPT_EMOJI_BMR = "🌙"  # Crescent moon for Bad Moon Rising

# Team icons from BOTC Wiki
ICON_GOOD = "https://wiki.bloodontheclocktower.com/images/1/12/Generic_townsfolk.png"
ICON_EVIL = "https://wiki.bloodontheclocktower.com/images/5/52/Generic_demon.png"

# Custom Discord emojis (latest uploads)
EMOJI_SECTS_AND_VIOLETS = "<:sects_and_violets:1443464437309636618>"
EMOJI_BAD_MOON_RISING = "<:bad_moon_rising:1443464418317963314>"
EMOJI_TOWN_SQUARE = "<:town_square:1443463539397365981>"
EMOJI_SWORD = "<:sword:1443463537879023676>"
EMOJI_SCRIPT = "<:script:1443463534766981181>"
EMOJI_PLAYERS = "<:players:1443463533449707631>"
EMOJI_GOOD = "<:good:1443463532422365216>"
EMOJI_GOOD_WIN = "<:good_win:1443463531511943208>"
EMOJI_EVIL = "<:evil:1443463530614358106>"
EMOJI_EVIL_WIN = "<:evil_win:1443463529523974225>"
EMOJI_CLOCK = "<:clock:1443463528185991238>"
EMOJI_CANDLE = "<:candle:1443463526839746641>"
EMOJI_TROUBLE_BREWING = "<:trouble_brewing:1443463389098676264>"
EMOJI_GEAR = "<:gear:1446681347631612147>"
EMOJI_THUMBSUP = "<:thumbsup:1446681223429623949>"
EMOJI_SCROLL = "<:scroll:1446681141888417942>"
EMOJI_BALANCE = "<:balance:1446680909192368299>"
EMOJI_SCRIPT2 = "<:script2:1446680727839183008>"
EMOJI_HEART = "<:heart:1446680613523427338>"
EMOJI_QUESTION = "<:question:1446680489006993439>"
EMOJI_PLANET = "<:planet:1446680422116233348>"
EMOJI_PEN = "<:pen:1446682438913888316>"
EMOJI_STAR = "<:general_star:1446683877342183445>"

# Database configuration
DATABASE_POOL_MIN_SIZE = 2
DATABASE_POOL_MAX_SIZE = 10
DATABASE_COMMAND_TIMEOUT = 60  # Seconds
DATABASE_QUERY_TIMEOUT = 5.0   # Seconds for individual queries

# Changelog display
MAX_CHANGELOG_VERSIONS = 10  # Maximum versions to show in *changelog

# Discord limits
DISCORD_NICKNAME_MAX_LENGTH = 32
DISCORD_EMBED_MAX_CHARS = 6000
DISCORD_FIELD_MAX_CHARS = 1024

# Poll script options
POLL_SCRIPT_MAP = {
    '1': 'Trouble Brewing',
    '2': 'Sects & Violets',
    '3': 'Bad Moon Rising',
    'c': 'Custom Script',
    'h': 'Homebrew Script'
}

POLL_EMOJI_MAP = {
    '1': EMOJI_TROUBLE_BREWING,
    '2': EMOJI_SECTS_AND_VIOLETS,
    '3': EMOJI_BAD_MOON_RISING,
    'c': '🇨',
    'h': '🇭'
}

POLL_VALID_OPTIONS = set('123ch')
