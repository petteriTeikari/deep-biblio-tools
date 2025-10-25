#!/usr/bin/env python3
"""Test basic Playwright functionality."""

import asyncio

from playwright.async_api import async_playwright


async def test_playwright():
    """Test basic Playwright setup."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Navigating to ScienceDirect...")
        await page.goto("https://www.sciencedirect.com")

        title = await page.title()
        print(f"Page title: {title}")

        await page.screenshot(path="sciencedirect_home.png")
        print("Screenshot saved to sciencedirect_home.png")

        await browser.close()
        print("Test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_playwright())
