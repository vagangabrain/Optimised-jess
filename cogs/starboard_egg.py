"""Starboard logging for egg hatches"""
import discord
import re
from datetime import datetime
from discord.ext import commands
from config import POKETWO_USER_ID, EMBED_COLOR, HIGH_IV_THRESHOLD, LOW_IV_THRESHOLD, Emojis
from starboard_utils import (
    get_gender_emoji,
    find_pokemon_image_url,
    format_iv_display,
    create_jump_button_view
)

class StarboardEgg(commands.Cog):
    """Automatic logging of egg hatches to starboard channels"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @property
    def db(self):
        """Get database from bot"""
        return self.bot.db
    
    async def get_hatched_by_user(self, message: discord.Message):
        """Get who hatched the egg from the reply"""
        if not message.reference:
            return None
        
        try:
            if message.reference.resolved:
                return message.reference.resolved.author.id
            
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            return referenced_message.author.id
        
        except Exception as e:
            print(f"Error getting hatched user: {e}")
            return None
    
    def parse_poketwo_hatch_message(self, message_content: str, hatched_by_id: int = None) -> dict:
        """Parse Poketwo egg hatch message"""
        
        # Pattern for Gigantamax hatches
        gigantamax_pattern = r"Your <:egg_[^>]+> \*\*Gigantamax (.+?) Egg\*\* has hatched into a \*\*<:_:\d+> (✨ )?Level (\d+) <:_:1242455099213877248> Gigantamax (.+?)(<:[^:]+:\d+>)\s*\((\d+\.?\d*)%\)\*\*"
        
        match = re.search(gigantamax_pattern, message_content)
        
        if match:
            egg_pokemon = match.group(1).strip()
            is_shiny = match.group(2) is not None
            level = match.group(3)
            pokemon_name = match.group(4).strip()
            gender_emoji = match.group(5)
            iv_str = match.group(6)
            
            is_gigantamax = True
            
            # Extract gender
            gender = None
            if gender_emoji:
                if 'male:' in gender_emoji and 'female' not in gender_emoji:
                    gender = 'male'
                elif 'female:' in gender_emoji:
                    gender = 'female'
                elif 'unknown:' in gender_emoji:
                    gender = 'unknown'
            
            iv = float(iv_str) if iv_str else "Hidden"
            
            return {
                'egg_pokemon': egg_pokemon,
                'level': level,
                'pokemon_name': pokemon_name,
                'iv': iv,
                'is_shiny': is_shiny,
                'is_gigantamax': is_gigantamax,
                'gender': gender,
                'message_type': 'hatch',
                'hatched_by_id': hatched_by_id
            }
        
        # Pattern for regular hatches
        regular_pattern = r"Your <:egg_[^>]+> \*\*(.+?) Egg\*\* has hatched into a \*\*<:_:\d+> (✨ )?Level (\d+) (.+?)(?:\s+\((\d+\.?\d*)%\))?\*\*"
        
        match = re.search(regular_pattern, message_content)
        if not match:
            return None
        
        egg_pokemon = match.group(1).strip()
        is_shiny = match.group(2) is not None
        level = match.group(3)
        pokemon_name_with_gender = match.group(4).strip()
        iv_str = match.group(5)
        
        # Handle IV
        iv = float(iv_str) if iv_str else "Hidden"
        
        # Extract gender
        gender = None
        pokemon_name = pokemon_name_with_gender
        
        if re.search(r'<:male:\d+>', message_content):
            gender = 'male'
            pokemon_name = re.sub(r'<:male:\d+>', '', pokemon_name_with_gender).strip()
        elif re.search(r'<:female:\d+>', message_content):
            gender = 'female'
            pokemon_name = re.sub(r'<:female:\d+>', '', pokemon_name_with_gender).strip()
        elif re.search(r'<:unknown:\d+>', message_content):
            gender = 'unknown'
            pokemon_name = re.sub(r'<:unknown:\d+>', '', pokemon_name_with_gender).strip()
        
        return {
            'egg_pokemon': egg_pokemon,
            'level': level,
            'pokemon_name': pokemon_name,
            'iv': iv,
            'is_shiny': is_shiny,
            'is_gigantamax': False,
            'gender': gender,
            'message_type': 'hatch',
            'hatched_by_id': hatched_by_id
        }
    
    def create_hatch_embed(self, hatch_data: dict, original_message: discord.Message = None) -> discord.Embed:
        """Create embed for hatch"""
        pokemon_name = hatch_data['pokemon_name']
        level = hatch_data['level']
        iv = hatch_data['iv']
        is_shiny = hatch_data['is_shiny']
        is_gigantamax = hatch_data['is_gigantamax']
        gender = hatch_data.get('gender')
        hatched_by_id = hatch_data.get('hatched_by_id')
        
        # Format IV
        iv_display = format_iv_display(iv)
        
        # Get gender emoji
        gender_emoji = get_gender_emoji(gender)
        
        # Display name
        display_name = f"Gigantamax {pokemon_name}" if is_gigantamax else pokemon_name
        
        # Format Pokemon name with gender
        if gender_emoji:
            pokemon_display = f"{display_name} {gender_emoji}"
        else:
            pokemon_display = display_name
        
        # Get Pokemon image URL
        image_url = find_pokemon_image_url(pokemon_name, is_shiny, gender, is_gigantamax)
        
        embed = discord.Embed(color=EMBED_COLOR, timestamp=datetime.utcnow())
        
        # Determine title based on criteria
        title_parts = []
        
        if is_shiny:
            title_parts.append("✨ Shiny")
        
        if is_gigantamax:
            title_parts.append(f"{Emojis.GIGANTAMAX} Gigantamax")
        
        # Check IV
        if iv != "Hidden":
            try:
                iv_value = float(iv)
                if iv_value >= HIGH_IV_THRESHOLD:
                    title_parts.append("📈 High IV")
                elif iv_value <= LOW_IV_THRESHOLD:
                    title_parts.append("📉 Low IV")
            except ValueError:
                pass
        
        if title_parts:
            embed.title = f"{Emojis.EGG} " + " ".join(title_parts) + f" Hatch Detected {Emojis.EGG}"
        else:
            embed.title = f"{Emojis.EGG} Rare Hatch Detected {Emojis.EGG}"
        
        # Description
        base_description = f"**Pokémon:** {pokemon_display}\n**Level:** {level}\n**IV:** {iv_display}"
        if hatched_by_id:
            embed.description = f"**Hatched By:** <@{hatched_by_id}>\n{base_description}"
        else:
            embed.description = base_description
        
        if image_url:
            embed.set_thumbnail(url=image_url)
        
        return embed
    
    async def send_to_starboard_channels(self, guild: discord.Guild, hatch_data: dict, original_message: discord.Message = None):
        """Send hatch to appropriate starboard channels"""
        is_shiny = hatch_data['is_shiny']
        is_gigantamax = hatch_data['is_gigantamax']
        iv = hatch_data['iv']
        
        settings = await self.db.get_guild_settings(guild.id)
        
        # Determine which channels to send to
        channels_to_send = []
        
        # General egg channel
        egg_channel_id = settings.get('starboard_egg_channel_id')
        if egg_channel_id:
            channels_to_send.append(egg_channel_id)
        
        # Shiny channel
        if is_shiny:
            shiny_channel_id = settings.get('starboard_shiny_channel_id')
            if shiny_channel_id and shiny_channel_id not in channels_to_send:
                channels_to_send.append(shiny_channel_id)
        
        # Gigantamax channel
        if is_gigantamax:
            gmax_channel_id = settings.get('starboard_gigantamax_channel_id')
            if gmax_channel_id and gmax_channel_id not in channels_to_send:
                channels_to_send.append(gmax_channel_id)
        
        # IV channels
        if iv != "Hidden":
            try:
                iv_value = float(iv)
                
                if iv_value >= HIGH_IV_THRESHOLD:
                    highiv_channel_id = settings.get('starboard_highiv_channel_id')
                    if highiv_channel_id and highiv_channel_id not in channels_to_send:
                        channels_to_send.append(highiv_channel_id)
                
                elif iv_value <= LOW_IV_THRESHOLD:
                    lowiv_channel_id = settings.get('starboard_lowiv_channel_id')
                    if lowiv_channel_id and lowiv_channel_id not in channels_to_send:
                        channels_to_send.append(lowiv_channel_id)
            
            except ValueError:
                pass
        
        # Create embed and view
        embed = self.create_hatch_embed(hatch_data, original_message)
        view = create_jump_button_view(original_message)
        
        # Send to all applicable channels
        for channel_id in channels_to_send:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(embed=embed, view=view)
                except Exception as e:
                    print(f"Error sending to starboard channel {channel_id}: {e}")
        
        # Send to global egg channel if configured
        global_egg_channel_id = await self.db.get_global_starboard_egg_channel()
        if global_egg_channel_id:
            global_channel = self.bot.get_channel(global_egg_channel_id)
            if global_channel:
                try:
                    await global_channel.send(embed=embed, view=view)
                except Exception as e:
                    print(f"Error sending to global starboard channel: {e}")
    
    def should_log_hatch(self, hatch_data: dict) -> bool:
        """Determine if hatch should be logged"""
        is_shiny = hatch_data['is_shiny']
        is_gigantamax = hatch_data['is_gigantamax']
        iv = hatch_data['iv']
        
        # Shiny or Gigantamax always logs
        if is_shiny or is_gigantamax:
            return True
        
        # Check IV criteria
        if iv != "Hidden":
            try:
                iv_value = float(iv)
                if iv_value >= HIGH_IV_THRESHOLD or iv_value <= LOW_IV_THRESHOLD:
                    return True
            except ValueError:
                pass
        
        return False
    
    @commands.command(name="eggcheck", aliases=["ec", "checkegg"])
    @commands.has_permissions(administrator=True)
    async def egg_check_command(self, ctx, *, input_data: str = None):
        """Manually check a Poketwo hatch message and send to starboard
        
        Usage:
            p!eggcheck (reply to a message)
            p!eggcheck <message_id>
        """
        original_message = None
        hatched_by_id = None
        hatch_message = None
        
        if input_data is None:
            if ctx.message.reference and ctx.message.reference.resolved:
                hatch_message = ctx.message.reference.resolved.content
                original_message = ctx.message.reference.resolved
                hatched_by_id = await self.get_hatched_by_user(original_message)
            else:
                await ctx.reply(
                    "Please provide a message ID or reply to a Poketwo hatch message.\n"
                    "Examples:\n"
                    "`p!eggcheck 123456789012345678` (message ID)\n"
                    "Or reply to a message with just `p!eggcheck`",
                    mention_author=False
                )
                return
        else:
            if input_data.strip().isdigit():
                message_id = int(input_data.strip())
                try:
                    try:
                        original_message = await ctx.channel.fetch_message(message_id)
                    except discord.NotFound:
                        found_message = None
                        for channel in ctx.guild.text_channels:
                            if channel.permissions_for(ctx.guild.me).read_message_history:
                                try:
                                    found_message = await channel.fetch_message(message_id)
                                    original_message = found_message
                                    break
                                except (discord.NotFound, discord.Forbidden):
                                    continue
                        
                        if not found_message:
                            await ctx.reply(f"❌ Could not find message with ID `{message_id}` in this server.", mention_author=False)
                            return
                    
                    hatch_message = original_message.content
                    
                    if original_message.author.id != POKETWO_USER_ID:
                        await ctx.reply(f"❌ The message with ID `{message_id}` is not from Poketwo.", mention_author=False)
                        return
                    
                    hatched_by_id = await self.get_hatched_by_user(original_message)
                
                except ValueError:
                    await ctx.reply(f"❌ Invalid message ID: `{input_data.strip()}`", mention_author=False)
                    return
                except Exception as e:
                    await ctx.reply(f"❌ Error fetching message: {str(e)}", mention_author=False)
                    return
            else:
                await ctx.reply("❌ Please provide a valid message ID or reply to a message.", mention_author=False)
                return
        
        # Parse hatch message
        hatch_data = self.parse_poketwo_hatch_message(hatch_message, hatched_by_id)
        
        if not hatch_data:
            await ctx.reply("❌ Invalid message format. Please make sure it's a proper Poketwo egg hatch message.", mention_author=False)
            return
        
        # Check if meets criteria
        if not self.should_log_hatch(hatch_data):
            pokemon_name = hatch_data['pokemon_name']
            level = hatch_data['level']
            iv = hatch_data['iv']
            is_shiny = hatch_data['is_shiny']
            is_gigantamax = hatch_data['is_gigantamax']
            
            gender_emoji = get_gender_emoji(hatch_data.get('gender'))
            pokemon_display = f"{pokemon_name} {gender_emoji}" if gender_emoji else pokemon_name
            iv_display = format_iv_display(iv)
            
            await ctx.reply(
                f"❌ This hatch doesn't meet starboard criteria.\n"
                f"**Pokémon:** {pokemon_display}\n"
                f"**Level:** {level}\n"
                f"**IV:** {iv_display}\n"
                f"**Shiny:** {'Yes' if is_shiny else 'No'}\n"
                f"**Gigantamax:** {'Yes' if is_gigantamax else 'No'}\n\n"
                f"**Criteria:** Shiny, Gigantamax, or IV ≥{HIGH_IV_THRESHOLD}% or ≤{LOW_IV_THRESHOLD}%",
                mention_author=False
            )
            return
        
        # Send to starboard
        await self.send_to_starboard_channels(ctx.guild, hatch_data, original_message)
        
        # Format success message
        criteria_met = []
        if hatch_data['is_shiny']:
            criteria_met.append("✨ Shiny")
        if hatch_data['is_gigantamax']:
            criteria_met.append(f"{Emojis.GIGANTAMAX} Gigantamax")
        
        iv = hatch_data['iv']
        if iv != "Hidden":
            try:
                iv_value = float(iv)
                if iv_value >= HIGH_IV_THRESHOLD:
                    criteria_met.append(f"📈 High IV ({iv}%)")
                elif iv_value <= LOW_IV_THRESHOLD:
                    criteria_met.append(f"📉 Low IV ({iv}%)")
            except ValueError:
                pass
        
        criteria_text = ", ".join(criteria_met)
        pokemon_name = hatch_data['pokemon_name']
        level = hatch_data['level']
        iv_display = format_iv_display(hatch_data['iv'])
        
        gender_emoji = get_gender_emoji(hatch_data.get('gender'))
        pokemon_display = f"{pokemon_name} {gender_emoji}" if gender_emoji else pokemon_name
        
        await ctx.reply(
            f"✅ Hatch sent to starboard!\n"
            f"**Criteria met:** {criteria_text}\n"
            f"**Pokémon:** {pokemon_display} (Level {level}, {iv_display})",
            mention_author=False
        )
    
    @egg_check_command.error
    async def egg_check_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You need administrator permissions to use this command.", mention_author=False)
        else:
            print(f"Unexpected error in eggcheck: {error}")
            await ctx.reply("❌ An unexpected error occurred. Please try again.", mention_author=False)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for Poketwo hatch messages"""
        if message.author.id != POKETWO_USER_ID:
            return
        
        # Check if it's a hatch message
        if "has hatched into" in message.content and "Egg" in message.content:
            hatched_by_id = await self.get_hatched_by_user(message)
            hatch_data = self.parse_poketwo_hatch_message(message.content, hatched_by_id)
            
            if not hatch_data:
                return
            
            # Check if should be logged
            if self.should_log_hatch(hatch_data):
                await self.send_to_starboard_channels(message.guild, hatch_data, message)

async def setup(bot):
    await bot.add_cog(StarboardEgg(bot))
