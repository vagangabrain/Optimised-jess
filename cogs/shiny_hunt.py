"""Shiny hunt management commands"""
import discord
from discord.ext import commands
from utils import load_pokemon_data, find_pokemon_by_name_flexible
from config import EMBED_COLOR

class ShinyHunt(commands.Cog):
    """Shiny hunt management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pokemon_data = load_pokemon_data()
    
    @property
    def db(self):
        """Get database from bot"""
        return self.bot.db
    
    @commands.command(name="sh")
    async def shiny_hunt_command(self, ctx, *, args: str = None):
        """Manage shiny hunt
        
        Examples:
            m!sh                    (check current hunt)
            m!sh Pikachu            (start hunting Pikachu)
            m!sh clear              (clear hunt)
        """
        if not args:
            # Check current hunt
            current_hunt = await self.db.get_user_shiny_hunt(ctx.author.id, ctx.guild.id)
            
            if current_hunt:
                await ctx.reply(f"You are currently hunting: **{current_hunt}**", mention_author=False)
            else:
                await ctx.reply("You are not hunting anything", mention_author=False)
            return
        
        args = args.strip().lower()
        
        # Clear hunt
        if args in ["clear", "none", "stop"]:
            cleared = await self.db.clear_shiny_hunt(ctx.author.id, ctx.guild.id)
            
            if cleared:
                await ctx.reply("✅ Shiny hunt cleared successfully", mention_author=False)
            else:
                await ctx.reply("You are not hunting anything", mention_author=False)
            return
        
        # Set hunt
        pokemon_names = [name.strip() for name in args.split(",") if name.strip()]
        
        if len(pokemon_names) > 1:
            await ctx.reply("❌ You can only hunt one Pokemon at a time!", mention_author=False)
            return
        
        if len(pokemon_names) == 1:
            pokemon = find_pokemon_by_name_flexible(pokemon_names[0], self.pokemon_data)
            
            if not pokemon or not pokemon.get('name'):
                await ctx.reply(f"❌ Invalid Pokemon name: {pokemon_names[0]}", mention_author=False)
                return
            
            await self.db.set_shiny_hunt(ctx.author.id, ctx.guild.id, pokemon['name'])
            await ctx.reply(f"✅ Now hunting: **{pokemon['name']}**", mention_author=False)
        else:
            await ctx.reply("Please provide a Pokemon name to hunt, or use 'clear' to stop hunting.", mention_author=False)

async def setup(bot):
    await bot.add_cog(ShinyHunt(bot))
