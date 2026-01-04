import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import time
import difflib
import asyncio
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import numpy as np
from openai import OpenAI
import hashlib
import re
import random 
from datetime import datetime, timedelta
from io import BytesIO
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont 

try:
    from sentence_transformers import SentenceTransformer
    from transformers import pipeline
    ML_AVAILABLE = True
except Exception:
    ML_AVAILABLE = False

if ML_AVAILABLE:
    semantic_model = SentenceTransformer(...)
else:
    semantic_model = None

# Optional: For image generation (aura cards)
try:
    from PIL import Image, ImageDraw, ImageFont
    import aiohttp
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL not installed - Aura cards will be text-based. Install with: pip install Pillow aiohttp")


key = os.getenv("OPENROUTER_API_KEY")
# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

key = os.getenv("OPENROUTER_API_KEY")
if not key:
    raise RuntimeError("OPENROUTER_API_KEY not set")

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=key
)

TOKEN = os.getenv("TOKEN")
PREFIX = "!"

# Data files
DATA_FILE = "aura_data.json"
CONFIG_FILE = "aura_config.json"
LOG_FILE = "aura_logs.json"
STREAKS_FILE = "aura_streaks.json"
SHOP_FILE = "aura_shop.json"
BATTLES_FILE = "aura_battles.json"
TOURNAMENTS_FILE = "aura_tournaments.json"
HISTORY_FILE = "aura_history.json"
GLOBAL_FILE = "aura_global.json"

# Battle settings
BATTLE_COOLDOWN = 3600  # 1 hour between battles
BATTLE_STAKE_PERCENT = 0.05  # 5% of lower player's aura at stake
BATTLE_MIN_STAKE = 5
BATTLE_MAX_STAKE = 100

# Daily streak settings
DAILY_BASE_REWARD = 10
DAILY_STREAK_BONUS = 5  # Extra per day of streak
DAILY_MAX_STREAK_BONUS = 50  # Cap at day 10

SHOP_ITEMS = {
    "titles": {
        "title_champion": {
            "name": "Champion",
            "emoji": "<:champion:YOUR_EMOJI_ID>",
            "price": 4000,
            "type": "title",
            "description": "Show off your champion status!"
        },
        "title_legend": {
            "name": "Legend",
            "emoji": "<:legend:YOUR_EMOJI_ID>",
            "price": 7000,
            "type": "title",
            "description": "A legendary title for legendary players!"
        },
        "title_godlike": {
            "name": "Godlike",
            "emoji": "<:godlike:YOUR_EMOJI_ID>",
            "price": 50000,
            "type": "title",
            "description": "The ultimate title of power!"
        },
        "title_mystic": {
            "name": "Mystic",
            "emoji": "<:mystic:YOUR_EMOJI_ID>",
            "price": 5500,
            "type": "title",
            "description": "Mysterious and powerful!"
        },
        "title_warrior": {
            "name": "Warrior",
            "emoji": "<:warrior:YOUR_EMOJI_ID>",
            "price": 2000,
            "type": "title",
            "description": "A battle-hardened warrior!"
        }
    },
    "badges": {
        "badge_star": {
            "name": "Star Badge",
            "emoji": "<:star_badge:YOUR_EMOJI_ID>",
            "price": 1500,
            "type": "badge",
            "description": "A shiny star badge!"
        },
        "badge_fire": {
            "name": "Fire Badge",
            "emoji": "<:fire_badge:YOUR_EMOJI_ID>",
            "price": 2000,
            "type": "badge",
            "description": "You're on fire!"
        },
        "badge_diamond": {
            "name": "Diamond Badge",
            "emoji": "<:diamond_badge:YOUR_EMOJI_ID>",
            "price": 4000,
            "type": "badge",
            "description": "Rare and precious!"
        },
        "badge_lightning": {
            "name": "Lightning Badge",
            "emoji": "<:lightning_badge:YOUR_EMOJI_ID>",
            "price": 2500,
            "type": "badge",
            "description": "Fast and powerful!"
        },
        "badge_crown": {
            "name": "Crown Badge",
            "emoji": "<:crown_badge:YOUR_EMOJI_ID>",
            "price": 10000,
            "type": "badge",
            "description": "Royalty status!"
        }
    },
    "colors": {
        "color_gold": {
            "name": "Gold Theme",
            "emoji": "<:gold_theme:YOUR_EMOJI_ID>",
            "price": 3000,
            "type": "color",
            "color_code": 0xFFD700,
            "description": "A golden aura card!"
        },
        "color_purple": {
            "name": "Purple Theme",
            "emoji": "<:purple_theme:YOUR_EMOJI_ID>",
            "price": 3000,
            "type": "color",
            "color_code": 0x9B59B6,
            "description": "A majestic purple theme!"
        },
        "color_red": {
            "name": "Red Theme",
            "emoji": "<:red_theme:YOUR_EMOJI_ID>",
            "price": 3000,
            "type": "color",
            "color_code": 0xE74C3C,
            "description": "A fiery red theme!"
        },
        "color_cyan": {
            "name": "Cyan Theme",
            "emoji": "<:cyan_theme:YOUR_EMOJI_ID>",
            "price": 3000,
            "type": "color",
            "color_code": 0x00CED1,
            "description": "A cool cyan theme!"
        }
    },
    "boosts": {
        "boost_2x": {
            "name": "2x Aura Boost",
            "emoji": "<:boost:YOUR_EMOJI_ID>",
            "price": 5000,
            "type": "boost",
            "duration": 24,
            "description": "Double aura gains for 24 hours!"
        }
    },
    "shields": {
        "shield": {
            "name": "Battle Shield",
            "emoji": "<:shield:YOUR_EMOJI_ID>",
            "price": 25000,
            "type": "shield",
            "duration": 24,
            "description": "Protection from battle losses for 24 hours!"
        }
    }
}
# Tournament settings
TOURNAMENT_DURATION = 604800  # 7 days in seconds
TOURNAMENT_PRIZES = {
    1: {"aura": 500, "title": "Weekly Champion"},
    2: {"aura": 300, "title": None},
    3: {"aura": 150, "title": None},
}

ADMIN_COMMANDS = {
    "aurach_enable",
    "aurach_disable",
    "aurach_status",
    "debug",
    "resetuser",
    "resetall",
}

SAFE_COMMANDS = {
    "aurainfo",
    "commandlist",
    "invite",
}

semantic_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
    top_k=None  # Return all scores
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

user_message_hashes = {}
MESSAGE_HISTORY_SIZE = 5
MESSAGE_HISTORY_WINDOW = 300

# FIXED: Separate cooldowns for positive and negative aura
recent_positive_aura_time = {}
recent_negative_aura_time = {}
POSITIVE_AURA_COOLDOWN = 30  # Keep cooldown for gains
NEGATIVE_AURA_COOLDOWN = 5   # Much shorter for toxic messages

