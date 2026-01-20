import discord
from discord.ext import commands
from discord import option
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(intents=intents)

db = sqlite3.connect("queue.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT,
    user_id TEXT,
    message TEXT,
    send_date TEXT,
    status TEXT
)
""")
db.commit()
cursor.execute("""
create table if not exists guild_settings (
    guild_id text primary key,
    channel_id text)
""")
db.commit()

@bot.slash_command(
        name="setlaguchannel",
        description="set channel untuk fitur 1 hari 1 lagu"
)

@commands.has_permissions(administrator=True)
async def setlaguchannel(ctx, channel: discord.TextChannel):

    cursor.execute("""
        insert into guild_settings  (guild_id, channel_id)
        values (?,?)
        on conflict(guild_id)
        do update set channel_id = excluded.channel_id
    """,(
      str(ctx.guild.id),
    str(channel.id)
    ))
    db.commit()
    
    await ctx.respond(
    f"channel 1 hari 1 lagu diset ke {channel.mention}",
    ephemeral=True
    )

@bot.slash_command(name="babuchat", description="1 hari 1 lagu")
@option("link", description="umtuk 1 hari satu lagu")
async def babuchat(ctx, link: str):
    if not link.startswith("https://open.spotify.com/"):
        await ctx.respond(
            "kirim link spotipy aja yh dik! **link Spotify**\n"
            "Contoh:\n"
            "https://open.spotify.com/track/xxxx",
            ephemeral=True
        )
        return

    # ambil tanggal terakhir di antrian
    cursor.execute("""
        SELECT send_date FROM queue
        WHERE status='pending'
        ORDER BY send_date DESC
        LIMIT 1
    """)
    last = cursor.fetchone()

    if last:
        send_date = datetime.strptime(last[0], "%Y-%m-%d") + timedelta(days=1)
    else:
        send_date = datetime.today()

    cursor.execute("""
        INSERT INTO queue (guild_id, user_id, message, send_date, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, 
        (str(ctx.guild.id),
        str(ctx.author.id), 
        link, 
        send_date.strftime("%Y-%m-%d")
    ))
    db.commit()

    await ctx.respond(
        f"link udh masuk antrian yh adik\n"
        f"dijadwalkan: **{send_date.strftime('%d %B %Y')}**",
        ephemeral=True
    )

async def kirim_pesan_harian():
    today = datetime.today().strftime("%Y-%m-%d")
    
    for guild in bot.guilds: 

        cursor.execute("""
            SELECT channel_id FROM guild_settings
            WHERE guild_id = ?
        """, (str(guild.id),))

        row_channel = cursor.fetchone()
        if not row_channel:
            continue   

        channel = bot.get_channel(int(row_channel[0]))


        cursor.execute("""
                        SELECT id, user_id, message FROM queue
                       WHERE guild_id = ? AND send_date= ? AND status='pending' 
                       LIMIT 1
            """, (
                str(guild.id),
                today))
        
        row = cursor.fetchone()
        if not row:
            continue

    queue_id, user_id, message = row
    user = await bot.fetch_user(int(user_id))
    
    await channel.send(
        content=(
            "@everyone\n\n"
            "**1 hari 1 lagu**\n\n"
            f"{message}\n\n"
            f"req by {user.mention}"
        ),
        allowed_mentions=discord.AllowedMentions(everyone=True)
    )

    cursor.execute(
        "UPDATE queue SET status='sent' WHERE id=?",
        (queue_id,)
    )
    db.commit()

scheduler = AsyncIOScheduler()
scheduler.add_job(
    kirim_pesan_harian,
    "cron",
    hour=21,
    minute=00
)
from datetime import datetime

@bot.slash_command(name="hapuslagu", description="hapus link dari antri terakhir")
async def hapuslagu(ctx, link:str):

    cursor.execute("""
        SELECT id, send_date FROM queue
        WHERE user_id = ?
        AND status = 'pending'
        ORDER BY send_date DESC
        LIMIT 1
    """, (str(ctx.author.id),))

    row = cursor.fetchone()

    if not row:
        await ctx.respond(
            "lu gpny pesan yg bs di hps",
            ephemeral=True
        )
        return

    queue_id, send_date = row

    cursor.execute(
        "DELETE FROM queue WHERE id = ?",
        (queue_id,)
    )
    db.commit()

    await ctx.respond(
        f"udh di hps\n",
        ephemeral=True
    )

@bot.slash_command(name="hapussemua", description="Hapus semua antrian pending")
async def hapussemua(ctx):

    cursor.execute(
        "DELETE FROM queue WHERE status = 'pending'"
    )
    db.commit()

    await ctx.respond(
        "syudah di apus semuanyah",
        ephemeral=True
    )

@bot.event
async def on_ready():
    print("Bot", {bot.user},"online")
    print("Waktu server:", datetime.now())
    if not scheduler.running:
        scheduler.start()
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    bot.run(token)

