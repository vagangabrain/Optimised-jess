"""Database operations and connection management"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional
from config import MONGODB_URI, DB_TIMEOUT_MS, DB_MAX_POOL_SIZE, DB_MIN_POOL_SIZE

class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        """Initialize MongoDB connection"""
        try:
            if not MONGODB_URI:
                print("Warning: MONGODB_URI not set, database features disabled")
                return False

            connection_config = {
                "serverSelectionTimeoutMS": DB_TIMEOUT_MS,
                "connectTimeoutMS": 5000,
                "socketTimeoutMS": 10000,
                "maxPoolSize": DB_MAX_POOL_SIZE,
                "minPoolSize": DB_MIN_POOL_SIZE,
                "maxIdleTimeMS": 30000,
                "retryWrites": True,
                "w": "majority"
            }

            self.client = AsyncIOMotorClient(MONGODB_URI, **connection_config)
            await asyncio.wait_for(self.client.admin.command('ping'), timeout=3)
            self.db = self.client.pokemon_collector

            await self._create_indexes()
            print("✅ Database connected successfully")
            return True

        except asyncio.TimeoutError:
            print("❌ Database connection timeout - features disabled")
            return False
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)[:100]}")
            return False

    async def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Collections
            await self.db.collections.create_index([("user_id", 1), ("guild_id", 1)])
            await self.db.collections.create_index("pokemon")

            # Shiny hunts
            await self.db.shiny_hunts.create_index([("user_id", 1), ("guild_id", 1)])
            await self.db.shiny_hunts.create_index("pokemon")

            # AFK users
            await self.db.collection_afk_users.create_index([("user_id", 1), ("guild_id", 1)])
            await self.db.shiny_hunt_afk_users.create_index([("user_id", 1), ("guild_id", 1)])

            # Rare pings
            await self.db.rare_pings.create_index([("user_id", 1), ("guild_id", 1)])

            # Guild settings - unique index on guild_id
            await self.db.guild_settings.create_index("guild_id", unique=True)

            # Global settings - NO index needed, _id is already unique by default
            # MongoDB automatically creates a unique index on _id field
            # So we don't need to create any additional indexes here

            print("✅ Database indexes created")
        except Exception as e:
            print(f"Warning: Could not create indexes: {e}")
            
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()

    # Collection operations
    async def add_pokemon_to_collection(self, user_id: int, guild_id: int, pokemon_names: List[str]):
        """Add Pokemon to user's collection"""
        await self.db.collections.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {"$addToSet": {"pokemon": {"$each": pokemon_names}}},
            upsert=True
        )

    async def remove_pokemon_from_collection(self, user_id: int, guild_id: int, pokemon_names: List[str]):
        """Remove Pokemon from user's collection"""
        result = await self.db.collections.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {"$pullAll": {"pokemon": pokemon_names}}
        )
        return result.modified_count > 0

    async def clear_collection(self, user_id: int, guild_id: int):
        """Clear user's entire collection"""
        result = await self.db.collections.delete_one(
            {"user_id": user_id, "guild_id": guild_id}
        )
        return result.deleted_count > 0

    async def get_user_collection(self, user_id: int, guild_id: int) -> List[str]:
        """Get user's collection"""
        collection = await self.db.collections.find_one(
            {"user_id": user_id, "guild_id": guild_id}
        )
        return collection.get('pokemon', []) if collection else []

    async def get_collectors_for_pokemon(self, guild_id: int, pokemon_names: List[str], afk_users: List[int]) -> List[int]:
        """Get all users who have collected any of the Pokemon names"""
        afk_users_set = set(afk_users)
        collectors = []

        collections = await self.db.collections.find(
            {
                "guild_id": guild_id,
                "pokemon": {"$in": pokemon_names}
            },
            {"user_id": 1}
        ).to_list(length=None)

        for collection in collections:
            user_id = collection['user_id']
            if user_id not in afk_users_set:
                collectors.append(user_id)

        return collectors

    # Shiny hunt operations
    async def set_shiny_hunt(self, user_id: int, guild_id: int, pokemon_name: str):
        """Set user's shiny hunt"""
        await self.db.shiny_hunts.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {"$set": {"pokemon": pokemon_name}},
            upsert=True
        )

    async def clear_shiny_hunt(self, user_id: int, guild_id: int):
        """Clear user's shiny hunt"""
        result = await self.db.shiny_hunts.delete_one(
            {"user_id": user_id, "guild_id": guild_id}
        )
        return result.deleted_count > 0

    async def get_user_shiny_hunt(self, user_id: int, guild_id: int) -> Optional[str]:
        """Get user's current shiny hunt"""
        hunt = await self.db.shiny_hunts.find_one(
            {"user_id": user_id, "guild_id": guild_id}
        )
        return hunt.get('pokemon') if hunt else None

    async def get_shiny_hunters_for_pokemon(self, guild_id: int, pokemon_names: List[str], afk_users: List[int]) -> List[int]:
        """Get all users hunting any of the Pokemon names"""
        afk_users_set = set(afk_users)
        hunters = []

        hunts = await self.db.shiny_hunts.find(
            {
                "guild_id": guild_id,
                "pokemon": {"$in": pokemon_names}
            },
            {"user_id": 1}
        ).to_list(length=None)

        for hunt in hunts:
            user_id = hunt['user_id']
            hunters.append((user_id, user_id in afk_users_set))

        return hunters

    # AFK operations
    async def get_collection_afk_users(self, guild_id: int) -> List[int]:
        """Get list of collection AFK users"""
        afk_docs = await self.db.collection_afk_users.find(
            {"guild_id": guild_id, "afk": True},
            {"user_id": 1}
        ).to_list(length=None)
        return [doc['user_id'] for doc in afk_docs]

    async def get_shiny_hunt_afk_users(self, guild_id: int) -> List[int]:
        """Get list of shiny hunt AFK users"""
        afk_docs = await self.db.shiny_hunt_afk_users.find(
            {"guild_id": guild_id, "afk": True},
            {"user_id": 1}
        ).to_list(length=None)
        return [doc['user_id'] for doc in afk_docs]

    async def toggle_collection_afk(self, user_id: int, guild_id: int) -> bool:
        """Toggle collection AFK status. Returns new state"""
        current = await self.db.collection_afk_users.find_one(
            {"user_id": user_id, "guild_id": guild_id}
        )

        if current and current.get('afk'):
            await self.db.collection_afk_users.delete_one(
                {"user_id": user_id, "guild_id": guild_id}
            )
            return False
        else:
            await self.db.collection_afk_users.update_one(
                {"user_id": user_id, "guild_id": guild_id},
                {"$set": {"afk": True}},
                upsert=True
            )
            return True

    async def toggle_shiny_hunt_afk(self, user_id: int, guild_id: int) -> bool:
        """Toggle shiny hunt AFK status. Returns new state"""
        current = await self.db.shiny_hunt_afk_users.find_one(
            {"user_id": user_id, "guild_id": guild_id}
        )

        if current and current.get('afk'):
            await self.db.shiny_hunt_afk_users.delete_one(
                {"user_id": user_id, "guild_id": guild_id}
            )
            return False
        else:
            await self.db.shiny_hunt_afk_users.update_one(
                {"user_id": user_id, "guild_id": guild_id},
                {"$set": {"afk": True}},
                upsert=True
            )
            return True

    async def is_collection_afk(self, user_id: int, guild_id: int) -> bool:
        """Check if user is collection AFK"""
        afk_doc = await self.db.collection_afk_users.find_one(
            {"user_id": user_id, "guild_id": guild_id}
        )
        return afk_doc and afk_doc.get('afk', False)

    async def is_shiny_hunt_afk(self, user_id: int, guild_id: int) -> bool:
        """Check if user is shiny hunt AFK"""
        afk_doc = await self.db.shiny_hunt_afk_users.find_one(
            {"user_id": user_id, "guild_id": guild_id}
        )
        return afk_doc and afk_doc.get('afk', False)

    # Rare pings
    async def get_rare_collectors(self, guild_id: int, afk_users: List[int]) -> List[int]:
        """Get users who want rare pings"""
        afk_users_set = set(afk_users)
        collectors = []

        rare_users = await self.db.rare_pings.find(
            {"guild_id": guild_id, "enabled": True},
            {"user_id": 1}
        ).to_list(length=None)

        for user_doc in rare_users:
            user_id = user_doc['user_id']
            if user_id not in afk_users_set:
                collectors.append(user_id)

        return collectors

    # Guild settings
    async def get_guild_settings(self, guild_id: int) -> dict:
        """Get all guild settings"""
        settings = await self.db.guild_settings.find_one({"guild_id": guild_id})
        return settings or {}

    async def set_rare_role(self, guild_id: int, role_id: int):
        """Set rare ping role"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"rare_role_id": role_id}},
            upsert=True
        )

    async def set_regional_role(self, guild_id: int, role_id: int):
        """Set regional ping role"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"regional_role_id": role_id}},
            upsert=True
        )

    async def set_low_prediction_channel(self, channel_id: int):
        """Set global low prediction channel"""
        await self.db.global_settings.update_one(
            {"_id": "prediction"},
            {"$set": {"low_prediction_channel_id": channel_id}},
            upsert=True
        )

    async def get_low_prediction_channel(self) -> Optional[int]:
        """Get global low prediction channel"""
        settings = await self.db.global_settings.find_one({"_id": "prediction"})
        return settings.get('low_prediction_channel_id') if settings else None

    # Add to Database class in database.py

    # Starboard channel settings
    async def set_starboard_catch_channel(self, guild_id: int, channel_id: int):
        """Set catch starboard channel"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"starboard_catch_channel_id": channel_id}},
            upsert=True
        )

    async def set_starboard_egg_channel(self, guild_id: int, channel_id: int):
        """Set egg starboard channel"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"starboard_egg_channel_id": channel_id}},
            upsert=True
        )

    async def set_starboard_unbox_channel(self, guild_id: int, channel_id: int):
        """Set unbox starboard channel"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"starboard_unbox_channel_id": channel_id}},
            upsert=True
        )

    async def set_starboard_shiny_channel(self, guild_id: int, channel_id: int):
        """Set shiny catch starboard channel"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"starboard_shiny_channel_id": channel_id}},
            upsert=True
        )

    async def set_starboard_gigantamax_channel(self, guild_id: int, channel_id: int):
        """Set Gigantamax catch starboard channel"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"starboard_gigantamax_channel_id": channel_id}},
            upsert=True
        )

    async def set_starboard_highiv_channel(self, guild_id: int, channel_id: int):
        """Set high IV starboard channel"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"starboard_highiv_channel_id": channel_id}},
            upsert=True
        )

    async def set_starboard_lowiv_channel(self, guild_id: int, channel_id: int):
        """Set low IV starboard channel"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"starboard_lowiv_channel_id": channel_id}},
            upsert=True
        )

    async def set_starboard_missingno_channel(self, guild_id: int, channel_id: int):
        """Set MissingNo starboard channel"""
        await self.db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {"starboard_missingno_channel_id": channel_id}},
            upsert=True
        )

    # Global starboard channels
    async def set_global_starboard_catch_channel(self, channel_id: int):
        """Set global catch starboard channel"""
        await self.db.global_settings.update_one(
            {"_id": "starboard_catch"},
            {"$set": {"global_channel_id": channel_id}},
            upsert=True
        )

    async def get_global_starboard_catch_channel(self) -> Optional[int]:
        """Get global catch starboard channel"""
        settings = await self.db.global_settings.find_one({"_id": "starboard_catch"})
        return settings.get('global_channel_id') if settings else None

    async def set_global_starboard_egg_channel(self, channel_id: int):
        """Set global egg starboard channel"""
        await self.db.global_settings.update_one(
            {"_id": "starboard_egg"},
            {"$set": {"global_channel_id": channel_id}},
            upsert=True
        )

    async def get_global_starboard_egg_channel(self) -> Optional[int]:
        """Get global egg starboard channel"""
        settings = await self.db.global_settings.find_one({"_id": "starboard_egg"})
        return settings.get('global_channel_id') if settings else None

    async def set_global_starboard_unbox_channel(self, channel_id: int):
        """Set global unbox starboard channel"""
        await self.db.global_settings.update_one(
            {"_id": "starboard_unbox"},
            {"$set": {"global_channel_id": channel_id}},
            upsert=True
        )

    async def get_global_starboard_unbox_channel(self) -> Optional[int]:
        """Get global unbox starboard channel"""
        settings = await self.db.global_settings.find_one({"_id": "starboard_unbox"})
        return settings.get('global_channel_id') if settings else None
