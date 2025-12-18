"""Storyteller stats card generator using Pillow.

Generates gothic-themed image cards for storyteller statistics with:
- User avatar
- Profile information (pronouns, favorite script, style)
- Game statistics (games played, win rates, averages)
- Dark/gothic aesthetic
"""
from __future__ import annotations

import io
import logging
import aiohttp
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger('botc_bot')

# Card dimensions and styling
CARD_WIDTH = 800
CARD_HEIGHT = 600
BACKGROUND_COLOR = (18, 18, 18)  # Near-black (BOTC primary)
TEXT_COLOR = (240, 240, 240)  # Light gray/white
ACCENT_COLOR = (138, 43, 226)  # Purple (bot accent)
PRIMARY_RED = (139, 0, 0)  # Dark red (BOTC primary)
SECONDARY_RED = (178, 34, 34)  # Firebrick red
CARD_BORDER = (80, 0, 0)  # Very dark red

# Font sizes
FONT_TITLE = 36
FONT_SUBTITLE = 24
FONT_BODY = 18
FONT_SMALL = 14


async def download_avatar(avatar_url: str) -> Optional[Image.Image]:
    """Download and return user avatar as PIL Image.
    
    Args:
        avatar_url: Discord CDN URL for user avatar
        
    Returns:
        PIL Image or None if download fails
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert('RGBA')
    except Exception as e:
        logger.error(f"Failed to download avatar: {e}")
    return None


def create_rounded_rectangle(draw: ImageDraw, bounds: tuple, radius: int, fill: tuple, outline: tuple = None, width: int = 1):
    """Draw a rounded rectangle.
    
    Args:
        draw: ImageDraw object
        bounds: (x1, y1, x2, y2) tuple
        radius: Corner radius
        fill: Fill color tuple
        outline: Outline color tuple (optional)
        width: Outline width
    """
    x1, y1, x2, y2 = bounds
    draw.rounded_rectangle(bounds, radius=radius, fill=fill, outline=outline, width=width)


async def generate_stats_card(
    username: str,
    avatar_url: str,
    stats: Dict[str, Any],
    profile: Optional[Dict[str, Any]] = None
) -> io.BytesIO:
    """Generate storyteller stats card image.
    
    Args:
        username: Discord username
        avatar_url: URL to user's avatar
        stats: Dictionary containing game statistics
        profile: Optional dictionary with profile fields (pronouns, favorite_script, style, bio)
        
    Returns:
        BytesIO object containing PNG image data
    """
    # Create blank image
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts (fallback to default if not available)
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", FONT_TITLE)
        font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", FONT_SUBTITLE)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_BODY)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", FONT_SMALL)
    except:
        logger.warning("Could not load custom fonts, using default")
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Download and process avatar
    avatar = await download_avatar(avatar_url)
    if avatar:
        # Resize and make circular
        avatar_size = 120
        avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        
        # Create circular mask
        mask = Image.new('L', (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        
        # Apply mask
        avatar_circular = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
        avatar_circular.paste(avatar, (0, 0), mask)
        
        # Paste avatar with border
        avatar_x, avatar_y = 40, 40
        # Draw dark red border (BOTC theme)
        draw.ellipse(
            (avatar_x - 4, avatar_y - 4, avatar_x + avatar_size + 4, avatar_y + avatar_size + 4),
            fill=PRIMARY_RED
        )
        img.paste(avatar_circular, (avatar_x, avatar_y), avatar_circular)
    
    # Draw username and profile info
    text_x = 180
    text_y = 50
    
    # Username
    draw.text((text_x, text_y), username, fill=TEXT_COLOR, font=font_title)
    text_y += 45
    
    # Pronouns (if available)
    if profile and profile.get('pronouns'):
        draw.text((text_x, text_y), f"({profile['pronouns']})", fill=(200, 150, 150), font=font_small)
        text_y += 25
    
    # Style (if available)
    if profile and profile.get('style'):
        draw.text((text_x, text_y), f"🎭 {profile['style']}", fill=(220, 160, 160), font=font_body)
        text_y += 30
    
    # Favorite script (if available)
    if profile and profile.get('favorite_script'):
        draw.text((text_x, text_y), f"⭐ {profile['favorite_script']}", fill=(220, 160, 160), font=font_body)
        text_y += 30
    
    # Draw stats section
    stats_y = 240
    
    # Stats header
    draw.text((40, stats_y), "STATISTICS", fill=SECONDARY_RED, font=font_subtitle)
    stats_y += 50
    
    # Calculate rates
    total_games = stats.get('total_games', 0)
    good_wins = stats.get('good_wins', 0)
    evil_wins = stats.get('evil_wins', 0)
    
    good_rate = (good_wins / total_games * 100) if total_games > 0 else 0
    evil_rate = (evil_wins / total_games * 100) if total_games > 0 else 0
    
    # Create stat boxes - 2x2 grid
    col1_x = 60
    col2_x = 420
    row_height = 90
    box_width = 300
    box_height = 75
    
    # Row 1: Total Games and Balance indicator
    create_rounded_rectangle(
        draw,
        (col1_x, stats_y, col1_x + box_width, stats_y + box_height),
        15,
        (30, 30, 30),
        PRIMARY_RED,
        2
    )
    draw.text((col1_x + 20, stats_y + 12), "Total Games", fill=(180, 100, 100), font=font_small)
    draw.text((col1_x + 20, stats_y + 38), str(total_games), fill=TEXT_COLOR, font=font_subtitle)
    
    # Balance indicator
    balance = 'Good-favored' if good_rate > 55 else 'Evil-favored' if evil_rate > 55 else 'Balanced'
    balance_color = (130, 180, 220) if good_rate > 55 else (220, 120, 120) if evil_rate > 55 else (180, 180, 180)
    create_rounded_rectangle(
        draw,
        (col2_x, stats_y, col2_x + box_width, stats_y + box_height),
        15,
        (30, 30, 30),
        PRIMARY_RED,
        2
    )
    draw.text((col2_x + 20, stats_y + 12), "Balance", fill=(180, 100, 100), font=font_small)
    draw.text((col2_x + 20, stats_y + 38), balance, fill=balance_color, font=font_body)
    
    stats_y += row_height
    
    # Row 2: Good wins and Evil wins with percentages
    create_rounded_rectangle(
        draw,
        (col1_x, stats_y, col1_x + box_width, stats_y + box_height),
        15,
        (25, 25, 30),
        (70, 130, 180),  # Blue border
        2
    )
    draw.text((col1_x + 20, stats_y + 12), "Good Wins", fill=(130, 180, 220), font=font_small)
    draw.text((col1_x + 20, stats_y + 38), f"{good_wins} ({good_rate:.1f}%)", fill=TEXT_COLOR, font=font_subtitle)
    
    create_rounded_rectangle(
        draw,
        (col2_x, stats_y, col2_x + box_width, stats_y + box_height),
        15,
        (25, 25, 30),
        SECONDARY_RED,  # Red border
        2
    )
    draw.text((col2_x + 20, stats_y + 12), "Evil Wins", fill=(220, 120, 120), font=font_small)
    draw.text((col2_x + 20, stats_y + 38), f"{evil_wins} ({evil_rate:.1f}%)", fill=TEXT_COLOR, font=font_subtitle)
    
    # Footer
    draw.text((40, CARD_HEIGHT - 30), "Grimkeeper", fill=(80, 60, 60), font=font_small)
    
    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer
