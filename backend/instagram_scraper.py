from playwright.async_api import async_playwright
import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InstagramScraperError(Exception):
    """Custom exception for Instagram scraper errors"""
    pass

async def parse_count(element) -> Optional[int]:
    """Parse Instagram number format (e.g., 1.2K, 1M) to integer"""
    try:
        text = await element.text_content()
        if not text:
            return None
            
        # Remove commas and convert to lowercase
        text = text.lower().replace(',', '').strip()
        
        # Extract number and multiplier using regex
        import re
        match = re.match(r'([\d,.]+)([kmb])?', text)
        if not match:
            return None
            
        number_str, suffix = match.groups()
        number = float(number_str.replace(',', ''))
        
        # Convert based on suffix
        multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}
        if suffix:
            number *= multipliers.get(suffix, 1)
            
        return int(number)
    except Exception as e:
        logger.error(f"Error parsing count from {text}: {str(e)}")
        return 0  # Return 0 instead of None for failed parses

import json
import re

async def get_shared_data(page) -> dict:
    """Extract shared data from Instagram page"""
    try:
        shared_data = await page.evaluate("""
            () => {
                const element = document.querySelector('script[type="text/javascript"]:not([src])');
                if (!element) return null;
                const match = element.textContent.match(/window\._sharedData = ({.+?});/);
                return match ? JSON.parse(match[1]) : null;
            }
        """)
        return shared_data
    except Exception as e:
        logger.error(f"Error extracting shared data: {str(e)}")
        return None

async def get_additional_data(page) -> dict:
    """Extract additional data from Instagram page"""
    try:
        additional_data = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script[type="text/javascript"]');
                for (const script of scripts) {
                    const match = script.textContent.match(/window\.__additionalDataLoaded\('.*?',(.*?)\);/);
                    if (match) return JSON.parse(match[1]);
                }
                return null;
            }
        """)
        return additional_data
    except Exception as e:
        logger.error(f"Error extracting additional data: {str(e)}")
        return None

# Common user agents for browser spoofing
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
]

async def scrape_instagram_profile(username: str, retries: int = 3) -> Dict[str, Any]:
    """
    Scrape Instagram profile data with retries and anti-detection measures
    
    Args:
        username (str): Instagram username to scrape
        retries (int): Number of retry attempts if scraping fails
    
    Returns:
        Dict[str, Any]: Profile data including metrics and recent posts
    """
    if not username:
        raise InstagramScraperError("Username cannot be empty")

    async def extract_post_data(post_link) -> dict:
        """Extract detailed data for a single post"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(post_link, timeout=30000)
                await page.wait_for_load_state('networkidle')
                
                # Get caption
                caption = ""
                caption_el = await page.query_selector('h1, [class*="caption"] span')
                if caption_el:
                    caption = await caption_el.text_content()
                
                # Get likes count
                likes = 0
                likes_el = await page.query_selector('[class*="like"] span')
                if likes_el:
                    likes_text = await likes_el.text_content()
                    likes = await parse_count(likes_el) or 0
                
                # Get comments count
                comments = 0
                comments_el = await page.query_selector('[class*="comment"] span')
                if comments_el:
                    comments = await parse_count(comments_el) or 0
                
                await browser.close()
                return {
                    "caption": caption,
                    "likes_count": likes,
                    "comments_count": comments
                }
        except Exception as e:
            logger.error(f"Error extracting post data: {str(e)}")
            return {"caption": "", "likes_count": 0, "comments_count": 0}

