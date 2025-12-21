"""Storyteller stats card generator using Playwright.

Generates gothic-themed image cards for storyteller statistics using
HTML/CSS rendering via Playwright browser automation.
"""
from __future__ import annotations

import base64
import io
import logging
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Any

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

logger = logging.getLogger('botc_bot')


def normalize_username(username: str) -> str:
    """Normalize Unicode characters in username to ASCII equivalents.
    
    Converts fancy Unicode characters (mathematical alphanumerics, decorative
    symbols, etc.) to their ASCII equivalents so they render in web fonts.
    
    Args:
        username: Original username with potentially unsupported Unicode chars
        
    Returns:
        Normalized username with ASCII-compatible characters
    """
    # NFD decomposition separates base characters from combining marks
    normalized = unicodedata.normalize('NFD', username)
    
    # Filter to ASCII-compatible characters and combining marks
    ascii_chars = []
    for char in normalized:
        # Try to get ASCII equivalent via NFKD (compatibility decomposition)
        decomp = unicodedata.normalize('NFKD', char)
        if decomp.isascii():
            ascii_chars.append(decomp)
        elif unicodedata.category(char) not in ('Mn', 'Mc', 'Me', 'Sk', 'So'):
            # If not a modifier/symbol, try decomposition again
            # This handles mathematical alphanumerics like 𝒯 → T
            for c in decomp:
                if c.isascii():
                    ascii_chars.append(c)
    
    result = ''.join(ascii_chars).strip()
    # Fallback to original if normalization produced nothing
    return result if result else username

# Template directory
TEMPLATE_DIR = Path(__file__).parent / 'templates'
ASSETS_DIR = Path(__file__).parent.parent / 'assets'
CARD_WIDTH = 400
CARD_HEIGHT = 750

