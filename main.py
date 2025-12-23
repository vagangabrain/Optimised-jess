"""Main bot file"""
import os
import discord
import asyncio
import aiohttp
from discord.ext import commands
from database import Database
from predict import Prediction
from config import TOKEN

# Custom prefix function for case-insensitive prefixes
def get_prefix(bot, message):
    prefixes = ['m!', 'M!']
    content_lower = message.content.lower()
    
    for prefix in prefixes:
        prefix_lower = prefix.lower()
        if content_lower.startswith(prefix_lower):
            return message.content[:len(prefix)]
    
    return prefixes

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
    """Initialize the predictor"""
    try:
        bot.predictor = Prediction()
        print("✅ Predictor initialized")
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
    
    # Initialize components
    await initialize_http_session()
    
    initialization_tasks = [
        initialize_predictor(),
        initialize_database()
    ]
    
    await asyncio.gather(*initialization_tasks, return_exceptions=True)
    
    # Load cogs
    cogs_to_load = [
        'cogs.collection',
        'cogs.shiny_hunt',
        'cogs.settings',
        'cogs.prediction',
        'cogs.help',
    ]
    
    try:
        # Load Jishaku for debugging
        await bot.load_extension('jishaku')
        print("✅ Jishaku loaded")
    except Exception as e:
        print(f"⚠️ Could not load Jishaku: {e}")
    
    for cog in cogs_to_load:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded {cog}")
        except Exception as e:
            print(f"❌ Failed to load {cog}: {e}")
    
    print(f"✅ Bot ready! Serving {len(bot.guilds)} guilds")
    
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
