import discord
from discord.ext import commands, tasks
import json
import os
import time
import difflib
import asyncio
from textblob import TextBlob
from sentence_transformers import SentenceTransformer
from detoxify import Detoxify
import numpy as np
from openai import OpenAI

key = os.getenv("OPENROUTER_API_KEY")
if not key:
    raise RuntimeError("OPENROUTER_API_KEY not set")

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=key
)

# ================== MODELS ==================
semantic_model = SentenceTransformer("all-MiniLM-L6-v2")
toxicity_model = Detoxify("original")

# ================== CONFIG ==================
TOKEN = os.getenv("TOKEN")
DATA_FILE = "aura_data.json"
CONFIG_FILE = "aura_config.json"
LOG_FILE = "aura_logs.json"
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

# ================== ANTI-SPAM =================
recent_aura_time = {}
recent_messages = {}
AURA_COOLDOWN = 30
DUPLICATE_WINDOW = 15
SIMILARITY_THRESHOLD = 0.85

def is_channel_enabled(guild_id: int, channel_id: int) -> bool:
    gid = str(guild_id)
    cid = str(channel_id)
    guild_cfg = config_data.get(gid, {})
    enabled_channels = guild_cfg.get("enabled_channels", [])
    if not enabled_channels:
        return True
    return cid in enabled_channels

# ================== DECAY TASK =================
DECAY_RATE = 0.01  # 1% per day

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

# ================== ROLE SYNC =================
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

# ================== SCORING ==================
def calculate_ai_aura_rules(message: str) -> int:
    score = 0
    if len(message) >= 20:  # was 15
        score += 1
    if len(message) >= 50:  # was 35
        score += 1
    hype_words = ["fire", "clean", "goated", "insane", "legend", "based"]
    hype_count = sum(1 for w in hype_words if w in message)
    score += min(hype_count, 1)  # MAX 1 hype word
    emojis = sum(message.count(e) for e in ["🔥", "🗿", "👑", "⚡", "😂"])
    score += min(emojis, 1)      # MAX 1 emoji
    return min(score, 2)         # MAX 2 total

def calculate_ai_aura_local(message: str) -> int:
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity
    score = 0
    if polarity > 0.4:
        score += 3
    elif polarity > 0.15:
        score += 2
    elif polarity > 0.05:
        score += 1
    elif polarity < -0.35:
        score -= 2
    elif polarity < -0.2:
        score -= 1
    return max(-2, min(score, 4))

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

def detoxify_score(message: str) -> float:
    result = toxicity_model.predict(message)
    return max(result.values())

def calculate_ai_aura_devstral(message: str) -> int:
    try:
        response = openrouter_client.chat.completions.create(
            model="mistralai/devstral-2512",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI that evaluates chat messages.\n"
                        "Return ONLY an integer aura score between -3 and +5.\n"
                        "Positive for confident, meaningful, cool messages.\n"
                        "Negative for cringe, weak, or low-effort messages.\n"
                        "Return only the number."
                    )
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            temperature=0.3,
            max_tokens=5
        )
        score_text = response.choices[0].message.content.strip()
        score = int(score_text)
        return max(-3, min(score, 5))
    except Exception as e:
        print("Devstral error:", e)
        return 0

