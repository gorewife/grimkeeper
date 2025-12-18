"""Blood on the Clocktower Wiki API integration.

This module provides functions to fetch and parse character information
from the official BOTC wiki at https://wiki.bloodontheclocktower.com/
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Dict, List
from html.parser import HTMLParser

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger('botc_bot')

WIKI_API_URL = "https://wiki.bloodontheclocktower.com/api.php"
WIKI_BASE_URL = "https://wiki.bloodontheclocktower.com"


class CharacterInfo:
    """Character information parsed from the wiki."""
    
    def __init__(self):
        self.name: str = ""
        self.character_type: str = ""  # Townsfolk, Outsider, Minion, Demon, Traveller, Fabled
        self.team: str = ""  # Good, Evil, Neutral
        self.icon_url: str = ""
        self.summary: str = ""
        self.ability: str = ""
        self.appears_in: List[str] = []
        self.how_to_run: str = ""
        self.tips_and_tricks: str = ""
        self.bluffing: str = ""
        self.fighting: str = ""
        self.wiki_url: str = ""
    
    def get_team_color(self) -> int:
        """Get Discord embed color based on team."""
        if self.team == "Good":
            return 0x3498db  # Blue
        elif self.team == "Evil":
            return 0xe74c3c  # Red
        else:
            return 0x95a5a6  # Gray for neutral/traveller


async def fetch_character(character_name: str) -> Optional[CharacterInfo]:
    """Fetch character information from the BOTC wiki.
    
    Args:
        character_name: Name of the character to look up
        
    Returns:
        CharacterInfo object if found, None otherwise
    """
    # Normalize character name to title case for better matching
    character_name = character_name.strip().title()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Fetch the parsed HTML version of the page
            params = {
                "action": "parse",
                "page": character_name,
                "prop": "text|displaytitle",
                "format": "json",
                "redirects": "1"
            }
            
            async with session.get(WIKI_API_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Wiki API returned status {response.status} for character: {character_name}")
                    return None
                
                data = await response.json()
                
                # Check if page exists
                if "error" in data:
                    logger.debug(f"Character not found: {character_name}")
                    return None
                
                parse_data = data.get("parse", {})
                html_content = parse_data.get("text", {}).get("*", "")
                page_title_raw = parse_data.get("displaytitle", character_name)
                
                # Strip HTML tags from title (e.g., <span class="mw-page-title-main">Fortune Teller</span>)
                title_soup = BeautifulSoup(page_title_raw, 'html.parser')
                page_title = title_soup.get_text(strip=True)
                
                # Parse the HTML content
                char_info = _parse_character_html(html_content, page_title)
                
                if char_info:
                    char_info.name = page_title
                    char_info.wiki_url = f"{WIKI_BASE_URL}/{character_name.replace(' ', '_')}"
                
                return char_info
                
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error fetching character {character_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching character {character_name}: {e}")
        return None


def _parse_character_html(html: str, title: str) -> Optional[CharacterInfo]:
    """Parse character information from wiki HTML.
    
    Args:
        html: HTML content from the wiki
        title: Page title
        
    Returns:
        CharacterInfo object with parsed data
    """
    soup = BeautifulSoup(html, 'html.parser')
    char_info = CharacterInfo()
    
    # Extract character type from the information table
    info_table = soup.find('table')
    if info_table:
        rows = info_table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                
                if key == "Type":
                    char_info.character_type = value
                    # Determine team based on type
                    if value in ["Townsfolk", "Outsider"]:
                        char_info.team = "Good"
                    elif value in ["Minion", "Demon"]:
                        char_info.team = "Evil"
                    elif value == "Traveller":
                        char_info.team = "Neutral"
                    elif value == "Fabled":
                        char_info.team = "Neutral"
    
    # Extract character icon - try multiple strategies
    icon_img = None
    
    # Strategy 1: Look for img with 'icon_' in src
    icon_img = soup.find('img', src=re.compile(r'icon_', re.IGNORECASE))
    
    # Strategy 2: Look for img with 'Icon' in src (capital I)
    if not icon_img:
        icon_img = soup.find('img', src=re.compile(r'Icon', re.IGNORECASE))
    
    # Strategy 3: Look for the first image in character-details div
    if not icon_img:
        details_div = soup.find('div', id='character-details')
        if details_div:
            icon_img = details_div.find('img')
    
    if icon_img:
        icon_src = icon_img.get('src') or icon_img.get('data-src')
        if icon_src:
            # Handle both relative and protocol-relative URLs
            if icon_src.startswith('//'):
                icon_src = 'https:' + icon_src
            elif not icon_src.startswith('http'):
                icon_src = WIKI_BASE_URL + icon_src
            char_info.icon_url = icon_src
            logger.debug(f"Extracted icon URL for {title}: {icon_src}")
        else:
            logger.debug(f"Icon img tag found but no src for {title}")
    else:
        logger.debug(f"No icon found for {title}")
    
    # Extract script logos (appears in)
    script_logos = soup.find_all('img', src=re.compile(r'logo_.*\.png', re.IGNORECASE))
    logger.debug(f"Found {len(script_logos)} script logos for {title}")
    for logo in script_logos:
        src = logo.get('src', '')
        logger.debug(f"Processing logo src: {src}")
        
        if 'logo_' in src.lower():
            # Extract just the script part from path like:
            # /images/thumb/f/f1/Logo_trouble_brewing.png/200px-Logo_trouble_brewing.png
            # or /images/f/f1/Logo_trouble_brewing.png
            match = re.search(r'[Ll]ogo_([^/\.]+)', src)
            if match:
                script_name = match.group(1).replace('_', ' ').title()
                logger.debug(f"Extracted script name: {script_name}")
                # Clean up common variations and avoid duplicates
                if script_name and script_name not in char_info.appears_in:
                    char_info.appears_in.append(script_name)
    
    # Extract sections
    char_info.summary = _extract_section(soup, "Summary")
    char_info.ability = _extract_ability(char_info.summary)
    char_info.how_to_run = _extract_section(soup, "How to Run")
    char_info.tips_and_tricks = _extract_section(soup, "Tips & Tricks")
    
    # Bluffing section - might be "Bluffing as the X" or just "Bluffing"
    bluffing = _extract_section(soup, "Bluffing")
    if not bluffing:
        # Try finding section with "Bluffing as" in the heading
        for heading in soup.find_all(['h2', 'h3']):
            heading_text = heading.get_text(strip=True)
            if "Bluffing" in heading_text:
                bluffing = _extract_section_after_element(heading)
                break
    char_info.bluffing = bluffing
    
    # Fighting section
    fighting = _extract_section(soup, "Fighting")
    if not fighting:
        # Try "How to Fight"
        fighting = _extract_section(soup, "How to Fight")
    char_info.fighting = fighting
    
    return char_info


def _extract_section(soup: BeautifulSoup, section_name: str) -> str:
    """Extract a section from the wiki page by heading name.
    
    Args:
        soup: BeautifulSoup object
        section_name: Name of the section heading
        
    Returns:
        Section content as plain text
    """
    # Find the heading
    heading = soup.find(['h2', 'h3'], id=re.compile(section_name.replace(' ', '_'), re.IGNORECASE))
    if not heading:
        # Try finding by text content
        for h in soup.find_all(['h2', 'h3']):
            if section_name.lower() in h.get_text(strip=True).lower():
                heading = h
                break
    
    if not heading:
        return ""
    
    return _extract_section_after_element(heading)


def _extract_section_after_element(heading) -> str:
    """Extract text content after a heading until the next heading.
    
    Args:
        heading: BeautifulSoup element for the section heading
        
    Returns:
        Section content as plain text
    """
    content_parts = []
    
    # Get all siblings until next heading
    for sibling in heading.find_next_siblings():
        if sibling.name in ['h2', 'h3', 'h4']:
            break
        
        # Skip edit buttons and other non-content elements
        if sibling.name in ['div'] and ('mw-editsection' in sibling.get('class', []) or 'edit-action' in sibling.get('class', [])):
            continue
        
        # Extract text, handling lists specially
        if sibling.name in ['p', 'div']:
            # Remove edit buttons and other UI elements
            for unwanted in sibling.find_all(['span', 'a'], class_=re.compile(r'mw-editsection|edit-action')):
                unwanted.decompose()
            
            text = sibling.get_text(separator=' ', strip=True)
            if text:
                content_parts.append(text)
        elif sibling.name in ['ul', 'ol']:
            for li in sibling.find_all('li'):
                # Remove edit buttons from list items
                for unwanted in li.find_all(['span', 'a'], class_=re.compile(r'mw-editsection|edit-action')):
                    unwanted.decompose()
                
                text = li.get_text(separator=' ', strip=True)
                if text:
                    content_parts.append(f"• {text}")
    
    content = '\n\n'.join(content_parts)
    
    # Clean up wiki formatting artifacts
    content = _clean_wiki_text(content)
    
    return content.strip()


def _clean_wiki_text(text: str) -> str:
    """Clean up wiki formatting artifacts and special tokens.
    
    Args:
        text: Raw text from wiki
        
    Returns:
        Cleaned text
    """
    # Remove wiki reminder tokens (e.g., NO ABILITY, YOU ARE, etc.)
    text = re.sub(r'(?<=[a-z])(?=[A-Z]{2,})', ' ', text)  # Add space before caps tokens
    
    # Common wiki tokens to separate
    wiki_tokens = ['NO ABILITY', 'YOU ARE', 'THESE ARE', 'THESE CHARACTERS ARE']
    for token in wiki_tokens:
        text = text.replace(token, f' **{token}** ')
    
    # Clean up excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Fix common formatting issues
    text = text.replace('  ', ' ')
    text = text.strip()
    
    return text


def _extract_ability(summary: str) -> str:
    """Extract just the ability text from the summary.
    
    The ability is typically in quotes at the start of the summary.
    
    Args:
        summary: Full summary text
        
    Returns:
        Just the ability description
    """
    # Look for text in quotes
    match = re.search(r'"([^"]+)"', summary)
    if match:
        return match.group(1)
    
    # Fallback: first paragraph
    lines = summary.split('\n')
    return lines[0] if lines else summary


def truncate_text(text: str, max_length: int = 1024) -> str:
    """Truncate text to fit Discord embed field limits.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (default 1024 for Discord fields)
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    
    # Try to truncate at a sentence boundary
    truncated = text[:max_length-3]
    last_period = truncated.rfind('.')
    last_newline = truncated.rfind('\n')
    
    cut_point = max(last_period, last_newline)
    if cut_point > max_length * 0.7:  # Only use sentence boundary if it's not too early
        return text[:cut_point+1] + "..."
    
    return text[:max_length-3] + "..."