# Predefined color themes for storyteller cards
COLOR_THEMES = {
    'gold': {
        'primary_color': '#c9a875',
        'secondary_color': '#8b7355',
        'accent_color': '#c9a875',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'silver': {
        'primary_color': '#c0c0c0',
        'secondary_color': '#808080',
        'accent_color': '#e8e8e8',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'crimson': {
        'primary_color': '#dc143c',
        'secondary_color': '#8b0000',
        'accent_color': '#ff6b6b',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'emerald': {
        'primary_color': '#50c878',
        'secondary_color': '#2e8b57',
        'accent_color': '#7fffd4',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'amethyst': {
        'primary_color': '#9966cc',
        'secondary_color': '#663399',
        'accent_color': '#b19cd9',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'sapphire': {
        'primary_color': '#0f52ba',
        'secondary_color': '#082567',
        'accent_color': '#6495ed',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'rose': {
        'primary_color': '#ff69b4',
        'secondary_color': '#c71585',
        'accent_color': '#ffb6c1',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'copper': {
        'primary_color': '#b87333',
        'secondary_color': '#8b4513',
        'accent_color': '#cd7f32',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'midnight': {
        'primary_color': '#4169e1',
        'secondary_color': '#191970',
        'accent_color': '#7b68ee',
        'text_color': '#ffffff',
        'background_color': '#000000'
    },
    'jade': {
        'primary_color': '#00a86b',
        'secondary_color': '#006400',
        'accent_color': '#3cb371',
        'text_color': '#ffffff',
        'background_color': '#000000'
    }
}


async def generate_stats_card(
    username: str,
    avatar_url: str,
    total_games: int,
    good_wins: int,
    evil_wins: int,
    pronouns: Optional[str] = None,
    favorite_script: Optional[str] = None,
    style: Optional[str] = None,
    version: str = "2.0",
    tb_games: int = 0,
    snv_games: int = 0,
    bmr_games: int = 0,
    avg_duration_minutes: Optional[float] = None,
    avg_players: Optional[float] = None,
    custom_title: Optional[str] = None,
    color_theme: Optional[str] = None
) -> Optional[io.BytesIO]:
    """Generate a stats card image from HTML template.
    
    Args:
        username: Discord username or display name
        avatar_url: URL to user's avatar image
        total_games: Total number of games storytold
        good_wins: Number of games won by good team
        evil_wins: Number of games won by evil team
        pronouns: User's preferred pronouns (optional)
        favorite_script: User's favorite script (optional, deprecated)
        style: User's storytelling style (optional, deprecated)
        version: Bot version string for footer
        tb_games: Trouble Brewing games count (optional)
        snv_games: Sects & Violets games count (optional)
        bmr_games: Bad Moon Rising games count (optional)
        avg_duration_minutes: Average game duration in minutes (optional)
        avg_players: Average player count (optional)
        custom_title: Custom title to display (max 15 chars, e.g., "Farmer", "Gamer")
        color_theme: Color theme name (gold, silver, crimson, emerald, amethyst, 
                     sapphire, rose, copper, midnight, jade) or None for default gold
        
    Returns:
        BytesIO containing PNG image data, or None if generation fails
    """
    try:
        # Normalize username to ASCII-compatible characters
        normalized_username = normalize_username(username)
        
        # Calculate percentages and balance
        good_rate = round((good_wins / total_games * 100) if total_games > 0 else 0, 1)
        evil_rate = round((evil_wins / total_games * 100) if total_games > 0 else 0, 1)
        
        # Calculate balance (-100 to 100 scale)
        if total_games > 0:
            balance_raw = ((good_wins - evil_wins) / total_games) * 100
            balance_str = f"{balance_raw:+.1f}"
            
            # Determine balance class for styling
            if abs(balance_raw) < 10:
                balance_class = "balanced"
            elif balance_raw > 0:
                balance_class = "good-favored"
            else:
                balance_class = "evil-favored"
        else:
            balance_str = "N/A"
            balance_class = "balanced"
        
        # Convert alignment images to base64 data URLs
        good_icon_path = ASSETS_DIR / 'wiki_images' / 'Generic_townsfolk.png'
        evil_icon_path = ASSETS_DIR / 'wiki_images' / 'Generic_demon.png'
        sparkle_path = ASSETS_DIR / 'sparkle.png'
        
        good_icon_b64 = ""
        evil_icon_b64 = ""
        sparkle_b64 = ""
        
        if good_icon_path.exists():
            with open(good_icon_path, 'rb') as f:
                good_icon_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        
        if evil_icon_path.exists():
            with open(evil_icon_path, 'rb') as f:
                evil_icon_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        
        if sparkle_path.exists():
            with open(sparkle_path, 'rb') as f:
                sparkle_b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        
        # Load and render template
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template('stats_card.html')
        
        # Truncate custom_title to 15 characters if provided
        display_title = "Storyteller"
        if custom_title:
            display_title = custom_title[:15]
        
        # Get color theme
        theme_colors = COLOR_THEMES.get(color_theme, COLOR_THEMES['gold'])
        
        html_content = template.render(
            username=normalized_username,
            avatar_url=avatar_url,
            pronouns=pronouns,
            custom_title=display_title,
            total_games=total_games,
            good_wins=good_wins,
            evil_wins=evil_wins,
            good_rate=good_rate,
            evil_rate=evil_rate,
            balance=balance_str,
            balance_class=balance_class,
            version=version,
            tb_games=tb_games,
            snv_games=snv_games,
            bmr_games=bmr_games,
            avg_duration=avg_duration_minutes,
            avg_players=avg_players,
            good_icon=good_icon_b64,
            evil_icon=evil_icon_b64,
            sparkle_icon=sparkle_b64,
            **theme_colors  # Unpack color theme variables
        )
        
        # Launch browser and render
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            try:
                page = await browser.new_page(
                    viewport={'width': CARD_WIDTH, 'height': CARD_HEIGHT}
                )
                
                # Set content and wait for fonts/images to load
                await page.set_content(html_content)
                await page.wait_for_load_state('networkidle')
                
                # Take screenshot
                screenshot_bytes = await page.screenshot(type='png')
                
                # Return as BytesIO
                return io.BytesIO(screenshot_bytes)
                
            finally:
                await browser.close()
                
    except Exception as e:
        logger.error(f"Failed to generate stats card: {e}", exc_info=True)
        return None


async def generate_stats_card_from_profile(
    user_data: Dict[str, Any],
    stats_data: Dict[str, Any],
    version: str = "2.0"
) -> Optional[io.BytesIO]:
    """Generate stats card from database profile and stats dictionaries.
    
    Convenience wrapper around generate_stats_card() that accepts
    database query results directly.
    
    Args:
        user_data: Dict with keys: username, avatar_url, pronouns, 
                   favorite_script, style
        stats_data: Dict with keys: total_games, good_wins, evil_wins
        version: Bot version string for footer
        
    Returns:
        BytesIO containing PNG image data, or None if generation fails
    """
    return await generate_stats_card(
        username=user_data.get('username', 'Unknown'),
        avatar_url=user_data.get('avatar_url', ''),
        total_games=stats_data.get('total_games', 0),
        good_wins=stats_data.get('good_wins', 0),
        evil_wins=stats_data.get('evil_wins', 0),
        pronouns=user_data.get('pronouns'),
        favorite_script=user_data.get('favorite_script'),
        style=user_data.get('style'),
        version=version
    )