# ================== EVENTS ===================
@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game("Measuring Aura ⚡")
    )
    if not daily_decay_task.is_running():
        daily_decay_task.start()
    if not aura_role_sync_task.is_running():
        aura_role_sync_task.start()
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.guild and not is_channel_enabled(message.guild.id, message.channel.id):
        return

    if bot.user in message.mentions:
        await message.channel.send(
            f"👋 Hey {message.author.mention}! "
            f"Use !commandlist to see commands or !aurainfo to learn how Auraxis works."
        )

    await bot.process_commands(message)

    content = message.content.strip().lower()

    if content.startswith(PREFIX):
        return

    if len(content.split()) < 4:
        return

    user_id = str(message.author.id)
    now = time.time()

    if now - recent_aura_time.get(user_id, 0) < AURA_COOLDOWN:
        return

    if user_id in recent_messages:
        last_msg, last_time = recent_messages[user_id]
        if now - last_time < DUPLICATE_WINDOW:
            if difflib.SequenceMatcher(None, content, last_msg).ratio() >= SIMILARITY_THRESHOLD:
                return

    tox = detoxify_score(content)

    if tox >= 0.80:
        aura_gain = -4
    elif tox >= 0.65:
        aura_gain = -3
    else:
        rule_score = calculate_ai_aura_rules(content)
        local_score = calculate_ai_aura_local(content)
        semantic_score = calculate_ai_aura_semantic(content)
        ai_score = calculate_ai_aura_devstral(content)

        # Conservative weights: max +4 realistic
        aura_gain_raw  = (
            rule_score * 0.8      # rules: 0-2 → 0-1.6
            + local_score * 1.0   # sentiment: 0-3 → 0-3  
            + semantic_score * 0.3 # semantic: 0-2 → 0-0.6
            + ai_score * 0.8      # AI: 0-5 → 0-4
)

        aura_gain = int(round(aura_gain_raw))

    aura_gain = max(-4, min(aura_gain, 6))

    if aura_gain == 0:
        return

    current = aura_data.get(user_id, 0)
    new_score = max(0, current + aura_gain)

    aura_data[user_id] = new_score
    save_data(aura_data)

    recent_aura_time[user_id] = now
    recent_messages[user_id] = (content, now)
    reason = "toxic" if tox >= 0.65 else "normal"
    log_aura_change(user_id, aura_gain, new_score, reason)

    if aura_gain <= -2:
        await message.channel.send(
            f"⚠️ {message.author.mention} your message was flagged as toxic.\n"
            f"**Aura change:** {aura_gain}"
        )

    print(
        f"[AURA] {message.author} "
        f"{'+' if aura_gain > 0 else ''}{aura_gain} → {new_score} | TOX={tox:.2f}"
    )

# ================== COMMANDS =================
@bot.command()
async def aura(ctx):
    await ctx.send(f"🔵 {ctx.author.mention}'s Aura: {aura_data.get(str(ctx.author.id), 0)}")

@bot.command()
async def auraof(ctx, member: discord.Member):
    await ctx.send(f"🔵 {member.mention}'s Aura: {aura_data.get(str(member.id), 0)}")

@bot.command()
async def aurarank(ctx):
    score = aura_data.get(str(ctx.author.id), 0)
    rank = get_rank_name(score)
    await ctx.send(f"{ctx.author.mention} → {rank} ({score})")

PAGE_SIZE = 10

def get_sorted_aura():
    return sorted(aura_data.items(), key=lambda x: x[1], reverse=True)

def make_leaderboard_embed(page: int, total_pages: int, entries, offset: int):
    desc_lines = []
    for i, (uid, score) in enumerate(entries, start=1):
        desc_lines.append(f"{offset + i}. <@{uid}> — {score}")
    embed = discord.Embed(
        title=f"🏆 Aura Leaderboard (Page {page+1}/{total_pages})",
        description="\n".join(desc_lines) or "No aura data.",
        color=0x5865F2,
    )
    return embed

