#!/usr/bin/env python3
"""探索1C页面结构 - 直接访问目标URL"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def explore():
    """探索页面结构"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # 加载会话
        session_file = Path("data/session.json")
        if session_file.exists():
            cookies = json.loads(session_file.read_text())
            await context.add_cookies(cookies)
            print("已加载会话")
        
        # 直接访问目标页面
        target_url = "https://clobus.uz/a/acc314/53211/en/"
        print(f"\n访问: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        print(f"当前URL: {page.url}")
        print(f"页面标题: {await page.title()}")
        
        # 截图
        await page.screenshot(path="data/explore_01_initial.png", full_page=True)
        print("截图: data/explore_01_initial.png")
        
        # 分析页面
        print("\n=== 分析页面元素 ===")
        
        # 检查关键元素
        key_elements = {
            "captionbar": "#captionbar",
            "mainSurface": "#mainSurface", 
            "commandInterface": ".commandInterface",
            "导航栏": "[class*='nav']",
            "菜单": "[class*='menu']",
            "iframe": "iframe"
        }
        
        for name, selector in key_elements.items():
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"✓ {name}: 找到 {len(elements)} 个")
        
        # 获取body内容概览
        body = await page.query_selector("body")
        if body:
            children_count = len(await body.query_selector_all("> *"))
            print(f"\nbody直接子元素数量: {children_count}")
        
        # 检查所有iframe
        print("\n=== Iframe分析 ===")
        iframes = await page.query_selector_all("iframe")
        for i, iframe in enumerate(iframes):
            attrs = {
                "id": await iframe.get_attribute("id") or "",
                "name": await iframe.get_attribute("name") or "",
                "src": await iframe.get_attribute("src") or "",
                "class": await iframe.get_attribute("class") or ""
            }
            print(f"iframe {i+1}: {attrs}")
        
        # 查找所有链接
        print("\n=== 所有链接 ===")
        links = await page.query_selector_all("a[href]")
        print(f"总链接数: {len(links)}")
        
        for link in links[:30]:
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text() or "").strip()[:40]
            if href:
                print(f"  {text} -> {href[:80]}")
        
        # 查找所有按钮
        print("\n=== 按钮 ===")
        buttons = await page.query_selector_all("button")
        for btn in buttons[:15]:
            text = (await btn.inner_text() or "").strip()[:30]
            title = await btn.get_attribute("title") or ""
            print(f"  {text or '(无文本)'} | {title[:40]}")
        
        print("\n\n按 Ctrl+C 关闭浏览器")
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(explore())
