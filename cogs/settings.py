"""Server and user settings management"""
import discord
from discord.ext import commands
from config import EMBED_COLOR, Emojis

class AFKView(discord.ui.View):
    """AFK toggle buttons"""
    
    def __init__(self, user_id, guild_id, collection_afk, shiny_hunt_afk, cog):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.guild_id = guild_id
        self.cog = cog
        self.update_buttons(collection_afk, shiny_hunt_afk)
    
    def update_buttons(self, collection_afk, shiny_hunt_afk):
        self.clear_items()
        
        # Shiny Hunt button (green=ON, red=OFF)
        shiny_button = discord.ui.Button(
            label="ShinyHunt",
            style=discord.ButtonStyle.red if shiny_hunt_afk else discord.ButtonStyle.green,
            custom_id="shiny_hunt_afk"
        )
        shiny_button.callback = self.toggle_shiny_hunt_afk
        self.add_item(shiny_button)
        
        # Collection button (green=ON, red=OFF)
        collection_button = discord.ui.Button(
            label="Collection",
            style=discord.ButtonStyle.red if collection_afk else discord.ButtonStyle.green,
            custom_id="collection_afk"
        )
        collection_button.callback = self.toggle_collection_afk
        self.add_item(collection_button)
    
    async def toggle_collection_afk(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        
        new_collection_afk = await self.cog.db.toggle_collection_afk(self.user_id, self.guild_id)
        current_shiny_hunt_afk = await self.cog.db.is_shiny_hunt_afk(self.user_id, self.guild_id)
        
        self.update_buttons(new_collection_afk, current_shiny_hunt_afk)
        embed = self._create_afk_embed(new_collection_afk, current_shiny_hunt_afk)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def toggle_shiny_hunt_afk(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        
        new_shiny_hunt_afk = await self.cog.db.toggle_shiny_hunt_afk(self.user_id, self.guild_id)
        current_collection_afk = await self.cog.db.is_collection_afk(self.user_id, self.guild_id)
        
        self.update_buttons(current_collection_afk, new_shiny_hunt_afk)
        embed = self._create_afk_embed(current_collection_afk, new_shiny_hunt_afk)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    def _create_afk_embed(self, collection_afk, shiny_hunt_afk):
        """Create embed with current AFK status"""
        shiny_emoji = Emojis.GREY_DOT if shiny_hunt_afk else Emojis.GREEN_DOT
        collection_emoji = Emojis.GREY_DOT if collection_afk else Emojis.GREEN_DOT
        
        embed = discord.Embed(
            title="AFK Status",
            description=f"✨ ShinyHunt Pings: {shiny_emoji}\n📚 Collection Pings: {collection_emoji}",
            color=EMBED_COLOR
        )
        
        return embed

class Settings(commands.Cog):
    """Server and user settings"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        """Get database from bot"""
        return self.bot.db
    
    # User settings
    @commands.command(name="afk")
    async def afk_command(self, ctx):
        """Toggle AFK status for collection and shiny hunt pings"""
        current_collection_afk = await self.db.is_collection_afk(ctx.author.id, ctx.guild.id)
        current_shiny_hunt_afk = await self.db.is_shiny_hunt_afk(ctx.author.id, ctx.guild.id)
        
        shiny_emoji = Emojis.GREY_DOT if current_shiny_hunt_afk else Emojis.GREEN_DOT
        collection_emoji = Emojis.GREY_DOT if current_collection_afk else Emojis.GREEN_DOT
        
        embed = discord.Embed(
            title="AFK Status",
            description=f"✨ ShinyHunt Pings: {shiny_emoji}\n📚 Collection Pings: {collection_emoji}",
            color=EMBED_COLOR
        )
        
        view = AFKView(ctx.author.id, ctx.guild.id, current_collection_afk, current_shiny_hunt_afk, self)
        await ctx.reply(embed=embed, view=view, mention_author=False)
    
    # Server settings (admin only)
    @commands.command(name="rare-role")
    @commands.has_permissions(administrator=True)
    async def rare_role_command(self, ctx, role: discord.Role):
        """Set the rare Pokemon ping role for this server"""
        await self.db.set_rare_role(ctx.guild.id, role.id)
        await ctx.reply(f"✅ Rare role set to {role.mention}", mention_author=False)
    
    @rare_role_command.error
    async def rare_role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You need administrator permissions to use this command.", mention_author=False)
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Invalid role mention or ID. Use @role or role ID.", mention_author=False)
    
    @commands.command(name="regional-role")
    @commands.has_permissions(administrator=True)
    async def regional_role_command(self, ctx, role: discord.Role):
        """Set the regional Pokemon ping role for this server"""
        await self.db.set_regional_role(ctx.guild.id, role.id)
        await ctx.reply(f"✅ Regional role set to {role.mention}", mention_author=False)
    
    @regional_role_command.error
    async def regional_role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You need administrator permissions to use this command.", mention_author=False)
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Invalid role mention or ID.", mention_author=False)
    
    @commands.command(name="server-settings")
    async def server_settings_command(self, ctx):
        """View current server settings"""
        settings = await self.db.get_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title=f"Server Settings for {ctx.guild.name}",
            color=EMBED_COLOR
        )
        
        # Rare role
        rare_role_id = settings.get('rare_role_id')
        if rare_role_id:
            embed.add_field(name="Rare Role", value=f"<@&{rare_role_id}>", inline=True)
        else:
            embed.add_field(name="Rare Role", value="Not set", inline=True)
        
        # Regional role
        regional_role_id = settings.get('regional_role_id')
        if regional_role_id:
            embed.add_field(name="Regional Role", value=f"<@&{regional_role_id}>", inline=True)
        else:
            embed.add_field(name="Regional Role", value="Not set", inline=True)

        # Add note about starboard settings
        embed.add_field(
            name="⭐ Starboard Settings",
            value="Use `m!starboard-settings` to view starboard channel configuration",
            inline=False
        )
        
        embed.set_footer(text=f"Guild ID: {ctx.guild.id}")
        await ctx.reply(embed=embed, mention_author=False)
    
    # Global settings (bot owner only)
    @commands.command(name="set-low-prediction-channel")
    @commands.is_owner()
    async def set_low_prediction_channel_command(self, ctx, channel: discord.TextChannel):
        """Set the global channel for low confidence predictions (bot owner only)"""
        await self.db.set_low_prediction_channel(channel.id)
        await ctx.reply(f"✅ Low prediction channel set to {channel.mention}", mention_author=False)
    
    @set_low_prediction_channel_command.error
    async def set_low_prediction_channel_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.reply("❌ Only the bot owner can use this command.", mention_author=False)
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("❌ Invalid channel mention or ID.", mention_author=False)

async def setup(bot):
    await bot.add_cog(Settings(bot))
