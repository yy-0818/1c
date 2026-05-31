"""详细分析登录页面结构"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def analyze():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("访问Clobus登录页面...")
        await page.goto("https://clobus.uz/a/acc314/53211/en/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # 保存截图
        await page.screenshot(path="data/analyze_full.png", full_page=True)

        # 获取所有input
        print("\n=== 所有INPUT元素 ===")
        inputs = await page.query_selector_all("input")
        for i, inp in enumerate(inputs):
            attrs = {}
            for attr in ["type", "name", "id", "placeholder", "class", "autocomplete", "value"]:
                val = await inp.get_attribute(attr)
                if val:
                    attrs[attr] = val
            print(f"[{i}] {attrs}")

        # 获取所有button
        print("\n=== 所有BUTTON元素 ===")
        buttons = await page.query_selector_all("button")
        for i, btn in enumerate(buttons):
            text = await btn.inner_text()
            attrs = {}
            for attr in ["type", "class", "id"]:
                val = await btn.get_attribute(attr)
                if val:
                    attrs[attr] = val
            print(f"[{i}] text='{text.strip()}' attrs={attrs}")

        # 获取页面body内容
        body_html = await page.inner_html("body")
        Path("data/clobus_login_body.html").write_text(body_html, encoding='utf-8')
        print(f"\n已保存HTML到 data/clobus_login_body.html")

        # 查找iframe
        print("\n=== IFRAME ===")
        iframes = await page.query_selector_all("iframe")
        for i, iframe in enumerate(iframes):
            src = await iframe.get_attribute("src")
            name = await iframe.get_attribute("name")
            print(f"[{i}] src={src}, name={name}")

        # 查找div和可能隐藏的元素
        print("\n=== 查找包含'input'的DIV ===")
        divs = await page.query_selector_all("div")
        for div in divs[:50]:
            div_html = await div.inner_html()
            if "input" in div_html.lower():
                text = await div.inner_text()
                print(f"  text='{text[:50]}...'")

        print("\n=== 等待手动检查 ===")
        print("请在浏览器中查看并登录...")
        input()

        # 登录后分析
        if "login" not in page.url.lower():
            print("\n登录成功！正在分析主页面...")

            # 保存登录后截图
            await page.screenshot(path="data/clobus_main.png", full_page=True)

            # 获取body
            body_html = await page.inner_html("body")
            Path("data/clobus_main_body.html").write_text(body_html, encoding='utf-8')

            # 查找导航
            print("\n=== 主页面导航 ===")
            nav_elements = await page.query_selector_all("nav, [role='navigation'], aside, [class*='sidebar'], [class*='menu']")
            for nav in nav_elements:
                tag = await nav.evaluate("el => el.tagName")
                class_name = await nav.get_attribute("class") or ""
                print(f"{tag}: class={class_name}")

            # 查找主要链接
            print("\n=== 主要链接 ===")
            links = await page.query_selector_all("a[href]")
            for link in links[:50]:
                href = await link.get_attribute("href") or ""
                text = await link.inner_text() or ""
                if href and "javascript" not in href:
                    print(f"  {text[:40]:40} -> {href[:60]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(analyze())
