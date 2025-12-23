"""Help commands"""
import discord
from discord.ext import commands
from config import EMBED_COLOR, BOT_PREFIX

class Help(commands.Cog):
    """Help and information commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="help", aliases=["h"])
    async def help_command(self, ctx, category: str = None):
        """Show help information
        
        Categories: collection, hunt, settings, prediction, starboard, all
        """
        prefix = BOT_PREFIX[0]  # Use first prefix for examples
        
        if not category:
            # Main help embed
            embed = discord.Embed(
                title="📚 Poketwo Helper Bot - Help",
                description=f"Use `{prefix}help <category>` for detailed information about a category\nUse `{prefix}help all` to see all commands at once",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name="📦 Collection",
                value=f"`{prefix}help collection` - Manage your Pokemon collection",
                inline=False
            )
            
            embed.add_field(
                name="✨ Shiny Hunt",
                value=f"`{prefix}help hunt` - Set up shiny hunting",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Settings",
                value=f"`{prefix}help settings` - Configure bot settings",
                inline=False
            )
            
            embed.add_field(
                name="🔮 Prediction",
                value=f"`{prefix}help prediction` - Manual Pokemon prediction",
                inline=False
            )
            
            embed.add_field(
                name="⭐ Starboard",
                value=f"`{prefix}help starboard` - Configure starboard channels",
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ About",
                value=f"`{prefix}about` - Bot information and stats",
                inline=False
            )
            
            embed.set_footer(text=f"Bot Prefix: {', '.join(BOT_PREFIX)}")
            
            await ctx.reply(embed=embed, mention_author=False)
            return
        
        category = category.lower()
        
        # Collection category
        if category in ["collection", "cl", "collect"]:
            embed = discord.Embed(
                title="📦 Collection Commands",
                description="Manage your Pokemon collection for this server. Get pinged when Pokemon you collect spawn!",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name=f"`{prefix}cl add <pokemon>`",
                value=(
                    "Add Pokemon to your collection\n"
                    f"**Examples:**\n"
                    f"• `{prefix}cl add Pikachu`\n"
                    f"• `{prefix}cl add Pikachu, Charizard, Mewtwo`\n"
                    f"• `{prefix}cl add Furfrou all` (adds all Furfrou variants)"
                ),
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}cl remove <pokemon>`",
                value=(
                    "Remove Pokemon from your collection\n"
                    f"**Example:** `{prefix}cl remove Pikachu`"
                ),
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}cl list`",
                value="View your collection in a paginated embed with buttons",
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}cl raw`",
                value="View your collection as comma-separated text (sends as .txt file if large)",
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}cl clear`",
                value="⚠️ Clear your entire collection",
                inline=False
            )
            
            embed.add_field(
                name="💡 How It Works",
                value=(
                    "• When a Pokemon you collect spawns, you get pinged!\n"
                    "• If you add `Furfrou`, you get pinged for all Furfrou variants\n"
                    "• If you add `Furfrou all`, all variants are explicitly added to your collection"
                ),
                inline=False
            )
        
        # Shiny Hunt category
        elif category in ["hunt", "sh", "shiny"]:
            embed = discord.Embed(
                title="✨ Shiny Hunt Commands",
                description="Set up shiny hunting to get pinged when your target Pokemon spawns!",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name=f"`{prefix}sh`",
                value="Check your current shiny hunt",
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}sh <pokemon>`",
                value=(
                    "Start hunting a Pokemon\n"
                    f"**Example:** `{prefix}sh Pikachu`"
                ),
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}sh clear`",
                value="Stop hunting (also accepts `none` or `stop`)",
                inline=False
            )
            
            embed.add_field(
                name="💡 Note",
                value="You can only hunt one Pokemon at a time per server!",
                inline=False
            )
        
        # Settings category
        elif category in ["settings", "setting", "config", "afk"]:
            embed = discord.Embed(
                title="⚙️ Settings Commands",
                description="Configure bot settings for your server and personal preferences",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name="👤 User Settings",
                value="",
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}afk`",
                value=(
                    "Toggle collection and shiny hunt pings using interactive buttons\n"
                    "🟢 **Green** = Pings ON (you'll be pinged)\n"
                    "🔴 **Red** = Pings OFF (you won't be pinged)"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🛠️ Server Settings (Admin Only)",
                value="",
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}rare-role @role`",
                value=(
                    "Set role to ping for rare Pokemon (Legendary/Mythical/Ultra Beast)\n"
                    f"**Example:** `{prefix}rare-role @Rare Hunters`"
                ),
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}regional-role @role`",
                value=(
                    "Set role to ping for regional Pokemon\n"
                    f"**Example:** `{prefix}regional-role @Regional`"
                ),
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}server-settings`",
                value="View all current server settings",
                inline=False
            )
        
        # Prediction category
        elif category in ["prediction", "predict", "pred"]:
            embed = discord.Embed(
                title="🔮 Prediction Commands",
                description="Manually predict Pokemon from images or view auto-detection info",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name=f"`{prefix}predict <image_url>`",
                value=(
                    "Predict Pokemon from image URL\n"
                    f"**Example:** `{prefix}predict https://...`"
                ),
                inline=False
            )
            
            embed.add_field(
                name=f"`{prefix}predict` (reply to message)",
                value="Reply to a message with an image to predict it",
                inline=False
            )
            
            embed.add_field(
                name="🤖 Auto-Detection",
                value=(
                    "The bot automatically predicts Poketwo spawns and pings:\n"
                    "• **Shiny hunters** hunting that Pokemon\n"
                    "• **Collectors** who have collected that Pokemon\n"
                    "• **Rare/Regional roles** if applicable"
                ),
                inline=False
            )
            
            embed.add_field(
                name="📊 Confidence Threshold",
                value=(
                    "Predictions with ≥50% confidence are posted automatically\n"
                    "Low confidence predictions are logged to a debug channel (if configured by bot owner)"
                ),
                inline=False
            )
        
        # Starboard category
        elif category in ["starboard", "star", "log"]:
            embed = discord.Embed(
                title="⭐ Starboard Commands",
                description="Configure automatic logging of rare catches, hatches, and unboxes to dedicated channels",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name=f"`{prefix}starboard-settings`",
                value="View current starboard channel configuration",
                inline=False
            )
            
            embed.add_field(
                name="📺 Channel Configuration (Admin Only)",
                value="",
                inline=False
            )
            
            embed.add_field(
                name="General Channels",
                value=(
                    f"`{prefix}starboard-catch #channel` - All catches\n"
                    f"`{prefix}starboard-egg #channel` - All egg hatches\n"
                    f"`{prefix}starboard-unbox #channel` - All box openings"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Specific Criteria Channels",
                value=(
                    f"`{prefix}starboard-shiny #channel` - Shiny catches/hatches/unboxes\n"
                    f"`{prefix}starboard-gigantamax #channel` - Gigantamax catches/hatches/unboxes\n"
                    f"`{prefix}starboard-highiv #channel` - High IV (≥90%)\n"
                    f"`{prefix}starboard-lowiv #channel` - Low IV (≤10%)\n"
                    f"`{prefix}starboard-missingno #channel` - MissingNo catches"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔍 Manual Checking (Admin Only)",
                value=(
                    f"`{prefix}catchcheck` - Manually check a catch message\n"
                    f"`{prefix}eggcheck` - Manually check an egg hatch\n"
                    f"`{prefix}unboxcheck` - Manually check a box opening\n"
                    "Use by replying to a message or providing message ID"
                ),
                inline=False
            )
            
            embed.add_field(
                name="📋 What Gets Logged?",
                value=(
                    "• **Shiny** catches/hatches/unboxes\n"
                    "• **Gigantamax** catches/hatches/unboxes\n"
                    "• **High IV** (≥90%) or **Low IV** (≤10%)\n"
                    "• **MissingNo** catches\n"
                    "• **Combinations** (e.g., Shiny + High IV)\n\n"
                    "Note: A Pokemon meeting multiple criteria will be sent to multiple channels!"
                ),
                inline=False
            )
        
        # All commands
        elif category in ["all", "commands"]:
            embed = discord.Embed(
                title="📚 All Commands",
                description="Complete list of all bot commands",
                color=EMBED_COLOR
            )
            
            embed.add_field(
                name="📦 Collection",
                value=(
                    f"`{prefix}cl add` • `{prefix}cl remove` • `{prefix}cl list`\n"
                    f"`{prefix}cl raw` • `{prefix}cl clear`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="✨ Shiny Hunt",
                value=f"`{prefix}sh` • `{prefix}sh <pokemon>` • `{prefix}sh clear`",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Settings",
                value=(
                    f"`{prefix}afk` • `{prefix}server-settings`\n"
                    f"`{prefix}rare-role` • `{prefix}regional-role`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔮 Prediction",
                value=f"`{prefix}predict`",
                inline=False
            )
            
            embed.add_field(
                name="⭐ Starboard Settings",
                value=(
                    f"`{prefix}starboard-settings`\n"
                    f"`{prefix}starboard-catch/egg/unbox`\n"
                    f"`{prefix}starboard-shiny/gigantamax`\n"
                    f"`{prefix}starboard-highiv/lowiv/missingno`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔍 Starboard Manual Check",
                value=f"`{prefix}catchcheck` • `{prefix}eggcheck` • `{prefix}unboxcheck`",
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ Info",
                value=f"`{prefix}help` • `{prefix}about`",
                inline=False
            )
        
        else:
            await ctx.reply(
                f"❌ Unknown category: `{category}`\n"
                f"Available categories: `collection`, `hunt`, `settings`, `prediction`, `starboard`, `all`\n"
                f"Use `{prefix}help` to see the main help menu.",
                mention_author=False
            )
            return
        
        embed.set_footer(text=f"Bot Prefix: {', '.join(BOT_PREFIX)}")
        await ctx.reply(embed=embed, mention_author=False)
    
    @commands.command(name="about")
    async def about_command(self, ctx):
        """Show bot information and statistics"""
        prefix = BOT_PREFIX[0]
        
        embed = discord.Embed(
            title="ℹ️ About Pokemon Helper Bot",
            description="A comprehensive Pokemon collection and prediction bot for Poketwo",
            color=EMBED_COLOR
        )
        
        embed.add_field(
            name="✨ Key Features",
            value=(
                "• 📦 **Collection Management** - Track and get pinged for Pokemon you collect\n"
                "• ✨ **Shiny Hunting** - Get notified when your hunt target spawns\n"
                "• 🔮 **Auto-Prediction** - Automatically identifies Poketwo spawns\n"
                "• ⭐ **Starboard Logging** - Log rare catches, hatches, and unboxes\n"
                "• 🎯 **Smart Pings** - Collectors, hunters, and role-based pings"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Statistics",
            value=(
                f"**Servers:** {len(self.bot.guilds)}\n"
                f"**Users:** {sum(g.member_count for g in self.bot.guilds)}\n"
                f"**Commands:** {len(self.bot.commands)}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Technical",
            value=(
                f"**Prefix:** {', '.join(BOT_PREFIX)}\n"
                f"**Library:** discord.py\n"
                f"**Database:** MongoDB"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🚀 Getting Started",
            value=f"Use `{prefix}help` to see all available commands and features!",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Quick Links",
            value=(
                f"• `{prefix}help collection` - Set up your collection\n"
                f"• `{prefix}help starboard` - Configure starboard logging\n"
                f"• `{prefix}afk` - Manage your ping preferences"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Made with ❤️ for the Poketwo community")
        
        await ctx.reply(embed=embed, mention_author=False)
    
    @commands.command(name="commands", aliases=["cmds"])
    async def commands_command(self, ctx):
        """Quick alias to show all commands"""
        await ctx.invoke(self.help_command, category="all")

async def setup(bot):
    await bot.add_cog(Help(bot))
