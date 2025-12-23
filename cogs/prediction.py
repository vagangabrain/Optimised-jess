"""Pokemon prediction and auto-detection"""
import discord
import asyncio
from discord.ext import commands
from utils import (
    format_pokemon_prediction,
    get_image_url_from_message,
    normalize_pokemon_name,
    get_pokemon_with_variants,
    is_rare_pokemon,
    load_pokemon_data
)
from config import POKETWO_USER_ID, PREDICTION_CONFIDENCE

# Hardcoded channel ID where any image will be auto-predicted
AUTO_PREDICT_CHANNEL_ID = 1453015934393651272  # Set to your channel ID (e.g., 1234567890)

class Prediction(commands.Cog):
    """Pokemon prediction commands and auto-detection"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pokemon_data = load_pokemon_data()
    
    @property
    def db(self):
        """Get database from bot"""
        return self.bot.db
    
    @property
    def predictor(self):
        """Get predictor from bot"""
        return self.bot.predictor
    
    @property
    def http_session(self):
        """Get HTTP session from bot"""
        return self.bot.http_session
    
    async def get_pokemon_ping_info(self, pokemon_name: str, guild_id: int) -> str:
        """Get ping information for a Pokemon based on its rarity"""
        pokemon_data = load_pokemon_data()
        from utils import find_pokemon_by_name
        pokemon = find_pokemon_by_name(pokemon_name, pokemon_data)
        
        if not pokemon:
            return None
        
        settings = await self.db.get_guild_settings(guild_id)
        
        if is_rare_pokemon(pokemon):
            rare_role_id = settings.get('rare_role_id')
            if rare_role_id:
                return f"Rare Ping: <@&{rare_role_id}>"
        
        rarity = pokemon.get('rarity', '').lower()
        if rarity == "regional":
            regional_role_id = settings.get('regional_role_id')
            if regional_role_id:
                return f"Regional Ping: <@&{regional_role_id}>"
        
        return None
    
    async def get_collectors_for_spawn(self, pokemon_name: str, guild_id: int) -> list:
        """Get all collectors for a Pokemon spawn (including variants and rare collectors)"""
        pokemon = None
        from utils import find_pokemon_by_name
        pokemon = find_pokemon_by_name(pokemon_name, self.pokemon_data)
        
        # Get all possible names to search for
        search_names = [pokemon_name]
        
        if pokemon:
            # If it's a variant, also search for base form collectors
            if pokemon.get('is_variant') and pokemon.get('variant_of'):
                search_names.append(pokemon['variant_of'])
            
            # Get all variants
            variants = get_pokemon_with_variants(pokemon_name, self.pokemon_data)
            search_names.extend(variants)
        
        # Remove duplicates
        search_names = list(set([normalize_pokemon_name(name) for name in search_names]))
        
        # Get AFK users
        afk_users = await self.db.get_collection_afk_users(guild_id)
        
        # Get collectors
        collectors = await self.db.get_collectors_for_pokemon(guild_id, search_names, afk_users)
        
        # If rare Pokemon, add rare collectors
        if pokemon and is_rare_pokemon(pokemon):
            rare_collectors = await self.db.get_rare_collectors(guild_id, afk_users)
            collectors = list(set(collectors + rare_collectors))
        
        return collectors
    
    async def get_shiny_hunters_for_spawn(self, pokemon_name: str, guild_id: int) -> list:
        """Get all shiny hunters for a Pokemon spawn (including variants)"""
        pokemon = None
        from utils import find_pokemon_by_name
        pokemon = find_pokemon_by_name(pokemon_name, self.pokemon_data)
        
        # Get all possible names to search for
        search_names = [pokemon_name]
        
        if pokemon:
            # If it's a variant, also search for base form hunters
            if pokemon.get('is_variant') and pokemon.get('variant_of'):
                search_names.append(pokemon['variant_of'])
            
            # Get all variants
            variants = get_pokemon_with_variants(pokemon_name, self.pokemon_data)
            search_names.extend(variants)
        
        # Remove duplicates
        search_names = list(set([normalize_pokemon_name(name) for name in search_names]))
        
        # Get AFK users
        afk_users = await self.db.get_shiny_hunt_afk_users(guild_id)
        
        # Get hunters
        hunters_data = await self.db.get_shiny_hunters_for_pokemon(guild_id, search_names, afk_users)
        
        # Format hunters (show AFK status)
        formatted_hunters = []
        for user_id, is_afk in hunters_data:
            if is_afk:
                formatted_hunters.append(f"{user_id}(AFK)")
            else:
                formatted_hunters.append(f"<@{user_id}>")
        
        return formatted_hunters
    
    async def _predict_pokemon(self, image_url: str, guild_id: int):
        """Helper method for Pokemon prediction"""
        if self.predictor is None:
            return "Predictor not initialized, please try again later."
        
        if self.http_session is None:
            return "HTTP session not available."
        
        try:
            # Use async prediction
            name, confidence = await self.predictor.predict(image_url, self.http_session)
            
            if not name or not confidence:
                return "Could not predict Pokemon from the provided image."
            
            formatted_output = format_pokemon_prediction(name, confidence)
            
            # Get ping information concurrently
            hunters_task = self.get_shiny_hunters_for_spawn(name, guild_id)
            collectors_task = self.get_collectors_for_spawn(name, guild_id)
            ping_info_task = self.get_pokemon_ping_info(name, guild_id)
            
            hunters, collectors, ping_info = await asyncio.gather(
                hunters_task, collectors_task, ping_info_task,
                return_exceptions=True
            )
            
            # Handle results safely
            if isinstance(hunters, list) and hunters:
                formatted_output += f"\nShiny Hunters: {' '.join(hunters)}"
            
            if isinstance(collectors, list) and collectors:
                collector_mentions = " ".join([f"<@{user_id}>" for user_id in collectors])
                formatted_output += f"\nCollectors: {collector_mentions}"
            
            if isinstance(ping_info, str) and ping_info:
                formatted_output += f"\n{ping_info}"
            
            return formatted_output
        
        except Exception as e:
            print(f"Prediction error: {e}")
            return f"Error: {str(e)[:100]}"
    
    @commands.command(name="predict")
    async def predict_command(self, ctx, *, image_url: str = None):
        """Predict Pokemon from image URL or replied message
        
        Examples:
            m!predict <image_url>
            m!predict (reply to a message with image)
        """
        # If no URL provided, check if replying to a message with image
        if not image_url and ctx.message.reference:
            try:
                replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                image_url = await get_image_url_from_message(replied_message)
            except discord.NotFound:
                await ctx.reply("Could not find the replied message.", mention_author=False)
                return
            except discord.Forbidden:
                await ctx.reply("I don't have permission to access that message.", mention_author=False)
                return
            except Exception as e:
                await ctx.reply(f"Error fetching replied message: {str(e)[:100]}", mention_author=False)
                return
        
        # If still no image URL found
        if not image_url:
            await ctx.reply("Please provide an image URL after m!predict or reply to a message with an image.", mention_author=False)
            return
        
        result = await self._predict_pokemon(image_url, ctx.guild.id)
        await ctx.reply(result, mention_author=False)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle auto-detection of Poketwo spawns and auto-predict channel"""
        # Don't respond to bot's own messages
        if message.author == self.bot.user:
            return
        
        # Check if predictor is available
        if self.predictor is None:
            return
        
        # Auto-predict any image in the designated channel
        if AUTO_PREDICT_CHANNEL_ID and message.channel.id == AUTO_PREDICT_CHANNEL_ID:
            # Don't predict Poketwo spawns in auto-predict channel (they'll be handled below)
            if message.author.id != POKETWO_USER_ID:
                image_url = await get_image_url_from_message(message)
                
                if image_url:
                    try:
                        name, confidence = await self.predictor.predict(image_url, self.http_session)
                        
                        if name and confidence:
                            formatted_output = format_pokemon_prediction(name, confidence)
                            
                            # Get all ping information concurrently
                            tasks = [
                                self.get_shiny_hunters_for_spawn(name, message.guild.id),
                                self.get_collectors_for_spawn(name, message.guild.id),
                                self.get_pokemon_ping_info(name, message.guild.id)
                            ]
                            
                            results = await asyncio.gather(*tasks, return_exceptions=True)
                            hunters, collectors, ping_info = results
                            
                            # Handle results safely
                            if isinstance(hunters, list) and hunters:
                                formatted_output += f"\nShiny Hunters: {' '.join(hunters)}"
                            
                            if isinstance(collectors, list) and collectors:
                                collector_mentions = " ".join([f"<@{user_id}>" for user_id in collectors])
                                formatted_output += f"\nCollectors: {collector_mentions}"
                            
                            if isinstance(ping_info, str) and ping_info:
                                formatted_output += f"\n{ping_info}"
                            
                            await message.reply(formatted_output)
                    
                    except Exception as e:
                        print(f"Auto-predict channel error: {e}")
        
        # Auto-detect Poketwo spawns
        if message.author.id == POKETWO_USER_ID:
            # Check if message has embeds with spawn titles
            if message.embeds:
                embed = message.embeds[0]
                if embed.title:
                    # Check for spawn embed titles
                    if (embed.title == "A wild pokémon has appeared!" or 
                        (embed.title.endswith("A new wild pokémon has appeared!") and 
                         "fled." in embed.title)):
                        
                        image_url = await get_image_url_from_message(message)
                        
                        if image_url:
                            try:
                                # Use async prediction
                                name, confidence = await self.predictor.predict(image_url, self.http_session)
                                
                                if name and confidence:
                                    # Parse confidence
                                    confidence_str = str(confidence).rstrip('%')
                                    try:
                                        confidence_value = float(confidence_str)
                                        
                                        # ALWAYS send the prediction in the spawn channel
                                        formatted_output = format_pokemon_prediction(name, confidence)
                                        
                                        # Get all ping information concurrently
                                        tasks = [
                                            self.get_shiny_hunters_for_spawn(name, message.guild.id),
                                            self.get_collectors_for_spawn(name, message.guild.id),
                                            self.get_pokemon_ping_info(name, message.guild.id)
                                        ]
                                        
                                        results = await asyncio.gather(*tasks, return_exceptions=True)
                                        hunters, collectors, ping_info = results
                                        
                                        # Handle results safely
                                        if isinstance(hunters, list) and hunters:
                                            formatted_output += f"\nShiny Hunters: {' '.join(hunters)}"
                                        
                                        if isinstance(collectors, list) and collectors:
                                            collector_mentions = " ".join([f"<@{user_id}>" for user_id in collectors])
                                            formatted_output += f"\nCollectors: {collector_mentions}"
                                        
                                        if isinstance(ping_info, str) and ping_info:
                                            formatted_output += f"\n{ping_info}"
                                        
                                        # Send prediction in spawn channel
                                        await message.reply(formatted_output)
                                        
                                        # If low confidence, ALSO send to low prediction channel
                                        if confidence_value < PREDICTION_CONFIDENCE:
                                            low_channel_id = await self.db.get_low_prediction_channel()
                                            
                                            if low_channel_id:
                                                low_channel = self.bot.get_channel(low_channel_id)
                                                
                                                if low_channel:
                                                    embed = discord.Embed(
                                                        title="Low Confidence Prediction",
                                                        description=f"**Pokemon:** {name}\n**Confidence:** {confidence}\n**Server:** {message.guild.name}\n**Channel:** {message.channel.mention}",
                                                        color=0xff9900
                                                    )
                                                    
                                                    if image_url:
                                                        embed.set_thumbnail(url=image_url)
                                                    
                                                    # Add jump button
                                                    view = discord.ui.View()
                                                    jump_button = discord.ui.Button(
                                                        label="Jump to Message",
                                                        url=message.jump_url,
                                                        emoji="🔗",
                                                        style=discord.ButtonStyle.link
                                                    )
                                                    view.add_item(jump_button)
                                                    
                                                    await low_channel.send(embed=embed, view=view)
                                                
                                                print(f"Low confidence prediction: {name} ({confidence}) in {message.guild.name}")
                                    
                                    except ValueError:
                                        print(f"Could not parse confidence value: {confidence}")
                            
                            except Exception as e:
                                print(f"Auto-detection error: {e}")

async def setup(bot):
    await bot.add_cog(Prediction(bot))