async def extract_ui_posts(page) -> list:
    """Extract posts from the UI by scrolling and parsing post elements"""
    try:
        posts = []
        seen_urls = set()

        # Scroll multiple times to load more posts
        for _ in range(3):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(2000)

        # Extract posts using JavaScript
        ui_posts = await page.evaluate("""
            () => {
                const posts = [];
                const seen = new Set();
                
                function extractPosts() {
                    // Get all post articles
                    document.querySelectorAll('article').forEach(article => {
                        // Get post link
                        const linkEl = article.querySelector('a[href*="/p/"]');
                        if (!linkEl) return;
                        
                        // Get image
                        const img = article.querySelector('img[src*="instagram"]');
                        if (!img || seen.has(img.src)) return;
                        
                        seen.add(img.src);
                        posts.push({
                            image_url: img.src,
                            post_url: linkEl.href,
                            temp_caption: img.alt || ''
                        });
                    });
                    
                    // Method 2: Grid items
                    document.querySelectorAll('div[style*="grid"] img[src*="instagram"]').forEach(img => {
                        if (!seen.has(img.src)) {
                            seen.add(img.src);
                            posts.push({
                                image_url: img.src,
                                caption: img.alt || ''
                            });
                        }
                    });
                }
                
                extractPosts();
                return posts;
            }
        """)

            # Process and deduplicate posts
        # Process the extracted posts
        for post in ui_posts:
            if post['image_url'] not in seen_urls:
                seen_urls.add(post['image_url'])
                post['timestamp'] = datetime.utcnow().isoformat()
                posts.append(post)
                if len(posts) >= 12:
                    break

            return posts
    except Exception as e:
        logger.error(f"Error extracting UI posts: {str(e)}")
        return []

    async def extract_post_details(post_url: str) -> dict:
        """Extract detailed data for a single post"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(post_url, timeout=30000)
                await page.wait_for_load_state('networkidle')
                
                # Get caption
                caption = ""
                caption_el = await page.query_selector('h1, [class*="caption"] span')
                if caption_el:
                    caption = await caption_el.text_content()
                
                # Get likes count
                likes = 0
                likes_el = await page.query_selector('[class*="like"] span')
                if likes_el:
                    likes = await parse_count(likes_el) or 0
                
                # Get comments count
                comments = 0
                comments_el = await page.query_selector('[class*="comment"] span')
                if comments_el:
                    comments = await parse_count(comments_el) or 0
                
                await browser.close()
                return {
                    "caption": caption,
                    "likes_count": likes,
                    "comments_count": comments
                }
        except Exception as e:
            logger.error(f"Error extracting post details: {str(e)}")
            return {"caption": "", "likes_count": 0, "comments_count": 0}

    # Main scraping loop
    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                # Launch browser with random user agent
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Enable request interception for GraphQL requests
                await page.route("**/*", lambda route: route.continue_())
                
                # Add random delay
                await page.wait_for_timeout(random.randint(2000, 4000))
                
                # Navigate to profile
                logger.info(f"Navigating to profile: {username}")
                await page.goto(f'https://www.instagram.com/{username}/', timeout=30000)
                await page.wait_for_load_state('networkidle')
                
                # Wait for content to load
                await page.wait_for_timeout(2000)
                
                # Get shared data
                shared_data = await get_shared_data(page)
                additional_data = await get_additional_data(page)
                
                logger.debug("Shared data retrieved: " + str(bool(shared_data)))
                logger.debug("Additional data retrieved: " + str(bool(additional_data)))
                
                # Extract profile data
                # Check if profile exists
                # Check various error conditions
                error_messages = [
                    'text="Sorry, this page isn\'t available."',
                    'text="Sorry, this page isn\'t available."',
                    'text="Page Not Found"',
                    '[data-testid="error-page"]'
                ]
                
                for selector in error_messages:
                    error_element = await page.query_selector(selector)
                    if error_element:
                        raise InstagramScraperError(f"Profile {username} does not exist")
                        
                # Also check the URL to see if we were redirected
                current_url = page.url
                if not username.lower() in current_url.lower():
                    raise InstagramScraperError(f"Profile {username} does not exist")

                # Extract metrics and basic info
                await page.wait_for_selector('header section ul', timeout=10000)
                
                # Get metrics
                metrics = await page.query_selector_all('header section ul li')
                if not metrics or len(metrics) < 3:
                    metrics = await page.query_selector_all('header ul li')
                
                if not metrics or len(metrics) < 3:
                    raise InstagramScraperError(f"Could not find metrics for {username}")
                
                # Parse counts
                posts_count = await parse_count(metrics[0])
                followers_count = await parse_count(metrics[1])
                following_count = await parse_count(metrics[2])
                
                # Get profile name
                name_el = await page.query_selector("header section h2, header h2")
                name = await name_el.text_content() if name_el else username
                
                # Get profile picture
                img_el = await page.query_selector("header img")
                profile_pic = await img_el.get_attribute("src") if img_el else None
                        
                        # Extract posts using UI scraping
                posts = await extract_ui_posts(page)
                logger.info(f"Found {len(posts)} posts using UI scraping")
                
                # Try GraphQL approach if we don't have enough posts
                if len(posts) < 10 and shared_data:
                    try:
                        if 'entry_data' in shared_data and 'ProfilePage' in shared_data['entry_data']:
                            user_data = shared_data['entry_data']['ProfilePage'][0]['graphql']['user']
                            edges = user_data.get('edge_owner_to_timeline_media', {}).get('edges', [])
                            
                            seen_urls = {p['image_url'] for p in posts}
                            
                            for edge in edges:
                                if len(posts) >= 12:
                                    break
                                    
                                node = edge['node']
                                image_url = node.get('display_url')
                                
                                if image_url and image_url not in seen_urls:
                                    caption = ""
                                    if node.get('edge_media_to_caption', {}).get('edges'):
                                        caption = node['edge_media_to_caption']['edges'][0]['node']['text']
                                    
                                    posts.append({
                                        'image_url': image_url,
                                        'caption': caption,
                                        'timestamp': datetime.utcnow().isoformat()
                                    })
                                    seen_urls.add(image_url)
                            
                            logger.info(f"Added {len(posts)} posts from GraphQL data")
                    except Exception as e:
                        logger.error(f"Error extracting additional posts from GraphQL: {str(e)}")
                
                # Sort posts by image URL to ensure consistent ordering
                posts.sort(key=lambda x: x['image_url'])
                # Initialize empty post list
                processed_posts = []
                try:
                    # Initial wait for content
                    await page.wait_for_load_state('networkidle')
                    
                    # Try to find and click "Load more posts" button if it exists
                    try:
                        load_more = await page.query_selector('text="Load more posts"')
                        if load_more:
                            await load_more.click()
                            await page.wait_for_timeout(2000)
                    except:
                        pass

                    # Scroll multiple times to ensure posts are loaded
                    previous_height = 0
                    scroll_attempts = 0
                    max_attempts = 5

                    while scroll_attempts < max_attempts:
                        # Scroll and wait
                        current_height = await page.evaluate('document.body.scrollHeight')
                        if current_height == previous_height:
                            break
                            
                        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        await page.wait_for_timeout(2000)  # Wait longer for content to load
                        
                        previous_height = current_height
                        scroll_attempts += 1

                    # Try to find posts using JavaScript evaluation with improved selectors
                    posts_data = await page.evaluate("""() => {
                        const posts = [];
                        
                        // Try different selectors for the posts grid
                        const gridSelectors = [
                            'article div[style*="grid"]',
                            'article div[class*="grid"]',
                            'main article',
                            'div[class*="Post"]'
                        ];
                        
                        let container = null;
                        for (const selector of gridSelectors) {
                            container = document.querySelector(selector);
                            if (container) break;
                        }
                        
                        if (!container) return posts;
                        
                        // Find all post elements
                        const postElements = container.querySelectorAll('a');
                        
                        for (const post of postElements) {
                            const img = post.querySelector('img');
                            if (!img) continue;
                            
                            const src = img.src;
                            if (!src || !src.includes('instagram')) continue;
                            
                            let caption = img.alt || '';
                            
                            // Try to find caption in surrounding elements
                            const captionEl = post.querySelector('span[class*="caption"], span[class*="Caption"], span[class*="alt"]');
                            if (captionEl) {
                                caption = captionEl.textContent || caption;
                            }
                            
                            posts.push({
                                image_url: src,
                                caption: caption,
                            });
                            
                            if (posts.length >= 12) break;  // Stop after finding 12 posts
                        }
                        
                        return posts;
                    }""")
                    
                    logger.debug(f"Found {len(posts_data)} posts using JavaScript evaluation")
                    
                    # If JavaScript evaluation didn't find enough posts, try alternative methods
                    if len(posts_data) < 10:
                        logger.debug("Not enough posts found, trying alternative methods")
                        
                        # Method 1: Try direct img selectors
                        post_selectors = [
                            'article a img[src*="instagram"]',
                            'article div[role="button"] img',
                            'main article img[src*="instagram"]',
                            'div[class*="Post"] img'
                        ]
                        
                        for selector in post_selectors:
                            if len(posts_data) >= 10:
                                break
                                
                            try:
                                images = await page.query_selector_all(selector)
                                logger.debug(f"Found {len(images)} images with selector: {selector}")
                                
                                for img in images:
                                    src = await img.get_attribute("src")
                                    if not src or not src.includes("instagram"):
                                        continue
                                        
                                    alt = await img.get_attribute("alt")
                                    posts_data.append({
                                        "image_url": src,
                                        "caption": alt or "",
                                    })
                                    
                                    if len(posts_data) >= 10:
                                        break
                            except Exception as e:
                                logger.debug(f"Error with selector {selector}: {str(e)}")
                                continue
                        
                        # Method 2: Try finding post links
                        if len(posts_data) < 10:
                            try:
                                post_links = await page.query_selector_all('a[href*="/p/"]')
                                for link in post_links:
                                    img = await link.query_selector('img[src*="instagram"]')
                                    if img:
                                        src = await img.get_attribute("src")
                                        alt = await img.get_attribute("alt")
                                        if src:
                                            posts_data.append({
                                                "image_url": src,
                                                "caption": alt or "",
                                            })
                                            
                                            if len(posts_data) >= 10:
                                                break
                            except Exception as e:
                                logger.debug(f"Error finding post links: {str(e)}")
                                
                        logger.debug(f"After alternative methods, found {len(posts_data)} posts")
                    
                    # Remove any duplicate posts based on image_url
                    seen_urls = set()
                    unique_posts = []
                    for post in posts_data:
                        if post["image_url"] not in seen_urls:
                            seen_urls.add(post["image_url"])
                            unique_posts.append(post)
                    
                    # Add timestamp and ensure we have at least some posts
                    posts = [{**post, "timestamp": datetime.utcnow().isoformat()} for post in unique_posts[:12]]
                    
                    if not posts:
                        logger.warning(f"No posts found for {username}")
                    else:
                        logger.info(f"Successfully retrieved {len(posts)} posts for {username}")
                        logger.debug("First post image URL: " + posts[0]["image_url"])
                        
                except Exception as e:
                    logger.error(f"Error fetching posts for {username}: {str(e)}")
                    # Log the full page HTML for debugging
                    page_content = await page.content()
                    logger.debug(f"Page HTML (first 1000 chars): {page_content[:1000]}")
                finally:
                    try:
                        await browser.close()
                    except:
                        pass
                
                # Return data with ISO formatted date
                return {
                    "username": username,
                    "full_name": name,
                    "profile_pic_url": profile_pic,
                    "followers_count": followers_count or 0,
                    "following_count": following_count or 0,
                    "posts_count": posts_count or 0,
                    "recent_posts": posts,
                    "last_updated": datetime.utcnow().isoformat()  # Convert to ISO string
                }
                
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{retries} failed for {username}: {str(e)}")
            if attempt == retries - 1:
                raise InstagramScraperError(f"Failed to scrape profile after {retries} attempts: {str(e)}")
            await asyncio.sleep(random.randint(3, 7))  # Random delay between retries

# Example usage for testing
if __name__ == "__main__":
    import json
    username = input("Enter Instagram username: ")
    profile = asyncio.run(scrape_instagram_profile(username))
    print(json.dumps(profile, indent=4))