def hash_message(content: str) -> str:
    # IMPROVED: Normalize before hashing to prevent bypass
    normalized = re.sub(r'[^\w\s]', '', content.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def is_duplicate_message(user_id: str, content: str) -> bool:
    now = time.time()
    msg_hash = hash_message(content)
    
    if user_id not in user_message_hashes:
        user_message_hashes[user_id] = []
    
    history = user_message_hashes[user_id]
    history[:] = [(h, t) for h, t in history if now - t < MESSAGE_HISTORY_WINDOW]
    
    for stored_hash, _ in history:
        if stored_hash == msg_hash:
            return True
    
    history.append((msg_hash, now))
    if len(history) > MESSAGE_HISTORY_SIZE:
        history[:] = history[-MESSAGE_HISTORY_SIZE:]
    
    return False

def is_hindi_or_hinglish(text: str) -> bool:
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    if devanagari_pattern.search(text):
        return True
    latin_hindi = [
        "kya", "hai", "bhai", "yaar", "matlab", "acha", "thik", "nahi", "haan",
        "kaise", "abhi", "baad", "mein", "tera", "mera", "koi", "naa", "aur",
        "par", "toh", "kab", "kyun", "chal", "theek", "yeh", "woh", "kuch",
        "sab", "dekh", "kar", "bol", "sun", "le", "de", "arre", "beta", "bhaiya",
        "dost", "fadu", "mast", "sahi", "scene", "bindaas", "pagal", "chill", "bakwas"
    ]
    words = text.lower().split()
    matches = sum(1 for w in words if w in latin_hindi)
    if matches >= 2:
        return True
    if len(words) > 0 and matches / len(words) > 0.25:
        return True
    return False

@bot.check
async def channel_command_gate(ctx):
    if not ctx.guild:
        return True

    if is_channel_enabled(ctx.guild.id, ctx.channel.id):
        return True

    cmd = ctx.command.name

    if (
        cmd in ADMIN_COMMANDS
        and ctx.author.guild_permissions.manage_guild
    ):
        return True

    if cmd in SAFE_COMMANDS:
        return True

    await ctx.send(
        "⚠️ Aura commands are disabled in this channel.",
        delete_after=5
    )
    return False

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_json(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# ============================================================================
# ADD NEAR THE TOP WITH OTHER DATA LOADING
# ============================================================================

# Inventory data file
INVENTORY_FILE = "inventory.json"

def load_inventory():
    """Load inventory data from file."""
    if os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_inventory():
    """Save inventory data to file."""
    with open(INVENTORY_FILE, "w") as f:
        json.dump(inventory_data, f, indent=4)

# Load inventory data
inventory_data = load_inventory()

# Config data file
CONFIG_FILE = "config.json"

def load_config():
    """Load config data from file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config():
    """Save config data to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

# Load config data
config_data = load_config()
# ============================================================================
# DATA LOADING & SAVING
# ============================================================================

def load_json_safe(path: str, default: dict = None) -> dict:
    """Safely load JSON file with default fallback."""
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default.copy()
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return default.copy()

def save_json_safe(path: str, data: dict):
    """Safely save JSON file."""
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[SAVE ERROR] {path}: {e}")

# Load all data
aura_data = load_json_safe(DATA_FILE)
config_data = load_json_safe(CONFIG_FILE)
aura_logs = load_json_safe(LOG_FILE)
streaks_data = load_json_safe(STREAKS_FILE)
shop_data = load_json_safe(SHOP_FILE)  # User purchases & inventory
battles_data = load_json_safe(BATTLES_FILE)  # Battle history & cooldowns
tournaments_data = load_json_safe(TOURNAMENTS_FILE)
history_data = load_json_safe(HISTORY_FILE)  # Daily aura snapshots
global_data = load_json_safe(GLOBAL_FILE)  # Cross-server stats

def save_all_data():
    """Save all data files."""
    save_json_safe(DATA_FILE, aura_data)
    save_json_safe(CONFIG_FILE, config_data)
    save_json_safe(LOG_FILE, aura_logs)
    save_json_safe(STREAKS_FILE, streaks_data)
    save_json_safe(SHOP_FILE, shop_data)
    save_json_safe(BATTLES_FILE, battles_data)
    save_json_safe(TOURNAMENTS_FILE, tournaments_data)
    save_json_safe(HISTORY_FILE, history_data)
    save_json_safe(GLOBAL_FILE, global_data)
# ============================================================================
aura_data = load_data()
config_data = load_json(CONFIG_FILE)
aura_logs = load_json(LOG_FILE)
MAX_LOGS_PER_USER = 50

def log_aura_change(user_id: str, change: int, new_score: int, reason: str):
    logs = aura_logs.setdefault(user_id, [])
    logs.append({
        "timestamp": int(time.time()),
        "change": change,
        "new_score": new_score,
        "reason": reason,
    })
    if len(logs) > MAX_LOGS_PER_USER:
        logs[:] = logs[-MAX_LOGS_PER_USER:]
    save_json(LOG_FILE, aura_logs)

recent_messages = {}
DUPLICATE_WINDOW = 15
SIMILARITY_THRESHOLD = 0.85

def is_channel_enabled(guild_id: int, channel_id: int) -> bool:
    gid = str(guild_id)
    cid = str(channel_id)
    guild_cfg = config_data.get(gid, {})
    disabled = set(guild_cfg.get("disabled_channels", []))
    return cid not in disabled

DECAY_RATE = 0.01

def apply_decay():
    if not aura_data:
        return
    changed = False
    for uid, score in list(aura_data.items()):
        if score <= 0:
            continue
        new_score = int(score * (1 - DECAY_RATE))
        if new_score != score:
            aura_data[uid] = new_score
            changed = True
    if changed:
        save_data(aura_data)

@tasks.loop(hours=24)
async def daily_decay_task():
    print("Applying daily aura decay...")
    apply_decay()

RANK_ROLES = [
    (1500, "GOD AURA"),
    (800, "Massive Aura"),
    (400, "Aura User"),
    (150, "Low Aura"),
]

def get_rank_name(score: int) -> str:
    for threshold, name in RANK_ROLES:
        if score >= threshold:
            return name
    return "No Aura"

@tasks.loop(minutes=10)
async def aura_role_sync_task():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        role_map = {r.name: r for r in guild.roles}
        for member in guild.members:
            if member.bot:
                continue
            score = aura_data.get(str(member.id), 0)
            rank_name = get_rank_name(score)
            target_role = role_map.get(rank_name)
            if not target_role:
                try:
                    target_role = await guild.create_role(name=rank_name)
                    role_map[rank_name] = target_role
                except Exception as e:
                    print("Role create error:", e)
                    continue
            member_roles = set(member.roles)
            aura_roles = [role_map[n] for _, n in RANK_ROLES if n in role_map]
            to_remove = [r for r in aura_roles if r in member_roles and r.name != rank_name]
            try:
                if to_remove:
                    await member.remove_roles(*to_remove, reason="Aura rank sync")
                if target_role not in member_roles:
                    await member.add_roles(target_role, reason="Aura rank sync")
            except Exception as e:
                print("Role assign error:", e)
                continue

def calculate_ai_aura_rules(message: str) -> int:
    score = 0
    if len(message) >= 20:
        score += 1
    if len(message) >= 50:
        score += 1
    hype_words = ["fire", "clean", "goated", "insane", "legend", "based", "mast", "fadu", "bindaas"]
    hype_count = sum(1 for w in hype_words if w in message.lower())
    score += min(hype_count, 1)
    emojis = sum(message.count(e) for e in ["🔥", "🗿", "👑", "⚡", "😂"])
    score += min(emojis, 1)
    return min(score, 2)

def calculate_ai_aura_local(message: str) -> int:
    """
    Calculate sentiment score using multilingual XLM-RoBERTa model + Hindi word boost.
    Supports Hindi, Hinglish, English, and 100+ other languages.
    """
    try:
        text = message[:512] if len(message) > 512 else message
        text_lower = text.lower()
        
        # === MULTILINGUAL ML SENTIMENT ===
        results = sentiment_analyzer(text)
        
        ml_score = 0
        if results and len(results) > 0:
            predictions = results[0]
            scores = {pred['label'].lower(): pred['score'] for pred in predictions}
            
            positive_score = scores.get('positive', 0)
            negative_score = scores.get('negative', 0)
            
            if positive_score > 0.7:
                ml_score = 4
            elif positive_score > 0.5:
                ml_score = 3
            elif positive_score > 0.35:
                ml_score = 2
            elif positive_score > 0.25 and positive_score > negative_score:
                ml_score = 1
            elif negative_score > 0.7:
                ml_score = -2
            elif negative_score > 0.5:
                ml_score = -1
            else:
                ml_score = 1 if positive_score >= negative_score else 0
        
        # === HINDI/HINGLISH WORD BOOST ===
        # Extra boost for clear Hindi positive/negative words the model might miss
        
        hindi_positive = {
            "acha", "accha", "achchha", "acchi", "badhiya", "mast", "sahi",
            "zabardast", "kamaal", "shandar", "pyar", "pyaar", "khushi",
            "dhanyawad", "shukriya", "behtareen", "gazab", "laajawab",
            "mazedaar", "tagda", "solid", "saccha", "dost", "bhai", "yaar",
            "khush", "pyaara", "pyari", "best", "legend", "fire", "goated"
        }
        
        hindi_negative_sentiment = {
            "bura", "kharab", "ghatiya", "bakwas", "bekar", "wahiyat",
            "ganda", "dukh", "dard", "pareshaan", "gussa", "nafrat",
            "galat", "dhoka", "sad", "worst", "terrible", "hate"
        }
        
        hindi_intensifiers = {
            "bhot", "bahut", "boht", "bht", "bahot", "bohot",
            "kaafi", "ekdum", "bilkul", "sabse", "itna", "zyada"
        }
        
        words = set(re.findall(r'\w+', text_lower))
        
        pos_matches = len(words & hindi_positive)
        neg_matches = len(words & hindi_negative_sentiment)
        has_intensifier = bool(words & hindi_intensifiers)
        
        # Apply boost
        word_boost = 0
        if pos_matches >= 2:
            word_boost = 2
        elif pos_matches == 1:
            word_boost = 1
        
        if neg_matches >= 2:
            word_boost = -2
        elif neg_matches == 1:
            word_boost -= 1
        
        if has_intensifier and word_boost != 0:
            word_boost = int(word_boost * 1.5)  # Intensify the boost
        
        # === COMBINE SCORES ===
        # If Hindi detected and word boost disagrees with ML, trust word boost more
        is_hindi = is_hindi_or_hinglish(message)
        
        if is_hindi and word_boost != 0:
            # Average them but lean toward word boost for Hindi
            final_score = int((ml_score + word_boost * 2) / 3)
        else:
            final_score = ml_score + (word_boost // 2)  # Small word boost
        
        return max(-2, min(final_score, 4))
        
    except Exception as e:
        print(f"[SENTIMENT ERROR] {e}")
        return 0

def get_multilingual_toxic_examples():
    return [
        "You are an idiot", "Nobody likes you", "You're useless", "I hate you", "Get lost", "Stop talking, loser", "You're disgusting",
        "Tu pagal hai", "Tu chutiya hai", "Tu bkl hai", "Teri maa ka", "Nikal yahan se", "Kutte", "Gaandu",
        "Bc tu serious hai kya", "Oye chup ho ja", "Tera dimaag kharab hai", "Madarchod tu", "Arey chhup be", "Tu bkl",
        "Teri maa ki", "Bhosdike", "Bhosadi ke", "Randi", "Saale", "Harami", "Kutta", "Kamina"
    ]

# IMPROVED: Better friendly banter detection
def is_casual_hinglish_banter(text: str) -> bool:
    """
    Detect if Hinglish usage is casual/friendly vs toxic.
    Returns True only if it's clearly friendly banter.
    """
    text_lower = text.lower()
    
    # Friendly Hinglish patterns (casual use in positive context)
    friendly_patterns = [
        r'\b(bc|bkl)\s+(mast|sahi|theek|maja|badhiya|cool|nice|good)\b',
        r'\b(arre|yaar|bhai|dost)\s+\w+\b',
        r'\b(pagal|crazy)\s+(hai kya|ho kya)\b',
        r'\bhaha\s+(bc|bkl|yaar)\b',
        r'\blol\s+(bc|bkl|yaar)\b',
        r'\b(kya baat|zabardast|kamaal)\b',
    ]
    
    for pattern in friendly_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False

# IMPROVED: More robust hostile intent detection
def has_hostile_targeted_intent(text: str, message=None) -> bool:
    """
    Return True only when:
     - a hostile keyword is present, AND
     - there's a clear target signal: @mention OR direct addressing
    """
    # Check if it's friendly banter first
    if is_casual_hinglish_banter(text):
        return False
    
    # Expanded hostile tokens
    target_keywords = {
        "idiot", "pagal", "madarchod", "chutiya", "bc", "bkl", "gaandu",
        "loser", "nobody", "hate", "bhosdike", "bhosda", "bhosadi", "bhosdi",
        "randi", "saale", "harami", "kutta", "kamina", "stupid", "dumb",
        "worthless", "pathetic", "disgusting", "ugly", "useless"
    }

    words = re.findall(r"\w+", text.lower())
    hostile_present = any(w in target_keywords for w in words)

    # Mention detection
    mention_hit = "@" in text
    if message:
        try:
            if getattr(message, "mentions", None):
                mention_hit = mention_hit or len(message.mentions) > 0
            if getattr(message, "mention_everyone", False):
                mention_hit = True
        except Exception:
            mention_hit = mention_hit or ("@" in text)

    # Direct addressing patterns
    direct_start = bool(re.match(r'^(tu|you|oye|beta|bhai|arre|tumhara|tumhari|teri|tera|tere)\b', text.strip().lower()))
    possessive_target = bool(re.search(r'\b(tera|teri|tere|tum|tujhe|tujh|tumhara|tumhari|your|yours)\b', text.lower()))

    direct_addressing = direct_start or possessive_target

    return hostile_present and (mention_hit or direct_addressing)

def semantic_toxic_intent_score(text: str) -> float:
    examples = get_multilingual_toxic_examples()
    emb_input = semantic_model.encode([text])
    emb_examples = semantic_model.encode(examples)
    similarities = np.dot(emb_examples, emb_input[0]) / (np.linalg.norm(emb_examples, axis=1) * np.linalg.norm(emb_input[0]) + 1e-7)
    max_sim = float(np.max(similarities))
    return max_sim

def semantic_toxic_classification(text: str) -> str:
    score = semantic_toxic_intent_score(text)
    if score >= 0.74:
        return "toxic"
    elif score >= 0.62:
        return "borderline"
    else:
        return "safe"

def calculate_ai_aura_semantic(message: str) -> int:
    embedding = semantic_model.encode(message)
    energy = np.linalg.norm(embedding)
    score = 0
    if energy > 11:
        score += 1
    if energy > 14:
        score += 1
    words = len(message.split())
    score += min(words // 10, 1)
    return min(score, 2)

# IMPROVED: More conservative safe detection
def is_obviously_safe(text: str) -> bool:
    """
    More conservative - only mark as safe if there's clear positive signals.
    """
    positive_indicators = [
        "awesome", "lol", "haha", "thanks", "thank you", "great", "congrats", 
        "amazing", "love", "nice", "good job", "well done", "excellent", "fantastic",
        "wonderful", "appreciate", "grateful", "blessed", "happy", "excited"
    ]
    
    text_lower = text.lower()
    
    # Must have at least one positive indicator
    has_positive = any(phrase in text_lower for phrase in positive_indicators)
    
    # Must NOT have hostile/targeted intent
    hit = has_hostile_targeted_intent(text)
    sem_cls = semantic_toxic_classification(text)
    
    # Only safe if: has positive signal AND no hostile intent AND semantic says safe
    return has_positive and (not hit) and sem_cls == "safe"

def normalize_message(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s@#]', '', text)
    return text.strip()

# NEW: Hate speech detection
def contains_hate_speech_patterns(text: str) -> tuple[bool, str]:
    """
    Detect hate speech, extremism, and discriminatory content.
    Returns (is_hate_speech, reason)
    """
    text_lower = text.lower()
    
    # Hate speech patterns
    hate_patterns = {
        "racism": [
            r'\b(racist|racism)\s+(to|against|towards)\b',
            r'\bwe should (be racist|discriminate|hate)\b',
            r'\b(black|brown|white|asian|dalit|scheduled caste) people (are|should)\b',
            r'\b(inferior|superior) race\b',
            r'\b(n|k)igger\b',
            r'\bslave\s+(deserved|should)\b',
        ],
        "extremism": [
            r'\b(hitler|nazi|fascis[tm])\s+(was|is)\s+(great|good|right|based|hero)\b',
            r'\b(genocide|ethnic cleansing)\s+(was good|should happen|is justified)\b',
            r'\bholocaust\s+(didn\'?t happen|was (good|justified|fake))\b',
            r'\b(jews|muslims|hindus|christians)\s+(should (die|be killed|be eliminated))\b',
        ],
        "discrimination": [
            r'\bwe should (ban|remove|deport|eliminate|exterminate)\s+(all\s+)?(muslims|jews|christians|hindus|sikhs|buddhists)\b',
            r'\b(women|men|gays|trans|lgbt|queer)\s+(shouldn\'?t|don\'?t deserve|are inferior|are disgusting)\b',
            r'\b(gay|trans|queer)\s+people\s+(are|should be)\s+(killed|eliminated|banned)\b',
        ],
        "violence_advocacy": [
            r'\bwe should (kill|attack|harm|hurt|eliminate|exterminate)\b',
            r'\b(death|violence)\s+to\s+(all\s+)?\w+\b',
            r'\b(shoot|stab|bomb|murder)\s+(all|every)\b',
            r'\bterrorism\s+(is|was)\s+(good|justified|right)\b',
        ],
        "slurs": [
            r'\b(faggot|tranny|retard|chink|spic|wetback)\b',
        ]
    }
    
    for category, patterns in hate_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True, category
    
    return False, ""

# IMPROVED: Better AI aura calculation with robust parsing
async def calculate_ai_aura_devstral(message: str) -> int:
    return await asyncio.to_thread(_devstral_sync, message)

def _devstral_sync(message: str) -> int:
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an advanced AI for moderating chat messages for an Indian Discord community (including Hindi, Hinglish, and English).\n"
                    "You must UNDERSTAND Indian slang and Hinglish culture.\n\n"
                    "CRITICAL RULES:\n"
                    "1. IGNORE casual or cultural profanity in friendly context (e.g., 'bc mast hai', 'bkl theek hai' = NOT toxic)\n"
                    "2. Context matters: 'tu pagal hai' between friends is a joke, not an insult\n"
                    "3. FLAG as negative ONLY if:\n"
                    "   - Message is hostile, harassing, hateful, threatening, or discriminatory, AND\n"
                    "   - It's clearly targeted at someone (explicit person, @mention, or direct 'tu', 'you', 'tera')\n"
                    "4. Sarcasm, friendly banter, jokes, and cultural expressions are NOT toxic\n"
                    "5. Frustration or mild negativity without targeting is neutral (0)\n\n"
                    "HATE SPEECH DETECTION:\n"
                    "- Racism, sexism, homophobia, religious hatred = ALWAYS negative (-4 or -5)\n"
                    "- Extremism, genocide advocacy, discrimination = ALWAYS negative (-4 or -5)\n\n"
                    "Score logic:\n"
                    "- Positive (+1 to +5): Helpful, encouraging, constructive, funny, engaging\n"
                    "- Neutral (0): Casual chat, questions, statements without strong sentiment\n"
                    "- Negative (-1 to -5): Only for clear targeted toxicity, abuse, hate, or threats\n"
                    "  - -1 to -2: Mild targeted negativity\n"
                    "  - -3 to -4: Strong abuse, harassment, or targeted hate\n"
                    "  - -5: Severe hate speech, threats, or extreme discrimination\n\n"
                    "When unsure, err on the side of neutral (0) or positive.\n"
                    "Return ONLY an integer between -5 and +5."
                ),
            },
            {"role": "user", "content": message}
        ]
        response = openrouter_client.chat.completions.create(
            model="mistralai/devstral-2512",
            messages=messages,
            temperature=0.3,
            max_tokens=8
        )
        raw = ""
        try:
            raw = response.choices[0].message.content.strip()
        except Exception:
            raw = str(response)
        
        print(f"[DEVSTRAL RAW] input='{message[:80]}' response='{raw}'")
        
        # Extract first token that looks like an int
        first_token = raw.split()
        if not first_token:
            return 0
        token = first_token[0].strip()
        token = re.sub(r'^[^\-0-9]+|[^\-0-9].*$', '', token)
        try:
            score = int(token)
        except Exception:
            print(f"[DEVSTRAL PARSE ERROR] could not parse token='{token}' from raw='{raw}'")
            return 0
        
        return max(-5, min(score, 5))
    except Exception as e:
        print("Devstral error:", e)
        return 0

# IMPROVED: Better toxic decision logic
def evaluate_toxic_decision(text: str, ai_score: int, message_obj=None) -> tuple[bool, int, dict]:
    """
    Improved voting system that doesn't let AI completely override strong toxic signals.
    """
    explanations = {}
    normalized = normalize_message(text)
    
    targeted = has_hostile_targeted_intent(normalized, message_obj)
    sem_cls = semantic_toxic_classification(normalized)
    toxic_sem = (sem_cls == "toxic")

    try:
        ai_score = int(ai_score)
    except Exception:
        ai_score = None

    explanations['semantic'] = sem_cls
    explanations['targeted_attack'] = targeted
    explanations['ai'] = ai_score if ai_score is not None else 0

    negative_votes = 0
    penalty = 0
    allowed = False

    # IMPROVED LOGIC: Don't let AI completely override strong signals
    if ai_score is not None and ai_score >= 1:
        # AI is confident it's positive - veto unless BOTH other systems strongly agree it's toxic
        if toxic_sem and targeted:
            # Both systems say toxic + targeted - override AI
            negative_votes = 2
            allowed = True
            penalty = -3
        else:
            allowed = False
            penalty = 0
    else:
        # AI is neutral or negative - use voting
        if toxic_sem:
            negative_votes += 1
        if targeted:
            negative_votes += 1
        if ai_score is not None and ai_score < 0:
            negative_votes += 1
        
        # Lower threshold: 2/3 votes OR semantic+targeted combo
        if negative_votes >= 2 or (toxic_sem and targeted):
            allowed = True
            # Penalty scales with severity
            if negative_votes == 3:
                penalty = min(-3, ai_score) if ai_score and ai_score <= -3 else -3
            else:
                penalty = min(-2, ai_score) if ai_score and ai_score <= -2 else -2
        else:
            penalty = 0
    
    explanations['votes'] = negative_votes
    explanations['allowed'] = allowed
    explanations['penalty'] = penalty

    print(f"[TOXIC DECISION] ai={ai_score} sem={sem_cls} targeted={targeted} votes={negative_votes} allowed={allowed} penalty={penalty}")

    return allowed, penalty, explanations

# ============================================================================
# AURA BATTLES
# ============================================================================

def get_battle_cooldown(user_id: str) -> int:
    """Get remaining cooldown in seconds for a user's next battle."""
    last_battle = battles_data.get(user_id, {}).get("last_battle", 0)
    elapsed = time.time() - last_battle
    remaining = BATTLE_COOLDOWN - elapsed
    return max(0, int(remaining))

def has_shield(user_id: str) -> bool:
    """Check if user has an active battle shield."""
    user_shop = shop_data.get(user_id, {})
    shield_expires = user_shop.get("shield_expires", 0)
    return time.time() < shield_expires

def calculate_battle_stake(aura1: int, aura2: int) -> int:
    """Calculate aura at stake based on lower player's aura."""
    lower_aura = min(aura1, aura2)
    stake = int(lower_aura * BATTLE_STAKE_PERCENT)
    return max(BATTLE_MIN_STAKE, min(stake, BATTLE_MAX_STAKE))

def simulate_battle(aura1: int, aura2: int) -> tuple[int, dict]:
    """
    Simulate a battle between two players.
    Returns: (winner: 1 or 2, battle_details: dict)
    """
    # Base win chance is 50/50, but higher aura gives slight advantage
    total_aura = aura1 + aura2
    if total_aura == 0:
        chance1 = 0.5
    else:
        # Higher aura = higher chance, but capped at 70%
        raw_chance = aura1 / total_aura
        chance1 = 0.3 + (raw_chance * 0.4)  # Range: 30% to 70%
    
    # Random events that can affect the battle
    events = []
    
    # Critical hit chance (10%)
    if random.random() < 0.1:
        if random.random() < 0.5:
            events.append(("crit", 1, "landed a **CRITICAL HIT!** 💥"))
            chance1 += 0.15
        else:
            events.append(("crit", 2, "landed a **CRITICAL HIT!** 💥"))
            chance1 -= 0.15
    
    # Dodge chance (8%)
    if random.random() < 0.08:
        if random.random() < 0.5:
            events.append(("dodge", 1, "**DODGED** the attack! 🌀"))
            chance1 += 0.1
        else:
            events.append(("dodge", 2, "**DODGED** the attack! 🌀"))
            chance1 -= 0.1
    
    # Aura surge (5%)
    if random.random() < 0.05:
        if random.random() < 0.5:
            events.append(("surge", 1, "unleashed an **AURA SURGE!** ⚡"))
            chance1 += 0.2
        else:
            events.append(("surge", 2, "unleashed an **AURA SURGE!** ⚡"))
            chance1 -= 0.2
    
    # Clamp chance
    chance1 = max(0.15, min(0.85, chance1))
    
    # Determine winner
    winner = 1 if random.random() < chance1 else 2
    
    return winner, {
        "events": events,
        "chance1": chance1,
        "chance2": 1 - chance1
    }

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def aurabattle(ctx, opponent: discord.Member):
    """Challenge someone to an aura battle!"""
    
    # Validation
    if opponent.bot:
        await ctx.send("❌ You can't battle a bot!")
        return
    
    if opponent.id == ctx.author.id:
        await ctx.send("❌ You can't battle yourself!")
        return
    
    challenger_id = str(ctx.author.id)
    opponent_id = str(opponent.id)
    
    # Check cooldowns
    challenger_cd = get_battle_cooldown(challenger_id)
    if challenger_cd > 0:
        minutes = challenger_cd // 60
        await ctx.send(f"⏰ You're still recovering! Battle again in **{minutes}** minutes.")
        return
    
    opponent_cd = get_battle_cooldown(opponent_id)
    if opponent_cd > 0:
        minutes = opponent_cd // 60
        await ctx.send(f"⏰ **{opponent.display_name}** is still recovering! They can battle in **{minutes}** minutes.")
        return
    
    # Check shield
    if has_shield(opponent_id):
        await ctx.send(f"🛡️ **{opponent.display_name}** has a Battle Shield active! They're protected from battles.")
        return
    
    # Get aura scores
    challenger_aura = aura_data.get(challenger_id, 0)
    opponent_aura = aura_data.get(opponent_id, 0)
    
    if challenger_aura < 10:
        await ctx.send("❌ You need at least **10 aura** to battle!")
        return
    
    if opponent_aura < 10:
        await ctx.send(f"❌ **{opponent.display_name}** needs at least **10 aura** to battle!")
        return
    
    # Calculate stake
    stake = calculate_battle_stake(challenger_aura, opponent_aura)
    
    # Send challenge
    embed = discord.Embed(
        title="⚔️ AURA BATTLE CHALLENGE! ⚔️",
        description=(
            f"**{ctx.author.mention}** challenges **{opponent.mention}** to battle!\n\n"
            f"🎯 **{ctx.author.display_name}**: {challenger_aura} aura\n"
            f"🎯 **{opponent.display_name}**: {opponent_aura} aura\n\n"
            f"💰 **Stake**: {stake} aura\n\n"
            f"{opponent.mention}, react with ⚔️ to accept or ❌ to decline!"
        ),
        color=0xFF6B6B
    )
    embed.set_footer(text="Challenge expires in 60 seconds")
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("⚔️")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return (
            user.id == opponent.id 
            and str(reaction.emoji) in ["⚔️", "❌"] 
            and reaction.message.id == msg.id
        )
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        
        if str(reaction.emoji) == "❌":
            await ctx.send(f"😔 **{opponent.display_name}** declined the battle challenge.")
            return
        
        # BATTLE ACCEPTED - FIGHT!
        await ctx.send("⚔️ **BATTLE ACCEPTED!** Let the aura clash begin...")
        await asyncio.sleep(2)
        
        # Simulate battle
        winner_num, details = simulate_battle(challenger_aura, opponent_aura)
        
        if winner_num == 1:
            winner = ctx.author
            loser = opponent
            winner_id = challenger_id
            loser_id = opponent_id
        else:
            winner = opponent
            loser = ctx.author
            winner_id = opponent_id
            loser_id = challenger_id
        
        # Apply shield check for loser
        if has_shield(loser_id):
            stake = 0  # Shield prevents loss
        
        # Update aura
        aura_data[winner_id] = aura_data.get(winner_id, 0) + stake
        aura_data[loser_id] = max(0, aura_data.get(loser_id, 0) - stake)
        
        # Update cooldowns
        battles_data.setdefault(challenger_id, {})["last_battle"] = time.time()
        battles_data.setdefault(opponent_id, {})["last_battle"] = time.time()
        
        # Update battle stats
        battles_data[winner_id].setdefault("wins", 0)
        battles_data[winner_id]["wins"] += 1
        battles_data[loser_id].setdefault("losses", 0)
        battles_data[loser_id]["losses"] += 1
        
        save_json_safe(DATA_FILE, aura_data)
        update_global_stats(
            winner_id,
            winner.name,
            aura_data.get(winner_id, 0),
            ctx.guild.name if ctx.guild else "DM"
        )
        update_global_stats(
            loser_id,
            loser.name,
            aura_data.get(loser_id, 0),
            ctx.guild.name if ctx.guild else "DM"
        )
        save_json_safe(BATTLES_FILE, battles_data)
        
        # Build result embed
        events_text = ""
        for event in details["events"]:
            player = ctx.author if event[1] == 1 else opponent
            events_text += f"⚡ {player.display_name} {event[2]}\n"
        
        result_embed = discord.Embed(
            title="🏆 BATTLE RESULTS 🏆",
            color=0x00FF00 if winner == ctx.author else 0xFF0000
        )
        
        if events_text:
            result_embed.add_field(
                name="💥 Battle Events",
                value=events_text,
                inline=False
            )
        
        result_embed.add_field(
            name="🎯 Winner",
            value=f"**{winner.display_name}** wins!",
            inline=True
        )
        
        result_embed.add_field(
            name="💰 Aura Transferred",
            value=f"+{stake}" if stake > 0 else "0 (Shield active)",
            inline=True
        )
        
        result_embed.add_field(
            name="📊 Final Scores",
            value=(
                f"**{ctx.author.display_name}**: {aura_data.get(challenger_id, 0)} aura\n"
                f"**{opponent.display_name}**: {aura_data.get(opponent_id, 0)} aura"
            ),
            inline=False
        )
        
        # Win chance info
        result_embed.set_footer(
            text=f"Win chances were {details['chance1']*100:.0f}% vs {details['chance2']*100:.0f}%"
        )
        
        await ctx.send(embed=result_embed)
        
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Battle challenge expired. **{opponent.display_name}** didn't respond in time.")

@bot.tree.command(name="aurabattle", description="Challenge someone to an aura battle!")
async def aurabattle_slash(interaction: discord.Interaction, opponent: discord.Member):
    """Slash command version of aura battle."""
    
    if opponent.bot:
        await interaction.response.send_message("❌ You can't battle a bot!", ephemeral=True)
        return
    
    if opponent.id == interaction.user.id:
        await interaction.response.send_message("❌ You can't battle yourself!", ephemeral=True)
        return
    
    challenger_id = str(interaction.user.id)
    opponent_id = str(opponent.id)
    
    # Check cooldowns
    challenger_cd = get_battle_cooldown(challenger_id)
    if challenger_cd > 0:
        minutes = challenger_cd // 60
        await interaction.response.send_message(
            f"⏰ You're still recovering! Battle again in **{minutes}** minutes.",
            ephemeral=True
        )
        return
    
    opponent_cd = get_battle_cooldown(opponent_id)
    if opponent_cd > 0:
        minutes = opponent_cd // 60
        await interaction.response.send_message(
            f"⏰ **{opponent.display_name}** is still recovering!",
            ephemeral=True
        )
        return
    
    if has_shield(opponent_id):
        await interaction.response.send_message(
            f"🛡️ **{opponent.display_name}** has a Battle Shield active!",
            ephemeral=True
        )
        return
    
    challenger_aura = aura_data.get(challenger_id, 0)
    opponent_aura = aura_data.get(opponent_id, 0)
    
    if challenger_aura < 10:
        await interaction.response.send_message("❌ You need at least **10 aura** to battle!", ephemeral=True)
        return
    
    if opponent_aura < 10:
        await interaction.response.send_message(
            f"❌ **{opponent.display_name}** needs at least **10 aura** to battle!",
            ephemeral=True
        )
        return
    
    stake = calculate_battle_stake(challenger_aura, opponent_aura)
    
    embed = discord.Embed(
        title="⚔️ AURA BATTLE CHALLENGE! ⚔️",
        description=(
            f"**{interaction.user.mention}** challenges **{opponent.mention}** to battle!\n\n"
            f"🎯 **{interaction.user.display_name}**: {challenger_aura} aura\n"
            f"🎯 **{opponent.display_name}**: {opponent_aura} aura\n\n"
            f"💰 **Stake**: {stake} aura\n\n"
            f"{opponent.mention}, react with ⚔️ to accept or ❌ to decline!"
        ),
        color=0xFF6B6B
    )
    embed.set_footer(text="Challenge expires in 60 seconds")
    
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("⚔️")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return (
            user.id == opponent.id 
            and str(reaction.emoji) in ["⚔️", "❌"] 
            and reaction.message.id == msg.id
        )
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        
        if str(reaction.emoji) == "❌":
            await interaction.followup.send(f"😔 **{opponent.display_name}** declined the battle.")
            return
        
        await interaction.followup.send("⚔️ **BATTLE ACCEPTED!** Let the aura clash begin...")
        await asyncio.sleep(2)
        
        winner_num, details = simulate_battle(challenger_aura, opponent_aura)
        
        if winner_num == 1:
            winner = interaction.user
            loser = opponent
            winner_id = challenger_id
            loser_id = opponent_id
        else:
            winner = opponent
            loser = interaction.user
            winner_id = opponent_id
            loser_id = challenger_id
        
        if has_shield(loser_id):
            stake = 0
        
        aura_data[winner_id] = aura_data.get(winner_id, 0) + stake
        aura_data[loser_id] = max(0, aura_data.get(loser_id, 0) - stake)
        
        battles_data.setdefault(challenger_id, {})["last_battle"] = time.time()
        battles_data.setdefault(opponent_id, {})["last_battle"] = time.time()
        
        battles_data[winner_id].setdefault("wins", 0)
        battles_data[winner_id]["wins"] += 1
        battles_data[loser_id].setdefault("losses", 0)
        battles_data[loser_id]["losses"] += 1
        
        save_json_safe(DATA_FILE, aura_data)
        save_json_safe(BATTLES_FILE, battles_data)
        
        events_text = ""
        for event in details["events"]:
            player = interaction.user if event[1] == 1 else opponent
            events_text += f"⚡ {player.display_name} {event[2]}\n"
        
        result_embed = discord.Embed(
            title="🏆 BATTLE RESULTS 🏆",
            color=0x00FF00 if winner == interaction.user else 0xFF0000
        )
        
        if events_text:
            result_embed.add_field(name="💥 Battle Events", value=events_text, inline=False)
        
        result_embed.add_field(name="🎯 Winner", value=f"**{winner.display_name}** wins!", inline=True)
        result_embed.add_field(
            name="💰 Aura Transferred",
            value=f"+{stake}" if stake > 0 else "0 (Shield active)",
            inline=True
        )
        result_embed.add_field(
            name="📊 Final Scores",
            value=(
                f"**{interaction.user.display_name}**: {aura_data.get(challenger_id, 0)} aura\n"
                f"**{opponent.display_name}**: {aura_data.get(opponent_id, 0)} aura"
            ),
            inline=False
        )
        result_embed.set_footer(
            text=f"Win chances were {details['chance1']*100:.0f}% vs {details['chance2']*100:.0f}%"
        )
        
        await interaction.followup.send(embed=result_embed)
        
    except asyncio.TimeoutError:
        await interaction.followup.send(f"⏰ Challenge expired. **{opponent.display_name}** didn't respond.")

@bot.command()
async def battlestats(ctx, member: discord.Member = None):
    """View your or someone's battle statistics."""
    member = member or ctx.author
    uid = str(member.id)
    
    stats = battles_data.get(uid, {})
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0
    
    cooldown = get_battle_cooldown(uid)
    shield_active = has_shield(uid)
    
    embed = discord.Embed(
        title=f"⚔️ {member.display_name}'s Battle Stats",
        color=0xFF6B6B
    )
    embed.add_field(name="🏆 Wins", value=str(wins), inline=True)
    embed.add_field(name="💀 Losses", value=str(losses), inline=True)
    embed.add_field(name="📊 Win Rate", value=f"{winrate:.1f}%", inline=True)
    embed.add_field(name="⚔️ Total Battles", value=str(total), inline=True)
    embed.add_field(
        name="⏰ Cooldown",
        value=f"{cooldown // 60}m remaining" if cooldown > 0 else "Ready!",
        inline=True
    )
    embed.add_field(
        name="🛡️ Shield",
        value="Active ✅" if shield_active else "None",
        inline=True
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.tree.command(name="battlestats", description="View battle statistics")
async def battlestats_slash(interaction: discord.Interaction, user: discord.Member = None):
    member = user or interaction.user
    uid = str(member.id)
    
    stats = battles_data.get(uid, {})
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0
    
    cooldown = get_battle_cooldown(uid)
    shield_active = has_shield(uid)
    
    embed = discord.Embed(
        title=f"⚔️ {member.display_name}'s Battle Stats",
        color=0xFF6B6B
    )
    embed.add_field(name="🏆 Wins", value=str(wins), inline=True)
    embed.add_field(name="💀 Losses", value=str(losses), inline=True)
    embed.add_field(name="📊 Win Rate", value=f"{winrate:.1f}%", inline=True)
    embed.add_field(name="⚔️ Total Battles", value=str(total), inline=True)
    embed.add_field(
        name="⏰ Cooldown",
        value=f"{cooldown // 60}m remaining" if cooldown > 0 else "Ready!",
        inline=True
    )
    embed.add_field(
        name="🛡️ Shield",
        value="Active ✅" if shield_active else "None",
        inline=True
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# ============================================================================
# DAILY STREAKS & CHECK-INS
# ============================================================================

def get_daily_info(user_id: str) -> dict:
    """Get user's daily streak information."""
    user_streaks = streaks_data.get(user_id, {})
    return {
        "streak": user_streaks.get("streak", 0),
        "last_claim": user_streaks.get("last_claim", 0),
        "total_claims": user_streaks.get("total_claims", 0),
        "highest_streak": user_streaks.get("highest_streak", 0)
    }

def can_claim_daily(user_id: str) -> tuple[bool, int]:
    """
    Check if user can claim daily reward.
    Returns: (can_claim: bool, seconds_until_next: int)
    """
    info = get_daily_info(user_id)
    last_claim = info["last_claim"]
    
    if last_claim == 0:
        return True, 0
    
    now = time.time()
    # Reset at midnight UTC
    last_claim_day = datetime.utcfromtimestamp(last_claim).date()
    today = datetime.utcfromtimestamp(now).date()
    
    if today > last_claim_day:
        return True, 0
    
    # Calculate seconds until next midnight UTC
    tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
    seconds_until = (tomorrow - datetime.utcnow()).total_seconds()
    
    return False, int(seconds_until)

def calculate_daily_reward(streak: int) -> int:
    """Calculate daily reward based on streak."""
    streak_bonus = min(streak * DAILY_STREAK_BONUS, DAILY_MAX_STREAK_BONUS)
    return DAILY_BASE_REWARD + streak_bonus

def claim_daily(user_id: str) -> dict:
    """
    Claim daily reward and update streak.
    Returns: reward info dict
    """
    info = get_daily_info(user_id)
    now = time.time()
    
    # Check if streak continues or resets
    if info["last_claim"] > 0:
        last_claim_day = datetime.utcfromtimestamp(info["last_claim"]).date()
        today = datetime.utcfromtimestamp(now).date()
        days_diff = (today - last_claim_day).days
        
        if days_diff == 1:
            # Consecutive day - streak continues
            new_streak = info["streak"] + 1
        elif days_diff > 1:
            # Streak broken
            new_streak = 1
        else:
            # Same day (shouldn't happen if can_claim_daily is checked)
            new_streak = info["streak"]
    else:
        new_streak = 1
    
    # Calculate reward
    reward = calculate_daily_reward(new_streak)
    
    # Check for multiplier boost
    user_shop = shop_data.get(user_id, {})
    multiplier_expires = user_shop.get("multiplier_expires", 0)
    if time.time() < multiplier_expires:
        multiplier = user_shop.get("multiplier_value", 1)
        reward = int(reward * multiplier)
    else:
        multiplier = 1
    
    # Update streak data
    streaks_data[user_id] = {
        "streak": new_streak,
        "last_claim": now,
        "total_claims": info["total_claims"] + 1,
        "highest_streak": max(info["highest_streak"], new_streak)
    }
    
    # Update aura
    aura_data[user_id] = aura_data.get(user_id, 0) + reward
    
    save_json_safe(STREAKS_FILE, streaks_data)
    save_json_safe(DATA_FILE, aura_data)
    
    return {
        "reward": reward,
        "streak": new_streak,
        "multiplier": multiplier,
        "total_claims": info["total_claims"] + 1,
        "highest_streak": max(info["highest_streak"], new_streak),
        "new_aura": aura_data[user_id]
    }

@bot.command()
async def daily(ctx):
    """Claim your daily aura reward!"""
    user_id = str(ctx.author.id)
    
    can_claim, seconds_until = can_claim_daily(user_id)
    
    if not can_claim:
        hours = seconds_until // 3600
        minutes = (seconds_until % 3600) // 60
        
        info = get_daily_info(user_id)
        
        embed = discord.Embed(
            title="⏰ Daily Already Claimed!",
            description=f"Come back in **{hours}h {minutes}m**!",
            color=0xFF6B6B
        )
        embed.add_field(name="🔥 Current Streak", value=f"**{info['streak']}** days", inline=True)
        embed.add_field(
            name="💰 Tomorrow's Reward",
            value=f"**{calculate_daily_reward(info['streak'] + 1)}** aura",
            inline=True
        )
        embed.set_footer(text="Keep your streak alive!")
        
        await ctx.send(embed=embed)
        return
    
    # Claim the daily!
    result = claim_daily(user_id)

    update_global_stats(
        user_id,
        ctx.author.name,
        result["new_aura"],
        ctx.guild.name if ctx.guild else "DM"
    )
    # Streak milestone messages
    milestone_msg = ""
    if result["streak"] == 7:
        milestone_msg = "\n\n🎉 **WEEKLY STREAK!** You've been consistent for a whole week!"
    elif result["streak"] == 30:
        milestone_msg = "\n\n🏆 **MONTHLY STREAK!** Incredible dedication!"
    elif result["streak"] == 100:
        milestone_msg = "\n\n👑 **LEGENDARY STREAK!** 100 days of pure commitment!"
    elif result["streak"] % 10 == 0 and result["streak"] > 0:
        milestone_msg = f"\n\n⭐ **{result['streak']} DAY STREAK!** Keep it going!"
    
    # Build embed
    embed = discord.Embed(
        title="✨ Daily Reward Claimed! ✨",
        color=0x00FF00
    )
    
    reward_text = f"+**{result['reward']}** aura"
    if result["multiplier"] > 1:
        reward_text += f" (x{result['multiplier']} boost!)"
    
    embed.add_field(name="💰 Reward", value=reward_text, inline=True)
    embed.add_field(name="🔥 Streak", value=f"**{result['streak']}** days", inline=True)
    embed.add_field(name="✨ Total Aura", value=f"**{result['new_aura']}**", inline=True)
    
    # Show next reward preview
    next_reward = calculate_daily_reward(result["streak"] + 1)
    embed.add_field(
        name="📈 Tomorrow's Reward",
        value=f"**{next_reward}** aura (+{DAILY_STREAK_BONUS} streak bonus)",
        inline=False
    )
    
    if milestone_msg:
        embed.description = milestone_msg
    
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Total claims: {result['total_claims']} | Highest streak: {result['highest_streak']}")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="daily", description="Claim your daily aura reward!")
async def daily_slash(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    can_claim, seconds_until = can_claim_daily(user_id)
    
    if not can_claim:
        hours = seconds_until // 3600
        minutes = (seconds_until % 3600) // 60
        
        info = get_daily_info(user_id)
        
        embed = discord.Embed(
            title="⏰ Daily Already Claimed!",
            description=f"Come back in **{hours}h {minutes}m**!",
            color=0xFF6B6B
        )
        embed.add_field(name="🔥 Current Streak", value=f"**{info['streak']}** days", inline=True)
        embed.add_field(
            name="💰 Tomorrow's Reward",
            value=f"**{calculate_daily_reward(info['streak'] + 1)}** aura",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
        return
    
    result = claim_daily(user_id)
    
    milestone_msg = ""
    if result["streak"] == 7:
        milestone_msg = "\n\n🎉 **WEEKLY STREAK!**"
    elif result["streak"] == 30:
        milestone_msg = "\n\n🏆 **MONTHLY STREAK!**"
    elif result["streak"] == 100:
        milestone_msg = "\n\n👑 **LEGENDARY STREAK!**"
    elif result["streak"] % 10 == 0 and result["streak"] > 0:
        milestone_msg = f"\n\n⭐ **{result['streak']} DAY STREAK!**"
    
    embed = discord.Embed(
        title="✨ Daily Reward Claimed! ✨",
        color=0x00FF00
    )
    
    reward_text = f"+**{result['reward']}** aura"
    if result["multiplier"] > 1:
        reward_text += f" (x{result['multiplier']} boost!)"
    
    embed.add_field(name="💰 Reward", value=reward_text, inline=True)
    embed.add_field(name="🔥 Streak", value=f"**{result['streak']}** days", inline=True)
    embed.add_field(name="✨ Total Aura", value=f"**{result['new_aura']}**", inline=True)
    
    next_reward = calculate_daily_reward(result["streak"] + 1)
    embed.add_field(
        name="📈 Tomorrow's Reward",
        value=f"**{next_reward}** aura",
        inline=False
    )
    
    if milestone_msg:
        embed.description = milestone_msg
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text=f"Total claims: {result['total_claims']} | Highest streak: {result['highest_streak']}")
    
    await interaction.response.send_message(embed=embed)

@bot.command()
async def streak(ctx, member: discord.Member = None):
    """Check your or someone's daily streak."""
    member = member or ctx.author
    info = get_daily_info(str(member.id))
    
    can_claim, seconds_until = can_claim_daily(str(member.id))
    
    embed = discord.Embed(
        title=f"🔥 {member.display_name}'s Streak",
        color=0xFF9500
    )
    embed.add_field(name="📅 Current Streak", value=f"**{info['streak']}** days", inline=True)
    embed.add_field(name="🏆 Highest Streak", value=f"**{info['highest_streak']}** days", inline=True)
    embed.add_field(name="📊 Total Claims", value=f"**{info['total_claims']}**", inline=True)
    
    if member == ctx.author:
        if can_claim:
            embed.add_field(
                name="✅ Daily Status",
                value="**Ready to claim!** Use `!daily`",
                inline=False
            )
        else:
            hours = seconds_until // 3600
            minutes = (seconds_until % 3600) // 60
            embed.add_field(
                name="⏰ Next Daily",
                value=f"In **{hours}h {minutes}m**",
                inline=False
            )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.tree.command(name="streak", description="Check daily streak information")
async def streak_slash(interaction: discord.Interaction, user: discord.Member = None):
    member = user or interaction.user
    info = get_daily_info(str(member.id))
    
    can_claim, seconds_until = can_claim_daily(str(member.id))
    
    embed = discord.Embed(
        title=f"🔥 {member.display_name}'s Streak",
        color=0xFF9500
    )
    embed.add_field(name="📅 Current Streak", value=f"**{info['streak']}** days", inline=True)
    embed.add_field(name="🏆 Highest Streak", value=f"**{info['highest_streak']}** days", inline=True)
    embed.add_field(name="📊 Total Claims", value=f"**{info['total_claims']}**", inline=True)
    
    if member == interaction.user:
        if can_claim:
            embed.add_field(
                name="✅ Daily Status",
                value="**Ready to claim!** Use `/daily`",
                inline=False
            )
        else:
            hours = seconds_until // 3600
            minutes = (seconds_until % 3600) // 60
            embed.add_field(
                name="⏰ Next Daily",
                value=f"In **{hours}h {minutes}m**",
                inline=False
            )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# ============================================================================
# AURA SHOP
# ============================================================================

def get_user_inventory(user_id: str) -> dict:
    """Get user's purchased items and active effects."""
    return shop_data.get(user_id, {
        "titles": [],
        "badges": [],
        "colors": [],
        "active_title": None,
        "active_badge": None,
        "active_color": None,
        "multiplier_expires": 0,
        "multiplier_value": 1,
        "shield_expires": 0
    })

def purchase_item(user_id: str, item_id: str) -> tuple[bool, str]:
    """
    Attempt to purchase an item.
    Returns: (success: bool, message: str)
    """
    if item_id not in SHOP_ITEMS:
        return False, "Item not found!"
    
    item = SHOP_ITEMS[item_id]
    user_aura = aura_data.get(user_id, 0)
    
    if user_aura < item["price"]:
        return False, f"Not enough aura! You need **{item['price']}** but have **{user_aura}**."
    
    inventory = get_user_inventory(user_id)
    shop_data[user_id] = inventory
    
    item_type = item["type"]
    
    # Check if already owned (for permanent items)
    if item_type in ["title", "badge", "color"]:
        owned_key = f"{item_type}s"  # titles, badges, colors
        if item_id in inventory.get(owned_key, []):
            return False, "You already own this item!"
        
        # Add to inventory
        inventory.setdefault(owned_key, []).append(item_id)
    
    elif item_type == "multiplier":
        # Temporary boost - extend if already active
        current_expires = inventory.get("multiplier_expires", 0)
        if time.time() < current_expires:
            # Extend existing boost
            inventory["multiplier_expires"] = current_expires + item["duration"]
        else:
            # New boost
            inventory["multiplier_expires"] = time.time() + item["duration"]
        inventory["multiplier_value"] = item["value"]
    
    elif item_type == "shield":
        current_expires = inventory.get("shield_expires", 0)
        if time.time() < current_expires:
            inventory["shield_expires"] = current_expires + item["duration"]
        else:
            inventory["shield_expires"] = time.time() + item["duration"]
    
    # Deduct aura
    aura_data[user_id] = user_aura - item["price"]
    
    save_json_safe(SHOP_FILE, shop_data)
    save_json_safe(DATA_FILE, aura_data)
    
    return True, f"Successfully purchased **{item['name']}**!"

def equip_item(user_id: str, item_id: str) -> tuple[bool, str]:
    """Equip a cosmetic item."""
    if item_id not in SHOP_ITEMS:
        return False, "Item not found!"
    
    item = SHOP_ITEMS[item_id]
    inventory = get_user_inventory(user_id)
    
    item_type = item["type"]
    
    if item_type not in ["title", "badge", "color"]:
        return False, "This item cannot be equipped!"
    
    owned_key = f"{item_type}s"
    if item_id not in inventory.get(owned_key, []):
        return False, "You don't own this item!"
    
    # Equip the item
    inventory[f"active_{item_type}"] = item_id
    shop_data[user_id] = inventory
    save_json_safe(SHOP_FILE, shop_data)
    
    return True, f"Equipped **{item['name']}**!"

@bot.command()
async def shop(ctx):
    """View the aura shop!"""
    user_aura = aura_data.get(str(ctx.author.id), 0)
    inventory = get_user_inventory(str(ctx.author.id))
    
    embed = discord.Embed(
        title="🛒 Aura Shop",
        description=f"Your Aura: **{user_aura}** ✨\n\nUse `!buy <item_id>` to purchase!",
        color=0x9B59B6
    )
    
    # Group items by type
    titles = []
    badges = []
    colors = []
    boosts = []
    
    for item_id, item in SHOP_ITEMS.items():
        owned = item_id in inventory.get(f"{item['type']}s", [])
        owned_tag = " ✅" if owned else ""
        line = f"`{item_id}` - {item['name']} - **{item['price']}** aura{owned_tag}"
        
        if item["type"] == "title":
            titles.append(line)
        elif item["type"] == "badge":
            badges.append(line)
        elif item["type"] == "color":
            colors.append(line)
        else:
            boosts.append(line)
    
    if titles:
        embed.add_field(name="🏷️ Titles", value="\n".join(titles), inline=False)
    if badges:
        embed.add_field(name="🎖️ Badges", value="\n".join(badges), inline=False)
    if colors:
        embed.add_field(name="🎨 Profile Colors", value="\n".join(colors), inline=False)
    if boosts:
        embed.add_field(name="⚡ Boosts", value="\n".join(boosts), inline=False)
    
    embed.set_footer(text="✅ = Owned | Use !inventory to see your items")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="shop", description="View the aura shop")
async def shop_slash(interaction: discord.Interaction):
    user_aura = aura_data.get(str(interaction.user.id), 0)
    inventory = get_user_inventory(str(interaction.user.id))
    
    embed = discord.Embed(
        title="🛒 Aura Shop",
        description=f"Your Aura: **{user_aura}** ✨\n\nUse `/buy <item_id>` to purchase!",
        color=0x9B59B6
    )
    
    titles = []
    badges = []
    colors = []
    boosts = []
    
    for item_id, item in SHOP_ITEMS.items():
        owned = item_id in inventory.get(f"{item['type']}s", [])
        owned_tag = " ✅" if owned else ""
        line = f"`{item_id}` - {item['name']} - **{item['price']}** aura{owned_tag}"
        
        if item["type"] == "title":
            titles.append(line)
        elif item["type"] == "badge":
            badges.append(line)
        elif item["type"] == "color":
            colors.append(line)
        else:
            boosts.append(line)
    
    if titles:
        embed.add_field(name="🏷️ Titles", value="\n".join(titles), inline=False)
    if badges:
        embed.add_field(name="🎖️ Badges", value="\n".join(badges), inline=False)
    if colors:
        embed.add_field(name="🎨 Profile Colors", value="\n".join(colors), inline=False)
    if boosts:
        embed.add_field(name="⚡ Boosts", value="\n".join(boosts), inline=False)
    
    embed.set_footer(text="✅ = Owned | Use /inventory to see your items")
    
    await interaction.response.send_message(embed=embed)

@bot.command()
async def buy(ctx, item_id: str = None):
    """Buy an item from the shop."""
    if item_id is None:
        embed = discord.Embed(
            title="🛒 How to Buy",
            description="Use `!buy <item_id>` to purchase an item!\n\nExample: `!buy title_champion`",
            color=0xFFD700
        )
        embed.add_field(
            name="📋 View Shop",
            value="Use `!shop` to see all available items and their IDs.",
            inline=False
        )
        embed.add_field(
            name="💡 Popular Items",
            value=(
                "`!buy title_champion` - Champion title (500 aura)\n"
                "`!buy badge_star` - Star badge (300 aura)\n"
                "`!buy boost_2x` - 2x Aura boost 24h (1000 aura)\n"
                "`!buy shield` - Battle shield 24h (500 aura)"
            ),
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    user_id = str(ctx.author.id)
    user_aura = aura_data.get(user_id, 0)
    
    # Check if item exists
    item = None
    for category in SHOP_ITEMS.values():
        if item_id in category:
            item = category[item_id]
            break
    
    if not item:
        await ctx.send(f"❌ Item `{item_id}` not found! Use `!shop` to see available items.")
        return
    
    # Check if user can afford it
    if user_aura < item["price"]:
        await ctx.send(f"❌ You need **{item['price']}** aura but only have **{user_aura}**!")
        return
    
    # Check if already owned (for non-consumables)
    user_inv = inventory_data.setdefault(user_id, {"items": [], "equipped": {}})
    
    if item["type"] in ["title", "badge", "color"] and item_id in user_inv.get("items", []):
        await ctx.send(f"❌ You already own **{item['name']}**!")
        return
    
    # Deduct aura
    aura_data[user_id] -= item["price"]
    save_data(aura_data)
    
    # Handle different item types
    if item["type"] == "boost":
        expiry = datetime.now() + timedelta(hours=24)
        user_inv["active_boost"] = expiry.isoformat()
        await ctx.send(f"✅ Purchased **{item['name']}**! 2x aura gains for 24 hours! 🚀")
    
    elif item["type"] == "shield":
        expiry = datetime.now() + timedelta(hours=24)
        user_inv["active_shield"] = expiry.isoformat()
        await ctx.send(f"✅ Purchased **{item['name']}**! Protected from battle losses for 24 hours! 🛡️")
    
    else:
        if "items" not in user_inv:
            user_inv["items"] = []
        user_inv["items"].append(item_id)
        await ctx.send(f"✅ Purchased **{item['name']}**! Use `!equip {item_id}` to equip it!")
    
    inventory_data[user_id] = user_inv
    save_inventory()

@bot.command()
async def equip(ctx, item_id: str = None):
    """Equip an item you own."""
    if item_id is None:
        embed = discord.Embed(
            title="👕 How to Equip",
            description="Use `!equip <item_id>` to equip an item!\n\nExample: `!equip title_champion`",
            color=0x9B59B6
        )
        embed.add_field(
            name="📦 View Your Items",
            value="Use `!inventory` to see items you own.",
            inline=False
        )
        embed.add_field(
            name="💡 Example",
            value=(
                "`!equip title_champion` - Equip Champion title\n"
                "`!equip badge_star` - Equip Star badge\n"
                "`!equip color_gold` - Equip Gold color"
            ),
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    user_id = str(ctx.author.id)
    user_inv = inventory_data.get(user_id, {"items": [], "equipped": {}})
    
    # Check if user owns the item
    if item_id not in user_inv.get("items", []):
        await ctx.send(f"❌ You don't own `{item_id}`! Use `!shop` to buy it first.")
        return
    
    # Find the item
    item = None
    for category in SHOP_ITEMS.values():
        if item_id in category:
            item = category[item_id]
            break
    
    if not item:
        await ctx.send(f"❌ Item `{item_id}` not found!")
        return
    
    # Equip the item
    if "equipped" not in user_inv:
        user_inv["equipped"] = {}
    
    user_inv["equipped"][item["type"]] = item_id
    inventory_data[user_id] = user_inv
    save_inventory()
    
    await ctx.send(f"✅ Equipped **{item['name']}**! {item.get('emoji', '✨')}")

@bot.tree.command(name="equip", description="Equip an item you own")
@app_commands.describe(item_id="The ID of the item to equip (use /inventory to see your items)")
async def equip_slash(interaction: discord.Interaction, item_id: str = None):
    if item_id is None:
        await interaction.response.send_message(
            "❌ Please specify an item! Example: `/equip item_id:title_champion`\n\nUse `/inventory` to see your items.",
            ephemeral=True
        )
        return
    
    user_id = str(interaction.user.id)
    user_inv = inventory_data.get(user_id, {"items": [], "equipped": {}})
    
    if item_id not in user_inv.get("items", []):
        await interaction.response.send_message(f"❌ You don't own `{item_id}`!", ephemeral=True)
        return
    
    item = None
    for category in SHOP_ITEMS.values():
        if item_id in category:
            item = category[item_id]
            break
    
    if not item:
        await interaction.response.send_message(f"❌ Item not found!", ephemeral=True)
        return
    
    user_inv.setdefault("equipped", {})[item["type"]] = item_id
    inventory_data[user_id] = user_inv
    save_inventory()
    
    await interaction.response.send_message(f"✅ Equipped **{item['name']}**! {item.get('emoji', '✨')}")

@bot.command()
async def inventory(ctx, member: discord.Member = None):
    """View your or someone's inventory."""
    member = member or ctx.author
    inventory = get_user_inventory(str(member.id))
    
    embed = discord.Embed(
        title=f"🎒 {member.display_name}'s Inventory",
        color=0x9B59B6
    )
    
    # Titles
    titles = inventory.get("titles", [])
    if titles:
        title_list = []
        for tid in titles:
            item = SHOP_ITEMS.get(tid, {})
            active = " (Equipped)" if inventory.get("active_title") == tid else ""
            title_list.append(f"{item.get('name', tid)}{active}")
        embed.add_field(name="🏷️ Titles", value="\n".join(title_list), inline=False)
    
    # Badges
    badges = inventory.get("badges", [])
    if badges:
        badge_list = []
        for bid in badges:
            item = SHOP_ITEMS.get(bid, {})
            active = " (Equipped)" if inventory.get("active_badge") == bid else ""
            badge_list.append(f"{item.get('name', bid)}{active}")
        embed.add_field(name="🎖️ Badges", value="\n".join(badge_list), inline=False)
    
    # Colors
    colors = inventory.get("colors", [])
    if colors:
        color_list = []
        for cid in colors:
            item = SHOP_ITEMS.get(cid, {})
            active = " (Equipped)" if inventory.get("active_color") == cid else ""
            color_list.append(f"{item.get('name', cid)}{active}")
        embed.add_field(name="🎨 Colors", value="\n".join(color_list), inline=False)
    
    # Active boosts
    now = time.time()
    boosts = []
    
    if inventory.get("multiplier_expires", 0) > now:
        remaining = int(inventory["multiplier_expires"] - now)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        boosts.append(f"⚡ **{inventory.get('multiplier_value', 2)}x Boost** - {hours}h {minutes}m remaining")
    
    if inventory.get("shield_expires", 0) > now:
        remaining = int(inventory["shield_expires"] - now)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        boosts.append(f"🛡️ **Battle Shield** - {hours}h {minutes}m remaining")
    
    if boosts:
        embed.add_field(name="⚡ Active Boosts", value="\n".join(boosts), inline=False)
    
    if not titles and not badges and not colors and not boosts:
        embed.description = "No items yet! Use `!shop` to browse."
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.tree.command(name="inventory", description="View your inventory")
async def inventory_slash(interaction: discord.Interaction, user: discord.Member = None):
    member = user or interaction.user
    inventory = get_user_inventory(str(member.id))
    
    embed = discord.Embed(
        title=f"🎒 {member.display_name}'s Inventory",
        color=0x9B59B6
    )
    
    titles = inventory.get("titles", [])
    if titles:
        title_list = []
        for tid in titles:
            item = SHOP_ITEMS.get(tid, {})
            active = " (Equipped)" if inventory.get("active_title") == tid else ""
            title_list.append(f"{item.get('name', tid)}{active}")
        embed.add_field(name="🏷️ Titles", value="\n".join(title_list), inline=False)
    
    badges = inventory.get("badges", [])
    if badges:
        badge_list = []
        for bid in badges:
            item = SHOP_ITEMS.get(bid, {})
            active = " (Equipped)" if inventory.get("active_badge") == bid else ""
            badge_list.append(f"{item.get('name', bid)}{active}")
        embed.add_field(name="🎖️ Badges", value="\n".join(badge_list), inline=False)
    
    colors = inventory.get("colors", [])
    if colors:
        color_list = []
        for cid in colors:
            item = SHOP_ITEMS.get(cid, {})
            active = " (Equipped)" if inventory.get("active_color") == cid else ""
            color_list.append(f"{item.get('name', cid)}{active}")
        embed.add_field(name="🎨 Colors", value="\n".join(color_list), inline=False)
    
    now = time.time()
    boosts = []
    
    if inventory.get("multiplier_expires", 0) > now:
        remaining = int(inventory["multiplier_expires"] - now)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        boosts.append(f"⚡ **{inventory.get('multiplier_value', 2)}x Boost** - {hours}h {minutes}m remaining")
    
    if inventory.get("shield_expires", 0) > now:
        remaining = int(inventory["shield_expires"] - now)
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        boosts.append(f"🛡️ **Battle Shield** - {hours}h {minutes}m remaining")
    
    if boosts:
        embed.add_field(name="⚡ Active Boosts", value="\n".join(boosts), inline=False)
    
    if not titles and not badges and not colors and not boosts:
        embed.description = "No items yet! Use `/shop` to browse."
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# ============================================================================
# WEEKLY TOURNAMENTS
# ============================================================================

def get_current_tournament(guild_id: str) -> dict:
    """Get or create current tournament for a guild."""
    guild_tournaments = tournaments_data.setdefault(guild_id, {})
    
    current = guild_tournaments.get("current")
    now = time.time()
    
    # Check if tournament expired or doesn't exist
    if not current or current.get("ends_at", 0) < now:
        # Archive old tournament if exists
        if current:
            guild_tournaments.setdefault("history", []).append(current)
            # Keep only last 10 tournaments
            guild_tournaments["history"] = guild_tournaments["history"][-10:]
        
        # Create new tournament
        current = {
            "started_at": now,
            "ends_at": now + TOURNAMENT_DURATION,
            "participants": {},
            "week_number": guild_tournaments.get("week_count", 0) + 1
        }
        guild_tournaments["current"] = current
        guild_tournaments["week_count"] = current["week_number"]
        save_json_safe(TOURNAMENTS_FILE, tournaments_data)
    
    return current

def record_tournament_aura(guild_id: str, user_id: str, aura_gained: int):
    """Record aura gained during tournament."""
    if aura_gained <= 0:
        return
    
    tournament = get_current_tournament(guild_id)
    participants = tournament.setdefault("participants", {})
    participants[user_id] = participants.get(user_id, 0) + aura_gained
    save_json_safe(TOURNAMENTS_FILE, tournaments_data)

def get_tournament_leaderboard(guild_id: str) -> list:
    """Get tournament leaderboard as sorted list of (user_id, aura_gained)."""
    tournament = get_current_tournament(guild_id)
    participants = tournament.get("participants", {})
    return sorted(participants.items(), key=lambda x: x[1], reverse=True)

@bot.command()
async def tournament(ctx):
    """View the current weekly tournament!"""
    guild_id = str(ctx.guild.id)
    tournament = get_current_tournament(guild_id)
    
    # Calculate time remaining
    remaining = int(tournament["ends_at"] - time.time())
    days = remaining // 86400
    hours = (remaining % 86400) // 3600
    
    # Get leaderboard
    leaderboard = get_tournament_leaderboard(guild_id)[:10]
    
    embed = discord.Embed(
        title=f"🏆 Weekly Tournament #{tournament['week_number']}",
        description=f"⏰ **{days}d {hours}h** remaining",
        color=0xFFD700
    )
    
    # Build leaderboard
    if leaderboard:
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (uid, gained) in enumerate(leaderboard):
            medal = medals[i] if i < 3 else f"**{i+1}.**"
            lines.append(f"{medal} <@{uid}> — **+{gained}** aura")
        
        embed.add_field(
            name="📊 Top 10 This Week",
            value="\n".join(lines),
            inline=False
        )
    else:
        embed.add_field(
            name="📊 Leaderboard",
            value="No participants yet! Start chatting to join!",
            inline=False
        )
    
    # Show prizes
    prizes_text = (
        "🥇 1st: **500 aura** + Weekly Champion title\n"
        "🥈 2nd: **300 aura**\n"
        "🥉 3rd: **150 aura**"
    )
    embed.add_field(name="🎁 Prizes", value=prizes_text, inline=False)
    
    # Show user's position
    user_id = str(ctx.author.id)
    user_pos = None
    user_gained = 0
    for i, (uid, gained) in enumerate(leaderboard):
        if uid == user_id:
            user_pos = i + 1
            user_gained = gained
            break
    
    if user_pos:
        embed.add_field(
            name="📍 Your Position",
            value=f"**#{user_pos}** with **+{user_gained}** aura gained",
            inline=False
        )
    else:
        embed.add_field(
            name="📍 Your Position",
            value="Not participating yet! Chat to join!",
            inline=False
        )
    
    embed.set_footer(text="Tournaments reset every Monday at midnight UTC")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="tournament", description="View the current weekly tournament")
async def tournament_slash(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    tournament = get_current_tournament(guild_id)
    
    remaining = int(tournament["ends_at"] - time.time())
    days = remaining // 86400
    hours = (remaining % 86400) // 3600
    
    leaderboard = get_tournament_leaderboard(guild_id)[:10]
    
    embed = discord.Embed(
        title=f"🏆 Weekly Tournament #{tournament['week_number']}",
        description=f"⏰ **{days}d {hours}h** remaining",
        color=0xFFD700
    )
    
    if leaderboard:
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (uid, gained) in enumerate(leaderboard):
            medal = medals[i] if i < 3 else f"**{i+1}.**"
            lines.append(f"{medal} <@{uid}> — **+{gained}** aura")
        
        embed.add_field(name="📊 Top 10 This Week", value="\n".join(lines), inline=False)
    else:
        embed.add_field(
            name="📊 Leaderboard",
            value="No participants yet!",
            inline=False
        )
    
    prizes_text = (
        "🥇 1st: **500 aura** + Weekly Champion title\n"
        "🥈 2nd: **300 aura**\n"
        "🥉 3rd: **150 aura**"
    )
    embed.add_field(name="🎁 Prizes", value=prizes_text, inline=False)
    
    user_id = str(interaction.user.id)
    user_pos = None
    user_gained = 0
    for i, (uid, gained) in enumerate(get_tournament_leaderboard(guild_id)):
        if uid == user_id:
            user_pos = i + 1
            user_gained = gained
            break
    
    if user_pos:
        embed.add_field(
            name="📍 Your Position",
            value=f"**#{user_pos}** with **+{user_gained}** aura gained",
            inline=False
        )
    else:
        embed.add_field(
            name="📍 Your Position",
            value="Not participating yet!",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@tasks.loop(hours=1)
async def tournament_check_task():
    """Check for tournament endings and award prizes."""
    now = time.time()
    
    for guild_id, guild_data in tournaments_data.items():
        current = guild_data.get("current")
        if not current:
            continue
        
        # Check if tournament just ended
        if current.get("ends_at", 0) < now and not current.get("prizes_awarded"):
            # Award prizes
            leaderboard = get_tournament_leaderboard(guild_id)
            
            for rank, prize_info in TOURNAMENT_PRIZES.items():
                if len(leaderboard) >= rank:
                    winner_id = leaderboard[rank - 1][0]
                    
                    # Award aura
                    aura_data[winner_id] = aura_data.get(winner_id, 0) + prize_info["aura"]
                    
                    # Award title if applicable
                    if prize_info.get("title"):
                        inventory = get_user_inventory(winner_id)
                        # Create a special tournament winner title
                        special_title = f"tournament_champion_week_{current['week_number']}"
                        inventory.setdefault("titles", []).append(special_title)
                        shop_data[winner_id] = inventory
            
            current["prizes_awarded"] = True
            save_json_safe(TOURNAMENTS_FILE, tournaments_data)
            save_json_safe(DATA_FILE, aura_data)
            save_json_safe(SHOP_FILE, shop_data)
            
            # Try to announce in the guild
            try:
                guild = bot.get_guild(int(guild_id))
                if guild:
                    # Find a general channel to announce
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            if "general" in channel.name.lower() or "chat" in channel.name.lower():
                                embed = discord.Embed(
                                    title=f"🏆 Tournament #{current['week_number']} has ended!",
                                    color=0xFFD700
                                )
                                
                                winners_text = ""
                                medals = ["🥇", "🥈", "🥉"]
                                for i, (uid, gained) in enumerate(leaderboard[:3]):
                                    prize = TOURNAMENT_PRIZES.get(i + 1, {})
                                    winners_text += f"{medals[i]} <@{uid}> — +{gained} aura (Prize: {prize.get('aura', 0)} aura)\n"
                                
                                embed.add_field(name="🎉 Winners", value=winners_text or "No participants", inline=False)
                                embed.add_field(name="🆕 New Tournament", value="A new tournament has begun! Use `!tournament` to check!", inline=False)
                                
                                await channel.send(embed=embed)
                                break
            except Exception as e:
                print(f"[TOURNAMENT] Could not announce results: {e}")

# ============================================================================
# AURA CARD / PROFILE
# ============================================================================

async def generate_aura_card_image(member: discord.Member, aura: int, rank: str, inventory: dict, stats: dict) -> BytesIO:
    """Generate an image aura card using PIL."""
    
    if not PIL_AVAILABLE:
        return None
    
    # Card dimensions
    width, height = 800, 400
    
    # Get profile color from inventory
    color_id = inventory.get("active_color")
    if color_id and color_id in SHOP_ITEMS:
        bg_color = SHOP_ITEMS[color_id]["value"]
    else:
        bg_color = 0x5865F2  # Default Discord blue
    
    # Convert hex to RGB
    bg_rgb = ((bg_color >> 16) & 255, (bg_color >> 8) & 255, bg_color & 255)
    
    # Create image
    img = Image.new('RGB', (width, height), bg_rgb)
    draw = ImageDraw.Draw(img)
    
    # Try to load a font (fall back to default if not available)
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw gradient overlay (darker at bottom)
    for y in range(height):
        alpha = int(50 * (y / height))
        draw.rectangle([(0, y), (width, y + 1)], fill=(0, 0, 0, alpha))
    
    # Fetch and paste avatar
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(str(member.display_avatar.url)) as resp:
                avatar_data = await resp.read()
        
        avatar_img = Image.open(BytesIO(avatar_data)).convert("RGBA")
        avatar_img = avatar_img.resize((120, 120))
        
        # Create circular mask
        mask = Image.new("L", (120, 120), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 120, 120), fill=255)
        
        # Paste avatar
        img.paste(avatar_img, (40, 40), mask)
    except Exception as e:
        print(f"[AURA CARD] Avatar error: {e}")
        # Draw placeholder circle
        draw.ellipse((40, 40, 160, 160), fill=(100, 100, 100))
    
    # Draw username and title
    title = inventory.get("active_title")
    if title and title in SHOP_ITEMS:
        title_text = SHOP_ITEMS[title]["value"]
        display_name = f"{member.display_name} • {title_text}"
    else:
        display_name = member.display_name
    
    draw.text((180, 50), display_name, fill=(255, 255, 255), font=title_font)
    
    # Draw badge if equipped
    badge_id = inventory.get("active_badge")
    if badge_id and badge_id in SHOP_ITEMS:
        badge = SHOP_ITEMS[badge_id]["value"]
        draw.text((180, 95), badge, fill=(255, 255, 255), font=title_font)
    
    # Draw aura score
    draw.text((180, 130), f"✨ {aura} Aura", fill=(255, 255, 255), font=text_font)
    
    # Draw rank
    draw.text((180, 165), f"🏆 {rank}", fill=(255, 215, 0), font=text_font)
    
    # Draw stats section
    stats_y = 220
    draw.text((40, stats_y), "📊 STATS", fill=(255, 255, 255), font=text_font)
    
    draw.text((40, stats_y + 40), f"Messages: {stats.get('total_messages', 0)}", fill=(200, 200, 200), font=small_font)
    draw.text((40, stats_y + 70), f"Battle Wins: {stats.get('wins', 0)}", fill=(200, 200, 200), font=small_font)
    draw.text((40, stats_y + 100), f"Daily Streak: {stats.get('streak', 0)} 🔥", fill=(200, 200, 200), font=small_font)
    
    # Draw weekly stats
    draw.text((400, stats_y), "📈 THIS WEEK", fill=(255, 255, 255), font=text_font)
    draw.text((400, stats_y + 40), f"Aura Gained: +{stats.get('weekly_gain', 0)}", fill=(200, 200, 200), font=small_font)
    draw.text((400, stats_y + 70), f"Server Rank: #{stats.get('server_rank', '?')}", fill=(200, 200, 200), font=small_font)
    
    # Save to BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer

def generate_text_aura_card(member: discord.Member, aura: int, rank: str, inventory: dict, stats: dict) -> discord.Embed:
    """Generate a text-based aura card embed."""
    
    # Get profile color
    color_id = inventory.get("active_color")
    if color_id and color_id in SHOP_ITEMS:
        color = SHOP_ITEMS[color_id]["value"]
    else:
        color = 0x5865F2
    
    # Get title
    title_id = inventory.get("active_title")
    title_text = ""
    if title_id and title_id in SHOP_ITEMS:
        title_text = f" • {SHOP_ITEMS[title_id]['value']}"
    
    # Get badge
    badge_id = inventory.get("active_badge")
    badge = ""
    if badge_id and badge_id in SHOP_ITEMS:
        badge = f" {SHOP_ITEMS[badge_id]['value']}"
    
    embed = discord.Embed(
        title=f"✨ {member.display_name}{title_text}{badge}",
        color=color
    )
    
    # Main stats
    embed.add_field(
        name="⚡ Aura",
        value=f"**{aura}**",
        inline=True
    )
    embed.add_field(
        name="🏆 Rank",
        value=f"**{rank}**",
        inline=True
    )
    embed.add_field(
        name="📍 Server Rank",
        value=f"**#{stats.get('server_rank', '?')}**",
        inline=True
    )
    
    # Battle stats
    embed.add_field(
        name="⚔️ Battles",
        value=f"**{stats.get('wins', 0)}**W / **{stats.get('losses', 0)}**L",
        inline=True
    )
    embed.add_field(
        name="🔥 Streak",
        value=f"**{stats.get('streak', 0)}** days",
        inline=True
    )
    embed.add_field(
        name="📈 Weekly",
        value=f"+**{stats.get('weekly_gain', 0)}** aura",
        inline=True
    )
    
    # Active boosts
    now = time.time()
    boosts = []
    if inventory.get("multiplier_expires", 0) > now:
        boosts.append(f"⚡ {inventory.get('multiplier_value', 2)}x Boost")
    if inventory.get("shield_expires", 0) > now:
        boosts.append("🛡️ Shield")
    
    if boosts:
        embed.add_field(
            name="✨ Active Boosts",
            value=" • ".join(boosts),
            inline=False
        )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Auraxis • !shop to customize your card")
    
    return embed

@bot.command()
async def auracard(ctx, member: discord.Member = None):
    """Display your or someone's aura profile card!"""
    member = member or ctx.author
    uid = str(member.id)
    
    aura = aura_data.get(uid, 0)
    rank = get_rank_name(aura)
    inventory = get_user_inventory(uid)
    
    # Gather stats
    battle_stats = battles_data.get(uid, {})
    streak_info = get_daily_info(uid)
    
    # Calculate server rank
    sorted_aura = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)
    server_rank = next((i + 1 for i, (u, _) in enumerate(sorted_aura) if u == uid), None)
    
    # Calculate weekly gain from tournament
    weekly_gain = 0
    if ctx.guild:
        tournament = get_current_tournament(str(ctx.guild.id))
        weekly_gain = tournament.get("participants", {}).get(uid, 0)
    
    stats = {
        "wins": battle_stats.get("wins", 0),
        "losses": battle_stats.get("losses", 0),
        "streak": streak_info.get("streak", 0),
        "server_rank": server_rank,
        "weekly_gain": weekly_gain,
        "total_messages": len(aura_logs.get(uid, []))
    }
    
    # Try to generate image card
    if PIL_AVAILABLE:
        try:
            buffer = await generate_aura_card_image(member, aura, rank, inventory, stats)
            if buffer:
                file = discord.File(buffer, filename="auracard.png")
                await ctx.send(file=file)
                return
        except Exception as e:
            print(f"[AURA CARD] Image generation failed: {e}")
    
    # Fall back to text embed
    embed = generate_text_aura_card(member, aura, rank, inventory, stats)
    await ctx.send(embed=embed)

@bot.tree.command(name="auracard", description="Display your aura profile card")
async def auracard_slash(interaction: discord.Interaction, user: discord.Member = None):
    member = user or interaction.user
    uid = str(member.id)
    
    aura = aura_data.get(uid, 0)
    rank = get_rank_name(aura)
    inventory = get_user_inventory(uid)
    
    battle_stats = battles_data.get(uid, {})
    streak_info = get_daily_info(uid)
    
    sorted_aura = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)
    server_rank = next((i + 1 for i, (u, _) in enumerate(sorted_aura) if u == uid), None)
    
    weekly_gain = 0
    if interaction.guild:
        tournament = get_current_tournament(str(interaction.guild.id))
        weekly_gain = tournament.get("participants", {}).get(uid, 0)
    
    stats = {
        "wins": battle_stats.get("wins", 0),
        "losses": battle_stats.get("losses", 0),
        "streak": streak_info.get("streak", 0),
        "server_rank": server_rank,
        "weekly_gain": weekly_gain,
        "total_messages": len(aura_logs.get(uid, []))
    }
    
    if PIL_AVAILABLE:
        try:
            buffer = await generate_aura_card_image(member, aura, rank, inventory, stats)
            if buffer:
                file = discord.File(buffer, filename="auracard.png")
                await interaction.response.send_message(file=file)
                return
        except Exception as e:
            print(f"[AURA CARD] Image generation failed: {e}")
    
    embed = generate_text_aura_card(member, aura, rank, inventory, stats)
    await interaction.response.send_message(embed=embed)

# ============================================================================
# AURA PREDICTION
# ============================================================================

def calculate_aura_trend(user_id: str, days: int = 7) -> dict:
    """Analyze user's aura trend over the past N days."""
    logs = aura_logs.get(user_id, [])
    
    if not logs:
        return {
            "avg_daily": 0,
            "trend": "stable",
            "total_gained": 0,
            "total_lost": 0,
            "active_days": 0
        }
    
    now = time.time()
    cutoff = now - (days * 86400)
    
    recent_logs = [log for log in logs if log.get("timestamp", 0) > cutoff]
    
    if not recent_logs:
        return {
            "avg_daily": 0,
            "trend": "inactive",
            "total_gained": 0,
            "total_lost": 0,
            "active_days": 0
        }
    
    total_gained = sum(log["change"] for log in recent_logs if log["change"] > 0)
    total_lost = abs(sum(log["change"] for log in recent_logs if log["change"] < 0))
    net = total_gained - total_lost
    
    # Count active days
    active_days = len(set(
        datetime.utcfromtimestamp(log["timestamp"]).date()
        for log in recent_logs
    ))
    
    avg_daily = net / days if days > 0 else 0
    
    # Determine trend
    if avg_daily > 10:
        trend = "rising_fast"
    elif avg_daily > 3:
        trend = "rising"
    elif avg_daily > 0:
        trend = "stable_positive"
    elif avg_daily > -3:
        trend = "stable"
    elif avg_daily > -10:
        trend = "declining"
    else:
        trend = "declining_fast"
    
    return {
        "avg_daily": avg_daily,
        "trend": trend,
        "total_gained": total_gained,
        "total_lost": total_lost,
        "active_days": active_days,
        "net": net
    }

def predict_future_aura(user_id: str, days_ahead: int = 7) -> dict:
    """Predict user's aura in N days based on trends."""
    current_aura = aura_data.get(user_id, 0)
    trend = calculate_aura_trend(user_id, 14)  # Use 2 weeks of data
    
    avg_daily = trend["avg_daily"]
    
    # Add some variance based on activity level
    streak_info = get_daily_info(user_id)
    streak_bonus = min(streak_info.get("streak", 0) * 0.5, 5)
    
    # Battle activity bonus
    battle_stats = battles_data.get(user_id, {})
    win_rate = 0
    total_battles = battle_stats.get("wins", 0) + battle_stats.get("losses", 0)
    if total_battles > 0:
        win_rate = battle_stats.get("wins", 0) / total_battles
    battle_bonus = win_rate * 2
    
    # Calculate prediction
    adjusted_daily = avg_daily + streak_bonus + battle_bonus
    predicted_gain = int(adjusted_daily * days_ahead)
    
    # Apply decay estimate
    decay_estimate = int(current_aura * DECAY_RATE * (days_ahead / 7))
    
    predicted_aura = max(0, current_aura + predicted_gain - decay_estimate)
    
    # Calculate confidence based on data amount
    logs_count = len(aura_logs.get(user_id, []))
    if logs_count < 10:
        confidence = "low"
    elif logs_count < 50:
        confidence = "medium"
    else:
        confidence = "high"
    
    return {
        "current": current_aura,
        "predicted": predicted_aura,
        "change": predicted_aura - current_aura,
        "avg_daily": adjusted_daily,
        "confidence": confidence,
        "trend": trend["trend"],
        "days": days_ahead
    }

TREND_EMOJIS = {
    "rising_fast": "🚀",
    "rising": "📈",
    "stable_positive": "✨",
    "stable": "➡️",
    "declining": "📉",
    "declining_fast": "💀",
    "inactive": "😴"
}

TREND_DESCRIPTIONS = {
    "rising_fast": "Skyrocketing! You're on fire!",
    "rising": "Growing steadily. Keep it up!",
    "stable_positive": "Maintaining positive momentum.",
    "stable": "Holding steady.",
    "declining": "Slipping a bit. Stay active!",
    "declining_fast": "Significant drop. Time to turn it around!",
    "inactive": "No recent activity."
}

@bot.command()
async def aurapredict(ctx, member: discord.Member = None, days: int = 7):
    """Predict future aura based on trends!"""
    member = member or ctx.author
    uid = str(member.id)
    
    days = max(1, min(days, 30))  # Clamp between 1 and 30 days
    
    prediction = predict_future_aura(uid, days)
    trend = calculate_aura_trend(uid, 14)
    
    emoji = TREND_EMOJIS.get(prediction["trend"], "❓")
    trend_desc = TREND_DESCRIPTIONS.get(prediction["trend"], "Unknown trend")
    
    embed = discord.Embed(
        title=f"🔮 Aura Prediction: {member.display_name}",
        color=0x9B59B6
    )
    
    embed.add_field(
        name="📊 Current Aura",
        value=f"**{prediction['current']}**",
        inline=True
    )
    
    change_prefix = "+" if prediction["change"] >= 0 else ""
    embed.add_field(
        name=f"🔮 Predicted in {days} days",
        value=f"**{prediction['predicted']}** ({change_prefix}{prediction['change']})",
        inline=True
    )
    
    embed.add_field(
        name=f"{emoji} Trend",
        value=trend_desc,
        inline=False
    )
    
    embed.add_field(
        name="📈 Daily Average",
        value=f"{'+' if prediction['avg_daily'] >= 0 else ''}{prediction['avg_daily']:.1f} aura/day",
        inline=True
    )
    
    embed.add_field(
        name="🎯 Confidence",
        value=prediction["confidence"].capitalize(),
        inline=True
    )
    
    # Advice based on trend
    if prediction["trend"] in ["declining", "declining_fast"]:
        advice = "💡 **Tip:** Stay active, claim dailies, and keep conversations positive!"
    elif prediction["trend"] == "inactive":
        advice = "💡 **Tip:** Start chatting to build up your aura!"
    elif prediction["trend"] in ["rising_fast", "rising"]:
        advice = "💡 **Tip:** Great momentum! Consider battling to win more!"
    else:
        advice = "💡 **Tip:** Try winning battles and maintaining streaks for faster growth!"
    
    embed.add_field(name="", value=advice, inline=False)
    
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Based on {len(aura_logs.get(uid, []))} recorded events")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="aurapredict", description="Predict future aura based on trends")
async def aurapredict_slash(interaction: discord.Interaction, user: discord.Member = None, days: int = 7):
    member = user or interaction.user
    uid = str(member.id)
    
    days = max(1, min(days, 30))
    
    prediction = predict_future_aura(uid, days)
    
    emoji = TREND_EMOJIS.get(prediction["trend"], "❓")
    trend_desc = TREND_DESCRIPTIONS.get(prediction["trend"], "Unknown trend")
    
    embed = discord.Embed(
        title=f"🔮 Aura Prediction: {member.display_name}",
        color=0x9B59B6
    )
    
    embed.add_field(name="📊 Current Aura", value=f"**{prediction['current']}**", inline=True)
    
    change_prefix = "+" if prediction["change"] >= 0 else ""
    embed.add_field(
        name=f"🔮 Predicted in {days} days",
        value=f"**{prediction['predicted']}** ({change_prefix}{prediction['change']})",
        inline=True
    )
    
    embed.add_field(name=f"{emoji} Trend", value=trend_desc, inline=False)
    embed.add_field(
        name="📈 Daily Average",
        value=f"{'+' if prediction['avg_daily'] >= 0 else ''}{prediction['avg_daily']:.1f} aura/day",
        inline=True
    )
    embed.add_field(name="🎯 Confidence", value=prediction["confidence"].capitalize(), inline=True)
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
    
# ============================================================================
# DETAILED STATS
# ============================================================================

@bot.command()
async def aurastats(ctx, member: discord.Member = None):
    """View detailed aura statistics!"""
    member = member or ctx.author
    uid = str(member.id)
    
    aura = aura_data.get(uid, 0)
    rank = get_rank_name(aura)
    logs = aura_logs.get(uid, [])
    battle_stats = battles_data.get(uid, {})
    streak_info = get_daily_info(uid)
    inventory = get_user_inventory(uid)
    
    now = time.time()
    today_start = now - (now % 86400)
    week_start = now - (7 * 86400)
    month_start = now - (30 * 86400)
    
    # Calculate period gains
    today_gain = sum(
        log["change"] for log in logs
        if log.get("timestamp", 0) > today_start
    )
    week_gain = sum(
        log["change"] for log in logs
        if log.get("timestamp", 0) > week_start
    )
    month_gain = sum(
        log["change"] for log in logs
        if log.get("timestamp", 0) > month_start
    )
    
    # Calculate peak aura
    peak_aura = aura
    for log in reversed(logs):
        if log.get("new_score", 0) > peak_aura:
            peak_aura = log["new_score"]
    
    # Find peak date
    peak_date = "Now"
    for log in logs:
        if log.get("new_score", 0) == peak_aura:
            peak_date = datetime.utcfromtimestamp(log["timestamp"]).strftime("%b %d, %Y")
            break
    
    # Calculate message activity
    messages_today = len([l for l in logs if l.get("timestamp", 0) > today_start])
    messages_week = len([l for l in logs if l.get("timestamp", 0) > week_start])
    
    # Toxicity stats
    toxic_count = len([l for l in logs if l.get("reason") in ["abuse", "hate_speech"]])
    toxicity_rate = (toxic_count / len(logs) * 100) if logs else 0
    
    # Battle stats
    wins = battle_stats.get("wins", 0)
    losses = battle_stats.get("losses", 0)
    total_battles = wins + losses
    winrate = (wins / total_battles * 100) if total_battles > 0 else 0
    
    # Server ranking
    sorted_aura = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)
    server_rank = next((i + 1 for i, (u, _) in enumerate(sorted_aura) if u == uid), None)
    total_users = len(sorted_aura)
    percentile = ((total_users - server_rank + 1) / total_users * 100) if server_rank else 0
    
    embed = discord.Embed(
        title=f"📊 {member.display_name}'s Detailed Stats",
        color=0x5865F2
    )
    
    # Main stats
    embed.add_field(
        name="✨ Aura Overview",
        value=(
            f"**Current:** {aura}\n"
            f"**Rank:** {rank}\n"
            f"**Peak:** {peak_aura} ({peak_date})\n"
            f"**Server Rank:** #{server_rank}/{total_users} (Top {percentile:.1f}%)"
        ),
        inline=False
    )
    
    # Period gains
    embed.add_field(
        name="📈 Aura Gains",
        value=(
            f"**Today:** {'+' if today_gain >= 0 else ''}{today_gain}\n"
            f"**This Week:** {'+' if week_gain >= 0 else ''}{week_gain}\n"
            f"**This Month:** {'+' if month_gain >= 0 else ''}{month_gain}"
        ),
        inline=True
    )
    
    # Activity stats
    embed.add_field(
        name="💬 Activity",
        value=(
            f"**Messages Today:** {messages_today}\n"
            f"**Messages (7d):** {messages_week}\n"
            f"**Total Logged:** {len(logs)}"
        ),
        inline=True
    )
    
    # Battle stats
    embed.add_field(
        name="⚔️ Battle Record",
        value=(
            f"**Wins:** {wins}\n"
            f"**Losses:** {losses}\n"
            f"**Win Rate:** {winrate:.1f}%"
        ),
        inline=True
    )
    
    # Streak stats
    embed.add_field(
        name="🔥 Streaks",
        value=(
            f"**Current:** {streak_info.get('streak', 0)} days\n"
            f"**Best:** {streak_info.get('highest_streak', 0)} days\n"
            f"**Total Claims:** {streak_info.get('total_claims', 0)}"
        ),
        inline=True
    )
    
    # Items owned
    titles_owned = len(inventory.get("titles", []))
    badges_owned = len(inventory.get("badges", []))
    colors_owned = len(inventory.get("colors", []))
    
    embed.add_field(
        name="🎒 Collection",
        value=(
            f"**Titles:** {titles_owned}\n"
            f"**Badges:** {badges_owned}\n"
            f"**Colors:** {colors_owned}"
        ),
        inline=True
    )
    
    # Toxicity warning (only show if relevant)
    if toxicity_rate > 5:
        embed.add_field(
            name="⚠️ Toxicity Rate",
            value=f"**{toxicity_rate:.1f}%** of messages flagged",
            inline=True
        )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Member since • Data from {len(logs)} events")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="aurastats", description="View detailed aura statistics")
async def aurastats_slash(interaction: discord.Interaction, user: discord.Member = None):
    member = user or interaction.user
    uid = str(member.id)
    
    aura = aura_data.get(uid, 0)
    rank = get_rank_name(aura)
    logs = aura_logs.get(uid, [])
    battle_stats = battles_data.get(uid, {})
    streak_info = get_daily_info(uid)
    
    now = time.time()
    today_start = now - (now % 86400)
    week_start = now - (7 * 86400)
    
    today_gain = sum(log["change"] for log in logs if log.get("timestamp", 0) > today_start)
    week_gain = sum(log["change"] for log in logs if log.get("timestamp", 0) > week_start)
    
    sorted_aura = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)
    server_rank = next((i + 1 for i, (u, _) in enumerate(sorted_aura) if u == uid), None)
    
    wins = battle_stats.get("wins", 0)
    losses = battle_stats.get("losses", 0)
    total_battles = wins + losses
    winrate = (wins / total_battles * 100) if total_battles > 0 else 0
    
    embed = discord.Embed(
        title=f"📊 {member.display_name}'s Stats",
        color=0x5865F2
    )
    
    embed.add_field(
        name="✨ Aura",
        value=f"**{aura}** ({rank})\nServer Rank: #{server_rank}",
        inline=True
    )
    embed.add_field(
        name="📈 Gains",
        value=f"Today: {'+' if today_gain >= 0 else ''}{today_gain}\nWeek: {'+' if week_gain >= 0 else ''}{week_gain}",
        inline=True
    )
    embed.add_field(
        name="⚔️ Battles",
        value=f"{wins}W/{losses}L ({winrate:.0f}%)",
        inline=True
    )
    embed.add_field(
        name="🔥 Streak",
        value=f"{streak_info.get('streak', 0)} days",
        inline=True
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# ============================================================================
# SERVER ANALYTICS (ADMIN)
# ============================================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def serveraura(ctx):
    """View server-wide aura analytics!"""
    guild = ctx.guild
    
    # Gather server stats
    guild_members = {str(m.id) for m in guild.members if not m.bot}
    
    # Filter aura data to this server
    server_aura = {uid: aura for uid, aura in aura_data.items() if uid in guild_members}
    
    if not server_aura:
        await ctx.send("❌ No aura data for this server yet!")
        return
    
    total_aura = sum(server_aura.values())
    avg_aura = total_aura / len(server_aura) if server_aura else 0
    max_aura = max(server_aura.values()) if server_aura else 0
    min_aura = min(server_aura.values()) if server_aura else 0
    
    # Find top and bottom users
    sorted_server = sorted(server_aura.items(), key=lambda x: x[1], reverse=True)
    top_user_id, top_aura = sorted_server[0] if sorted_server else (None, 0)
    bottom_user_id, bottom_aura = sorted_server[-1] if sorted_server else (None, 0)
    
    # Activity stats from logs
    now = time.time()
    week_start = now - (7 * 86400)
    
    weekly_gains = defaultdict(int)
    weekly_messages = defaultdict(int)
    toxic_users = defaultdict(int)
    
    for uid in guild_members:
        logs = aura_logs.get(uid, [])
        for log in logs:
            if log.get("timestamp", 0) > week_start:
                weekly_gains[uid] += log.get("change", 0)
                weekly_messages[uid] += 1
                if log.get("reason") in ["abuse", "hate_speech"]:
                    toxic_users[uid] += 1
    
    total_weekly_gain = sum(weekly_gains.values())
    total_messages = sum(weekly_messages.values())
    total_toxic = sum(toxic_users.values())
    toxicity_rate = (total_toxic / total_messages * 100) if total_messages > 0 else 0
    
    # Most active user this week
    most_active_id = max(weekly_messages.items(), key=lambda x: x[1])[0] if weekly_messages else None
    
    # Most toxic user (if any significant toxicity)
    most_toxic_id = None
    if toxic_users:
        most_toxic_id = max(toxic_users.items(), key=lambda x: x[1])[0]
        if toxic_users[most_toxic_id] < 3:
            most_toxic_id = None  # Only show if significant
    
    # Channel activity (from config)
    guild_config = config_data.get(str(guild.id), {})
    disabled_channels = len(guild_config.get("disabled_channels", []))
    total_channels = len([c for c in guild.text_channels])
    enabled_channels = total_channels - disabled_channels
    
    # Rank distribution
    rank_dist = defaultdict(int)
    for uid, aura in server_aura.items():
        rank_dist[get_rank_name(aura)] += 1
    
    embed = discord.Embed(
        title=f"🏛️ {guild.name} Aura Analytics",
        color=0x5865F2
    )
    
    embed.add_field(
        name="✨ Aura Overview",
        value=(
            f"**Total Aura:** {total_aura:,}\n"
            f"**Average:** {avg_aura:.0f}\n"
            f"**Highest:** {max_aura}\n"
            f"**Lowest:** {min_aura}"
        ),
        inline=True
    )
    
    embed.add_field(
        name="👥 Users",
        value=(
            f"**Tracked:** {len(server_aura)}\n"
            f"**Total Members:** {len(guild_members)}\n"
            f"**Coverage:** {len(server_aura)/len(guild_members)*100:.0f}%"
        ),
        inline=True
    )
    
    embed.add_field(
        name="📈 This Week",
        value=(
            f"**Net Aura:** {'+' if total_weekly_gain >= 0 else ''}{total_weekly_gain}\n"
            f"**Messages:** {total_messages}\n"
            f"**Avg/User:** {total_messages/len(guild_members):.1f}"
        ),
        inline=True
    )
    
    # Rank distribution
    rank_text = "\n".join([f"**{rank}:** {count}" for rank, count in sorted(rank_dist.items(), key=lambda x: -x[1])])
    embed.add_field(
        name="🏆 Rank Distribution",
        value=rank_text or "No data",
        inline=True
    )
    
    # Health metrics
    health_score = 100
    if toxicity_rate > 10:
        health_score -= 30
    elif toxicity_rate > 5:
        health_score -= 15
    if avg_aura < 50:
        health_score -= 20
    if total_weekly_gain < 0:
        health_score -= 10
    
    health_emoji = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
    
    embed.add_field(
        name=f"{health_emoji} Server Health",
        value=(
            f"**Score:** {health_score}/100\n"
            f"**Toxicity Rate:** {toxicity_rate:.1f}%\n"
            f"**Channels Active:** {enabled_channels}/{total_channels}"
        ),
        inline=True
    )
    
    # Notable users
    notable = []
    if top_user_id:
        notable.append(f"👑 **Top Aura:** <@{top_user_id}> ({top_aura})")
    if most_active_id:
        notable.append(f"💬 **Most Active:** <@{most_active_id}> ({weekly_messages[most_active_id]} msgs)")
    if most_toxic_id:
        notable.append(f"⚠️ **Most Flagged:** <@{most_toxic_id}> ({toxic_users[most_toxic_id]} flags)")
    
    if notable:
        embed.add_field(
            name="📌 Notable Users",
            value="\n".join(notable),
            inline=False
        )
    
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.set_footer(text="Use !tournament to see weekly competition")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="serveraura", description="View server-wide aura analytics")
@app_commands.checks.has_permissions(manage_guild=True)
async def serveraura_slash(interaction: discord.Interaction):
    guild = interaction.guild
    
    guild_members = {str(m.id) for m in guild.members if not m.bot}
    server_aura = {uid: aura for uid, aura in aura_data.items() if uid in guild_members}
    
    if not server_aura:
        await interaction.response.send_message("❌ No aura data for this server yet!", ephemeral=True)
        return
    
    total_aura = sum(server_aura.values())
    avg_aura = total_aura / len(server_aura) if server_aura else 0
    
    now = time.time()
    week_start = now - (7 * 86400)
    
    weekly_messages = 0
    total_toxic = 0
    
    for uid in guild_members:
        logs = aura_logs.get(uid, [])
        for log in logs:
            if log.get("timestamp", 0) > week_start:
                weekly_messages += 1
                if log.get("reason") in ["abuse", "hate_speech"]:
                    total_toxic += 1
    
    toxicity_rate = (total_toxic / weekly_messages * 100) if weekly_messages > 0 else 0
    
    embed = discord.Embed(
        title=f"🏛️ {guild.name} Analytics",
        color=0x5865F2
    )
    
    embed.add_field(name="✨ Total Aura", value=f"**{total_aura:,}**", inline=True)
    embed.add_field(name="📊 Average", value=f"**{avg_aura:.0f}**", inline=True)
    embed.add_field(name="👥 Users", value=f"**{len(server_aura)}**", inline=True)
    embed.add_field(name="💬 Weekly Messages", value=f"**{weekly_messages}**", inline=True)
    embed.add_field(name="⚠️ Toxicity Rate", value=f"**{toxicity_rate:.1f}%**", inline=True)
    
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    
    await interaction.response.send_message(embed=embed)

@serveraura_slash.error
async def serveraura_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)

# ============================================================================
# AURA HISTORY GRAPH
# ============================================================================

def record_daily_snapshot():
    """Record daily aura snapshots for graphing."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    for uid, aura in aura_data.items():
        user_history = history_data.setdefault(uid, {})
        user_history[today] = aura
        
        # Keep only last 30 days
        dates = sorted(user_history.keys())
        if len(dates) > 30:
            for old_date in dates[:-30]:
                del user_history[old_date]
    
    save_json_safe(HISTORY_FILE, history_data)

@tasks.loop(hours=24)
async def daily_snapshot_task():
    """Take daily snapshots of all aura scores."""
    print("[SNAPSHOT] Recording daily aura snapshots...")
    record_daily_snapshot()

def generate_text_graph(data_points: list, height: int = 10, width: int = 30) -> str:
    """Generate a simple ASCII graph."""
    if not data_points:
        return "No data available"
    
    min_val = min(data_points)
    max_val = max(data_points)
    range_val = max_val - min_val or 1
    
    # Normalize to height
    normalized = [(v - min_val) / range_val * (height - 1) for v in data_points]
    
    # Sample data to width
    if len(data_points) > width:
        step = len(data_points) / width
        sampled = [normalized[int(i * step)] for i in range(width)]
    else:
        sampled = normalized
    
    # Build graph
    lines = []
    for row in range(height - 1, -1, -1):
        line = ""
        for val in sampled:
            if val >= row:
                line += "█"
            else:
                line += " "
        lines.append(f"│{line}")
    
    lines.append("└" + "─" * len(sampled))
    
    return "```\n" + "\n".join(lines) + "\n```"

async def generate_image_graph(data_points: list, dates: list, username: str) -> BytesIO:
    """Generate an image graph using PIL."""
    if not PIL_AVAILABLE:
        return None
    
    width, height = 600, 300
    padding = 50
    
    img = Image.new('RGB', (width, height), (54, 57, 63))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
    
    # Title
    draw.text((width // 2 - 80, 10), f"{username}'s Aura History", fill=(255, 255, 255), font=title_font)
    
    if not data_points:
        draw.text((width // 2 - 50, height // 2), "No data", fill=(150, 150, 150), font=font)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    
    # Calculate graph area
    graph_left = padding
    graph_right = width - padding
    graph_top = padding + 20
    graph_bottom = height - padding
    graph_width = graph_right - graph_left
    graph_height = graph_bottom - graph_top
    
    min_val = min(data_points)
    max_val = max(data_points)
    range_val = max_val - min_val or 1
    
    # Draw axes
    draw.line([(graph_left, graph_bottom), (graph_right, graph_bottom)], fill=(100, 100, 100), width=2)
    draw.line([(graph_left, graph_top), (graph_left, graph_bottom)], fill=(100, 100, 100), width=2)
    
    # Draw Y-axis labels
    for i in range(5):
        y = graph_bottom - (i / 4) * graph_height
        val = min_val + (i / 4) * range_val
        draw.text((5, y - 7), f"{int(val)}", fill=(150, 150, 150), font=font)
        draw.line([(graph_left, y), (graph_right, y)], fill=(50, 50, 50), width=1)
    
    # Plot data
    points = []
    for i, val in enumerate(data_points):
        x = graph_left + (i / (len(data_points) - 1 or 1)) * graph_width
        y = graph_bottom - ((val - min_val) / range_val) * graph_height
        points.append((x, y))
    
    # Draw line
    if len(points) > 1:
        draw.line(points, fill=(88, 101, 242), width=3)
    
    # Draw points
    for x, y in points:
        draw.ellipse([(x - 4, y - 4), (x + 4, y + 4)], fill=(114, 137, 218))
    
    # Draw X-axis labels (first and last date)
    if dates:
        draw.text((graph_left, graph_bottom + 5), dates[0], fill=(150, 150, 150), font=font)
        draw.text((graph_right - 60, graph_bottom + 5), dates[-1], fill=(150, 150, 150), font=font)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

@bot.command()
async def auragraph(ctx, member: discord.Member = None, days: int = 14):
    """View aura history graph!"""
    member = member or ctx.author
    uid = str(member.id)
    
    days = max(7, min(days, 30))
    
    user_history = history_data.get(uid, {})
    
    # If no history, build from logs
    if not user_history:
        logs = aura_logs.get(uid, [])
        if logs:
            for log in logs:
                date = datetime.utcfromtimestamp(log["timestamp"]).strftime("%Y-%m-%d")
                user_history[date] = log.get("new_score", 0)
    
    if not user_history:
        await ctx.send(f"❌ No history data for {member.display_name} yet!")
        return
    
    # Get last N days
    sorted_dates = sorted(user_history.keys())[-days:]
    data_points = [user_history[d] for d in sorted_dates]
    
    # Format dates for display
    display_dates = [datetime.strptime(d, "%Y-%m-%d").strftime("%m/%d") for d in sorted_dates]
    
    # Try to generate image graph
    if PIL_AVAILABLE:
        try:
            buffer = await generate_image_graph(data_points, display_dates, member.display_name)
            if buffer:
                file = discord.File(buffer, filename="auragraph.png")
                
                # Add summary embed
                current = data_points[-1] if data_points else 0
                start = data_points[0] if data_points else 0
                change = current - start
                
                embed = discord.Embed(
                    title=f"📈 {member.display_name}'s Aura History",
                    color=0x00FF00 if change >= 0 else 0xFF0000
                )
                embed.add_field(name="📊 Current", value=f"**{current}**", inline=True)
                embed.add_field(name="📈 Change", value=f"**{'+' if change >= 0 else ''}{change}**", inline=True)
                embed.add_field(name="📅 Period", value=f"Last **{len(data_points)}** days", inline=True)
                
                await ctx.send(embed=embed, file=file)
                return
        except Exception as e:
            print(f"[GRAPH] Image generation failed: {e}")
    
    # Fall back to text graph
    graph = generate_text_graph(data_points)
    
    current = data_points[-1] if data_points else 0
    start = data_points[0] if data_points else 0
    change = current - start
    
    embed = discord.Embed(
        title=f"📈 {member.display_name}'s Aura History",
        description=graph,
        color=0x00FF00 if change >= 0 else 0xFF0000
    )
    embed.add_field(name="📊 Current", value=f"**{current}**", inline=True)
    embed.add_field(name="📈 Change", value=f"**{'+' if change >= 0 else ''}{change}**", inline=True)
    embed.add_field(name="📅 Period", value=f"Last **{len(data_points)}** days", inline=True)
    embed.set_footer(text=f"Showing {display_dates[0]} to {display_dates[-1]}")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="auragraph", description="View aura history graph")
async def auragraph_slash(interaction: discord.Interaction, user: discord.Member = None, days: int = 14):
    member = user or interaction.user
    uid = str(member.id)
    
    days = max(7, min(days, 30))
    
    user_history = history_data.get(uid, {})
    
    if not user_history:
        logs = aura_logs.get(uid, [])
        if logs:
            for log in logs:
                date = datetime.utcfromtimestamp(log["timestamp"]).strftime("%Y-%m-%d")
                user_history[date] = log.get("new_score", 0)
    
    if not user_history:
        await interaction.response.send_message(f"❌ No history data for {member.display_name}!", ephemeral=True)
        return
    
    sorted_dates = sorted(user_history.keys())[-days:]
    data_points = [user_history[d] for d in sorted_dates]
    display_dates = [datetime.strptime(d, "%Y-%m-%d").strftime("%m/%d") for d in sorted_dates]
    
    if PIL_AVAILABLE:
        try:
            buffer = await generate_image_graph(data_points, display_dates, member.display_name)
            if buffer:
                file = discord.File(buffer, filename="auragraph.png")
                
                current = data_points[-1] if data_points else 0
                start = data_points[0] if data_points else 0
                change = current - start
                
                embed = discord.Embed(
                    title=f"📈 {member.display_name}'s Aura History",
                    color=0x00FF00 if change >= 0 else 0xFF0000
                )
                embed.add_field(name="📊 Current", value=f"**{current}**", inline=True)
                embed.add_field(name="📈 Change", value=f"**{'+' if change >= 0 else ''}{change}**", inline=True)
                
                await interaction.response.send_message(embed=embed, file=file)
                return
        except Exception as e:
            print(f"[GRAPH] Image generation failed: {e}")
    
    graph = generate_text_graph(data_points)
    
    current = data_points[-1] if data_points else 0
    start = data_points[0] if data_points else 0
    change = current - start
    
    embed = discord.Embed(
        title=f"📈 {member.display_name}'s Aura History",
        description=graph,
        color=0x00FF00 if change >= 0 else 0xFF0000
    )
    embed.add_field(name="📊 Current", value=f"**{current}**", inline=True)
    embed.add_field(name="📈 Change", value=f"**{'+' if change >= 0 else ''}{change}**", inline=True)
    
    await interaction.response.send_message(embed=embed)

# ============================================================================
# GLOBAL LEADERBOARD
# ============================================================================

def update_global_stats(user_id: str, username: str, aura: int, guild_name: str):
    """Update global stats for a user. REMOVES entry if aura <= 0."""
    
    if aura <= 0:
        # If the local score is 0, we must remove the entry from global_data 
        # to ensure the stale data (e.g., 9999) is deleted from the leaderboard.
        if user_id in global_data:
            del global_data[user_id]
            print(f"[GLOBAL] Removed {username} (Aura 0)")
    else:
        global_data[user_id] = {
            "username": username,
            "aura": aura,
            "guild": guild_name,
            "updated": time.time()
        }
        print(f"[GLOBAL] Updated {username}: {aura} aura")
    save_json_safe(GLOBAL_FILE, global_data)

def get_global_leaderboard(limit: int = 20) -> list:
    """Get global leaderboard sorted by aura."""
    return sorted(
        global_data.items(),
        key=lambda x: x[1].get("aura", 0),
        reverse=True
    )[:limit]

def get_global_rank(user_id: str) -> int:
    """Get user's global rank."""
    sorted_global = sorted(
        global_data.items(),
        key=lambda x: x[1].get("aura", 0),
        reverse=True
    )
    for i, (uid, _) in enumerate(sorted_global):
        if uid == user_id:
            return i + 1
    return None

@tasks.loop(minutes=30)
async def sync_global_stats():
    """Sync local aura data to global stats."""
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            uid = str(member.id)
            aura = aura_data.get(uid, 0)
            
            update_global_stats(uid, member.name, aura, guild.name)

@bot.command()
async def global_leaderboard(ctx, page: int = 1):
    """View the global aura leaderboard across all servers!"""
    
    page = max(1, page)
    per_page = 10
    
    leaderboard = get_global_leaderboard(100)
    
    if not leaderboard:
        await ctx.send("❌ No global data yet!")
        return
    
    total_pages = (len(leaderboard) + per_page - 1) // per_page
    page = min(page, total_pages)
    
    start = (page - 1) * per_page
    end = start + per_page
    page_data = leaderboard[start:end]
    
    embed = discord.Embed(
        title="🌍 Global Aura Leaderboard",
        description=f"Top players across **{len(bot.guilds)}** servers!",
        color=0xFFD700
    )
    
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    
    for i, (uid, data) in enumerate(page_data):
        rank = start + i + 1
        medal = medals[rank - 1] if rank <= 3 else f"**{rank}.**"
        username = data.get("username", "Unknown")
        aura = data.get("aura", 0)
        guild = data.get("guild", "Unknown Server")
        
        lines.append(f"{medal} **{username}** — {aura} aura\n　　└ *{guild}*")
    
    embed.add_field(
        name=f"📊 Rankings ({start + 1}-{start + len(page_data)})",
        value="\n".join(lines) or "No data",
        inline=False
    )
    
    # User's global position
    user_rank = get_global_rank(str(ctx.author.id))
    user_aura = aura_data.get(str(ctx.author.id), 0)
    
    if user_rank:
        embed.add_field(
            name="📍 Your Global Position",
            value=f"**#{user_rank}** with **{user_aura}** aura",
            inline=False
        )
    else:
        embed.add_field(
            name="📍 Your Global Position",
            value="Not ranked yet! Keep chatting!",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{total_pages} • !globalboard <page> to navigate • {len(global_data)} total players")
    
    await ctx.send(embed=embed)
# ============================================================================
# GLOBAL LEADERBOARD
# ============================================================================

def update_global_stats(user_id: str, username: str, aura: int, guild_name: str):
    """Update global stats for a user."""
    global_data[user_id] = {
        "username": username,
        "aura": aura,
        "guild": guild_name,
        "updated": time.time()
    }
    save_json_safe(GLOBAL_FILE, global_data)

def get_global_leaderboard(limit: int = 20) -> list:
    """Get global leaderboard sorted by aura."""
    return sorted(
        global_data.items(),
        key=lambda x: x[1].get("aura", 0),
        reverse=True
    )[:limit]

def get_global_rank(user_id: str) -> int:
    """Get user's global rank."""
    sorted_global = sorted(
        global_data.items(),
        key=lambda x: x[1].get("aura", 0),
        reverse=True
    )
    for i, (uid, _) in enumerate(sorted_global):
        if uid == user_id:
            return i + 1
    return None

@tasks.loop(minutes=30)
async def sync_global_stats():
    """Sync local aura data to global stats."""
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            uid = str(member.id)
            aura = aura_data.get(uid, 0)
            if aura > 0:
                update_global_stats(uid, member.name, aura, guild.name)

@bot.command()
async def globalboard(ctx, page: int = 1):
    """View the global aura leaderboard across all servers!"""
    
    page = max(1, page)
    per_page = 10
    
    leaderboard = get_global_leaderboard(100)
    
    if not leaderboard:
        await ctx.send("❌ No global data yet!")
        return
    
    total_pages = (len(leaderboard) + per_page - 1) // per_page
    page = min(page, total_pages)
    
    start = (page - 1) * per_page
    end = start + per_page
    page_data = leaderboard[start:end]
    
    embed = discord.Embed(
        title="🌍 Global Aura Leaderboard",
        description=f"Top players across **{len(bot.guilds)}** servers!",
        color=0xFFD700
    )
    
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    
    for i, (uid, data) in enumerate(page_data):
        rank = start + i + 1
        medal = medals[rank - 1] if rank <= 3 else f"**{rank}.**"
        username = data.get("username", "Unknown")
        aura = data.get("aura", 0)
        guild = data.get("guild", "Unknown Server")
        
        lines.append(f"{medal} **{username}** — {aura} aura\n　　└ *{guild}*")
    
    embed.add_field(
        name=f"📊 Rankings ({start + 1}-{start + len(page_data)})",
        value="\n".join(lines) or "No data",
        inline=False
    )
    
    # User's global position
    user_rank = get_global_rank(str(ctx.author.id))
    user_aura = aura_data.get(str(ctx.author.id), 0)
    
    if user_rank:
        embed.add_field(
            name="📍 Your Global Position",
            value=f"**#{user_rank}** with **{user_aura}** aura",
            inline=False
        )
    else:
        embed.add_field(
            name="📍 Your Global Position",
            value="Not ranked yet! Keep chatting!",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{total_pages} • !globalboard <page> to navigate • {len(global_data)} total players")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="globalboard", description="View the global aura leaderboard")
async def globalboard_slash(interaction: discord.Interaction, page: int = 1):
    page = max(1, page)
    per_page = 10
    
    leaderboard = get_global_leaderboard(100)
    
    if not leaderboard:
        await interaction.response.send_message("❌ No global data yet!", ephemeral=True)
        return
    
    total_pages = (len(leaderboard) + per_page - 1) // per_page
    page = min(page, total_pages)
    
    start = (page - 1) * per_page
    end = start + per_page
    page_data = leaderboard[start:end]
    
    embed = discord.Embed(
        title="🌍 Global Aura Leaderboard",
        description=f"Top players across **{len(bot.guilds)}** servers!",
        color=0xFFD700
    )
    
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    
    for i, (uid, data) in enumerate(page_data):
        rank = start + i + 1
        medal = medals[rank - 1] if rank <= 3 else f"**{rank}.**"
        username = data.get("username", "Unknown")
        aura = data.get("aura", 0)
        
        lines.append(f"{medal} **{username}** — {aura} aura")
    
    embed.add_field(
        name=f"📊 Rankings",
        value="\n".join(lines) or "No data",
        inline=False
    )
    
    user_rank = get_global_rank(str(interaction.user.id))
    user_aura = aura_data.get(str(interaction.user.id), 0)
    
    if user_rank:
        embed.add_field(
            name="📍 Your Position",
            value=f"**#{user_rank}** with **{user_aura}** aura",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{total_pages}")
    
    await interaction.response.send_message(embed=embed)

# ============================================================================
# SERVER VS SERVER
# ============================================================================

def get_server_stats(guild: discord.Guild) -> dict:
    """Calculate aggregate stats for a server."""
    guild_members = {str(m.id) for m in guild.members if not m.bot}
    server_aura = {uid: aura for uid, aura in aura_data.items() if uid in guild_members}
    
    if not server_aura:
        return {
            "total_aura": 0,
            "avg_aura": 0,
            "user_count": 0,
            "top_user": None,
            "top_aura": 0
        }
    
    total = sum(server_aura.values())
    avg = total / len(server_aura)
    sorted_users = sorted(server_aura.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "total_aura": total,
        "avg_aura": avg,
        "user_count": len(server_aura),
        "top_user": sorted_users[0][0] if sorted_users else None,
        "top_aura": sorted_users[0][1] if sorted_users else 0
    }

@bot.command()
async def servercompare(ctx):
    """Compare this server's aura with global averages!"""
    
    guild_stats = get_server_stats(ctx.guild)
    
    # Calculate global averages
    all_servers = []
    for guild in bot.guilds:
        stats = get_server_stats(guild)
        if stats["user_count"] > 0:
            all_servers.append({
                "name": guild.name,
                "id": guild.id,
                "total": stats["total_aura"],
                "avg": stats["avg_aura"],
                "users": stats["user_count"]
            })
    
    # Sort by total aura
    all_servers.sort(key=lambda x: x["total"], reverse=True)
    
    # Find this server's rank
    server_rank = next(
        (i + 1 for i, s in enumerate(all_servers) if s["id"] == ctx.guild.id),
        None
    )
    
    # Calculate global averages
    if all_servers:
        global_avg_total = sum(s["total"] for s in all_servers) / len(all_servers)
        global_avg_per_user = sum(s["avg"] for s in all_servers) / len(all_servers)
    else:
        global_avg_total = 0
        global_avg_per_user = 0
    
    embed = discord.Embed(
        title=f"🏟️ {ctx.guild.name} vs The World",
        color=0x5865F2
    )
    
    # This server's stats
    embed.add_field(
        name=f"📊 {ctx.guild.name}",
        value=(
            f"**Total Aura:** {guild_stats['total_aura']:,}\n"
            f"**Average:** {guild_stats['avg_aura']:.0f}/user\n"
            f"**Active Users:** {guild_stats['user_count']}\n"
            f"**Global Rank:** #{server_rank or '?'}/{len(all_servers)}"
        ),
        inline=True
    )
    
    # Global averages
    embed.add_field(
        name="🌍 Global Average",
        value=(
            f"**Total Aura:** {global_avg_total:,.0f}\n"
            f"**Average:** {global_avg_per_user:.0f}/user\n"
            f"**Servers:** {len(all_servers)}"
        ),
        inline=True
    )
    
    # Comparison
    diff_total = guild_stats["total_aura"] - global_avg_total
    diff_avg = guild_stats["avg_aura"] - global_avg_per_user
    
    comparison = []
    if diff_total > 0:
        comparison.append(f"✅ **{diff_total:,.0f}** more total aura than average")
    else:
        comparison.append(f"❌ **{abs(diff_total):,.0f}** less total aura than average")
    
    if diff_avg > 0:
        comparison.append(f"✅ **{diff_avg:.0f}** higher average than global")
    else:
        comparison.append(f"❌ **{abs(diff_avg):.0f}** lower average than global")
    
    embed.add_field(
        name="📈 Comparison",
        value="\n".join(comparison),
        inline=False
    )
    
    # Top 5 servers
    if len(all_servers) > 1:
        top5_lines = []
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, server in enumerate(all_servers[:5]):
            medal = medals[i]
            is_this = " ⬅️" if server["id"] == ctx.guild.id else ""
            top5_lines.append(f"{medal} **{server['name']}** — {server['total']:,} aura{is_this}")
        
        embed.add_field(
            name="🏆 Top 5 Servers",
            value="\n".join(top5_lines),
            inline=False
        )
    
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_footer(text=f"Comparing {len(all_servers)} servers with Auraxis")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="servercompare", description="Compare this server with others")
async def servercompare_slash(interaction: discord.Interaction):
    guild_stats = get_server_stats(interaction.guild)
    
    all_servers = []
    for guild in bot.guilds:
        stats = get_server_stats(guild)
        if stats["user_count"] > 0:
            all_servers.append({
                "name": guild.name,
                "id": guild.id,
                "total": stats["total_aura"],
                "avg": stats["avg_aura"],
                "users": stats["user_count"]
            })
    
    all_servers.sort(key=lambda x: x["total"], reverse=True)
    
    server_rank = next(
        (i + 1 for i, s in enumerate(all_servers) if s["id"] == interaction.guild.id),
        None
    )
    
    if all_servers:
        global_avg_total = sum(s["total"] for s in all_servers) / len(all_servers)
    else:
        global_avg_total = 0
    
    embed = discord.Embed(
        title=f"🏟️ {interaction.guild.name} vs The World",
        color=0x5865F2
    )
    
    embed.add_field(
        name="📊 This Server",
        value=(
            f"**Total:** {guild_stats['total_aura']:,}\n"
            f"**Rank:** #{server_rank or '?'}/{len(all_servers)}"
        ),
        inline=True
    )
    
    embed.add_field(
        name="🌍 Global Average",
        value=f"**Total:** {global_avg_total:,.0f}",
        inline=True
    )
    
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    await interaction.response.send_message(embed=embed)


#===========Events and Message Handling============
@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game("Measuring Aura ⚡")
    )
    
    # ✅ Force immediate global sync on startup
    print("[STARTUP] Syncing global stats...")
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            uid = str(member.id)
            aura = aura_data.get(uid, 0)
            if aura > 0:
                update_global_stats(uid, member.name, aura, guild.name)
    print(f"[STARTUP] Synced {len(global_data)} users to global leaderboard")
    # Start all tasks
    if not daily_decay_task.is_running():
        daily_decay_task.start()
    if not aura_role_sync_task.is_running():
        aura_role_sync_task.start()
    if not tournament_check_task.is_running():
        tournament_check_task.start()
    if not daily_snapshot_task.is_running():
        daily_snapshot_task.start()
    if not sync_global_stats.is_running():
        sync_global_stats.start()
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    
    print(f"✅ Logged in as {bot.user}")
    print(f"✅ Serving {len(bot.guilds)} servers")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # --- BOT MENTION HANDLER ---
    if (
        message.content.strip() == f"<@{bot.user.id}>"
        or message.content.strip() == f"<@!{bot.user.id}>"
    ):
        embed = discord.Embed(
            title="👋 Hey there!",
            description=(
                f"Hey {message.author.mention}!\n\n"
                "👉 Type `!commandlist` to see the command list\n"
                "👉 Type `!aurainfo` to learn how **Auraxis** works"
            ),
            color=0x5865F2
        )
        embed.set_footer(text="Auraxis • Impact matters more than volume ⚡")
        await message.channel.send(embed=embed)
        return

# --- END BOT MENTION HANDLER ---
    await bot.process_commands(message)

    if not message.guild:
        return

    if not is_channel_enabled(message.guild.id, message.channel.id):
        content = message.content.strip().lower()
        if content.startswith(PREFIX):
            cmd = content[len(PREFIX):].split()[0]
            if (
                cmd in ADMIN_COMMANDS
                and message.author.guild_permissions.manage_guild
            ):
                return
            if cmd in SAFE_COMMANDS:
                return
            return
        return

    content = message.content.strip()
    content_norm = normalize_message(content)

    # ✅ EARLY EXIT: Friendly Hinglish / casual positive messages
    if is_casual_hinglish_banter(content_norm):
        rule_score = calculate_ai_aura_rules(content)
        local_score = calculate_ai_aura_local(content)
        semantic_score = calculate_ai_aura_semantic(content)

        aura_gain = int(round(
            rule_score * 1.0 +
            max(0, local_score) * 1.2 +
            semantic_score * 0.5
        ))

        aura_gain = max(2, min(aura_gain, 4))  # force positive band

        user_id = str(message.author.id)
        current = aura_data.get(user_id, 0)
        new_score = max(0, current + aura_gain)

        aura_data[user_id] = new_score
        if aura_gain > 0 and message.guild:
            record_tournament_aura(str(message.guild.id), user_id, aura_gain)

        # ✅ ALWAYS update global stats when aura changes
        update_global_stats(
            user_id,
            message.author.name,
            new_score,
            message.guild.name if message.guild else "DM"
        )

        save_data(aura_data)

        log_aura_change(user_id, aura_gain, new_score, "friendly_banter")

        return  # 🚨 IMPORTANT: skip ALL toxicity logic

    if content_norm.startswith(PREFIX):
        return
    if len(content_norm.split()) < 4:
        return

    user_id = str(message.author.id)
    now = time.time()

    # NEW: Check for hate speech first (immediate severe penalty)
    is_hate, hate_reason = contains_hate_speech_patterns(content)
    if is_hate:
        current = aura_data.get(user_id, 0)
        penalty = -5  # Severe penalty
        new_score = max(0, current + penalty)
        aura_data[user_id] = new_score
        save_data(aura_data)
        
        log_aura_change(user_id, penalty, new_score, f"hate_speech_{hate_reason}")
        
        await message.channel.send(
            f"🚨 **HATE SPEECH DETECTED** 🚨\n"
            f"{message.author.mention} this type of content is **NOT TOLERATED**.\n"
            f"**Aura change:** {penalty} (Category: {hate_reason})\n"
            f"⚠️ Repeated violations may result in server action.",
            delete_after=15
        )
        
        # Optionally delete the message if bot has permissions
        try:
            if message.guild.me.guild_permissions.manage_messages:
                await message.delete()
        except Exception:
            pass
        
        return

    if is_duplicate_message(user_id, content_norm):
        return

    if user_id in recent_messages:
        last_msg, last_time = recent_messages[user_id]
        if now - last_time < DUPLICATE_WINDOW:
            if difflib.SequenceMatcher(None, content_norm, last_msg).ratio() >= SIMILARITY_THRESHOLD:
                return

    is_hindi = is_hindi_or_hinglish(content_norm)

    if is_obviously_safe(content_norm):
        toxic_loss = False
        toxic_reason = None
        penalty_amount = 0
    else:
        ai_score = await calculate_ai_aura_devstral(content)
        allowed, penalty_amount, toxic_expls = evaluate_toxic_decision(content, ai_score, message)
        toxic_loss = allowed
        toxic_reason = toxic_expls
    
    rule_score = calculate_ai_aura_rules(content)
    local_score = calculate_ai_aura_local(content)
    semantic_score = calculate_ai_aura_semantic(content)

    if is_obviously_safe(content_norm):
        aura_gain_raw = (
            rule_score * 1.0
            + max(0, local_score) * 1.3
            + semantic_score * 0.6
        )
        aura_gain = int(round(aura_gain_raw))
        penalty_amount = 0
        toxic_loss = False
    elif toxic_loss:
        aura_gain = penalty_amount
    else:
        aura_gain_raw = (
            rule_score * 0.8
            + max(0, local_score) * 1.0
            + semantic_score * 0.3
        )
        aura_gain = int(round(aura_gain_raw))
        if aura_gain < 0:
            aura_gain = 0

    aura_gain = max(-5, min(aura_gain, 6))

    # FIXED: Separate cooldown checks
    if aura_gain > 0:
        # Positive gain - check positive cooldown
        if now - recent_positive_aura_time.get(user_id, 0) < POSITIVE_AURA_COOLDOWN:
            return
        recent_positive_aura_time[user_id] = now
    elif aura_gain < 0:
        # Negative (toxic) - check negative cooldown
        if now - recent_negative_aura_time.get(user_id, 0) < NEGATIVE_AURA_COOLDOWN:
            return
        recent_negative_aura_time[user_id] = now
    else:
        # Zero gain - skip
        return

    current = aura_data.get(user_id, 0)
    new_score = max(0, current + aura_gain)

    aura_data[user_id] = new_score
    save_data(aura_data)

    recent_messages[user_id] = (content_norm, now)

    reason = "abuse" if toxic_loss else "normal"
    log_aura_change(user_id, aura_gain, new_score, reason)

    # Notifications
    if aura_gain <= -2:
        if toxic_loss and toxic_reason:
            sem = toxic_reason.get("semantic")
            targeted = toxic_reason.get("targeted_attack")
            ai = toxic_reason.get("ai")
            expl = f"⚠️ Message flagged as **targeted toxicity**\nReason: "
            parts = []
            if sem == "toxic":
                parts.append("Semantic intent")
            if targeted:
                parts.append("targeted at person")
            if isinstance(ai, (int, float)) and ai <= -2:
                parts.append("AI (culture aware) flagged")
            expl += ", ".join(parts)
        else:
            expl = "⚠️ Message flagged as toxic."
        await message.channel.send(
            f"{expl}\n**Aura change:** {aura_gain}",
            delete_after=10
        )

    print(
        f"[AURA] {message.author} "
        f"{'+' if aura_gain > 0 else ''}{aura_gain} → {new_score}"
    )

# ============================================================================
# COMMAND IMPLEMENTATIONS
# ============================================================================

@bot.command()
async def aura(ctx):
    """Check your aura score"""
    score = aura_data.get(str(ctx.author.id), 0)
    rank = get_rank_name(score)
    embed = discord.Embed(
        title=f"✨ {ctx.author.display_name}'s Aura",
        color=0x5865F2
    )
    embed.add_field(name="Score", value=f"**{score}**", inline=True)
    embed.add_field(name="Rank", value=f"**{rank}**", inline=True)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.tree.command(name="aura", description="Check your aura score")
async def aura_slash(interaction: discord.Interaction):
    score = aura_data.get(str(interaction.user.id), 0)
    rank = get_rank_name(score)
    embed = discord.Embed(
        title=f"✨ {interaction.user.display_name}'s Aura",
        color=0x5865F2
    )
    embed.add_field(name="Score", value=f"**{score}**", inline=True)
    embed.add_field(name="Rank", value=f"**{rank}**", inline=True)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.command()
async def auraof(ctx, member: discord.Member):
    """Check someone else's aura score"""
    score = aura_data.get(str(member.id), 0)
    rank = get_rank_name(score)
    embed = discord.Embed(
        title=f"✨ {member.display_name}'s Aura",
        color=0x5865F2
    )
    embed.add_field(name="Score", value=f"**{score}**", inline=True)
    embed.add_field(name="Rank", value=f"**{rank}**", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.tree.command(name="auraof", description="Check someone's aura score")
async def auraof_slash(interaction: discord.Interaction, user: discord.Member):
    score = aura_data.get(str(user.id), 0)
    rank = get_rank_name(score)
    embed = discord.Embed(
        title=f"✨ {user.display_name}'s Aura",
        color=0x5865F2
    )
    embed.add_field(name="Score", value=f"**{score}**", inline=True)
    embed.add_field(name="Rank", value=f"**{rank}**", inline=True)
    embed.set_thumbnail(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.command()
async def aurarank(ctx):
    """Check your aura rank"""
    score = aura_data.get(str(ctx.author.id), 0)
    rank = get_rank_name(score)
    
    # Find position in leaderboard
    sorted_list = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)
    position = next((i+1 for i, (uid, _) in enumerate(sorted_list) if uid == str(ctx.author.id)), None)
    
    embed = discord.Embed(
        title=f"🏆 {ctx.author.display_name}'s Rank",
        color=0x5865F2
    )
    embed.add_field(name="Rank", value=f"**{rank}**", inline=False)
    embed.add_field(name="Score", value=f"**{score}**", inline=True)
    if position:
        embed.add_field(name="Leaderboard Position", value=f"**#{position}**", inline=True)
    
    # Show next rank threshold
    for threshold, name in RANK_ROLES:
        if score < threshold:
            needed = threshold - score
            embed.add_field(
                name="Next Rank",
                value=f"**{name}** ({needed} more needed)",
                inline=False
            )
            break
    
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.tree.command(name="aurarank", description="Check your aura rank")
async def aurarank_slash(interaction: discord.Interaction):
    score = aura_data.get(str(interaction.user.id), 0)
    rank = get_rank_name(score)
    
    # Find position in leaderboard
    sorted_list = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)
    position = next((i+1 for i, (uid, _) in enumerate(sorted_list) if uid == str(interaction.user.id)), None)
    
    embed = discord.Embed(
        title=f"🏆 {interaction.user.display_name}'s Rank",
        color=0x5865F2
    )
    embed.add_field(name="Rank", value=f"**{rank}**", inline=False)
    embed.add_field(name="Score", value=f"**{score}**", inline=True)
    if position:
        embed.add_field(name="Leaderboard Position", value=f"**#{position}**", inline=True)
    
    # Show next rank threshold
    for threshold, name in RANK_ROLES:
        if score < threshold:
            needed = threshold - score
            embed.add_field(
                name="Next Rank",
                value=f"**{name}** ({needed} more needed)",
                inline=False
            )
            break
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

PAGE_SIZE = 10

def get_sorted_aura():
    return sorted(aura_data.items(), key=lambda x: x[1], reverse=True)

def make_leaderboard_embed(page: int, total_pages: int, entries, offset: int):
    desc_lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, score) in enumerate(entries, start=1):
        pos = offset + i
        medal = medals[pos-1] if pos <= 3 else f"**{pos}.**"
        desc_lines.append(f"{medal} <@{uid}> — **{score}** aura")
    
    embed = discord.Embed(
        title=f"🏆 Aura Leaderboard",
        description="\n".join(desc_lines) or "No aura data.",
        color=0xFFD700,
    )
    embed.set_footer(text=f"Page {page+1}/{total_pages} • Use !auraboard <page> to navigate")
    return embed

@bot.command()
async def auraboard(ctx, page: int = 1):
    """View the aura leaderboard"""
    if not aura_data:
        await ctx.send("No aura data yet.")
        return

    page = max(page, 1) - 1
    sorted_list = get_sorted_aura()
    total_pages = max(1, (len(sorted_list) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages - 1)

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    entries = sorted_list[start:end]
    embed = make_leaderboard_embed(page, total_pages, entries, start)
    await ctx.send(embed=embed)

@bot.tree.command(name="auraboard", description="View the aura leaderboard")
async def auraboard_slash(interaction: discord.Interaction, page: int = 1):
    if not aura_data:
        await interaction.response.send_message("No aura data yet.", ephemeral=True)
        return

    page = max(page, 1) - 1
    sorted_list = get_sorted_aura()
    total_pages = max(1, (len(sorted_list) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages - 1)

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    entries = sorted_list[start:end]
    embed = make_leaderboard_embed(page, total_pages, entries, start)
    await interaction.response.send_message(embed=embed)

@bot.command()
async def commandlist(ctx):
    """Show all available commands."""
    embed = discord.Embed(
        title="✨ Auraxis Bot Commands",
        description="Your ultimate aura tracking system with battles, shop, tournaments & more!",
        color=0x5865F2
    )
    
    embed.add_field(
        name="📊 Aura & Stats",
        value=(
            "`!aura [@user]` - Check aura score\n"
            "`!leaderboard [page]` - Server leaderboard\n"
            "`!aurastats [@user]` - Detailed statistics\n"
            "`!auracard [@user]` - Profile card with cosmetics\n"
            "`!auragraph [@user] [days]` - Aura history graph\n"
            "`!aurapredict [@user] [days]` - Predict future aura\n"
            "`!aurainfo` - How the aura system works"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Battles",
        value=(
            "`!aurabattle @user` - Challenge someone to battle\n"
            "`!battlestats [@user]` - View battle win/loss record"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📅 Daily Rewards & Streaks",
        value=(
            "`!daily` - Claim daily aura reward\n"
            "`!streak [@user]` - Check daily streak info"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛒 Shop & Cosmetics",
        value=(
            "`!shop` - Browse titles, badges, colors & boosts\n"
            "`!buy <item_id>` - Purchase an item\n"
            "`!equip <item_id>` - Equip a cosmetic item\n"
            "`!inventory [@user]` - View owned items & active boosts"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏆 Competitions",
        value=(
            "`!tournament` - View weekly tournament standings\n"
            "`!globalboard [page]` - Global leaderboard (all servers)\n"
            "`!servercompare` - Compare your server vs others"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin Commands",
        value=(
            "`!setchannel` - Enable aura tracking in channel\n"
            "`!disablechannel` - Disable aura tracking\n"
            "`!enablechannel` - Re-enable aura tracking\n"
            "`!setaura @user <amount>` - Set user's aura\n"
            "`!resetaura @user` - Reset user's aura to 0\n"
            "`!serveraura` - View server-wide analytics"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔧 Utility",
        value="`!ping` - Check bot latency",
        inline=False
    )
    
    embed.set_footer(text="💡 All commands also work as /slash commands! • [] = optional, <> = required")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.tree.command(name="help", description="Show all available commands")
async def help_slash(interaction: discord.Interaction):
    """Slash command version of help."""
    embed = discord.Embed(
        title="✨ Auraxis Bot Commands",
        description="Your ultimate aura tracking system!",
        color=0x5865F2
    )
    
    embed.add_field(
        name="📊 Aura & Stats",
        value="`/aura` `/leaderboard` `/aurastats` `/auracard` `/auragraph` `/aurapredict` `/aurainfo`",
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Battles",
        value="`/aurabattle` `/battlestats`",
        inline=False
    )
    
    embed.add_field(
        name="📅 Daily & Streaks",
        value="`/daily` `/streak`",
        inline=False
    )
    
    embed.add_field(
        name="🛒 Shop & Cosmetics",
        value="`/shop` `/buy` `/equip` `/inventory`",
        inline=False
    )
    
    embed.add_field(
        name="🏆 Competitions",
        value="`/tournament` `/globalboard` `/servercompare`",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin",
        value="`/setaura` `/resetaura` `/serveraura`",
        inline=False
    )
    
    embed.set_footer(text="💡 Use !help for detailed command descriptions")
    embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

@bot.command()
async def aurainfo(ctx):
    """Learn how the aura system works."""
    embed = discord.Embed(
        title="✨ How Auraxis Works",
        description="Auraxis is a comprehensive aura tracking system that measures the vibe, energy, and positivity of your messages!",
        color=0x5865F2
    )
    
    embed.add_field(
        name="📈 Ways to Gain Aura",
        value=(
            "• **Positive Messages** — Be helpful, kind, supportive (+1 to +5)\n"
            "• **Daily Rewards** — Claim `!daily` every day (+10 to +60)\n"
            "• **Streak Bonuses** — Consecutive daily claims = bigger rewards\n"
            "• **Win Battles** — Challenge others with `!aurabattle` (+5 to +100)\n"
            "• **Quality Content** — Thoughtful, engaging messages\n"
            "• **2x Boost** — Buy from shop for double gains!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📉 Ways to Lose Aura",
        value=(
            "• **Toxic Messages** — Insults, negativity (-1 to -3)\n"
            "• **Targeted Attacks** — Direct harassment (-3 to -5)\n"
            "• **Hate Speech** — Severe penalty + message deleted (-5)\n"
            "• **Lose Battles** — Lost aura goes to winner (-5 to -100)\n"
            "• **Weekly Decay** — 2% decay if inactive (100+ aura)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏆 Rank Tiers",
        value=(
            "```"
            "🌌 Cosmic Entity   10,000+\n"
            "👑 Aura God         7,500+\n"
            "⚡ Transcendent     5,000+\n"
            "🔮 Mythical         3,500+\n"
            "💎 Diamond          2,500+\n"
            "🏆 Platinum         1,500+\n"
            "🥇 Gold             1,000+\n"
            "🥈 Silver             500+\n"
            "🥉 Bronze             250+\n"
            "✨ Rising Star        100+\n"
            "🌱 Seedling            50+\n"
            "👤 Unranked             0+\n"
            "```"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Battle System",
        value=(
            "• Challenge anyone with `!aurabattle @user`\n"
            "• Stake is 5% of lower player's aura (5-100 range)\n"
            "• Higher aura = slightly better win chance (30%-70%)\n"
            "• Random events: Critical Hits, Dodges, Aura Surges!\n"
            "• 1 hour cooldown between battles\n"
            "• Buy 🛡️ Shield from shop for protection!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📅 Daily Streak System",
        value=(
            "• Base reward: **10 aura**\n"
            "• Streak bonus: **+5 per consecutive day** (max +50)\n"
            "• Day 1: 10 → Day 7: 45 → Day 10+: 60 aura!\n"
            "• Miss a day = streak resets to 0\n"
            "• 2x Boost doubles daily rewards too!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛒 Shop Items",
        value=(
            "• **Titles** — Display next to your name (500-2000 aura)\n"
            "• **Badges** — Show on your profile (300-1500 aura)\n"
            "• **Colors** — Customize your aura card (600 aura)\n"
            "• **2x Boost** — Double aura gains for 24h (1000 aura)\n"
            "• **Shield** — Block battle losses for 24h (500 aura)"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🏆 Weekly Tournaments",
        value=(
            "• Compete for most aura **gained** each week\n"
            "• 🥇 1st: 500 aura + Champion title\n"
            "• 🥈 2nd: 300 aura\n"
            "• 🥉 3rd: 150 aura\n"
            "• Check standings with `!tournament`"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🌍 Global Features",
        value=(
            "• `!globalboard` — Compete across ALL servers\n"
            "• `!servercompare` — See how your server ranks\n"
            "• `!auracard` — Generate shareable profile card"
        ),
        inline=False
    )
    
    embed.set_footer(text="💡 Type !help for full command list • Stay positive, gain aura! ✨")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.tree.command(name="aurainfo", description="Learn how the aura system works")
async def aurainfo_slash(interaction: discord.Interaction):
    """Slash command version of aurainfo."""
    embed = discord.Embed(
        title="✨ How Auraxis Works",
        description="A comprehensive aura tracking system!",
        color=0x5865F2
    )
    
    embed.add_field(
        name="📈 Gain Aura",
        value=(
            "• Positive messages (+1 to +5)\n"
            "• Daily rewards (`/daily`)\n"
            "• Win battles (`/aurabattle`)\n"
            "• Streak bonuses"
        ),
        inline=True
    )
    
    embed.add_field(
        name="📉 Lose Aura",
        value=(
            "• Toxic messages (-1 to -3)\n"
            "• Hate speech (-5)\n"
            "• Lose battles\n"
            "• Weekly decay (2%)"
        ),
        inline=True
    )
    
    embed.add_field(
        name="🏆 Top Ranks",
        value=(
            "🌌 Cosmic Entity: 10,000+\n"
            "👑 Aura God: 7,500+\n"
            "⚡ Transcendent: 5,000+\n"
            "🔮 Mythical: 3,500+"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Battles",
        value="Challenge others, stake aura, random events! 1h cooldown.",
        inline=True
    )
    
    embed.add_field(
        name="📅 Dailies",
        value="10 base + 5 per streak day. Max 60/day!",
        inline=True
    )
    
    embed.add_field(
        name="🛒 Shop",
        value="Titles, badges, colors, 2x boost, shields!",
        inline=True
    )
    
    embed.add_field(
        name="🏆 Tournaments",
        value="Weekly competition! 1st: 500 aura + title, 2nd: 300, 3rd: 150",
        inline=False
    )
    
    embed.set_footer(text="Use /help for full command list!")
    embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)
@bot.command()
@commands.has_permissions(manage_guild=True)
async def aurach_enable(ctx, channel: discord.TextChannel = None):
    """Enable aura tracking in a channel"""
    channel = channel or ctx.channel
    gid = str(ctx.guild.id)
    cid = str(channel.id)

    guild_cfg = config_data.setdefault(gid, {})
    disabled = set(guild_cfg.get("disabled_channels", []))
    disabled.discard(cid)
    guild_cfg["disabled_channels"] = list(disabled)

    save_json(CONFIG_FILE, config_data)
    
    embed = discord.Embed(
        title="✅ Aura Enabled",
        description=f"Aura tracking is now enabled in {channel.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.tree.command(name="aurach_enable", description="Enable aura tracking in a channel")
@app_commands.checks.has_permissions(manage_guild=True)
async def aurach_enable_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    channel = channel or interaction.channel
    gid = str(interaction.guild.id)
    cid = str(channel.id)
    guild_cfg = config_data.setdefault(gid, {})
    disabled = set(guild_cfg.get("disabled_channels", []))

    disabled.discard(cid)
    guild_cfg["disabled_channels"] = list(disabled)

    save_json(CONFIG_FILE, config_data)
    
    embed = discord.Embed(
        title="✅ Aura Enabled",
        description=f"Aura tracking is now enabled in {channel.mention}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def aurach_disable(ctx, channel: discord.TextChannel = None):
    """Disable aura tracking in a channel"""
    channel = channel or ctx.channel
    gid = str(ctx.guild.id)
    cid = str(channel.id)

    guild_cfg = config_data.setdefault(gid, {})
    disabled = set(guild_cfg.get("disabled_channels", []))

    disabled.add(cid)
    guild_cfg["disabled_channels"] = list(disabled)

    save_json(CONFIG_FILE, config_data)
    
    embed = discord.Embed(
        title="❌ Aura Disabled",
        description=f"Aura tracking is now disabled in {channel.mention}",
        color=0xff0000
    )
    await ctx.send(embed=embed)

@bot.tree.command(name="aurach_disable", description="Disable aura tracking in a channel")
@app_commands.checks.has_permissions(manage_guild=True)
async def aurach_disable_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    channel = channel or interaction.channel
    gid = str(interaction.guild.id)
    cid = str(channel.id)

    guild_cfg = config_data.setdefault(gid, {})
    disabled = set(guild_cfg.get("disabled_channels", []))

    disabled.add(cid)
    guild_cfg["disabled_channels"] = list(disabled)

    save_json(CONFIG_FILE, config_data)
    
    embed = discord.Embed(
        title="❌ Aura Disabled",
        description=f"Aura tracking is now disabled in {channel.mention}",
        color=0xff0000
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command()
async def auralogs(ctx, member: discord.Member = None):
    """View recent aura changes for a user"""
    member = member or ctx.author
    uid = str(member.id)
    logs = aura_logs.get(uid, [])
    if not logs:
        await ctx.send(f"No aura logs for {member.mention}.")
        return

    last_logs = logs[-10:]
    lines = []
    for entry in reversed(last_logs):
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry["timestamp"]))
        chg = entry["change"]
        score = entry["new_score"]
        rsn = entry.get("reason", "unknown")
        prefix = "+" if chg > 0 else ""
        
        # Add emoji based on reason
        emoji = "📈" if chg > 0 else "📉"
        if "hate" in rsn:
            emoji = "🚨"
        elif "abuse" in rsn:
            emoji = "⚠️"
        
        lines.append(f"{emoji} `{ts}` {prefix}{chg} → **{score}** ({rsn})")

    embed = discord.Embed(
        title=f"📜 Aura logs for {member.display_name}",
        description="\n".join(lines),
        color=0x5865F2,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Showing last 10 changes")
    await ctx.send(embed=embed)

@bot.tree.command(name="auralogs", description="View recent aura changes for a user")
async def auralogs_slash(interaction: discord.Interaction, user: discord.Member = None):
    member = user or interaction.user
    uid = str(member.id)
    logs = aura_logs.get(uid, [])
    if not logs:
        await interaction.response.send_message(f"No aura logs for {member.mention}.", ephemeral=True)
        return

    last_logs = logs[-10:]
    lines = []
    for entry in reversed(last_logs):
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry["timestamp"]))
        chg = entry["change"]
        score = entry["new_score"]
        rsn = entry.get("reason", "unknown")
        prefix = "+" if chg > 0 else ""
        
        # Add emoji based on reason
        emoji = "📈" if chg > 0 else "📉"
        if "hate" in rsn:
            emoji = "🚨"
        elif "abuse" in rsn:
            emoji = "⚠️"
        
        lines.append(f"{emoji} `{ts}` {prefix}{chg} → **{score}** ({rsn})")

    embed = discord.Embed(
        title=f"📜 Aura logs for {member.display_name}",
        description="\n".join(lines),
        color=0x5865F2,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Showing last 10 changes")
    await interaction.response.send_message(embed=embed)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def debug(ctx):
    """View bot statistics and debug info"""
    embed = discord.Embed(title="🔧 Bot Debug Info", color=0x5865F2)
    total_aura = sum(aura_data.values()) if aura_data else 0
    embed.add_field(
        name="📊 Aura Data",
        value=f"{len(aura_data)} users | {total_aura:,} total",
        inline=True
    )
    guild_id = str(ctx.guild.id)
    guild_cfg = config_data.get(guild_id, {})
    disabled_chs = len(guild_cfg.get("disabled_channels", []))
    status = "✅ All channels" if not disabled_chs else f"❌ {disabled_chs} channels disabled"
    embed.add_field(name="⚙️ Channel Config", value=status, inline=True)
    decay_status = "✅ Running" if daily_decay_task.is_running() else "❌ Stopped"
    role_status = "✅ Running" if aura_role_sync_task.is_running() else "❌ Stopped"
    embed.add_field(name="🔄 Tasks", value=f"Decay: {decay_status}\nRoles: {role_status}", inline=True)
    if aura_data:
        top3 = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)[:3]
        top_list = "\n".join([f"<@{uid}> (**{score}**)" for uid, score in top3])
        embed.add_field(name="🏆 Top 3", value=top_list or "No data", inline=False)
    else:
        embed.add_field(name="🏆 Top 3", value="No aura data yet", inline=False)
    embed.add_field(
        name="💾 Memory",
        value=f"{len(aura_logs)} logs | {len(config_data)} guilds",
        inline=True
    )
    embed.add_field(
        name="⏰ Status",
        value=f"{len(bot.guilds)} servers | {len(bot.commands)} cmds",
        inline=True
    )
    embed.set_footer(text=f"Server: {ctx.guild.name} | Latency: {round(bot.latency * 1000)}ms")
    await ctx.send(embed=embed)

@bot.tree.command(name="debug", description="View bot statistics and debug info")
@app_commands.checks.has_permissions(manage_guild=True)
async def debug_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="🔧 Bot Debug Info", color=0x5865F2)
    total_aura = sum(aura_data.values()) if aura_data else 0
    embed.add_field(
        name="📊 Aura Data",
        value=f"{len(aura_data)} users | {total_aura:,} total",
        inline=True
    )
    guild_id = str(interaction.guild.id)
    guild_cfg = config_data.get(guild_id, {})
    disabled_chs = len(guild_cfg.get("disabled_channels", []))
    status = "✅ All channels" if not disabled_chs else f"❌ {disabled_chs} channels disabled"
    embed.add_field(name="⚙️ Channel Config", value=status, inline=True)
    decay_status = "✅ Running" if daily_decay_task.is_running() else "❌ Stopped"
    role_status = "✅ Running" if aura_role_sync_task.is_running() else "❌ Stopped"
    embed.add_field(name="🔄 Tasks", value=f"Decay: {decay_status}\nRoles: {role_status}", inline=True)
    if aura_data:
        top3 = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)[:3]
        top_list = "\n".join([f"<@{uid}> (**{score}**)" for uid, score in top3])
        embed.add_field(name="🏆 Top 3", value=top_list or "No data", inline=False)
    else:
        embed.add_field(name="🏆 Top 3", value="No aura data yet", inline=False)
    embed.add_field(
        name="💾 Memory",
        value=f"{len(aura_logs)} logs | {len(config_data)} guilds",
        inline=True
    )
    embed.add_field(
        name="⏰ Status",
        value=f"{len(bot.guilds)} servers | {len(bot.commands)} cmds",
        inline=True
    )
    embed.set_footer(text=f"Server: {interaction.guild.name} | Latency: {round(bot.latency * 1000)}ms")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def resetall(ctx):
    """Reset all aura scores (Admin only)"""
    # Confirmation message
    embed = discord.Embed(
        title="⚠️ WARNING",
        description="This will **PERMANENTLY DELETE** all aura data for everyone in this server!\n\nReact with ✅ to confirm or ❌ to cancel.",
        color=0xff0000
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        
        if str(reaction.emoji) == "✅":
            aura_data.clear()
            aura_logs.clear()
            save_data(aura_data)
            save_json(LOG_FILE, aura_logs)
            
            success_embed = discord.Embed(
                title="🗑️ Reset Complete",
                description="All aura data has been reset! Fresh start for everyone!",
                color=0x00ff00
            )
            await ctx.send(embed=success_embed)
        else:
            await ctx.send("❌ Reset cancelled.")
    except asyncio.TimeoutError:
        await ctx.send("⏰ Reset cancelled (timeout).")

@bot.tree.command(name="resetall", description="Reset all aura scores (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def resetall_slash(interaction: discord.Interaction):
    aura_data.clear()
    aura_logs.clear()
    save_data(aura_data)
    save_json(LOG_FILE, aura_logs)
    
    embed = discord.Embed(
        title="🗑️ Reset Complete",
        description="All aura data has been reset! Fresh start for everyone!",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def resetuser(ctx, member: discord.Member):
    """Reset a user's aura score"""
    uid = str(member.id)
    old_score = aura_data.get(uid, 0)
    aura_data.pop(uid, None)
    aura_logs.pop(uid, None)
    save_data(aura_data)
    save_json(LOG_FILE, aura_logs)
    
    embed = discord.Embed(
        title="🗑️ User Reset",
        description=f"{member.mention}'s aura has been reset!\n\nPrevious score: **{old_score}**",
        color=0x5865F2
    )
    await ctx.send(embed=embed)

@bot.tree.command(name="resetuser", description="Reset a user's aura score")
@app_commands.checks.has_permissions(manage_guild=True)
async def resetuser_slash(interaction: discord.Interaction, user: discord.Member):
    uid = str(user.id)
    old_score = aura_data.get(uid, 0)
    aura_data.pop(uid, None)
    aura_logs.pop(uid, None)
    save_data(aura_data)
    save_json(LOG_FILE, aura_logs)
    
    embed = discord.Embed(
        title="🗑️ User Reset",
        description=f"{user.mention}'s aura has been reset!\n\nPrevious score: **{old_score}**",
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command()
async def auraexplain(ctx):
    """Reply to a message to see why it scored high/low"""
    if not ctx.message.reference:
        embed = discord.Embed(
            title="❓ How to use !auraexplain",
            description="Reply to any message with `!auraexplain` to see a detailed breakdown of why it would gain or lose aura.",
            color=0x5865F2
        )
        await ctx.send(embed=embed)
        return
    
    replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    content = replied_msg.content.strip()
    content_norm = normalize_message(content)

    if len(content_norm.split()) < 4:
        await ctx.send("❌ Message too short to analyze (needs at least 4 words)!")
        return

    # Check hate speech first
    is_hate, hate_reason = contains_hate_speech_patterns(content)
    if is_hate:
        embed = discord.Embed(
            title=f"📝 {replied_msg.author.display_name}'s message analysis",
            description=f"**Would gain: -5 aura (HATE SPEECH)**",
            color=0xff0000
        )
        embed.add_field(
            name="Why this score?",
            value=f"🚨 **HATE SPEECH DETECTED**\nCategory: {hate_reason}\n\nThis type of content receives an immediate severe penalty with no exceptions.",
            inline=False
        )
        snippet = content[:100] + ("..." if len(content) > 100 else "")
        embed.set_footer(text=f"Message: '{snippet}'")
        await ctx.send(embed=embed)
        return

    is_hindi = is_hindi_or_hinglish(content_norm)

    # Calculate scores
    if is_obviously_safe(content_norm):
        toxic_loss = False
        toxic_reason = None
        penalty_amount = 0
        ai_score = 0
    else:
        ai_score = await calculate_ai_aura_devstral(content)
        allowed, penalty_amount, toxic_expls = evaluate_toxic_decision(content, ai_score, replied_msg)
        toxic_loss = allowed
        toxic_reason = toxic_expls

    rule_score = calculate_ai_aura_rules(content)
    local_score = calculate_ai_aura_local(content)
    semantic_score = calculate_ai_aura_semantic(content)

    if is_obviously_safe(content_norm):
        aura_gain_raw = (
            rule_score * 0.8
            + max(0, local_score) * 1.0
            + semantic_score * 0.3
        )
        total = int(round(aura_gain_raw))
        penalty_amount = 0
        toxic_loss = False
    elif toxic_loss:
        total = penalty_amount
    else:
        aura_gain_raw = (
            rule_score * 0.8
            + max(0, local_score) * 1.0
            + semantic_score * 0.3
        )
        total = int(round(aura_gain_raw))
        if total < 0:
            total = 0

    total = max(-5, min(total, 6))

    # Build explanation
    explanations = []
    if is_hindi:
        explanations.append("🌍 **Hindi/Hinglish detected** — cultural slang and casual swears in friendly context are NOT penalized.")
    
    if is_obviously_safe(content_norm):
        explanations.append("🟢 **No negative intent or targeting detected.**\n• Message classified as safe/positive")
    else:
        if toxic_loss and toxic_reason:
            sem = toxic_reason.get("semantic")
            targeted = toxic_reason.get("targeted_attack")
            ai = toxic_reason.get("ai")
            subexs = []
            if sem == "toxic":
                subexs.append("multilingual semantic intent matched toxic examples")
            if targeted:
                subexs.append("clearly targeted at a person")
            if isinstance(ai, (int, float)) and ai <= -2:
                subexs.append("AI flagged for abuse/harassment")
            if subexs:
                explanations.append(f"⚠️ **{toxic_reason.get('votes', 0)}/3 systems flagged as toxicity:**\n" + "\n".join(f"  • {s}" for s in subexs))
            elif not toxic_loss:
                explanations.append(
                    "🟢 Message classified as **non-toxic**.\n"
                    "• No hostility\n"
                    "• No targeting\n"
                    "• Casual / friendly language"
    )
            else:
                explanations.append("✋ Message NOT considered toxic: either not targeted OR not abusive enough")
        
        if total > 0:
            if rule_score >= 2:
                explanations.append("✅ Positive signals detected (good length, positive words/emojis)")
            if total > 3:
                explanations.append("🌟 **High quality message! Elite aura gain**")
            elif total > 0:
                explanations.append("👍 **Solid message contribution**")
        elif total == 0:
            explanations.append("⚖️ **Balanced - neutral impact**")

    embed = discord.Embed(
        title=f"📝 Message Analysis: {replied_msg.author.display_name}",
        description=f"**Would gain: {'+' if total >= 0 else ''}{total} aura**",
        color=0x00ff00 if total >= 0 else (0xff0000 if total <= -2 else 0xffa500)
    )

    if explanations:
        embed.add_field(
            name="💡 Why this score?",
            value="\n\n".join(explanations),
            inline=False
        )
    
    # Add detailed breakdown
    embed.add_field(
        name="📊 Score Breakdown",
        value=(
            f"**Rule-based:** {rule_score} (length, hype words, emojis)\n"
            f"**Sentiment:** {local_score} (positive/negative tone)\n"
            f"**Semantic:** {semantic_score} (message energy)\n"
            f"**AI Score:** {ai_score if ai_score else 0} (culture-aware analysis)"
        ),
        inline=False
    )
    
    snippet = content[:100] + ("..." if len(content) > 100 else "")
    embed.set_thumbnail(url=replied_msg.author.display_avatar.url)
    embed.set_footer(text=f"Message: '{snippet}'")
    await ctx.send(embed=embed)

@bot.command()
async def invite(ctx):
    """Get the bot invite link"""
    # Replace with your actual bot invite URL
    invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
    
    embed = discord.Embed(
        title="🚀 Add Auraxis to YOUR Server!",
        description=f"[Click here to invite Auraxis]({invite_url})\n\nBring AI-powered aura tracking to your community!",
        color=0x5865F2
    )
    embed.add_field(
        name="✨ Features",
        value=(
            "• AI-powered toxicity detection\n"
            "• Multi-language support (EN/HI/Hinglish)\n"
            "• Automatic role assignments\n"
            "• Detailed analytics\n"
            "• Per-channel controls"
        ),
        inline=False
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    await ctx.send(embed=embed)

@bot.tree.command(name="invite", description="Get the bot invite link")
async def invite_slash(interaction: discord.Interaction):
    invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
    
    embed = discord.Embed(
        title="🚀 Add Auraxis to YOUR Server!",
        description=f"[Click here to invite Auraxis]({invite_url})\n\nBring AI-powered aura tracking to your community!",
        color=0x5865F2
    )
    embed.add_field(
        name="✨ Features",
        value=(
            "• AI-powered toxicity detection\n"
            "• Multi-language support (EN/HI/Hinglish)\n"
            "• Automatic role assignments\n"
            "• Detailed analytics\n"
            "• Per-channel controls"
        ),
        inline=False
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    await interaction.response.send_message(embed=embed)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def aurach_status(ctx):
    """Check which channels have aura enabled/disabled"""
    gid = str(ctx.guild.id)
    guild_cfg = config_data.get(gid, {})
    disabled = guild_cfg.get("disabled_channels", [])
    
    embed = discord.Embed(
        title="⚙️ Aura Channel Status",
        color=0x5865F2
    )
    
    if not disabled:
        embed.description = "✅ Aura is **enabled** in all channels"
    else:
        mentions = [f"<#{cid}>" for cid in disabled]
        embed.add_field(
            name="❌ Disabled Channels",
            value="\n".join(mentions),
            inline=False
        )
        
        total_text_channels = len([c for c in ctx.guild.channels if isinstance(c, discord.TextChannel)])
        enabled_count = total_text_channels - len(disabled)
        embed.add_field(
            name="📊 Summary",
            value=f"**Enabled:** {enabled_count} channels\n**Disabled:** {len(disabled)} channels",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.tree.command(name="aurach_status", description="Check which channels have aura enabled/disabled")
@app_commands.checks.has_permissions(manage_guild=True)
async def aurach_status_slash(interaction: discord.Interaction):
    gid = str(interaction.guild.id)
    guild_cfg = config_data.get(gid, {})
    disabled = guild_cfg.get("disabled_channels", [])
    
    embed = discord.Embed(
        title="⚙️ Aura Channel Status",
        color=0x5865F2
    )
    
    if not disabled:
        embed.description = "✅ Aura is **enabled** in all channels"
    else:
        mentions = [f"<#{cid}>" for cid in disabled]
        embed.add_field(
            name="❌ Disabled Channels",
            value="\n".join(mentions),
            inline=False
        )
        
        total_text_channels = len([c for c in interaction.guild.channels if isinstance(c, discord.TextChannel)])
        enabled_count = total_text_channels - len(disabled)
        embed.add_field(
            name="📊 Summary",
            value=f"**Enabled:** {enabled_count} channels\n**Disabled:** {len(disabled)} channels",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================================================
# MISSING COMMANDS - ADD THESE TO YOUR BOT.PY
# ============================================================================

@bot.command()
async def ping(ctx):
    """Check bot latency."""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! **{latency}ms**")

@bot.tree.command(name="ping", description="Check bot latency")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! **{latency}ms**")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def setchannel(ctx):
    """Enable aura tracking in this channel."""
    guild_id = str(ctx.guild.id)
    channel_id = ctx.channel.id
    
    guild_config = config_data.setdefault(guild_id, {})
    disabled = guild_config.setdefault("disabled_channels", [])
    
    if channel_id in disabled:
        disabled.remove(channel_id)
        save_config()
        await ctx.send(f"✅ Aura tracking enabled in {ctx.channel.mention}!")
    else:
        await ctx.send(f"ℹ️ Aura tracking is already enabled in {ctx.channel.mention}!")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def disablechannel(ctx):
    """Disable aura tracking in this channel."""
    guild_id = str(ctx.guild.id)
    channel_id = ctx.channel.id
    
    guild_config = config_data.setdefault(guild_id, {})
    disabled = guild_config.setdefault("disabled_channels", [])
    
    if channel_id not in disabled:
        disabled.append(channel_id)
        save_config()
        await ctx.send(f"✅ Aura tracking disabled in {ctx.channel.mention}!")
    else:
        await ctx.send(f"ℹ️ Aura tracking is already disabled in {ctx.channel.mention}!")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def enablechannel(ctx):
    """Re-enable aura tracking in this channel."""
    await setchannel(ctx)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def setaura(ctx, member: discord.Member, amount: int):
    """Set a user's aura to a specific amount."""
    uid = str(member.id)
    old_aura = aura_data.get(uid, 0)
    aura_data[uid] = max(0, amount)
    save_data(aura_data)
    
    log_aura_change(uid, amount - old_aura, amount, "admin_set")
    
    await ctx.send(f"✅ Set **{member.display_name}**'s aura to **{amount}** (was {old_aura})")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def resetaura(ctx, member: discord.Member):
    """Reset a user's aura to 0."""
    uid = str(member.id)
    old_aura = aura_data.get(uid, 0)
    aura_data[uid] = 0
    save_data(aura_data)
    
    log_aura_change(uid, -old_aura, 0, "admin_reset")
    
    await ctx.send(f"✅ Reset **{member.display_name}**'s aura to **0** (was {old_aura})")

@bot.tree.command(name="setaura", description="Set a user's aura (Admin)")
@app_commands.checks.has_permissions(manage_guild=True)
async def setaura_slash(interaction: discord.Interaction, user: discord.Member, amount: int):
    uid = str(user.id)
    old_aura = aura_data.get(uid, 0)
    new_aura = max(0, amount) # Ensure non-negative
    aura_data[uid] = new_aura
    save_data(aura_data)
    
    log_aura_change(uid, new_aura - old_aura, new_aura, "admin_set")
    
    # ✅ CRITICAL: Force global update immediately
    update_global_stats(uid, user.name, new_aura, interaction.guild.name) 
    
    await interaction.response.send_message(
        f"✅ Set **{user.display_name}**'s aura to **{new_aura}** (was {old_aura})",
        ephemeral=True
    )

@setaura_slash.error
async def setaura_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)

@bot.tree.command(name="resetaura", description="Reset a user's aura (Admin)")
@app_commands.checks.has_permissions(manage_guild=True)
async def resetaura_slash(interaction: discord.Interaction, user: discord.Member):
    uid = str(user.id)
    old_aura = aura_data.get(uid, 0)
    aura_data[uid] = 0
    save_data(aura_data)
    
    log_aura_change(uid, -old_aura, 0, "admin_reset")
    
    await interaction.response.send_message(
        f"✅ Reset **{user.display_name}**'s aura to **0** (was {old_aura})",
        ephemeral=True
    )
@bot.command()
@commands.has_permissions(administrator=True)
async def syncglobal(ctx):
    """Manually sync global stats (Admin only)"""
    count = 0
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            uid = str(member.id)
            aura = aura_data.get(uid, 0)
            if aura > 0:
                update_global_stats(uid, member.name, aura, guild.name)
                count += 1
    
    await ctx.send(f"✅ Synced {count} users to global leaderboard!")
    
@resetaura_slash.error
async def resetaura_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need Manage Server permission!", ephemeral=True)

# Error handlers for slash commands
@aurach_enable_slash.error
async def aurach_enable_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)

@aurach_disable_slash.error
async def aurach_disable_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)

@aurach_status_slash.error
async def aurach_status_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)

@resetuser_slash.error
async def resetuser_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)

@resetall_slash.error
async def resetall_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)

@debug_slash.error
async def debug_slash_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You need Manage Server permission to use this command.", ephemeral=True)

if not TOKEN:
    raise RuntimeError("TOKEN not found in environment variables")

print("=" * 50)
print("🚀 Starting Auraxis Bot...")
print("=" * 50)
bot.run(TOKEN)