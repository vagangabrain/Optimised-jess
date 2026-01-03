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
        print(f"[AUTO-PREDICT] Channel ID set to: {AUTO_PREDICT_CHANNEL_ID}")

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

    async def extract_image_url(self, message):
        """Extract image URL from message with multiple fallback methods"""
        # Method 1: Check message attachments
        if message.attachments:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    return attachment.url

        # Method 2: Check embeds
        if message.embeds:
            for embed in message.embeds:
                if embed.image:
                    return embed.image.url
                if embed.thumbnail:
                    return embed.thumbnail.url

        # Method 3: Check message content for URLs
        import re
        url_pattern = r'https?://[^\s<>"]+?\.(?:png|jpg|jpeg|gif|webp)'
        urls = re.findall(url_pattern, message.content, re.IGNORECASE)
        if urls:
            return urls[0]

        # Method 4: Use the utility function as fallback
        url = await get_image_url_from_message(message)
        if url:
            return url

        return None

    async def get_pokemon_ping_info(self, pokemon_name: str, guild_id: int) -> str:
        """Get ping information for a Pokemon based on its rarity"""
        pokemon_data = load_pokemon_data()
        from utils import find_pokemon_by_name
        pokemon = find_pokemon_by_name(pokemon_name, pokemon_data)

        if not pokemon:
            return None

        settings = await self.db.get_guild_settings(guild_id)
        pings = []

        # Get rarity - handle both string and list
        rarity_value = pokemon.get('rarity', '')
        rarities = rarity_value if isinstance(rarity_value, list) else [rarity_value]

        # Normalize to lowercase
        rarities = [r.lower() for r in rarities if r]

        # Check for rare ping (Legendary, Mythical, Ultra Beast)
        if any(r in ['legendary', 'mythical', 'ultra beast'] for r in rarities):
            rare_role_id = settings.get('rare_role_id')
            if rare_role_id:
                pings.append(f"Rare Ping: <@&{rare_role_id}>")

        # Check for regional ping
        if 'regional' in rarities:
            regional_role_id = settings.get('regional_role_id')
            if regional_role_id:
                pings.append(f"Regional Ping: <@&{regional_role_id}>")

        # Return all pings joined together
        return "\n".join(pings) if pings else None

    async def get_shiny_hunters_for_spawn(self, pokemon_name: str, guild_id: int) -> list:
        """Get all shiny hunters for a Pokemon spawn

        Only checks for hunters who are hunting THIS EXACT Pokemon.
        The database method handles matching against their hunt list.
        """
        # Only search for the exact Pokemon that spawned
        search_names = [pokemon_name]

        # Get global AFK users
        afk_users = await self.db.get_shiny_hunt_afk_users()

        # Get hunters - the DB method will check if this Pokemon matches their hunt list
        hunters_data = await self.db.get_shiny_hunters_for_pokemon(guild_id, search_names, afk_users)

        # Format hunters (show AFK status)
        formatted_hunters = []
        for user_id, is_afk in hunters_data:
            if is_afk:
                formatted_hunters.append(f"{user_id}(AFK)")
            else:
                formatted_hunters.append(f"<@{user_id}>")

        return formatted_hunters

    async def get_collectors_for_spawn(self, pokemon_name: str, guild_id: int) -> list:
        """Get all collectors for a Pokemon spawn

        Only checks for collectors who have collected THIS EXACT Pokemon.
        The database method handles matching against their collection.
        """
        pokemon = None
        from utils import find_pokemon_by_name
        pokemon = find_pokemon_by_name(pokemon_name, self.pokemon_data)

        # Only search for the exact Pokemon that spawned
        search_names = [pokemon_name]

        # Get global AFK users
        afk_users = await self.db.get_collection_afk_users()

        # Get collectors
        collectors = await self.db.get_collectors_for_pokemon(guild_id, search_names, afk_users)

        # If rare Pokemon, add rare collectors
        if pokemon and is_rare_pokemon(pokemon):
            rare_collectors = await self.db.get_rare_collectors(guild_id, afk_users)
            collectors = list(set(collectors + rare_collectors))

        return collectors

    async def _predict_pokemon(self, image_url: str, guild_id: int):
        """Helper method for Pokemon prediction"""
        if self.predictor is None:
            return "Predictor not initialized, please try again later."

        if self.http_session is None:
            return "HTTP session not available."

        try:
            # Use async prediction
            name, confidence = await self.predictor.predict(image_url, self.http_session)
            # ADD THIS: Increment prediction counter
            if hasattr(self.bot, 'prediction_count'):
                self.bot.prediction_count += 1

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

        except ValueError as e:
            error_msg = str(e)
            if "404" in error_msg or "Failed to load image" in error_msg:
                return "Image not accessible (likely expired or deleted)."
            print(f"Prediction error: {e}")
            return f"Error: {str(e)[:100]}"
        except Exception as e:
            print(f"Prediction error: {e}")
            return f"Error: {str(e)[:100]}"

    async def should_send_prediction(self, name: str, guild_id: int, hunters, collectors, ping_info) -> bool:
        """Check if prediction should be sent based on only-pings setting"""
        only_pings_enabled = await self.db.get_only_pings(guild_id)

        if not only_pings_enabled:
            return True  # Always send if disabled

        # Check if there are any pings
        has_hunters = isinstance(hunters, list) and len(hunters) > 0
        has_collectors = isinstance(collectors, list) and len(collectors) > 0
        has_ping_info = isinstance(ping_info, str) and ping_info

        return has_hunters or has_collectors or has_ping_info

    async def log_secondary_model_prediction(
        self,
        name: str,
        confidence: str,
        model_used: str,
        message: discord.Message,
        image_url: str
    ):
        """Log secondary model predictions to dedicated channel"""
        if model_used not in ["secondary", "primary_fallback"]:
            return  # Only log when secondary model was involved

        secondary_channel_id = await self.db.get_secondary_model_channel()

        if not secondary_channel_id:
            return

        secondary_channel = self.bot.get_channel(secondary_channel_id)

        if not secondary_channel:
            return

        try:
            # Determine model label
            if model_used == "secondary":
                model_label = "Secondary Model (High Confidence)"
            else:  # primary_fallback
                model_label = "Secondary Model Used (Fallback to Primary)"

            embed = discord.Embed(
                title=f"🔬 {model_label}",
                description=(
                    f"**Pokemon:** {name}\n"
                    f"**Confidence:** {confidence}\n"
                    f"**Server:** {message.guild.name}\n"
                    f"**Channel:** {message.channel.mention}"
                ),
                color=0x00bfff
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

            await secondary_channel.send(embed=embed, view=view)
            print(f"[SECONDARY-MODEL] Logged: {name} ({confidence}) - {model_used}")

        except Exception as e:
            print(f"[SECONDARY-MODEL] Failed to log: {e}")

    @commands.command(name="predict", aliases=["pred", "p"])
    async def predict_command(self, ctx, *, image_url: str = None):
        """Predict Pokemon from image URL or replied message

        Examples:
            p!predict <image_url>
            p!predict (reply to a message with image)
        """
        # If no URL provided, check if replying to a message with image
        if not image_url and ctx.message.reference:
            try:
                replied_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                image_url = await self.extract_image_url(replied_message)
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
            await ctx.reply("Please provide an image URL after p!predict or reply to a message with an image.", mention_author=False)
            return

        result = await self._predict_pokemon(image_url, ctx.guild.id)
        await ctx.reply(result, mention_author=False)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle auto-detection of Poketwo spawns and auto-predict channel"""
        # Don't respond to bot's own messages
        if message.author == self.bot.user:
            return

        # Don't respond to messages without a guild (DMs)
        if not message.guild:
            return

        # Check if predictor is available
        if self.predictor is None:
            return

        # Auto-predict any image in the designated channel (INCLUDING POKETWO)
        if AUTO_PREDICT_CHANNEL_ID and message.channel.id == AUTO_PREDICT_CHANNEL_ID:
            image_url = await self.extract_image_url(message)

            if image_url:
                try:
                    # Get prediction with model tracking
                    cache_key = self.predictor._generate_cache_key(image_url)
                    cached_result = self.predictor.cache.get(cache_key)

                    if cached_result:
                        name, confidence, model_used = cached_result
                    else:
                        name, confidence = await self.predictor.predict(image_url, self.http_session)

                        if hasattr(self.bot, 'prediction_count'):
                            self.bot.prediction_count += 1
                        # Get the model used from the last prediction
                        cached_result = self.predictor.cache.get(cache_key)
                        model_used = cached_result[2] if cached_result else "unknown"

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

                        # ALWAYS send in auto-predict channel (ignore only-pings)
                        await message.reply(formatted_output)

                        # Log to secondary model channel if secondary model was used
                        await self.log_secondary_model_prediction(name, confidence, model_used, message, image_url)

                except ValueError as e:
                    # Handle image loading errors (404, expired URLs, etc.)
                    error_msg = str(e)
                    if "404" in error_msg or "Failed to load image" in error_msg:
                        print(f"[AUTO-PREDICT] Image not accessible (likely expired/deleted): {image_url[:100]}")
                        # Silently skip - don't notify user as this is expected for expired Discord URLs
                    else:
                        print(f"[AUTO-PREDICT] ValueError: {e}")

                except Exception as e:
                    print(f"[AUTO-PREDICT] Error: {e}")
                    import traceback
                    traceback.print_exc()

        # Auto-detect Poketwo spawns in OTHER channels (not auto-predict channel)
        elif message.author.id == POKETWO_USER_ID:
            # Check if message has embeds with spawn titles
            if message.embeds:
                embed = message.embeds[0]
                if embed.title:
                    # Check for spawn embed titles
                    if (embed.title == "A wild pokémon has appeared!" or 
                        (embed.title.endswith("A new wild pokémon has appeared!") and 
                         "fled." in embed.title)):

                        image_url = await self.extract_image_url(message)

                        if image_url:
                            try:
                                # Get prediction with model tracking
                                cache_key = self.predictor._generate_cache_key(image_url)
                                cached_result = self.predictor.cache.get(cache_key)

                                if cached_result:
                                    name, confidence, model_used = cached_result
                                else:
                                    name, confidence = await self.predictor.predict(image_url, self.http_session)
                                    if hasattr(self.bot, 'prediction_count'):
                                        self.bot.prediction_count += 1
                                    # Get the model used from the last prediction
                                    cached_result = self.predictor.cache.get(cache_key)
                                    model_used = cached_result[2] if cached_result else "unknown"

                                if name and confidence:
                                    # Parse confidence
                                    confidence_str = str(confidence).rstrip('%')
                                    try:
                                        confidence_value = float(confidence_str)

                                        # Get all ping information concurrently
                                        tasks = [
                                            self.get_shiny_hunters_for_spawn(name, message.guild.id),
                                            self.get_collectors_for_spawn(name, message.guild.id),
                                            self.get_pokemon_ping_info(name, message.guild.id)
                                        ]

                                        results = await asyncio.gather(*tasks, return_exceptions=True)
                                        hunters, collectors, ping_info = results

                                        # Check if should send based on only-pings setting
                                        should_send = await self.should_send_prediction(
                                            name, message.guild.id, hunters, collectors, ping_info
                                        )

                                        if should_send:
                                            # Format and send prediction in spawn channel
                                            formatted_output = format_pokemon_prediction(name, confidence)

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

                                        # Log to secondary model channel if secondary model was used
                                        await self.log_secondary_model_prediction(name, confidence, model_used, message, image_url)

                                    except ValueError:
                                        print(f"Could not parse confidence value: {confidence}")

                            except ValueError as e:
                                # Handle image loading errors (404, expired URLs, etc.)
                                error_msg = str(e)
                                if "404" in error_msg or "Failed to load image" in error_msg:
                                    print(f"[POKETWO-SPAWN] Image not accessible: {image_url[:100]}")
                                    # Don't reply to Poketwo spawn if image fails - it might retry
                                else:
                                    print(f"[POKETWO-SPAWN] ValueError: {e}")

                            except Exception as e:
                                print(f"Auto-detection error: {e}")

async def setup(bot):
    await bot.add_cog(Prediction(bot))
