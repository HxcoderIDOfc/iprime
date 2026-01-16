from discord import app_commands

def setup(tree: app_commands.CommandTree):

    @tree.command(name="ping", description="Cek bot latency")
    async def ping(interaction):
        await interaction.response.send_message("🏓 Pong!")
