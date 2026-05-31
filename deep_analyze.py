#!/usr/bin/env python3
"""深度分析1C页面结构"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def deep_analyze():
    """深度分析页面结构"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # 加载保存的会话
        session_file = Path("data/session.json")
        if session_file.exists():
            cookies = json.loads(session_file.read_text())
            await context.add_cookies(cookies)
            print("已加载会话")
        
        # 访问主页
        await page.goto("https://clobus.uz/a/acc314/53211/en/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # 1. 分析页面结构
        print("\n" + "="*60)
        print("1. 页面基本信息")
        print("="*60)
        print(f"标题: {await page.title()}")
        print(f"URL: {page.url}")
        
        # 2. 查找导航菜单
        print("\n" + "="*60)
        print("2. 导航菜单分析")
        print("="*60)
        
        nav_selectors = [
            "nav", ".nav", "[role='navigation']", 
            ".commandInterface", ".menu", ".sidebar"
        ]
        
        for sel in nav_selectors:
            elements = await page.query_selector_all(sel)
            if elements:
                print(f"\n找到 {sel}: {len(elements)} 个元素")
        
        # 查找所有链接
        print("\n3. 所有链接分析")
        links = await page.query_selector_all("a[href*='e1cib']")
        print(f"找到 {len(links)} 个系统内链接:")
        for i, link in enumerate(links[:30]):
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text())[:50].strip()
            title = await link.get_attribute("title") or ""
            if href:
                print(f"  {i+1}. {text} -> {href[:80]}")
                if title:
                    print(f"     (title: {title})")
        
        # 4. 查找数据表格
        print("\n" + "="*60)
        print("4. 数据表格分析")
        print("="*60)
        
        table_selectors = [
            "table.dataGrid",
            "table.vtable",
            ".dataGrid",
            "[class*='Grid']",
            "[class*='Table']"
        ]
        
        for sel in table_selectors:
            tables = await page.query_selector_all(sel)
            if tables:
                print(f"\n找到 {sel}: {len(tables)} 个")
                for table in tables[:2]:
                    rows = await table.query_selector_all("tbody tr, tr")
                    print(f"  表格行数: {len(rows)}")
        
        # 5. 查找按钮和命令
        print("\n" + "="*60)
        print("5. 按钮和命令分析")
        print("="*60)
        
        buttons = await page.query_selector_all("button, .commandButton, [class*='button']")
        print(f"找到 {len(buttons)} 个按钮")
        for btn in buttons[:10]:
            text = (await btn.inner_text())[:30].strip()
            title = await btn.get_attribute("title") or ""
            if text or title:
                print(f"  - {text or '(无文本)'} | {title[:40]}")
        
        # 6. 获取完整HTML用于进一步分析
        print("\n" + "="*60)
        print("6. 保存HTML用于分析")
        print("="*60)
        
        html = await page.content()
        Path("data/deep_analysis.html").write_text(html)
        print("已保存到 data/deep_analysis.html")
        
        # 7. 尝试导航到各个功能模块
        print("\n" + "="*60)
        print("7. 功能模块URL")
        print("="*60)
        
        # 常见的1C功能模块路径
        modules = [
            "/e1cib/app/Catalog.Партнеры",
            "/e1cib/app/Catalog.Номенклатура", 
            "/e1cib/app/Document.ЗаказКлиента",
            "/e1cib/app/InformationRegister.КурсыВалют",
        ]
        
        for module in modules:
            try:
                # 先检查链接是否存在
                link = await page.query_selector(f"a[href*='{module.split('.')[1]}']")
                if link:
                    href = await link.get_attribute("href")
                    print(f"  ✓ {module.split('.')[1]}: {href}")
                else:
                    print(f"  ? {module.split('.')[1]}: 未找到直接链接")
            except Exception as e:
                print(f"  ✗ {module}: {e}")
        
        # 截图
        await page.screenshot(path="data/deep_analysis.png", full_page=True)
        print("\n截图已保存到 data/deep_analysis.png")
        
        await browser.close()
        print("\n分析完成!")

if __name__ == "__main__":
    asyncio.run(deep_analyze())
