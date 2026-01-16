from discord import app_commands
import discord

def setup(client, tree):

    @tree.command(name="ping", description="Cek bot hidup")
    async def ping(interaction: discord.Interaction):
        await interaction.response.send_message("🏓 Pong dari plugin!")
