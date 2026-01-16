import discord
from discord import app_commands

def setup(tree: app_commands.CommandTree):

    @tree.command(name="ping", description="Cek latency bot")
    async def ping(interaction: discord.Interaction):
        latency_ms = round(interaction.client.latency * 1000)

        # tentukan warna & status
        if latency_ms <= 150:
            color = discord.Color.green()
            status = "🟢 Aman"
        elif latency_ms <= 300:
            color = discord.Color.gold()
            status = "🟡 Sedang"
        else:
            color = discord.Color.red()
            status = "🔴 Tinggi"

        embed = discord.Embed(
            title="🏓 Pong!",
            color=color
        )
        embed.add_field(
            name="Latency",
            value=f"**{latency_ms} ms**",
            inline=True
        )
        embed.add_field(
            name="Status",
            value=status,
            inline=True
        )
        embed.set_footer(text="Iprime-Bot • Network Status")

        await interaction.response.send_message(embed=embed)
