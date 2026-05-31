#!/usr/bin/env python3
"""探索1C Clobus登录后的页面结构"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def explore_page():
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
        
        # 访问主页
        print("\n访问主页...")
        await page.goto("https://clobus.uz/a/acc314/53211/en/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        print(f"当前URL: {page.url}")
        print(f"页面标题: {await page.title()}")
        
        # 截图
        await page.screenshot(path="data/explore_01_home.png", full_page=True)
        print("截图已保存: data/explore_01_home.png")
        
        # 分析页面结构
        print("\n=== 页面结构分析 ===")
        
        # 1. 查找所有链接
        links = await page.query_selector_all("a[href]")
        print(f"\n找到 {len(links)} 个链接")
        
        # 2. 查找导航相关元素
        nav_selectors = [
            "#captionbar",
            "#mainSurface", 
            ".commandInterface",
            "[class*='nav']",
            "[class*='menu']",
            "[class*='sidebar']"
        ]
        
        for sel in nav_selectors:
            elements = await page.query_selector_all(sel)
            if elements:
                print(f"\n{sel}: 找到 {len(elements)} 个")
        
        # 3. 查找iframe
        iframes = await page.query_selector_all("iframe")
        print(f"\n找到 {len(iframes)} 个iframe")
        
        # 4. 查找主要区域
        areas = await page.query_selector_all("[id*='Area'], [class*='area']")
        print(f"\n找到 {len(areas)} 个区域元素")
        
        # 5. 获取页面HTML片段
        print("\n=== 关键元素 ===")
        
        # 检查captionbar
        captionbar = await page.query_selector("#captionbar")
        if captionbar:
            html = await captionbar.inner_html()
            print(f"\nCaptionbar HTML (前500字符):\n{html[:500]}")
        
        # 检查mainSurface
        main = await page.query_selector("#mainSurface")
        if main:
            style = await main.get_attribute("style") or ""
            print(f"\nMainSurface style: {style[:200]}")
        
        # 6. 尝试查找导航菜单项
        print("\n=== 导航菜单 ===")
        menu_items = await page.query_selector_all("[class*='Command'], .commandInterface a, nav a")
        for i, item in enumerate(menu_items[:20]):
            text = (await item.inner_text() or "").strip()[:50]
            href = await item.get_attribute("href") or ""
            if text or href:
                print(f"  {i+1}. {text} -> {href[:80]}")
        
        # 7. 查找功能按钮
        print("\n=== 功能按钮 ===")
        buttons = await page.query_selector_all("button, [class*='button'], [class*='Command']")
        for btn in buttons[:15]:
            text = (await btn.inner_text() or "").strip()[:30]
            title = await btn.get_attribute("title") or ""
            if text or title:
                print(f"  - {text or '(无文本)'} | title: {title[:40]}")
        
        # 8. 检查是否有iframe需要切换
        print("\n=== 检查iframe ===")
        for i, iframe in enumerate(iframes):
            src = await iframe.get_attribute("src") or ""
            name = await iframe.get_attribute("name") or ""
            id = await iframe.get_attribute("id") or ""
            print(f"  iframe {i+1}: id={id}, name={name}, src={src[:80]}")
        
        # 9. 尝试直接访问数据页面
        print("\n=== 尝试访问数据页面 ===")
        test_urls = [
            "https://clobus.uz/a/acc314/53211/en/e1cib/app/Catalog.Партнеры",
            "https://clobus.uz/a/acc314/53211/en/e1cib/app/Catalog.Номенклатура",
            "https://clobus.uz/a/acc314/53211/en/e1cib/app/Document.ЗаказКлиента",
        ]
        
        for url in test_urls:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=5000)
                await asyncio.sleep(2)
                print(f"  ✓ {url.split('/')[-1]}: {page.url}")
                await page.screenshot(path=f"data/explore_{url.split('.')[-1]}.png")
            except Exception as e:
                print(f"  ✗ {url.split('/')[-1]}: {e}")
        
        # 返回主页
        await page.goto("https://clobus.uz/a/acc314/53211/en/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        print("\n\n探索完成!")
        print("浏览器将保持打开，按 Ctrl+C 关闭")
        
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(explore_page())
