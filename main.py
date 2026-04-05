import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ==========================================
# --- 1. הגדרות, מזהים וקבועים ---
# ==========================================

TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_USERNAME = "datykvuktf"

# ערוצים (Channels)
EVENT_CHANNEL_ID = 1380774477020795003
MINIGAMES_CHANNEL_ID = 1483890075212447814
DROP_CHANNEL_ID = 1400927271275073716
LEVEL_UP_CHANNEL_ID = 1381684732642984077 
LEADERBOARD_CHANNEL_ID = 1479489007279935581 # ערוץ טבלת עושר
UPDATES_CHANNEL_ID = 1380774477020795003 # ערוץ עדכונים
BOOST_THANKS_CHANNEL_ID = 1391713777904517120 # ערוץ תודה על בוסט

# רולים (Roles)
HELP_ROLE_ID = 1413784216478416958
BIRTHDAY_ROLE_ID = 1483864049190961324
DROP_ROLE_ID = 1400927981030998146
SPIDER_CHAMPION_ROLE_ID = 1484146329033642005

# רולי מובילים (Leaderboard Roles)
TOP_ROLES = {
    1: 1479468224289706114, # מקום ראשון
    2: 1479468396553703425, # מקום שני
    3: 1479468543836950750  # מקום שלישי
}

# רולים לפי רצף כניסות (Daily Streak Roles)
STREAK_ROLES = {
    10: 1484089551365476362, 
    25: 1484089852910768138, 
    50: 1484089857121714186, 
    75: 1484090111527489567, 
    100: 1484090115847618694
}

# רולים למכירה בחנות
SHOP_ROLES_NEW = [  # 15 רולים חדשים
    1486304012817924218,
    1486304418621292674,
    1486304778916200448,
    1486304998240292995,
    1486305310426660945,
    1486305694180446309,
    1486305939031326802,
    1486306163921391698,
    1486306360806342676,
    1486306662519148615,
    1486306866651987989,
    1486307117517242439,
    1486307407456895077,
    1452256500637630526,
    1452260424631451770,
]

# מחירים
SHOP_ROLE_PRICE_NEW = 15000  # מחיר הרולים החדשים

# נדירות לביצים
TIERS = [
    {"name": "🟢 נדיר", "color": 0x2ecc71, "chance": 80, "icon": "🟢"},
    {"name": "🔵 נדיר במיוחד", "color": 0x3498db, "chance": 60, "icon": "🔵"},
    {"name": "🟣 אדיר", "color": 0x9b59b6, "chance": 40, "icon": "🟣"},
    {"name": "🟠 מדהים", "color": 0xe67e22, "chance": 25, "icon": "🟠"},
    {"name": "🔴 אגדי", "color": 0xe74c3c, "chance": 10, "icon": "🔴"},
    {"name": "🕷️ ספיידר", "color": 0x1a1a1a, "chance": 1, "icon": "🕷️"}  # 1% סיכוי!
]

# רולים OP ל-Spider tier
SPIDER_ROLES = [
    1484134768559001650,
    1484135058146197505,
    1484135675094896650,
    1484136144252960908,
    1484136354496512000,
]

DATA_FILE = 'bot_data.json'
PREMIUM_PASS_PRICE = 50000
leaderboard_msg_id = None

# מערכת בוסטים
BOOST_REWARDS = {
    1: {"name": "🔮 Pro", "eggs": 7, "xp": 10000, "premium": False},
    2: {"name": "💎 Elite", "eggs": 12, "xp": 20000, "premium": True},
    3: {"name": "🕷️ Spider", "eggs": 15, "xp": 30000, "premium": True},
}

# ==========================================
# --- 2. ניהול נתונים ---
# ==========================================

