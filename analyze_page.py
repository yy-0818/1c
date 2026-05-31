"""页面结构分析脚本 - 帮助用户找到正确的选择器"""
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

# 用户账户
CLOCUS_URL = "https://clobus.uz"
USERNAME = "Guzalruz_2577@mail.ru"
PASSWORD = "fUnu2ru"
LOGIN_PATH = "/a/acc314/53211/en/"


async def analyze_login_page():
    """分析登录页面结构"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 访问登录页面
        login_url = f"{CLOCUS_URL}{LOGIN_PATH}"
        print(f"访问: {login_url}")
        await page.goto(login_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # 保存截图
        await page.screenshot(path="data/analyze_login.png", full_page=True)
        print("截图已保存: data/analyze_login.png")
        
        # 分析页面元素
        print("\n" + "=" * 60)
        print("页面元素分析")
        print("=" * 60)
        
        # 1. 查找所有input元素
        print("\n1. 所有输入框 (input):")
        inputs = await page.query_selector_all("input")
        for i, inp in enumerate(inputs):
            inp_type = await inp.get_attribute("type") or "text"
            name = await inp.get_attribute("name") or ""
            placeholder = await inp.get_attribute("placeholder") or ""
            id = await inp.get_attribute("id") or ""
            class_name = await inp.get_attribute("class") or ""
            print(f"   [{i}] type={inp_type}, name={name}, id={id}, placeholder={placeholder[:30]}")
        
        # 2. 查找所有按钮
        print("\n2. 所有按钮 (button, input[type=button/submit]):")
        buttons = await page.query_selector_all("button, input[type='button'], input[type='submit']")
        for i, btn in enumerate(buttons):
            text = await btn.inner_text()
            btn_type = await btn.get_attribute("type") or ""
            class_name = await btn.get_attribute("class") or ""
            print(f"   [{i}] text={text[:40]}, type={btn_type}")
        
        # 3. 查找form元素
        print("\n3. 表单 (form):")
        forms = await page.query_selector_all("form")
        for i, form in enumerate(forms):
            action = await form.get_attribute("action") or ""
            method = await form.get_attribute("method") or ""
            print(f"   [{i}] action={action}, method={method}")
        
        # 4. 查找可能的登录相关元素
        print("\n4. 查找登录相关元素:")
        login_keywords = ["login", "войти", "вход", "enter", "логин", "email", "username", "password", "auth"]
        
        all_text_elements = await page.query_selector_all("a, span, div, label")
        for el in all_text_elements[:100]:
            text = await el.inner_text()
            if text:
                text_lower = text.lower().strip()
                for keyword in login_keywords:
                    if keyword in text_lower and len(text.strip()) < 50:
                        tag = await el.evaluate("el => el.tagName")
                        print(f"   {tag}: {text.strip()[:50]}")
                        break
        
        # 5. 获取页面标题和URL
        print(f"\n5. 页面信息:")
        print(f"   标题: {await page.title()}")
        print(f"   URL: {page.url}")
        
        # 6. 获取HTML片段
        html_file = Path("data/login_page_html.html")
        html_content = await page.content()
        html_file.write_text(html_content, encoding='utf-8')
        print(f"\n6. 完整HTML已保存: {html_file}")
        
        # 7. 等待用户输入
        print("\n" + "=" * 60)
        print("请在浏览器中查看登录页面")
        print("如果需要手动登录，请输入任何内容后按回车继续...")
        print("=" * 60)
        input()
        
        # 登录后截图
        await page.screenshot(path="data/analyze_after_login.png", full_page=True)
        print("登录后截图已保存: data/analyze_after_login.png")
        
        # 保存登录后的HTML
        html_content = await page.content()
        Path("data/after_login_html.html").write_text(html_content, encoding='utf-8')
        print("登录后HTML已保存: data/after_login_html.html")
        
        # 分析登录后的页面结构
        print("\n" + "=" * 60)
        print("登录后页面结构分析")
        print("=" * 60)
        
        # 查找导航菜单
        nav_selectors = ["nav", "[role='navigation']", "aside", "[class*='sidebar']", "[class*='menu']"]
        for sel in nav_selectors:
            elements = await page.query_selector_all(sel)
            if elements:
                print(f"\n找到导航: {sel} ({len(elements)}个)")
        
        # 查找主要链接
        print("\n查找主要链接:")
        links = await page.query_selector_all("a[href]")
        for link in links[:30]:
            href = await link.get_attribute("href") or ""
            text = await link.inner_text() or ""
            if href and (not href.startswith('#')):
                print(f"   {text[:30]:30} -> {href[:60]}")
        
        await browser.close()
        print("\n分析完成!")


async def test_login_with_selectors():
    """用找到的选择器测试登录"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        login_url = f"{CLOCUS_URL}{LOGIN_PATH}"
        print(f"访问: {login_url}")
        await page.goto(login_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # 尝试常见的选择器
        username_selectors = [
            "input[name='username']",
            "input[name='login']",
            "input[name='email']",
            "input[type='email']",
            "input[id='username']",
            "input[placeholder*='mail']",
            "input[placeholder*='email']",
            "input[autocomplete='username']",
        ]
        
        password_selectors = [
            "input[name='password']",
            "input[type='password']",
            "input[id='password']",
        ]
        
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Войти')",
            "button:has-text('Вход')",
            "button:has-text('Login')",
            "button:has-text('Sign in')",
        ]
        
        print("\n尝试查找用户名输入框:")
        for sel in username_selectors:
            element = await page.query_selector(sel)
            if element:
                print(f"  ✅ 找到: {sel}")
            else:
                print(f"  ❌ 未找到: {sel}")
        
        print("\n尝试查找密码输入框:")
        for sel in password_selectors:
            element = await page.query_selector(sel)
            if element:
                print(f"  ✅ 找到: {sel}")
            else:
                print(f"  ❌ 未找到: {sel}")
        
        print("\n尝试查找提交按钮:")
        for sel in submit_selectors:
            element = await page.query_selector(sel)
            if element:
                print(f"  ✅ 找到: {sel}")
            else:
                print(f"  ❌ 未找到: {sel}")
        
        await browser.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(test_login_with_selectors())
    else:
        asyncio.run(analyze_login_page())
