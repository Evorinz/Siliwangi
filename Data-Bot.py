import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import json
import asyncio

# Inisialisasi bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# File untuk menyimpan data pengumuman
ANNOUNCEMENTS_FILE = "announcements.json"

# Channel tujuan default
DEFAULT_CHANNEL_ID = 1354880000112726136

# Struktur data untuk menyimpan pengumuman
announcements = {"yearly": [], "once": []}


# Fungsi untuk memuat data pengumuman dari file
def load_announcements():
    try:
        with open(ANNOUNCEMENTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"yearly": [], "once": []}


# Fungsi untuk menyimpan data pengumuman ke file
def save_announcements():
    with open(ANNOUNCEMENTS_FILE, 'w') as f:
        json.dump(announcements, f, indent=4)


# Fungsi untuk memeriksa dan mengirim pengumuman
async def check_and_send_announcements():
    now = datetime.now()
    current_date = now.strftime("%m-%d")
    current_datetime = now.strftime("%m-%d %H:%M")

    channel = bot.get_channel(DEFAULT_CHANNEL_ID)
    if channel is None:
        print(f"Channel dengan ID {DEFAULT_CHANNEL_ID} tidak ditemukan!")
        return

    # Periksa pengumuman tahunan
    for announcement in announcements["yearly"]:
        if announcement["date"] == current_date:
            await channel.send(f"📣 Pengumuman Tahunan: {announcement['message']}")

    # Periksa pengumuman sekali
    to_remove = []
    for i, announcement in enumerate(announcements["once"]):
        if announcement["datetime"] == current_datetime:
            await channel.send(f"📣 Pengumuman: {announcement['message']}")
            to_remove.append(i)

    # Hapus pengumuman sekali yang sudah dikirim
    for i in sorted(to_remove, reverse=True):
        announcements["once"].pop(i)

    if to_remove:
        save_announcements()


# Event ketika bot siap
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} telah online!')

    # Muat data pengumuman
    global announcements
    announcements = load_announcements()

    # Mulai loop pengecekan pengumuman
    check_announcements.start()

    # Kirim pesan tes
    channel = bot.get_channel(DEFAULT_CHANNEL_ID)
    if channel:
        await channel.send("🤖 Bot pengingat pengumuman telah aktif dan siap digunakan!")


# Loop pengecekan pengumuman setiap menit
@tasks.loop(minutes=1)
async def check_announcements():
    await check_and_send_announcements()


# Command untuk menambah pengumuman tahunan
@bot.command(name='tambah_tahunan', help='Tambahkan pengumuman tahunan (format: MM-DD pesan)')
async def add_yearly(ctx, date: str, *, message: str):
    try:
        # Validasi format tanggal
        datetime.strptime(date, "%m-%d")
    except ValueError:
        await ctx.send("Format tanggal salah! Gunakan format MM-DD (contoh: 12-31 untuk 31 Desember)")
        return

    announcements["yearly"].append({
        "date": date,
        "message": message,
        "added_by": ctx.author.name,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    save_announcements()
    await ctx.send(f"✅ Pengumuman tahunan pada {date} berhasil ditambahkan!")


# Command untuk menambah pengumuman sekali
@bot.command(name='tambah_sekali', help='Tambahkan pengumuman sekali (format: MM-DD HH:MM pesan)')
async def add_once(ctx, date: str, time: str, *, message: str):
    try:
        # Validasi format tanggal dan waktu
        datetime.strptime(f"{date} {time}", "%m-%d %H:%M")
    except ValueError:
        await ctx.send("Format tanggal/waktu salah! Gunakan format MM-DD HH:MM (contoh: 12-31 15:00 untuk 31 Desember jam 3 sore)")
        return

    datetime_str = f"{date} {time}"
    announcements["once"].append({
        "datetime": datetime_str,
        "message": message,
        "added_by": ctx.author.name,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    save_announcements()
    await ctx.send(f"✅ Pengumuman sekali pada {datetime_str} berhasil ditambahkan!")


# Command untuk melihat daftar pengumuman
@bot.command(name='daftar_pengumuman', help='Lihat daftar pengumuman yang sudah terdaftar')
async def list_announcements(ctx):
    if not announcements["yearly"] and not announcements["once"]:
        await ctx.send("Belum ada pengumuman yang terdaftar.")
        return
    
    embed = discord.Embed(title="📋 Daftar Pengumuman", color=discord.Color.blue())
    now = datetime.now()

    if announcements["yearly"]:
        yearly_list = []
        for ann in announcements["yearly"]:
            # Hitung tanggal pengumuman tahun ini
            month, day = map(int, ann["date"].split("-"))
            next_date = datetime(now.year, month, day)
            
            # Jika sudah lewat tahun ini, hitung untuk tahun depan
            if next_date < now:
                next_date = datetime(now.year + 1, month, day)
            
            time_left = next_date - now
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            yearly_list.append(
                f"• **{ann['date']}**: {ann['message']}\n"
                f"  Akan dikirim dalam: **{days} hari {hours} jam {minutes} menit**\n"
                f"  (Ditambahkan oleh {ann['added_by']})"
            )
        
        embed.add_field(
            name="📅 Pengumuman Tahunan",
            value="\n\n".join(yearly_list),
            inline=False
        )

    if announcements["once"]:
        once_list = []
        for ann in announcements["once"]:
            # Parse tanggal dan waktu pengumuman
            datetime_str = ann["datetime"]
            month, day, hour, minute = map(int, [datetime_str[:2], datetime_str[3:5], datetime_str[6:8], datetime_str[9:]])
            announcement_time = datetime(now.year, month, day, hour, minute)
            
            time_left = announcement_time - now
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            once_list.append(
                f"• **{ann['datetime']}**: {ann['message']}\n"
                f"  Akan dikirim dalam: **{days} hari {hours} jam {minutes} menit**\n"
                f"  (Ditambahkan oleh {ann['added_by']})"
            )
        
        embed.add_field(
            name="⏰ Pengumuman Sekali",
            value="\n\n".join(once_list),
            inline=False
        )

    await ctx.send(embed=embed)


# Command untuk menghapus pengumuman
@bot.command(
    name='hapus_pengumuman',
    help='Hapus pengumuman berdasarkan indeks (gunakan !daftar_pengumuman untuk melihat indeks)'
)
async def delete_announcement(ctx, category: str, index: int):
    category = category.lower()

    if category not in ["yearly", "once"]:
        await ctx.send("Kategori tidak valid! Gunakan 'yearly' atau 'once'.")
        return

    try:
        index = int(index)
        if index < 1 or index > len(announcements[category]):
            raise ValueError

        deleted = announcements[category].pop(index - 1)
        save_announcements()
        await ctx.send(f"✅ Pengumuman '{deleted['message']}' berhasil dihapus!")
    except (ValueError, IndexError):
        await ctx.send(
            "Indeks tidak valid! Gunakan !daftar_pengumuman untuk melihat indeks yang benar."
        )


# Command untuk menguji bot
@bot.command(name='test', help='Kirim pesan test ke channel tujuan')
async def test_bot(ctx):
    channel = bot.get_channel(DEFAULT_CHANNEL_ID)
    if channel:
        await channel.send("🔧 Ini adalah pesan test dari bot!")
        await ctx.send("✅ Pesan test berhasil dikirim ke channel tujuan!")
    else:
        await ctx.send("❌ Channel tujuan tidak ditemukan!")


# Jalankan bot
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
bot.run(TOKEN)