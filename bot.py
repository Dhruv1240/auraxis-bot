import discord
from discord.ext import commands
import json
import os
import random

# ================= CONFIG =================

DATA_FILE = "aura_data.json"
GENERAL_CHANNEL = "general"

# ================= INTENTS =================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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

aura_data = load_data()

# ================= AURA LOGIC =================

def calculate_aura(message):
    text = message.content.lower()
    score = 0

    confident_words = ["bro", "trust", "nah", "fr", "bet"]
    insecure_words = ["idk", "maybe", "sorry", "i guess"]
    dominant_words = ["listen", "watch", "wait"]
    emojis = ["🔥", "💀", "😈", "🗿"]

    score += sum(4 for w in confident_words if w in text)
    score -= sum(3 for w in insecure_words if w in text)
    score += sum(5 for w in dominant_words if w in text)

    if 15 < len(text) < 120:
        score += 5

    if message.content.isupper() and len(message.content) > 5:
        score += 8

    score += message.content.count("!") * 2
    score -= message.content.count("?")

    score += sum(6 for e in emojis if e in message.content)

    return max(min(score, 25), 0)

async def assign_roles(member, score):
    role_map = {
        "💤 No Aura": 0,
        "🌫 Low Aura": 150,
        "✨ Aura User": 400,
        "🔥 Massive Aura": 800,
        "☄️ GOD AURA": 1500
    }

    for role_name, min_score in role_map.items():
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role and score >= min_score and role not in member.roles:
            await member.add_roles(role)

# ================= EVENTS =================

@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Game("Judging aura 👁️")
    )
    print(f"🟢 Aura Bot Online as {bot.user}")

import time
import re

last_message_time = {}  # user_id -> timestamp

import time
import re

last_message_time = {}

@bot.event
async def on_message(message):
    # 1️⃣ Ignore bots
    if message.author.bot:
        return

    # 2️⃣ Always allow commands
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    # 3️⃣ Basic text cleanup
    text = message.content.strip()

    # Ignore empty / very short messages
    if len(text) < 5:
        return

    user_id = str(message.author.id)
    now = time.time()

    # 4️⃣ Cooldown (20 seconds)
    last_time = last_message_time.get(user_id, 0)
    if now - last_time < 20:
        return

    last_message_time[user_id] = now

    # 5️⃣ Load aura data
    aura_data = load_data()
    current = aura_data.get(user_id, 0)

    # =========================
    # 🧠 AI-STYLE AURA SCORING
    # =========================

    aura_gain = 1  # base

    # Length bonus
    if len(text) >= 30:
        aura_gain += 1
    if len(text) >= 80:
        aura_gain += 1

    # Emoji bonus (max +2)
    emojis = re.findall(r"[🔥😂❤️✨💀👍🙏]", text)
    aura_gain += min(len(emojis), 2)

    # Anti-spam hard cap
    aura_gain = min(aura_gain, 5)

    # 6️⃣ Save aura
    aura_data[user_id] = current + aura_gain
    save_data(aura_data)

    # 7️⃣ Optional reaction (visual feedback)
    if aura_gain >= 4:
        try:
            await message.add_reaction("🔥")
        except:
            pass





@bot.event
async def on_presence_update(before, after):
    if before.status == after.status:
        return

    role = discord.utils.get(after.guild.roles, name="🔥 Massive Aura")
    if role and role in after.roles and after.status == discord.Status.online:
        channel = discord.utils.get(after.guild.text_channels, name=GENERAL_CHANNEL)
        if channel:
            await channel.send(
                f"🗿 **PRESENCE SHIFT DETECTED** 🗿\n{after.mention} is online."
            )

# ================= COMMANDS =================

@bot.command()
async def aura(ctx):
    uid = str(ctx.author.id)
    score = aura_data.get(uid, 0)
    await ctx.send(f"🧿 {ctx.author.mention}'s Aura Score: **{score}**")

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
    top = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = "🏆 **TOP AURA USERS** 🏆\n"

    for i, (uid, score) in enumerate(top, 1):
        user = await bot.fetch_user(int(uid))
        msg += f"{i}. {user.name} → **{score}**\n"

    await ctx.send(msg)

@bot.command()
async def auraof(ctx, member: discord.Member):
    score = aura_data.get(str(member.id), 0)
    await ctx.send(f"🧿 {member.mention}'s Aura Score: **{score}**")

@bot.command()
async def about(ctx):
    embed = discord.Embed(
        title="🗿 Auraxis",
        description="Aura-based presence detection bot.",
        color=0x2ecc71
    )

    embed.add_field(
        name="✨ Features",
        value=(
            "• Aura Analysis\n"
            "• Presence Detection\n"
            "• Role Automation\n"
            "• Vibe Check System"
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Creator",
        value="Made by **Dhruv**",
        inline=False
    )

    embed.set_footer(text="Monitoring presence. Measuring aura.")

    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📖 Auraxis Commands",
        color=0x3498db
    )

    embed.add_field(
        name="🧿 Aura",
        value=(
            "`!aura` → Your aura score\n"
            "`!aurarank` → Your aura rank\n"
            "`!topaura` → Top aura users\n"
            "`!auraof @user` → Check someone else's aura"
        ),
        inline=False
    )

    embed.add_field(
        name="ℹ️ Info",
        value="`!about` → About the bot",
        inline=False
    )

    embed.set_footer(text="Auraxis • Made by Dhruv")

    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send("pong")

def calculate_aura_score(text: str) -> int:
    text = text.strip()

    score = 0

    # Base score for meaningful messages
    score += min(len(text) // 20, 5)  # max +5 from length

    # Positive sentiment heuristics
    positive_words = [
        "good", "great", "awesome", "nice", "love", "amazing",
        "cool", "fun", "happy", "gg", "well played"
    ]

    negative_words = [
        "hate", "stupid", "idiot", "trash", "worst",
        "kill", "die", "shut up"
    ]

    lowered = text.lower()

    for word in positive_words:
        if word in lowered:
            score += 2

    for word in negative_words:
        if word in lowered:
            score -= 2

    # Emoji bonus
    emoji_count = len(re.findall(r"[😀-🙏🔥✨💀😂❤️👍]", text))
    score += min(emoji_count, 3)

    # Caps rage penalty
    if text.isupper() and len(text) > 8:
        score -= 3

    # Clamp final score
    return max(-2, min(score, 8))

# ================= RUN =================
import os 


TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    raise Exception("TOKEN not found in environment variables")

bot.run(TOKEN)

