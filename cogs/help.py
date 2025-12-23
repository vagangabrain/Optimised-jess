"""Help commands"""
import discord
from discord.ext import commands
from config import EMBED_COLOR

class Help(commands.Cog):
    """Help and information commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="help")
    async def help_command(self, ctx, category: str = None):
        """Show help information
        
        Categories: collection, hunt, settings, prediction
        """
        if not category:
            embed = discord.Embed(
                title="📚 Bot Help",
                description="Use `m!help <category>` for detailed information",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name="📦 Collection",
                value="`m!help collection` - Manage your Pokemon collection",
                inline=False
            )
            
            embed.add_field(
                name="✨ Shiny Hunt",
                value="`m!help hunt` - Set up shiny hunting",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Settings",
                value="`m!help settings` - Configure bot settings",
                inline=False
            )
            
            embed.add_field(
                name="🔮 Prediction",
                value="`m!help prediction` - Manual Pokemon prediction",
                inline=False
            )
            # Add this field to the main help embed
            embed.add_field(
                name="⭐ Starboard",
                value="`m!help starboard` - Configure starboard channels",
                inline=False
            )
            
            await ctx.reply(embed=embed, reference=ctx.message, mention_author=False)
            return
        
        category = category.lower()
        
        if category in ["collection", "cl"]:
            embed = discord.Embed(
                title="📦 Collection Commands",
                description="Manage your Pokemon collection for this server",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name="`m!cl add <pokemon>`",
                value="Add Pokemon to your collection\nExample: `m!cl add Pikachu, Charizard`\nUse `m!cl add Furfrou all` to add all variants",
                inline=False
            )
            
            embed.add_field(
                name="`m!cl remove <pokemon>`",
                value="Remove Pokemon from your collection\nExample: `m!cl remove Pikachu`",
                inline=False
            )
            
            embed.add_field(
                name="`m!cl list`",
                value="View your collection in a paginated embed",
                inline=False
            )
            
            embed.add_field(
                name="`m!cl raw`",
                value="View your collection as comma-separated text\nSends as file if collection is large",
                inline=False
            )
            
            embed.add_field(
                name="`m!cl clear`",
                value="Clear your entire collection",
                inline=False
            )
            
        elif category in ["hunt", "sh", "shiny"]:
            embed = discord.Embed(
                title="✨ Shiny Hunt Commands",
                description="Set up shiny hunting to get pinged when your target spawns",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name="`m!sh`",
                value="Check your current shiny hunt",
                inline=False
            )
            
            embed.add_field(
                name="`m!sh <pokemon>`",
                value="Start hunting a Pokemon\nExample: `m!sh Pikachu`",
                inline=False
            )
            
            embed.add_field(
                name="`m!sh clear`",
                value="Stop hunting (also accepts `none` or `stop`)",
                inline=False
            )
            
        elif category in ["settings", "setting", "config"]:
            embed = discord.Embed(
                title="⚙️ Settings Commands",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name="`m!afk`",
                value="Toggle collection and shiny hunt pings using buttons\nGreen = Pings ON, Red = Pings OFF",
                inline=False
            )
            
            embed.add_field(
                name="`m!server-settings`",
                value="View current server settings",
                inline=False
            )
            
            embed.add_field(
                name="`m!rare-role @role`",
                value="**(Admin)** Set role to ping for rare Pokemon\nExample: `m!rare-role @Rare Hunters`",
                inline=False
            )
            
            embed.add_field(
                name="`m!regional-role @role`",
                value="**(Admin)** Set role to ping for regional Pokemon\nExample: `m!regional-role @Regional`",
                inline=False
            )

            
        elif category in ["prediction", "predict", "pred"]:
            embed = discord.Embed(
                title="🔮 Prediction Commands",
                description="Manually predict Pokemon from images",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name="`m!predict <image_url>`",
                value="Predict Pokemon from image URL\nExample: `m!predict https://...`",
                inline=False
            )
            
            embed.add_field(
                name="`m!predict` (reply)",
                value="Reply to a message with an image to predict it",
                inline=False
            )
            
            embed.add_field(
                name="Auto-Detection",
                value="Bot automatically predicts Poketwo spawns and pings:\n• Shiny hunters\n• Collectors\n• Rare/Regional role if applicable",
                inline=False
            )
            
        else:
            await ctx.reply(f"Unknown category: `{category}`\nAvailable: collection, hunt, settings, prediction", mention_author=False)
            return
        
        await ctx.reply(embed=embed, reference=ctx.message, mention_author=False)
    
    @commands.command(name="about")
    async def about_command(self, ctx):
        """Show bot information"""
        embed = discord.Embed(
            title="About This Bot",
            description="A Pokemon collection and prediction bot for Poketwo",
            color=EMBED_COLOR
        )
        
        embed.add_field(
            name="Features",
            value="• Pokemon collection management\n• Shiny hunt tracking\n• Auto-prediction of spawns\n• Collector & hunter pings\n• Rare/Regional role pings",
            inline=False
        )
        
        embed.add_field(
            name="Commands",
            value="Use `m!help` to see all commands",
            inline=False
        )
        
        # Add bot stats
        total_guilds = len(self.bot.guilds)
        total_users = sum(guild.member_count for guild in self.bot.guilds)
        
        embed.add_field(
            name="Stats",
            value=f"**Servers:** {total_guilds}\n**Users:** {total_users}",
            inline=False
        )
        
        await ctx.reply(embed=embed, reference=ctx.message, mention_author=False)

async def setup(bot):
    await bot.add_cog(Help(bot))
