from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "insta_analytics")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "profiles")

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_URL)
db = client[DATABASE_NAME]
profiles = db[COLLECTION_NAME]

async def init_indexes():
    """Create necessary indexes for the profiles collection"""
    try:
        # Create index on username (unique)
        await profiles.create_index("username", unique=True)
        
        # Create index on last_updated for cache management
        await profiles.create_index("last_updated")
        
    except Exception as e:
        print(f"Error creating indexes: {str(e)}")

async def get_cached_profile(username: str, cache_duration: int = 24) -> dict:
    """Get cached profile if not expired"""
    return await profiles.find_one({
        "username": username.lower(),
        "last_updated": {"$gte": datetime.utcnow() - timedelta(hours=cache_duration)}
    })

async def update_profile(username: str, profile_data: dict) -> dict:
    """Update or insert profile data"""
    await profiles.update_one(
        {"username": username.lower()},
        {"$set": profile_data},
        upsert=True
    )
    return profile_data