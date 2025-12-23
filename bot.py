import discord
from discord.ext import commands
import json
import os
import time
import difflib
from textblob import TextBlob
from sentence_transformers import SentenceTransformer
import numpy as np

# ================== AI MODEL ==================

semantic_model = SentenceTransformer("all-MiniLM-L6-v2")

# ================== CONFIG ==================

TOKEN = os.getenv("TOKEN")
DATA_FILE = "aura_data.json"
PREFIX = "!"

# ================== INTENTS =================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ================== DATA ====================

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

aura_data = load_data()

# ================== ANTI-SPAM MEMORY =========

recent_aura_time = {}   # user_id -> last aura timestamp
recent_messages = {}    # user_id -> (last_message, timestamp)

AURA_COOLDOWN = 30
DUPLICATE_WINDOW = 15
SIMILARITY_THRESHOLD = 0.85

# ================== AI SCORING ===============

def calculate_ai_aura_rules(message: str) -> int:
    score = 0

    if len(message) >= 15:
        score += 1
    if len(message) >= 35:
        score += 1

    if any(word in message for word in [
        "fire", "clean", "goated", "insane", "love",
        "cool", "legend", "based"
    ]):
        score += 1

    emojis = ["🔥", "🗿", "👑", "⚡", "😂"]
    score += min(sum(message.count(e) for e in emojis), 2)

    if message.count("!") >= 2:
        score += 1

    return max(0, min(score, 3))

def calculate_ai_aura_local(message: str) -> int:
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    score = 0

    if polarity > 0.4:
        score += 3
    elif polarity > 0.1:
        score += 2
    elif polarity > 0:
        score += 1

    if polarity < -0.3:
        score -= 2

    if len(message) > 30:
        score += 1

    if subjectivity > 0.5:
        score += 1

    return max(0, min(score, 4))

def calculate_ai_aura_semantic(message: str) -> int:
    embedding = semantic_model.encode(message)

    # Energy = confidence / presence
    energy = np.linalg.norm(embedding)

    length_bonus = min(len(message.split()) // 6, 2)

    score = 0

    if energy > 14:
        score += 1
    if energy > 17:
        score += 1
    if energy > 20:
        score += 2

    score += length_bonus

    return max(0, min(score, 5))

# ================== EVENTS ===================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    content = message.content.strip().lower()
    if content.startswith(PREFIX):
        return


    if len(message.split()) < 4:
        return

    user_id = str(message.author.id)
    now = time.time()

    # Cooldown
    if now - recent_aura_time.get(user_id, 0) < AURA_COOLDOWN:
        return

    # Duplicate detection
    if user_id in recent_messages:
        last_msg, last_time = recent_messages[user_id]
        if now - last_time < DUPLICATE_WINDOW:
            similarity = difflib.SequenceMatcher(None, content, last_msg).ratio()
            if similarity >= SIMILARITY_THRESHOLD:
                return

    # 🔥 HYBRID AI SCORING 
    rule_score = calculate_ai_aura_rules(content)
    nlp_score = calculate_ai_aura_local(content)
    semantic_score = calculate_ai_aura_semantic(content)

    # Final AI decision
    aura_gain = max(rule_score, nlp_score, semantic_score)

    
    

    if aura_gain <= 0:
        return

    aura_data[user_id] = aura_data.get(user_id, 0) + aura_gain
    save_data(aura_data)

    recent_aura_time[user_id] = now
    recent_messages[user_id] = (content, now)

    print(f"[AURA] {message.author} +{aura_gain} → {aura_data[user_id]}")

# ================== COMMANDS =================

@bot.command()
async def aura(ctx):
    score = aura_data.get(str(ctx.author.id), 0)
    await ctx.send(f"🔵 {ctx.author.mention}'s Aura Score: **{score}**")

@bot.command()
async def auraof(ctx, member: discord.Member):
    score = aura_data.get(str(member.id), 0)
    await ctx.send(f"🔵 {member.mention}'s Aura Score: **{score}**")

@bot.command()
async def aurarank(ctx):
    score = aura_data.get(str(ctx.author.id), 0)

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
async def topaura(ctx):
    if not aura_data:
        await ctx.send("No aura data yet.")
        return

    top = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = "**🏆 Top Aura Users:**\n"

    for i, (uid, score) in enumerate(top, start=1):
        user = await bot.fetch_user(int(uid))
        msg += f"{i}. {user.name} — {score}\n"

    await ctx.send(msg)

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="✨ Auraxis Bot Commands",
        description="Earn aura by chatting naturally (no spam)",
        color=0x5865F2
    )
    embed.add_field(
        name="Commands",
        value=(
            "`!aura` → Your aura score\n"
            "`!aurarank` → Your aura rank\n"
            "`!auraof @user` → Someone else's aura\n"
            "`!topaura` → Top aura users"
        ),
        inline=False
    )
    embed.set_footer(text="Auraxis • Made by Dhruv")
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def aura(ctx):
    ...

# ================== RUN =====================

if not TOKEN:
    raise RuntimeError("TOKEN not found in environment variables")

bot.run(TOKEN)

