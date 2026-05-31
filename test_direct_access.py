#!/usr/bin/env python3
"""测试直接访问数据页面"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def test_direct_access():
    """测试直接访问数据页面"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        # 加载会话
        session_file = Path("data/session.json")
        if session_file.exists():
            cookies = json.loads(session_file.read_text())
            await context.add_cookies(cookies)
            print("✓ 会话已加载")
        
        # 测试URL列表
        test_urls = [
            ("客户列表", "https://clobus.uz/a/acc314/53211/en/e1cib/app/DataProcessor.Партнеры.ListForm"),
            ("产品列表", "https://clobus.uz/a/acc314/53211/en/e1cib/app/Catalog.Номенклатура.ListForm"),
            ("订单列表", "https://clobus.uz/a/acc314/53211/en/e1cib/app/Document.ЗаказКлиента.ListForm"),
        ]
        
        for name, url in test_urls:
            print(f"\n{'='*50}")
            print(f"测试: {name}")
            print(f"URL: {url}")
            print('='*50)
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(3)
                
                print(f"当前URL: {page.url}")
                print(f"页面标题: {await page.title()}")
                
                # 截图
                filename = f"data/test_{name.replace('列表', '')}.png"
                await page.screenshot(path=filename, full_page=True)
                print(f"截图: {filename}")
                
                # 检查是否有数据
                rows = await page.query_selector_all("tbody tr")
                print(f"表格行数: {len(rows)}")
                
                if rows:
                    # 尝试获取第一行数据
                    first_row = rows[0]
                    cells = await first_row.query_selector_all("td")
                    print(f"第一行单元格数: {len(cells)}")
                    if cells:
                        text = await cells[0].inner_text()
                        print(f"第一列内容: {text[:50]}")
                
            except Exception as e:
                print(f"✗ 错误: {e}")
        
        print("\n\n测试完成!")
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_direct_access())
