import discord
from discord.ext import commands
import json
import os
import time
import difflib
import random
from collections import defaultdict

# ================= CONFIG =================

DATA_FILE = "aura_data.json"
GENERAL_CHANNEL = "general"   # optional, not enforced

# ================= INTENTS =================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# ================= DATA =================

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

aura = load_data()

# ================= AURA MEMORY (ANTI-SPAM) =================

recent_aura_time = {}          # user_id -> last aura timestamp
recent_messages = {}           # user_id -> (last_message, timestamp)

AURA_COOLDOWN = 8              # seconds between aura gains
DUPLICATE_WINDOW = 15          # seconds
SIMILARITY_THRESHOLD = 0.85

# ================= AURA SCORING =================

POSITIVE_KEYWORDS = {
    "fire": 3,
    "clean": 2,
    "based": 3,
    "legend": 4,
    "goated": 4,
    "crazy": 2,
    "insane": 2,
    "love": 3,
    "nice": 2,
    "cool": 2,
}

NEGATIVE_KEYWORDS = {
    "fk": -3,
    "fking": -3,
    "hell": -2,
    "shit": -2,
    "trash": -3,
    "bad": -2,
}

POSITIVE_EMOJIS = {"🔥", "💯", "✨", "🗿", "👑", "⚡"}
NEGATIVE_EMOJIS = {"💀", "🤡", "😡", "👎"}

def calculate_aura_gain(content: str) -> int:
    score = 0

    words = content.split()

    for word in words:
        score += POSITIVE_KEYWORDS.get(word, 0)
        score += NEGATIVE_KEYWORDS.get(word, 0)

    for char in content:
        if char in POSITIVE_EMOJIS:
            score += 1
        elif char in NEGATIVE_EMOJIS:
            score -= 1

    # Message quality bonus
    if len(content) > 40:
        score += 2
    elif len(content) < 5:
        score -= 1

    # Random micro variance (prevents exact farming)
    score += random.choice([0, 0, 1])

    return max(score, 0)

# ================= EVENTS =================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    content = message.content.strip().lower()

    # Ignore commands
    if content.startswith("!"):
        return

    user_id = str(message.author.id)
    now = time.time()

    # Cooldown check
    last_time = recent_aura_time.get(user_id, 0)
    if now - last_time < AURA_COOLDOWN:
        return

    # Duplicate / similarity check
    last_msg, last_msg_time = recent_messages.get(user_id, ("", 0))
    similarity = difflib.SequenceMatcher(None, content, last_msg).ratio()

    if similarity >= SIMILARITY_THRESHOLD and now - last_msg_time < DUPLICATE_WINDOW:
        return

    aura_gain = calculate_aura_gain(content)

    if aura_gain <= 0:
        recent_messages[user_id] = (content, now)
        return

    aura[user_id] = aura.get(user_id, 0) + aura_gain

    recent_aura_time[user_id] = now
    recent_messages[user_id] = (content, now)

    save_data(aura)

    print(f"[AURA] {message.author} +{aura_gain} → {aura[user_id]}")

# ================= COMMANDS =================

@bot.command()
async def aura(ctx):
    score = aura.get(str(ctx.author.id), 0)
    await ctx.send(f"🔵 {ctx.author.mention}'s Aura Score: **{score}**")

@bot.command()
async def aurarank(ctx):
    score = aura.get(str(ctx.author.id), 0)

    if score >= 1500:
        rank = "☄️ GOD AURA"
    elif score >= 800:
        rank = "🔥 Massive Aura"
    elif score >= 400:
        rank = "✨ Aura User"
    elif score >= 150:
        rank = "🌫 Low Aura"
    else:
        rank = "💤 No Aura"

    await ctx.send(f"{ctx.author.mention} → **{rank}** ({score})")

@bot.command()
async def auraof(ctx, member: discord.Member):
    score = aura.get(str(member.id), 0)
    await ctx.send(f"🔵 {member.mention}'s Aura Score: **{score}**")

@bot.command()
async def topaura(ctx):
    if not aura:
        await ctx.send("No aura data yet.")
        return

    top = sorted(aura.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = "**🏆 Top Aura Users**\n"

    for i, (uid, score) in enumerate(top, start=1):
        member = ctx.guild.get_member(int(uid))
        name = member.name if member else "Unknown"
        msg += f"{i}. **{name}** — {score}\n"

    await ctx.send(msg)

@bot.command()
async def ping(ctx):
    await ctx.send("pong")

# ================= RUN =================

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise Exception("TOKEN not found in environment variables")

bot.run(TOKEN)
