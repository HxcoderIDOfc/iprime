# =========================
# Iprime-Bot FINAL
# VIDVAUL STYLE (IG/TT/FB/YT)
# ONE MESSAGE (VIDEO + BUTTON)
# MODE 1 MODAL (HP SAFE)
# =========================

import os
import asyncio
import uuid
import discord
from discord import app_commands
from qcloud_cos import CosConfig, CosS3Client

# ========= ENV CONFIG =========
TOKEN = os.getenv("DISCORD_TOKEN")
SECRET_ID = os.getenv("TENCENT_SECRET_ID")
SECRET_KEY = os.getenv("TENCENT_SECRET_KEY")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is required")

if not SECRET_ID or not SECRET_KEY:
    raise RuntimeError("TENCENT_SECRET_ID & TENCENT_SECRET_KEY are required")

REGION = "ap-singapore"
BUCKET = "ip-1339522405"
DOMAIN = "https://iprimeteam.my.id"

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==============================

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ========= PLATFORM DETECT =========
def detect_platform(url: str) -> str:
    u = url.lower()
    if "instagram.com" in u:
        return "Instagram"
    if "tiktok.com" in u:
        return "TikTok"
    if "facebook.com" in u or "fb.watch" in u:
        return "Facebook"
    if "youtube.com" in u or "youtu.be" in u:
        return "YouTube"
    return "Video"

# ========= COS =========
def cos_client():
    return CosS3Client(
        CosConfig(
            Region=REGION,
            SecretId=SECRET_ID,
            SecretKey=SECRET_KEY,
            Scheme="https"
        )
    )

def upload_to_cos(local_path, remote_name):
    key = f"videos/{remote_name}"
    cos_client().upload_file(
        Bucket=BUCKET,
        LocalFilePath=local_path,
        Key=key,
        ContentType="video/mp4",
        ContentDisposition="inline"
    )
    return f"{DOMAIN}/{key}"

# ========= YT-DLP =========
async def download_video(url, out_path):
    cmd = ["yt-dlp", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", out_path, url]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.communicate()

async def download_audio(url, out_path):
    cmd = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", out_path, url]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.communicate()

# ========= BUTTON VIEW =========
class VidVaulButtons(discord.ui.View):
    def __init__(self, source_url: str):
        super().__init__(timeout=180)
        self.source_url = source_url

        self.add_item(discord.ui.Button(
            label="Use App",
            url="https://discord.com/application-directory",
            style=discord.ButtonStyle.link
        ))

        self.add_item(discord.ui.Button(
            label="Go to Video",
            url=source_url,
            style=discord.ButtonStyle.link
        ))

        self.add_item(discord.ui.Button(
            label="Donasi",
            url="https://saweria.co/iprime",
            style=discord.ButtonStyle.link
        ))

    @discord.ui.button(label="Download Audio", style=discord.ButtonStyle.primary, emoji="🎵", row=1)
    async def audio(self, interaction: discord.Interaction, _):
        await interaction.response.send_message("⏳ Mengambil audio...", ephemeral=True)

        uid = uuid.uuid4().hex[:6]
        path = os.path.join(DOWNLOAD_DIR, f"{uid}.mp3")
        await download_audio(self.source_url, path)
        await interaction.followup.send(file=discord.File(path))
        os.remove(path)

# ========= MODAL =========
class DownloadModal(discord.ui.Modal, title="Video Download"):
    video_url = discord.ui.TextInput(
        label="Video Link",
        placeholder="Instagram / TikTok / FB / YouTube",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await process_video(interaction, self.video_url.value)

# ========= PROCESS =========
async def process_video(interaction: discord.Interaction, url: str):
    platform = detect_platform(url)
    await interaction.response.send_message(f"⏳ Mengambil video dari **{platform}**...")

    uid = uuid.uuid4().hex[:8]
    path = os.path.join(DOWNLOAD_DIR, f"{uid}.mp4")

    try:
        await download_video(url, path)
        size_mb = os.path.getsize(path) / (1024 * 1024)

        if size_mb <= 25:
            await interaction.followup.send(
                file=discord.File(path),
                view=VidVaulButtons(url)
            )
        else:
            link = upload_to_cos(path, f"{uid}.mp4")
            await interaction.followup.send(
                content=link,
                view=VidVaulButtons(url)
            )
    finally:
        if os.path.exists(path):
            os.remove(path)

# ========= COMMAND =========
@tree.command(name="download", description="Download video (IG/TT/FB/YT)")
async def download(interaction: discord.Interaction):
    try:
        await interaction.response.send_modal(DownloadModal())
    except discord.NotFound:
        pass

# ========= READY =========
@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot online sebagai {client.user}")

# ========= RUN =========
client.run(TOKEN)
