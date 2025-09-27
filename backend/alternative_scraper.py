"""
Alternative Instagram scraper using different approaches
"""
import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AlternativeInstagramScraper:
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def scrape_profile(self, username: str) -> Dict[str, Any]:
        """Try multiple scraping approaches"""
        
        # Approach 1: Try Instagram's public API endpoints
        try:
            result = await self._scrape_via_public_api(username)
            if result and result.get('followers_count', 0) > 0:
                logger.info("Successfully scraped via public API")
                return result
        except Exception as e:
            logger.debug(f"Public API approach failed: {str(e)}")
        
        # Approach 2: Try scraping with different user agents and headers
        try:
            result = await self._scrape_with_headers(username)
            if result and result.get('followers_count', 0) > 0:
                logger.info("Successfully scraped with custom headers")
                return result
        except Exception as e:
            logger.debug(f"Custom headers approach failed: {str(e)}")
        
        # Approach 3: Try using Instagram's embed endpoint
        try:
            result = await self._scrape_via_embed(username)
            if result and result.get('followers_count', 0) > 0:
                logger.info("Successfully scraped via embed endpoint")
                return result
        except Exception as e:
            logger.debug(f"Embed approach failed: {str(e)}")
        
        # Return empty result if all approaches fail
        return {
            "username": username,
            "full_name": username,
            "profile_pic_url": None,
            "followers_count": 0,
            "following_count": 0,
            "posts_count": 0,
            "recent_posts": [],
            "last_updated": None
        }
    
    async def _scrape_via_public_api(self, username: str) -> Optional[Dict[str, Any]]:
        """Try to scrape using Instagram's public endpoints"""
        try:
            # Try the profile page with minimal headers
            url = f"https://www.instagram.com/{username}/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Try to extract JSON data
                    json_match = re.search(r'window\._sharedData\s*=\s*({.+?});', content)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        if 'entry_data' in data and 'ProfilePage' in data['entry_data']:
                            user_data = data['entry_data']['ProfilePage'][0]['graphql']['user']
                            
                            # Extract posts
                            posts = []
                            edges = user_data.get('edge_owner_to_timeline_media', {}).get('edges', [])
                            for edge in edges[:12]:
                                node = edge.get('node', {})
                                posts.append({
                                    "image_url": node.get('display_url', ''),
                                    "caption": node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                                    "timestamp": None
                                })
                            
                            return {
                                "username": user_data.get('username', username),
                                "full_name": user_data.get('full_name', username),
                                "profile_pic_url": user_data.get('profile_pic_url_hd') or user_data.get('profile_pic_url'),
                                "followers_count": user_data.get('edge_followed_by', {}).get('count', 0),
                                "following_count": user_data.get('edge_follow', {}).get('count', 0),
                                "posts_count": user_data.get('edge_owner_to_timeline_media', {}).get('count', 0),
                                "recent_posts": posts,
                                "last_updated": None
                            }
        except Exception as e:
            logger.debug(f"Public API scraping failed: {str(e)}")
        
        return None
    
    async def _scrape_with_headers(self, username: str) -> Optional[Dict[str, Any]]:
        """Try scraping with different headers and approaches"""
        try:
            # Try with mobile user agent
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            url = f"https://www.instagram.com/{username}/"
            async with self.session.get(url, headers=mobile_headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Look for any numbers that might be follower counts
                    numbers = re.findall(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)', content)
                    if numbers:
                        # Try to extract meaningful data
                        return {
                            "username": username,
                            "full_name": username,
                            "profile_pic_url": None,
                            "followers_count": 0,
                            "following_count": 0,
                            "posts_count": 0,
                            "recent_posts": [],
                            "last_updated": None
                        }
        except Exception as e:
            logger.debug(f"Mobile headers approach failed: {str(e)}")
        
        return None
    
    async def _scrape_via_embed(self, username: str) -> Optional[Dict[str, Any]]:
        """Try using Instagram's embed endpoint"""
        try:
            embed_url = f"https://www.instagram.com/{username}/embed/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            async with self.session.get(embed_url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Look for follower count in embed
                    follower_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?[KMB]?)\s*followers', content, re.IGNORECASE)
                    if follower_match:
                        return {
                            "username": username,
                            "full_name": username,
                            "profile_pic_url": None,
                            "followers_count": 0,  # Would need to parse the number
                            "following_count": 0,
                            "posts_count": 0,
                            "recent_posts": [],
                            "last_updated": None
                        }
        except Exception as e:
            logger.debug(f"Embed approach failed: {str(e)}")
        
        return None

async def scrape_instagram_profile_alternative(username: str) -> Dict[str, Any]:
    """Alternative scraping function"""
    async with AlternativeInstagramScraper() as scraper:
        return await scraper.scrape_profile(username)

# Test function
if __name__ == "__main__":
    async def test():
        result = await scrape_instagram_profile_alternative("kbv_kishore")
        print(json.dumps(result, indent=2))
    
    asyncio.run(test())
