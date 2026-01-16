# =========================
# Iprime-Bot FINAL FIX
# IG / TT / FB / YT
# Cookies ENV + COS CDN
# Modal + Plugin System
# =========================

import os
import asyncio
import uuid
import threading
import shutil
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib

import discord
from discord import app_commands
from qcloud_cos import CosConfig, CosS3Client

# ========= ENV =========
TOKEN = os.getenv("DISCORD_TOKEN")
SECRET_ID = os.getenv("TENCENT_SECRET_ID")
SECRET_KEY = os.getenv("TENCENT_SECRET_KEY")
IG_COOKIES = os.getenv("IG_COOKIES")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN missing")
if not SECRET_ID or not SECRET_KEY:
    raise RuntimeError("Tencent COS ENV missing")
if not IG_COOKIES:
    raise RuntimeError("IG_COOKIES ENV missing")

# ========= CHECK FFMPEG =========
if not shutil.which("ffmpeg"):
    raise RuntimeError("ffmpeg not found")

# ========= WRITE IG COOKIES (NETSCAPE FIX) =========
with open("ig_cookies.txt", "w") as f:
    f.write("# Netscape HTTP Cookie File\n")
    f.write("# https://curl.haxx.se/rfc/cookie_spec.html\n")
    f.write("# This is a generated file! Do not edit.\n\n")
    f.write(IG_COOKIES.strip() + "\n")

# ========= HTTP DUMMY (KOYEB KEEPALIVE) =========
def run_http():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Iprime Bot Running")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()

threading.Thread(target=run_http, daemon=True).start()

# ========= BASIC =========
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ========= PLATFORM DETECT =========
def detect_platform(url: str):
    u = url.lower()
    if "instagram" in u: return "Instagram"
    if "tiktok" in u: return "TikTok"
    if "facebook" in u or "fb.watch" in u: return "Facebook"
    if "youtube" in u or "youtu.be" in u: return "YouTube"
    return "Video"

# ========= COS CONFIG =========
REGION = "ap-singapore"
BUCKET = "ip-1339522405"
DOMAIN = "https://iprimeteam.my.id"

def cos_client():
    return CosS3Client(CosConfig(
        Region=REGION,
        SecretId=SECRET_ID,
        SecretKey=SECRET_KEY,
        Scheme="https"
    ))

def upload_to_cos(local, name):
    key = f"videos/{name}"
    cos_client().upload_file(
        Bucket=BUCKET,
        LocalFilePath=local,
        Key=key,
        ContentType="video/mp4",
        ContentDisposition="inline"
    )
    return f"{DOMAIN}/{key}"

# ========= YTDLP (ANTI LIMIT FIX) =========
async def download_video(url, out):
    cmd = [
        "yt-dlp",
        "--cookies", "ig_cookies.txt",
        "--sleep-interval", "2",
        "--max-sleep-interval", "5",
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", out,
        url
    ]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.communicate()

# ========= BUTTON VIEW (FIXED) =========
class VidButtons(discord.ui.View):
    def __init__(self, video_url=None):
        super().__init__(timeout=180)
        if video_url:
            self.add_item(discord.ui.Button(
                label="▶️ Go to Video",
                url=video_url,
                style=discord.ButtonStyle.link
            ))
        self.add_item(discord.ui.Button(
            label="❤️ Donasi",
            url="https://saweria.co/Indoprime",
            style=discord.ButtonStyle.link
        ))

# ========= MODAL =========
class DownloadModal(discord.ui.Modal, title="Video Downloader"):
    url = discord.ui.TextInput(label="Video URL", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        uid = uuid.uuid4().hex[:8]
        path = f"{DOWNLOAD_DIR}/{uid}.mp4"
        platform = detect_platform(self.url.value)

        try:
            await download_video(self.url.value, path)

            if not os.path.exists(path):
                await interaction.followup.send(
                    f"❌ {platform} gagal diambil (login / limit).",
                    ephemeral=True
                )
                return

            size = os.path.getsize(path) / (1024 * 1024)

            # Discord upload kecil
            if size <= 25:
                await interaction.followup.send(
                    file=discord.File(path),
                    view=VidButtons()
                )
            # Upload ke COS
            else:
                link = upload_to_cos(path, f"{uid}.mp4")
                await interaction.followup.send(
                    content=link,
                    view=VidButtons(link)
                )

        finally:
            if os.path.exists(path):
                os.remove(path)

# ========= SLASH COMMAND =========
@tree.command(name="download", description="IG / TT / FB / YT Downloader")
async def download(interaction: discord.Interaction):
    await interaction.response.send_modal(DownloadModal())

# ========= PLUGIN LOADER =========
def load_plugins():
    if not os.path.isdir("plugins"):
        return
    for file in os.listdir("plugins"):
        if file.endswith(".py") and not file.startswith("_"):
            mod = importlib.import_module(f"plugins.{file[:-3]}")
            if hasattr(mod, "setup"):
                mod.setup(tree)
                print(f"🔌 Plugin loaded: {file}")

@client.event
async def on_ready():
    load_plugins()
    await tree.sync()
    print(f"✅ Bot online sebagai {client.user}")

client.run(TOKEN)
