"""Main bot file"""
import os
import discord
import asyncio
import aiohttp
from discord.ext import commands
from database import Database
from predict import Prediction
from config import TOKEN, BOT_PREFIX

# Custom prefix function for case-insensitive prefixes
def get_prefix(bot, message):
    content_lower = message.content.lower()
    
    for prefix in BOT_PREFIX:
        prefix_lower = prefix.lower()
        if content_lower.startswith(prefix_lower):
            return message.content[:len(prefix)]
    
    return BOT_PREFIX

# Bot setup
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# Global instances
bot.db = None
bot.predictor = None
bot.http_session = None

async def initialize_predictor():
    """Initialize the predictor with dual model system"""
    try:
        bot.predictor = Prediction()
        print("✅ Predictor initialized (dual model system)")
    except Exception as e:
        print(f"❌ Failed to initialize predictor: {e}")

async def initialize_database():
    """Initialize MongoDB connection"""
    bot.db = Database()
    success = await bot.db.connect()
    return success

async def initialize_http_session():
    """Initialize aiohttp session"""
    timeout = aiohttp.ClientTimeout(total=10, connect=3)
    connector = aiohttp.TCPConnector(
        limit=100,
        limit_per_host=10,
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
    
    bot.http_session = aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers={'User-Agent': 'Pokemon-Helper-Bot/1.0'}
    )
    print("✅ HTTP session initialized")

async def keep_alive():
    """Keep Railway container alive"""
    while True:
        try:
            await asyncio.sleep(240)
            if bot.http_session:
                async with bot.http_session.get('https://httpbin.org/status/200') as resp:
                    pass
        except Exception:
            pass

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Bot prefix: {', '.join(BOT_PREFIX)}")
    
    # Initialize HTTP session first
    await initialize_http_session()
    
    # Initialize predictor (needs http_session for model downloads)
    await initialize_predictor()
    
    # Initialize models after predictor is created
    if bot.predictor and bot.http_session:
        try:
            print("Downloading and initializing prediction models...")
            await bot.predictor.initialize_models(bot.http_session)
            print("✅ Dual model system ready!")
        except Exception as e:
            print(f"❌ Failed to initialize models: {e}")
    
    # Initialize database
    await initialize_database()
    
    # Load cogs
    cogs_to_load = [
        'cogs.collection',
        'cogs.shiny_hunt',
        'cogs.settings',
        'cogs.prediction',
        'cogs.starboard_settings',
        'cogs.starboard_catch',
        'cogs.starboard_egg',
        'cogs.starboard_unbox',
        'cogs.help',
    ]
    
    try:
        # Load Jishaku for debugging
        await bot.load_extension('jishaku')
        print("✅ Jishaku loaded")
    except Exception as e:
        print(f"⚠️ Could not load Jishaku: {e}")
    
    loaded_count = 0
    failed_count = 0
    
    for cog in cogs_to_load:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded {cog}")
            loaded_count += 1
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")
            failed_count += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Bot ready!")
    print(f"📊 Loaded {loaded_count}/{len(cogs_to_load)} cogs")
    if failed_count > 0:
        print(f"⚠️ Failed to load {failed_count} cogs")
    print(f"🌐 Serving {len(bot.guilds)} guilds")
    print(f"👥 Serving {sum(g.member_count for g in bot.guilds)} users")
    print(f"🤖 Dual Model System: Primary (224x224) + Secondary (336x224)")
    print(f"{'='*50}\n")
    
    # Start keep-alive task
    asyncio.create_task(keep_alive())

@bot.event
async def on_message_edit(before, after):
    """Process edited messages as commands"""
    if after.author.bot:
        return
    
    if before.content == after.content:
        return
    
    await bot.process_commands(after)

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    # Ignore commands not found
    if isinstance(error, commands.CommandNotFound):
        return
    
    # Handle cooldown
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"⏳ This command is on cooldown. Try again in {error.retry_after:.1f}s", mention_author=False)
        return
    
    # Handle missing permissions
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ You don't have permission to use this command.", mention_author=False)
        return
    
    # Handle bot missing permissions
    if isinstance(error, commands.BotMissingPermissions):
        await ctx.reply("❌ I don't have the necessary permissions to execute this command.", mention_author=False)
        return
    
    # Handle missing required argument
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"❌ Missing required argument: `{error.param.name}`\nUse `m!help` for command usage.", mention_author=False)
        return
    
    # Handle bad argument
    if isinstance(error, commands.BadArgument):
        await ctx.reply(f"❌ Invalid argument provided.\nUse `m!help` for command usage.", mention_author=False)
        return
    
    # Log unexpected errors
    print(f"Unexpected error in command {ctx.command}: {error}")
    await ctx.reply("❌ An unexpected error occurred. Please try again later.", mention_author=False)

async def cleanup():
    """Clean up resources on shutdown"""
    if bot.http_session:
        await bot.http_session.close()
    
    if bot.db:
        bot.db.close()

def main():
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN environment variable not set")
        return
    
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Error: Invalid Discord token")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
    finally:
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(cleanup())
        except:
            pass

if __name__ == "__main__":
    main()