def load_data():
    if not os.path.exists(DATA_FILE): 
        return {"users": {}, "birthdays": {}}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f: 
            return json.load(f)
    except:
        return {"users": {}, "birthdays": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: 
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(data, u_id):
    u_id = str(u_id)
    if u_id not in data["users"]:
        data["users"][u_id] = {}
    u = data["users"][u_id]
    defaults = {
        "money": 0, "eggs": 0, "xp": 0, "level": 1, 
        "has_premium": False, "streak": 0, "last_daily": "", 
        "daily_tasks": [], "task_progress": {}, 
        "last_task_update": "", "tasks_claimed": [],
        "boosts": 0, "last_boost_month": "", "boost_rewards_claimed": False
    }
    for key, value in defaults.items():
        u.setdefault(key, value)
    return u

def generate_tasks():
    possible = [
        {"id": "vc", "desc": "תהיה {n} דקות בשיחה קולית", "goal": random.randint(15, 60)},
        {"id": "msg", "desc": "שלח {n} הודעות בשרת", "goal": random.randint(20, 100)},
        {"id": "reply", "desc": "הגב ל-{n} הודעות של אחרים", "goal": random.randint(3, 8)},
        {"id": "minigame", "desc": "הרוויח {n} מטבעות ממיני-גיימס", "goal": 500}
    ]
    selected = random.sample(possible, 3)
    for t in selected:
        t["desc"] = t["desc"].format(n=t["goal"])
    return selected

# ==========================================
# --- 3. לוגיקת XP ורמות ---
# ==========================================

def get_reward_for_level(level):
    if level == 100: return "🕷️ רול SPIDER CHAMPION!"
    if level <= 20: return f"💰 {level*100} מטבעות + 🥚 ביצה"
    return f"💰 {level*150} מטבעות"

async def add_xp(member, amount, data=None):
    external_data = True
    if data is None:
        data = load_data()
        external_data = False
    
    u = get_user(data, member.id)
    if u.get("has_premium"): 
        amount *= 2
    
    u["xp"] += amount
    leveled_up = False
    
    while u["xp"] >= (u["level"] * 500):
        u["xp"] -= (u["level"] * 500)
        u["level"] += 1
        leveled_up = True
        
        # פרסים
        if u["level"] <= 20:
            u["money"] += (u["level"] * 100)
            u["eggs"] += 1
        else:
            u["money"] += (u["level"] * 150)
            
        ch = bot.get_channel(LEVEL_UP_CHANNEL_ID)
        if ch:
            reward = get_reward_for_level(u["level"])
            emb = discord.Embed(
                title="🆙 עליית רמה!",
                color=0xffd700,
                timestamp=datetime.now()
            )
            emb.description = f"כל הכבוד {member.mention}!\nהגעת לרמה **{u['level']}**\n**פרס:** {reward}"
            emb.set_thumbnail(url=member.avatar.url if member.avatar else None)
            await ch.send(embed=emb)
            
        if u["level"] == 100:
            role = member.guild.get_role(SPIDER_CHAMPION_ROLE_ID)
            if role: await member.add_roles(role)
            
    if not external_data or leveled_up:
        save_data(data)

# ==========================================
# --- 4. מערכת ה-UI (ביצים) ---
# ==========================================

class EggView(View):
    def __init__(self, user_id, ctx):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.ctx = ctx
        self.tier = 0
        self.clicks = 0
        self.hatched = False  # פלאג כדי למנוע לחיצות אחרי שבקע

    def make_embed(self, status="לחץ על הכפתור למטה כדי לשדרג את הביצה!"):
        t = TIERS[self.tier]
        emb = discord.Embed(
            title="🥚 חדר הדגירה המלכותי",
            description=f"### {status}",
            color=t['color'],
            timestamp=datetime.now()
        )
        prog = "🔹" * self.clicks + "🔸" * (5 - self.clicks)
        emb.add_field(name="📈 התקדמות (5 לחיצות)", value=f"`{prog}`", inline=False)
        emb.add_field(name="⭐ רמה נוכחית", value=f"{t['icon']} **{t['name']}**", inline=True)
        emb.add_field(name="⚡ לחיצות", value=f"**{self.clicks}/5**", inline=True)
        return emb

    @discord.ui.button(label="שדרג! 🔼", style=discord.ButtonStyle.primary)
    async def upgrade_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ זו לא הביצה שלך!", ephemeral=True)
        
        # אם כבר בקע, בטל
        if self.hatched:
            return await interaction.response.send_message("❌ הביצה כבר בקעה!", ephemeral=True)
        
        self.clicks += 1
        
        # ניסיון לעלות tier
        if random.randint(1, 100) <= TIERS[self.tier]["chance"]:
            if self.tier < len(TIERS) - 1:  # אל תעלה מעבר ל-Spider
                self.tier += 1
        
        # בדוק אם השלמנו 5 לחיצות
        if self.clicks >= 5:
            self.hatched = True  # סמן שבקע כדי למנוע לחיצות נוספות
            self.stop()
            data = load_data()
            u = get_user(data, self.user_id)
            
            # חישוב הפרס לפי tier
            if self.tier == 5:  # Spider!
                money_prize = 50000
                extra_text = "\n🕷️ **וואו! ספיידר שחור נדיר מאוד!**"
            else:
                money_prize = (self.tier + 1) * 2000
                extra_text = ""
            
            u["money"] += money_prize
            
            # רולים OP לSpider
            if self.tier == 5:
                r_id = random.choice(SPIDER_ROLES)
                role = self.ctx.guild.get_role(r_id)
                if role:
                    await self.ctx.author.add_roles(role)
                    extra_text += f"\n🎭 **רול OP: {role.name}!**"
            else:
                # בדוק אם יש בונוס רולים
                roll = random.randint(1, 100)
                if self.tier == 4:  # אגדי
                    if roll <= 20:
                        u["has_premium"] = True
                        extra_text += "\n💎 **וואו! זכית ב-VIP Premium לצמיתות!**"
                    elif roll <= 50:
                        r_id = random.choice(SHOP_ROLES_NEW)
                        role = self.ctx.guild.get_role(r_id)
                        if role:
                            await self.ctx.author.add_roles(role)
                            extra_text += f"\n🎭 **זכית ברול נדיר מהחנות: {role.name}!**"
                elif self.tier >= 2 and roll <= 15:
                    r_id = random.choice(SHOP_ROLES_NEW)
                    role = self.ctx.guild.get_role(r_id)
                    if role:
                        await self.ctx.author.add_roles(role)
                        extra_text += f"\n🎭 **בונוס: זכית ברול {role.name}!**"

            save_data(data)
            await interaction.response.edit_message(
                content=f"🏁 **הביצה בקעה!** זכית ב-**{money_prize}** מטבעות!{extra_text}",
                embed=self.make_embed("✅ בקע בהצלחה!"),
                view=None
            )
        else:
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

# ==========================================
# --- 5. הגדרות בוט ואירועים ---
# ==========================================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"--- {bot.user.name} מחובר ---")
    if not vc_tracker_loop.is_running(): vc_tracker_loop.start()
    if not minigame_loop.is_running(): minigame_loop.start()
    if not hourly_drop.is_running(): hourly_drop.start()
    if not leaderboard_loop.is_running(): leaderboard_loop.start()
    if not monthly_boost_check.is_running(): monthly_boost_check.start()

@bot.event
async def on_member_update(before, after):
    """כשמישהו בוסטים"""
    # בדוק אם זה בוסט חדש
    if before.premium_since is None and after.premium_since is not None:
        # מישהו בוסט למראשונה!
        data = load_data()
        u = get_user(data, after.id)
        u["boosts"] = 1
        
        # שלח תודה
        thanks_ch = bot.get_channel(BOOST_THANKS_CHANNEL_ID)
        if thanks_ch:
            emb = discord.Embed(
                title="🎉 תודה על הבוסט!",
                color=0xff73fa,
                timestamp=datetime.now()
            )
            emb.description = f"תודה רבה על הבוסט {after.mention}! 💜"
            emb.set_thumbnail(url=after.avatar.url if after.avatar else None)
            msg = await thanks_ch.send(embed=emb)
            await msg.add_reaction("❤️")
        
        # עדכון הודעות בערוץ עדכונים
        updates_ch = bot.get_channel(UPDATES_CHANNEL_ID)
        if updates_ch:
            boost_count = len(after.guild.premium_subscribers)
            emb = discord.Embed(
                title="✨ בוסט חדש!",
                color=0xff73fa,
                timestamp=datetime.now()
            )
            emb.description = f"**{after.mention}** בוסטם את השרת! 💜\n\n"
            
            # בדוק רמת בוסט לפי כמות הבוסטים הכוללת
            for boost_num in sorted(BOOST_REWARDS.keys(), reverse=True):
                if boost_count >= boost_num:
                    tier = BOOST_REWARDS[boost_num]
                    emb.description += f"📊 **רמת שרת:** {tier['name']}\n"
                    emb.description += f"🎁 **פרסים חודשיים:**\n"
                    emb.description += f"   🥚 {tier['eggs']} ביצים\n"
                    emb.description += f"   ⭐ {tier['xp']} XP\n"
                    if tier['premium']:
                        emb.description += f"   💎 Premium Pass\n"
                    break
            
            emb.set_thumbnail(url=after.guild.icon.url if after.guild.icon else None)
            await updates_ch.send(embed=emb)
        
        save_data(data)

@tasks.loop(hours=1)
async def monthly_boost_check():
    """בדוק מדי חודש אם צריך לחלק פרסי בוסט - רץ בחצות בדיוק"""
    # רק בחצות (00:00) ובתחילת החודש (היום הראשון)
    now = datetime.now()
    if now.hour != 0 or now.day != 1:
        return
    
    data = load_data()
    
    for guild in bot.guilds:
        boost_count = len(guild.premium_subscribers)
        
        if boost_count == 0:
            continue
        
        # בדוק רמת בוסט
        tier_num = 0
        for boost_num in sorted(BOOST_REWARDS.keys(), reverse=True):
            if boost_count >= boost_num:
                tier_num = boost_num
                break
        
        if tier_num == 0:
            continue
        
        tier = BOOST_REWARDS[tier_num]
        
        # חלק פרסים לכל בוסטרים
        for booster in guild.premium_subscribers:
            u = get_user(data, booster.id)
            
            # בדוק אם כבר קיבל הודעות החודש
            current_month = datetime.now().strftime("%Y-%m")
            if u.get("last_boost_month") == current_month and u.get("boost_rewards_claimed"):
                continue
            
            # תן פרסים
            u["eggs"] += tier["eggs"]
            u["xp"] += tier["xp"]
            if tier["premium"]:
                u["has_premium"] = True
            
            u["last_boost_month"] = current_month
            u["boost_rewards_claimed"] = True
            
            # שלח הודעה לבוסטר
            try:
                emb = discord.Embed(
                    title="🎁 פרסי בוסט חודשיים!",
                    color=0xff73fa,
                    timestamp=datetime.now()
                )
                emb.description = f"תודה על בוסט השרת! קיבלת את הפרסים החודשיים:\n\n"
                emb.add_field(name="🥚 ביצים", value=f"+{tier['eggs']}", inline=True)
                emb.add_field(name="⭐ XP", value=f"+{tier['xp']}", inline=True)
                if tier['premium']:
                    emb.add_field(name="💎 Premium", value="✅ הופעל", inline=True)
                
                await booster.send(embed=emb)
            except:
                pass
        
        # הודעה בערוץ עדכונים
        updates_ch = bot.get_channel(UPDATES_CHANNEL_ID)
        if updates_ch:
            emb = discord.Embed(
                title="📊 עדכון בוסטים חודשי",
                color=0xff73fa,
                timestamp=datetime.now()
            )
            emb.description = f"**{boost_count}** בוסטרים קיבלו את הפרסים החודשיים!\n\n"
            emb.description += f"📋 **רמה:** {tier['name']}\n"
            emb.description += f"🎁 **כל בוסטר קיבל:**\n"
            emb.description += f"   🥚 {tier['eggs']} ביצים\n"
            emb.description += f"   ⭐ {tier['xp']} XP\n"
            if tier['premium']:
                emb.description += f"   💎 Premium Pass\n"
            
            await updates_ch.send(embed=emb)
    
    save_data(data)

@bot.event
async def on_message(message):
    if message.author.bot: return
    data = load_data()
    u = get_user(data, message.author.id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if u["last_task_update"] != today:
        u["daily_tasks"] = generate_tasks()
        u["task_progress"] = {t["id"]: 0 for t in u["daily_tasks"]}
        u["tasks_claimed"] = []
        u["last_task_update"] = today
        
    # עדכון משימות לפי התוכן
    if any(t['id'] == 'msg' for t in u["daily_tasks"]):
        u["task_progress"]["msg"] = u["task_progress"].get("msg", 0) + 1
    
    if message.reference and any(t['id'] == 'reply' for t in u["daily_tasks"]):
        u["task_progress"]["reply"] = u["task_progress"].get("reply", 0) + 1
        
    save_data(data)
    await bot.process_commands(message)

# ==========================================
# --- 6. פקודות משתמש ---
# ==========================================

@bot.command()
async def balance(ctx):
    u = get_user(load_data(), ctx.author.id)
    emb = discord.Embed(
        title=f"💰 חשבון - {ctx.author.name}",
        color=0x2ecc71,
        timestamp=datetime.now()
    )
    emb.add_field(name="💵 כסף", value=f"`{u['money']:,}` מטבעות", inline=True)
    emb.add_field(name="🥚 ביצים", value=f"`{u['eggs']}` ביצים", inline=True)
    emb.add_field(name="📊 רמה", value=f"`Lv. {u['level']}`", inline=True)
    emb.add_field(name="⭐ XP", value=f"`{u['xp']}/{u['level'] * 500}`", inline=True)
    emb.add_field(name="🔥 רצף יומי", value=f"`{u['streak']}` ימים", inline=True)
    if u.get("has_premium"):
        emb.add_field(name="💎 סטטוס", value="**VIP Premium** ✨", inline=True)
    emb.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
    await ctx.send(embed=emb)

@bot.command()
async def daily(ctx):
    data = load_data(); u = get_user(data, ctx.author.id)
    today = datetime.now(); today_str = today.strftime("%Y-%m-%d")
    if u["last_daily"] == today_str:
        emb = discord.Embed(title="❌ כבר לקחת היום!", color=0xe74c3c)
        emb.description = f"חוזרים מחר! רצפך הנוכחי: **{u['streak']}**"
        return await ctx.send(embed=emb)
    
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    u["streak"] = u["streak"] + 1 if u["last_daily"] == yesterday else 1
    u["last_daily"] = today_str
    
    prize = 500 + (u["streak"] * 100)
    u["money"] += prize
    if u["streak"] in STREAK_ROLES:
        role = ctx.guild.get_role(STREAK_ROLES[u["streak"]])
        if role: await ctx.author.add_roles(role)
    save_data(data)
    
    emb = discord.Embed(
        title="✅ פרס יומי!",
        color=0x2ecc71,
        timestamp=datetime.now()
    )
    emb.description = f"קיבלת **{prize}** מטבעות! 💰"
    emb.add_field(name="🔥 רצף", value=f"**{u['streak']}** ימים ברציפות!", inline=False)
    if u["streak"] in [10, 25, 50, 75, 100]:
        emb.add_field(name="🎉 בונוס!", value=f"זכית ברול של {u['streak']} ימים!", inline=False)
    await ctx.send(embed=emb)

@bot.command()
async def mission(ctx):
    data = load_data(); u = get_user(data, ctx.author.id)
    if not u["daily_tasks"]:
        emb = discord.Embed(title="❌ אין משימות זמינות", color=0xe74c3c)
        return await ctx.send(embed=emb)
    
    emb = discord.Embed(
        title="📋 משימות יומיות",
        color=0x3498db,
        timestamp=datetime.now()
    )
    for i, t in enumerate(u["daily_tasks"], 1):
        prog = u["task_progress"].get(t["id"], 0)
        status = "✅" if prog >= t["goal"] else f"⏳ {prog}/{t['goal']}"
        emb.add_field(name=f"{i}. {t['desc']}", value=status, inline=False)
    
    view = View()
    btn = Button(label="אסוף פרסים 🎁", style=discord.ButtonStyle.success)
    async def claim_cb(interaction):
        if interaction.user.id != ctx.author.id:
            return await interaction.response.send_message("❌ זו לא המשימה שלך!", ephemeral=True)
        d = load_data(); user = get_user(d, interaction.user.id)
        count = 0
        for task in user["daily_tasks"]:
            if user["task_progress"].get(task["id"], 0) >= task["goal"]:
                if task["id"] not in user["tasks_claimed"]:
                    user["money"] += 1500; user["tasks_claimed"].append(task["id"]); count += 1
        save_data(d)
        
        if count > 0:
            resp_emb = discord.Embed(title="🎁 פרסים!", color=0x2ecc71)
            resp_emb.description = f"אספת **{count*1500}** מטבעות!"
        else:
            resp_emb = discord.Embed(title="❌ אין פרסים לאיסוף", color=0xe74c3c)
        
        await interaction.response.send_message(embed=resp_emb, ephemeral=True)
    btn.callback = claim_cb; view.add_item(btn)
    await ctx.send(embed=emb, view=view)

@bot.command()
async def shop(ctx):
    emb = discord.Embed(
        title="🛒 Spider Shop",
        color=0xe74c3c,
        timestamp=datetime.now()
    )
    
    emb.description = "🌙 **רולים חדשים!** יקרים יותר 💎\n\n**מחיר: 15,000 מטבעות ליחידה**"
    
    emb.add_field(
        name="💎 Premium Pass",
        value=f"`{PREMIUM_PASS_PRICE:,}` מטבעות\n⚡ דו-חזק XP",
        inline=False
    )
    emb.add_field(name="",value="", inline=False)
    
    for i, r_id in enumerate(SHOP_ROLES_NEW, 1):
        role = ctx.guild.get_role(r_id)
        emb.add_field(
            name=f"#{i} {role.name if role else 'רול'}",
            value="`15,000` מטבעות",
            inline=True
        )
    
    emb.set_footer(text="השתמש ב: !buy premium או !buy [מספר]")
    await ctx.send(embed=emb)

@bot.command()
async def buy(ctx, item: str):
    data = load_data()
    u = get_user(data, ctx.author.id)
    
    if item == "premium":
        if u["money"] >= PREMIUM_PASS_PRICE:
            u["money"] -= PREMIUM_PASS_PRICE
            u["has_premium"] = True
            save_data(data)
            emb = discord.Embed(
                title="💎 Premium Pass!",
                color=0x9b59b6,
                description="תתחדש על ה-Premium! כל XP יהיה בדו-חזק!"
            )
            await ctx.send(embed=emb)
        else:
            emb = discord.Embed(title="❌ כסף לא מספיק", color=0xe74c3c)
            emb.description = f"יש לך: `{u['money']}` מטבעות\nצריך: `{PREMIUM_PASS_PRICE}` מטבעות"
            await ctx.send(embed=emb)
    elif item.isdigit():
        idx = int(item) - 1
        if 0 <= idx < len(SHOP_ROLES_NEW) and u["money"] >= SHOP_ROLE_PRICE_NEW:
            role = ctx.guild.get_role(SHOP_ROLES_NEW[idx])
            if role:
                u["money"] -= SHOP_ROLE_PRICE_NEW
                await ctx.author.add_roles(role)
                save_data(data)
                
                emb = discord.Embed(title="✅ קנייה הצליחה!", color=0x2ecc71)
                emb.description = f"קנית את הרול **{role.name}**!\n\n💰 שילמת: `{SHOP_ROLE_PRICE_NEW:,}` מטבעות"
                await ctx.send(embed=emb)
        else:
            emb = discord.Embed(title="❌ שגיאה בקנייה", color=0xe74c3c)
            needed = SHOP_ROLE_PRICE_NEW - u["money"]
            if needed > 0:
                emb.description = f"חוסר במזומן!\n\nיש לך: `{u['money']}` מטבעות\nצריך: `{SHOP_ROLE_PRICE_NEW}` מטבעות\nחסר: `{needed}` מטבעות"
            else:
                emb.description = "פריט לא נמצא או מספר לא תקין"
            await ctx.send(embed=emb)

@bot.command(name="open")
async def open_egg_cmd(ctx):
    data = load_data(); u = get_user(data, ctx.author.id)
    if u["eggs"] <= 0:
        emb = discord.Embed(title="❌ אין לך ביצים!", color=0xe74c3c)
        return await ctx.send(embed=emb)
    u["eggs"] -= 1; save_data(data)
    view = EggView(ctx.author.id, ctx)
    await ctx.send(embed=view.make_embed(), view=view)

# ==========================================
# --- 7. לופים (החלק החדש והחשוב) ---
# ==========================================

@tasks.loop(minutes=1)
async def leaderboard_loop():
    global leaderboard_msg_id
    ch = bot.get_channel(LEADERBOARD_CHANNEL_ID)
    if not ch: return
    
    data = load_data()
    # מיון המשתמשים לפי כמות כסף (5 ראשונים)
    top_users = sorted(data["users"].items(), key=lambda x: x[1].get("money", 0), reverse=True)[:5]
    
    emb = discord.Embed(
        title="💰 טבלת עשירי הספיידר",
        color=0xf1c40f,
        timestamp=datetime.now()
    )
    description = "🏆 המובילים בשרת:\n\n"
    
    guild = ch.guild
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for i, (u_id, u_data) in enumerate(top_users):
        member = guild.get_member(int(u_id))
        name = member.mention if member else f"משתמש ({u_id})"
        money = u_data.get('money', 0)
        description += f"{medals[i]} **#{i+1}** {name} — `{money:,}` 💰\n"
        
        # ניהול רולים (מקומות 1-3)
        if i < 3:
            role = guild.get_role(TOP_ROLES[i+1])
            if role:
                # הסרה ממי שכבר לא שם
                for m in role.members:
                    if m.id != int(u_id): await m.remove_roles(role)
                # הוספה למי שזכה
                if member and role not in member.roles: await member.add_roles(role)

    emb.description = description
    emb.set_footer(text="🔄 מתעדכן אוטומטית כל דקה")

    try:
        if leaderboard_msg_id:
            msg = await ch.fetch_message(leaderboard_msg_id)
            await msg.edit(embed=emb)
        else:
            async for m in ch.history(limit=5):
                if m.author == bot.user:
                    leaderboard_msg_id = m.id
                    await m.edit(embed=emb)
                    return
            new_msg = await ch.send(embed=emb)
            leaderboard_msg_id = new_msg.id
    except:
        new_msg = await ch.send(embed=emb)
        leaderboard_msg_id = new_msg.id

@tasks.loop(minutes=30)
async def minigame_loop():
    ch = bot.get_channel(MINIGAMES_CHANNEL_ID)
    if not ch: return
    
    # בחירת משחק
    g = random.choice(['math', 'fast'])
    
    if g == 'math':
        a, b = random.randint(10, 50), random.randint(10, 50)
        ans = str(a + b)
        emb = discord.Embed(
            title="🧮 מיני-גיים מתמטיקה",
            color=0x3498db,
            timestamp=datetime.now()
        )
        emb.description = f"### כמה זה `{a} + {b}`?\n\nיש לך 60 שניות!"
        emb.set_footer(text="⏱️ הלחצן מתחיל...")
    else:
        ans = "ספיידר"
        emb = discord.Embed(
            title="⌨️ מיני-גיים מהירות",
            color=0xe67e22,
            timestamp=datetime.now()
        )
        emb.description = f"### כתוב הכי מהר: **{ans}**\n\nיש לך 60 שניות!"
        emb.set_footer(text="⏱️ הלחצן מתחיל...")
    
    msg = await ch.send(embed=emb)
    
    try:
        message = await bot.wait_for(
            'message',
            check=lambda m: m.channel == ch and m.content == ans and not m.author.bot,
            timeout=60
        )
        d = load_data()
        user = get_user(d, message.author.id)
        user["money"] += 400
        
        # עדכון משימת מיני-גיימס
        if any(t['id'] == 'minigame' for t in user.get("daily_tasks", [])):
            user["task_progress"]["minigame"] = user["task_progress"].get("minigame", 0) + 400
        
        save_data(d)
        await add_xp(message.author, 150)
        
        # הודעת ניצחון
        win_emb = discord.Embed(
            title="🏆 יש מנצח!",
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        win_emb.description = f"{message.author.mention} זכה ב-**400 מטבעות** ו-**150 XP**!\n\n✨ כל הכבוד!"
        win_emb.set_thumbnail(url=message.author.avatar.url if message.author.avatar else None)
        await ch.send(embed=win_emb)
        
    except asyncio.TimeoutError:
        # הודעת סיום זמן - **זה החלק החדש שביקשת!**
        timeout_emb = discord.Embed(
            title="⏰ זמן עבר!",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        timeout_emb.description = f"לא הצליחו לעשות את זה בזמן...\n**התשובה הנכונה הייתה:** `{ans}`\n\nמשחק הבא תוך 30 דקות!"
        timeout_emb.set_footer(text="💭 ניסו שוב בהזדמנות הבאה")
        await ch.send(embed=timeout_emb)

@tasks.loop(minutes=60)
async def hourly_drop():
    ch = bot.get_channel(DROP_CHANNEL_ID)
    if not ch: return
    
    view = View(timeout=60)
    btn = Button(label="קח! 🎁", style=discord.ButtonStyle.green)
    
    drop_emb = discord.Embed(
        title="🎁 דרופ הופיע!",
        color=0x2ecc71,
        timestamp=datetime.now()
    )
    drop_emb.description = "### הראשון שילחץ על הכפתור זוכה!\n💰 1,000 מטבעות בהמתנה"
    
    async def cb(interaction):
        d = load_data()
        u = get_user(d, interaction.user.id)
        u["money"] += 1000
        save_data(d)
        btn.disabled = True
        btn.label = "✅ נלקח!"
        
        # הודעה שהדרופ נלקח
        taken_emb = discord.Embed(
            title="🎉 דרופ נלקח!",
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        taken_emb.description = f"{interaction.user.mention} תפס את הדרופ!\n**קיבל:** 1,000 מטבעות 💰"
        taken_emb.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        await interaction.response.edit_message(content="", embed=taken_emb, view=view)
    
    btn.callback = cb
    view.add_item(btn)
    
    await ch.send(
        content=f"<@&{DROP_ROLE_ID}>",
        embed=drop_emb,
        view=view
    )
    
    # המתן 60 שניות, ואם אף אחד לא לחץ - שלח הודעה
    await asyncio.sleep(60)
    
    # בדוק אם הכפתור היה פעיל עדיין
    if not btn.disabled:
        timeout_emb = discord.Embed(
            title="⏰ הדרופ עבר!",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        timeout_emb.description = "אף אחד לא הצליח לתפוס את הדרופ בזמן... 😢\n\nדרופ הבא תוך שעה!"
        timeout_emb.set_footer(text="📢 היה קול בערוץ, אבל זה לא מספיק מהר")
        
        # נסה לשלוח את ההודעה (אם הערוץ עדיין קיים)
        try:
            await ch.send(embed=timeout_emb)
        except:
            pass

@tasks.loop(minutes=1)
async def vc_tracker_loop():
    data = load_data()
    for g in bot.guilds:
        for vc in g.voice_channels:
            for m in vc.members:
                if not m.bot:
                    await add_xp(m, 25, data=data)
                    u = get_user(data, m.id)
                    if any(t['id'] == 'vc' for t in u.get("daily_tasks", [])):
                        u["task_progress"]["vc"] = u["task_progress"].get("vc", 0) + 1
    save_data(data)

# ==========================================
# --- 8. פקודות ניהול ---
# ==========================================

@bot.command()
async def egg(ctx, member: discord.Member, amount: int):
    if ctx.author.name != ADMIN_USERNAME: return
    data = load_data(); u = get_user(data, member.id)
    u["eggs"] += amount; save_data(data)
    emb = discord.Embed(
        title="✅ ביצים נוספו",
        color=0x2ecc71,
        description=f"נתת {amount} 🥚 ל-{member.mention}"
    )
    await ctx.send(embed=emb)

@bot.command()
async def admin_xp(ctx, member: discord.Member, amount: int):
    if ctx.author.name == ADMIN_USERNAME:
        await add_xp(member, amount)
        emb = discord.Embed(
            title="✅ XP נוסף",
            color=0x2ecc71,
            description=f"הוספת {amount} XP ל-{member.mention}"
        )
        await ctx.send(embed=emb)

bot.run(TOKEN)
