from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .instagram_scraper import scrape_instagram_profile, InstagramScraperError
import motor.motor_asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
CACHE_DURATION = int(os.getenv("CACHE_DURATION", "24"))  # Cache duration in hours

# Initialize FastAPI app
app = FastAPI(title="Instagram Analytics API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MongoDB
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client["insta_analytics"]
profiles = db["profiles"]


from datetime import datetime

def serialize_profile(profile: dict) -> dict:
    """Convert Mongo ObjectId and ensure consistent data types"""
    serialized = {}
    
    # Convert ObjectId to string
    if "_id" in profile:
        serialized["_id"] = str(profile["_id"])
    
    # Copy basic fields
    serialized["username"] = profile["username"]
    serialized["full_name"] = profile.get("full_name", profile["username"])
    serialized["profile_pic_url"] = profile.get("profile_pic_url", "")
    
    # Ensure consistent integer types for counts
    serialized["followers_count"] = int(profile.get("followers_count", 0))
    serialized["following_count"] = int(profile.get("following_count", 0))
    serialized["posts_count"] = int(profile.get("posts_count", 0))
    
    # Handle recent posts
    serialized["recent_posts"] = profile.get("recent_posts", [])
    
    # Handle last_updated
    last_updated = profile.get("last_updated")
    if isinstance(last_updated, str):
        serialized["last_updated"] = last_updated
    elif isinstance(last_updated, datetime):
        serialized["last_updated"] = last_updated.isoformat()
    else:
        serialized["last_updated"] = datetime.utcnow().isoformat()
    
    return serialized

@app.get("/api/profile/{username}")
async def get_profile(username: str, force_refresh: bool = False):
    try:
        logger.info(f"Fetching profile for username: {username} (force_refresh: {force_refresh})")
        
        # Check MongoDB cache if not forcing refresh
        if not force_refresh:
            profile = await profiles.find_one({"username": username.lower()})
            logger.debug(f"Cache lookup result: {profile is not None}")
            
            # If profile exists and is not expired
            if profile:
                try:
                    if isinstance(profile["last_updated"], str):
                        last_updated = datetime.fromisoformat(profile["last_updated"])
                    else:
                        last_updated = profile["last_updated"]
                        
                    if datetime.utcnow() - last_updated < timedelta(hours=CACHE_DURATION):
                        # Only return cache if it has posts
                        if profile.get("recent_posts") and len(profile["recent_posts"]) > 0:
                            logger.info("Returning cached profile with posts")
                            return serialize_profile(profile)
                        else:
                            logger.info("Cached profile has no posts, fetching fresh data")
                except Exception as e:
                    logger.error(f"Error processing cached profile: {str(e)}")
        
        # Scrape fresh data from Instagram
        logger.info("Scraping fresh profile data")
        data = await scrape_instagram_profile(username)
        
        if not data:
            raise InstagramScraperError("Failed to scrape profile data")
            
        logger.debug(f"Scraped data: {data}")
        
        # Update or insert in MongoDB
        await profiles.update_one(
            {"username": username.lower()},
            {"$set": data},
            upsert=True
        )
        
        serialized_data = serialize_profile(data)
        logger.debug(f"Serialized response: {serialized_data}")
        return serialized_data
        
    except InstagramScraperError as e:
        logger.error(f"Scraper error for {username}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error for {username}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    try:
        # Check MongoDB connection
        await client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.get("/api/debug/{username}")
async def debug_profile(username: str):
    """Debug endpoint for testing scraper"""
    try:
        profile_data = await scrape_instagram_profile(username)
        return {
            "success": True,
            "data": profile_data,
            "raw_metrics": {
                "posts": profile_data["posts_count"],
                "followers": profile_data["followers_count"],
                "following": profile_data["following_count"]
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
