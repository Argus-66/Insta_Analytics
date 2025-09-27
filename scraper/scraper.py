# scraper/scraper.py
from playwright.async_api import async_playwright
import asyncio
import json
import re

async def scrape_instagram_profile(username: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"https://www.instagram.com/{username}/", timeout=120000)

        # Wait for page to load
        await page.wait_for_selector("body", timeout=30000)

        # Get JSON from window._sharedData
        content = await page.content()
        m = re.search(r'window\._sharedData = (.*?);</script>', content)
        if not m:
            await browser.close()
            raise Exception("Cannot find JSON data on page")

        data = json.loads(m.group(1))
        user = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]

        profile_data = {
            "username": user["username"],
            "name": user.get("full_name"),
            "profile_pic": user.get("profile_pic_url_hd"),
            "followers": user["edge_followed_by"]["count"],
            "following": user["edge_follow"]["count"],
            "posts_count": user["edge_owner_to_timeline_media"]["count"],
            "recent_posts": []
        }

        edges = user["edge_owner_to_timeline_media"]["edges"]
        for edge in edges[:10]:
            node = edge["node"]
            profile_data["recent_posts"].append({
                "image": node.get("display_url"),
                "caption": node.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {}).get("text", "")
            })

        await browser.close()
        return profile_data

# Standalone test
if __name__ == "__main__":
    username = input("Enter Instagram username: ")
    profile = asyncio.run(scrape_instagram_profile(username))
    print(json.dumps(profile, indent=4))