@bot.command()
async def auraboard(ctx, page: int = 1):
    if not aura_data:
        await ctx.send("No aura data yet.")
        return

    page = max(page, 1) - 1  # 0-based
    sorted_list = get_sorted_aura()
    total_pages = max(1, (len(sorted_list) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages - 1)

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    entries = sorted_list[start:end]
    embed = make_leaderboard_embed(page, total_pages, entries, start)
    await ctx.send(embed=embed)

@bot.command(aliases=['help', 'commands'])
async def commandlist(ctx):
    embed = discord.Embed(
        title=" **Auraxis — All Commands** ",
        description="**Auraxis measures your chat impact!** Positive = gains, toxic = losses.",
        color=0x5865F2
    )
    
    # Player commands
    embed.add_field(
        name="👤 **Player Commands**",
        value=(
            "`!aura` — Your current aura score\n"
            "`!aurarank` — Your rank + role\n"
            "`!auraof @user` — Check someone's aura\n"
            "`!auralogs [@user]` — Recent changes\n"
            "`!auraexplain` — **Reply** to analyze any message\n"
            "`!invite` - invite auraxis to your server"
        ),
        inline=False
    )
    
    # Leaderboard & stats
    embed.add_field(
        name="🏆 **Leaderboards & Stats**",
        value=(
            "`!auraboard [page]` — Top players (paginated)"
        ),
        inline=False
    )
    
    # Admin commands
    embed.add_field(
        name="🔧 **Admin Commands** (Manage Server)",
        value=(
            "`!aurach_enable [#channel]` — Enable aura here\n"
            "`!aurach_disable [#channel]` — Disable aura here\n"
            "`!debug` — Bot status & stats\n"
            "`!resetuser @user` — Reset their aura\n"
            "`!resetall` — Reset **everyone** (Admin only)"
        ),
        inline=False
    )
    
    # Info
    embed.add_field(
        name="ℹ️ **Info**",
        value=(
            "`!aurainfo` — How aura works\n"
            "`!commandlist` — This help menu"
        ),
        inline=False
    )
    
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    embed.set_footer(
        text="💡 Reply to ANY message with !auraexplain to see why it scored high/low!",
        icon_url="https://cdn.discordapp.com/emojis/1089084571584613448.png"
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def aurainfo(ctx):
    embed = discord.Embed(
        title="🧠 About Auraxis",
        description="Auraxis is an AI-powered aura measuring system.",
        color=0x5865F2
    )
    embed.add_field(
        name="✨ What is Aura?",
        value="Aura represents your presence, confidence, positivity, and originality.",
        inline=False
    )
    embed.add_field(
        name="📈 How Aura Increases",
        value=(
            "• Meaningful messages, not random crap\n"
            "• Positive tone\n"
            "• Original thoughts\n"
            "• Natural conversation"
        ),
        inline=False
    )
    embed.add_field(
        name="📉 How Aura Decreases",
        value=(
            "• Toxicity\n"
            "• Aggression\n"
            "• Repeated negativity"
        ),
        inline=False
    )
    embed.set_footer(text="Auraxis • Impact matters more than volume")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def aurach_enable(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    gid = str(ctx.guild.id)
    cid = str(channel.id)
    guild_cfg = config_data.setdefault(gid, {})
    enabled = set(guild_cfg.get("enabled_channels", []))
    enabled.add(cid)
    guild_cfg["enabled_channels"] = list(enabled)
    save_json(CONFIG_FILE, config_data)
    await ctx.send(f"Aura enabled in {channel.mention}.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def aurach_disable(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    gid = str(ctx.guild.id)
    cid = str(channel.id)
    guild_cfg = config_data.setdefault(gid, {})
    enabled = set(guild_cfg.get("enabled_channels", []))
    if cid in enabled:
        enabled.remove(cid)
    guild_cfg["enabled_channels"] = list(enabled)
    save_json(CONFIG_FILE, config_data)
    await ctx.send(f"Aura disabled in {channel.mention}.")

@bot.command()
async def auralogs(ctx, member: discord.Member = None):
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
        lines.append(f"`{ts}` {prefix}{chg} → {score} ({rsn})")

    embed = discord.Embed(
        title=f"Aura logs for {member}",
        description="\n".join(lines),
        color=0x5865F2,
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def debug(ctx):
    embed = discord.Embed(title="🔧 Bot Debug Info", color=0x5865F2)
    
    # Aura data stats
    total_aura = sum(aura_data.values()) if aura_data else 0
    embed.add_field(
        name="📊 Aura Data", 
        value=f"**{len(aura_data)}** users | **{total_aura:,}** total", 
        inline=True
    )
    
    # Config status
    guild_id = str(ctx.guild.id)
    guild_cfg = config_data.get(guild_id, {})
    enabled_chs = len(guild_cfg.get("enabled_channels", []))
    status = "✅ All channels" if not enabled_chs else f"✅ {enabled_chs} channels"
    embed.add_field(name="⚙️ Channel Config", value=status, inline=True)
    
    # Background tasks
    decay_status = "✅ Running" if daily_decay_task.is_running() else "❌ Stopped"
    role_status = "✅ Running" if aura_role_sync_task.is_running() else "❌ Stopped"
    embed.add_field(name="Tasks", value=f"Decay: {decay_status}\nRoles: {role_status}", inline=True)
    
    # Top 3 users
    if aura_data:
        top3 = sorted(aura_data.items(), key=lambda x: x[1], reverse=True)[:3]
        top_list = "\n".join([f"<@{uid}> ({score})" for uid, score in top3])
        embed.add_field(name="🏆 Top 3", value=top_list or "No data", inline=False)
    else:
        embed.add_field(name="🏆 Top 3", value="No aura data yet", inline=False)
    
    # Memory usage
    embed.add_field(
        name="💾 Memory", 
        value=f"**{len(aura_logs)}** logs | **{len(config_data)}** guilds", 
        inline=True
    )
    
    # Uptime + bot status
    embed.add_field(
        name="⏰ Status", 
        value=f"**{len(bot.guilds)}** servers | **{len(bot.commands)}** cmds", 
        inline=True
    )
    
    embed.set_footer(text=f"Server: {ctx.guild.name} | Reload to refresh")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def resetall(ctx):
    aura_data.clear()
    save_data(aura_data)
    await ctx.send("🗑️ **All aura reset!** Fresh start!")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def resetuser(ctx, member: discord.Member):
    aura_data.pop(str(member.id), None)
    save_data(aura_data)
    await ctx.send(f"🗑️ **{member.mention}'s aura reset!**")

@bot.command()
async def auraexplain(ctx):
    # Works by REPLYING to a message
    if not ctx.message.reference:
        await ctx.send("📝 **Reply to a message** with `!auraexplain` to see why it scored high/low!")
        return
    
    replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
    content = replied_msg.content.strip().lower()
    
    if len(content.split()) < 4:
        await ctx.send("❌ Message too short to analyze!")
        return
    
    rule_score = calculate_ai_aura_rules(content)
    local_score = calculate_ai_aura_local(content)
    semantic_score = calculate_ai_aura_semantic(content)
    ai_score = calculate_ai_aura_devstral(content)
    
    aura_gain_raw = (
        rule_score * 0.8 + local_score * 1.0 + semantic_score * 0.3 + ai_score * 0.8
    )
    total = int(round(aura_gain_raw))
    total = max(-4, min(total, 6))
    
    # Simple explanations everyone understands
    explanations = []
    
    if rule_score >= 2:
        explanations.append("✅ **Perfect length + hype words/emojis**")
    elif rule_score == 1:
        explanations.append("➕ **Good length or 1 hype word**")
    
    if local_score >= 2:
        explanations.append(" **Super positive vibe**")
    elif local_score == 1:
        explanations.append(" **Positive tone**")
    elif local_score < 0:
        explanations.append(" **Negative vibe**")
    
    if semantic_score >= 1:
        explanations.append("⚡ **High energy message**")
    
    if total >= 4:
        explanations.append("🌟 **Auraxis loved it! Elite aura**")
    elif total >= 2:
        explanations.append("👍 **Auraxis thinks it's solid**")
    elif total <= -2:
        explanations.append("⚠️ **Auraxis flagged low effort**")
    
    embed = discord.Embed(
        title=f"🔍 {replied_msg.author.mention}'s message analysis",
        description=f"**Would gain: {'+' if total >= 0 else ''}{total} aura**",
        color=0x00ff00 if total >= 0 else 0xff0000
    )
    
    if explanations:
        embed.add_field(
            name="Why this score?",
            value="\n".join(explanations),
            inline=False
        )
    else:
        embed.add_field(
            name="Why this score?",
            value="⚖️ Balanced - no strong positives/negatives",
            inline=False
        )
    
    embed.set_footer(text=f"Message: '{content[:50]}...'")
    await ctx.send(embed=embed)

@bot.command()
async def invite(ctx):
    embed = discord.Embed(
        title="🚀 Add Auraxis to YOUR Server!",
        description="**[Invite Link](https://discord.com/oauth2/authorize?client_id=1452461307935854755&permissions=268504064&integration_type=0&scope=bot)**",
        color=0x5865F2
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1089084571584613448.png")
    await ctx.send(embed=embed)

# ================== RUN =====================
if not TOKEN:
    raise RuntimeError("TOKEN not found in environment variables")

bot.run(TOKEN)
#just a prototype
