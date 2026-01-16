# =========================
# Iprime-Bot FINAL (PRODUCTION)
# IG / TT / FB / YT
# IG = Cookies + Delay
# Others = Simple MP4
# One Message (Video + Buttons)
# Modal Safe (HP Friendly)
# Plugin System Enabled
# Koyeb / Render / Docker Safe
# =========================

import os
import asyncio
import uuid
import threading
import importlib
import shutil
from http.server import BaseHTTPRequestHandler, HTTPServer

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

# ========= FFMPEG CHECK (IG ONLY) =========
if not shutil.which("ffmpeg"):
    raise RuntimeError("ffmpeg not found (required for Instagram)")

# ========= WRITE IG COOKIES =========
with open("ig_cookies.txt", "w") as f:
    f.write("# Netscape HTTP Cookie File\n")
    f.write("# https://curl.haxx.se/rfc/cookie_spec.html\n")
    f.write("# Generated\n\n")
    f.write(IG_COOKIES.strip() + "\n")

# ========= HTTP DUMMY (KOYEB HEALTHCHECK) =========
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
    if "instagram.com" in u:
        return "instagram"
    if "tiktok.com" in u:
        return "tiktok"
    if "facebook.com" in u or "fb.watch" in u:
        return "facebook"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    return "unknown"

# ========= COS =========
REGION = "ap-singapore"
BUCKET = "ip-1339522405"
DOMAIN = "https://iprimeteam.my.id"

def cos_client():
    return CosS3Client(
        CosConfig(
            Region=REGION,
            SecretId=SECRET_ID,
            SecretKey=SECRET_KEY,
            Scheme="https"
        )
    )

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

# ========= YT-DLP =========

# --- Instagram (cookies + delay + merge) ---
async def download_instagram(url, out):
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

# --- Others (NO cookies, NO ffmpeg) ---
async def download_simple(url, out):
    cmd = [
        "yt-dlp",
        "-f", "mp4",
        "--no-playlist",
        "-o", out,
        url
    ]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.communicate()

# --- Audio ---
async def download_audio(url, out):
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--no-playlist",
        "-o", out,
        url
    ]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.communicate()

# ========= BUTTON VIEW =========
class VidVaulButtons(discord.ui.View):
    def __init__(self, source_url: str):
        super().__init__(timeout=180)
        self.source_url = source_url

        self.add_item(discord.ui.Button(
            label="Use App",
            style=discord.ButtonStyle.secondary,
            custom_id="use_app"
        ))

        self.add_item(discord.ui.Button(
            label="Go to Video",
            url=source_url,
            style=discord.ButtonStyle.link
        ))

        self.add_item(discord.ui.Button(
            label="Donasi",
            url="https://saweria.co/Indoprime",
            style=discord.ButtonStyle.link
        ))

    @discord.ui.button(
        label="Download Audio",
        style=discord.ButtonStyle.primary,
        emoji="🎵",
        row=1
    )
    async def audio(self, interaction: discord.Interaction, _):
        await interaction.response.defer(ephemeral=True)

        uid = uuid.uuid4().hex[:6]
        path = f"{DOWNLOAD_DIR}/{uid}.mp3"

        try:
            await download_audio(self.source_url, path)
            if os.path.exists(path):
                await interaction.followup.send(
                    file=discord.File(path, filename="audio.mp3"),
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Audio gagal diambil",
                    ephemeral=True
                )
        finally:
            if os.path.exists(path):
                os.remove(path)

# ========= MODAL =========
class DownloadModal(discord.ui.Modal, title="Video Downloader"):
    url = discord.ui.TextInput(
        label="Video URL",
        placeholder="Instagram / TikTok / Facebook / YouTube",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await process_video(interaction, self.url.value)

# ========= PROCESS =========
async def process_video(interaction: discord.Interaction, url: str):
    await interaction.response.defer()

    platform = detect_platform(url)
    uid = uuid.uuid4().hex[:8]
    path = f"{DOWNLOAD_DIR}/{uid}.mp4"

    try:
        if platform == "instagram":
            await download_instagram(url, path)
        else:
            await download_simple(url, path)

        if not os.path.exists(path):
            await interaction.followup.send(
                "❌ Video tidak bisa diambil (rate-limit / login)."
            )
            return

        size_mb = os.path.getsize(path) / (1024 * 1024)

        if size_mb <= 25:
            await interaction.followup.send(
                file=discord.File(path, filename="video.mp4"),
                view=VidVaulButtons(url)
            )
        else:
            link = upload_to_cos(path, f"{uid}.mp4")
            await interaction.followup.send(
                content=link,
                view=VidVaulButtons(url)
            )

    except Exception as e:
        print(e)
        await interaction.followup.send("❌ Gagal memproses video.")
    finally:
        if os.path.exists(path):
            os.remove(path)

# ========= INTERACTION (Use App Button) =========
@client.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get("custom_id") == "use_app":
            await interaction.response.send_modal(DownloadModal())

# ========= COMMAND =========
@tree.command(name="download", description="IG / TT / FB / YT Downloader")
async def download(interaction: discord.Interaction):
    await interaction.response.send_modal(DownloadModal())

# ========= PLUGIN LOADER =========
def load_plugins():
    if not os.path.isdir("plugins"):
        return
    for file in os.listdir("plugins"):
        if file.endswith(".py") and not file.startswith("_"):
            try:
                mod = importlib.import_module(f"plugins.{file[:-3]}")
                if hasattr(mod, "setup"):
                    mod.setup(client, tree)
                    print(f"🔌 Plugin loaded: {file}")
            except Exception as e:
                print(f"❌ Plugin error {file}: {e}")

# ========= READY =========
@client.event
async def on_ready():
    load_plugins()
    await tree.sync()
    print(f"✅ Bot online sebagai {client.user}")

client.run(TOKEN)
