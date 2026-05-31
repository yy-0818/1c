"""登录认证模块"""
import asyncio
from typing import Optional

from ..core.config_loader import get_config, get_selectors
from ..utils.logger import get_logger
from .driver import BrowserDriver

logger = get_logger("auth")


class LoginError(Exception):
    """登录错误"""
    pass


class AuthManager:
    """认证管理器"""
    
    def __init__(self, driver: BrowserDriver):
        self.driver = driver
        self.config = get_config()
        self.selectors = get_selectors()
    
    async def login(self) -> bool:
        """
        执行登录流程
        
        Returns:
            bool: 登录是否成功
        """
        config = self.config
        selectors = self.selectors
        
        login_url = f"{config.clobus.url}{selectors.get('login', {}).get('url', '/')}"
        
        logger.info(f"正在访问登录页面: {login_url}")
        
        try:
            # 访问登录页面
            await self.driver.page.goto(login_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # 等待页面加载
            await self.driver.wait_for_element("body")
            
            # 查找用户名输入框
            username_selectors = selectors.get('login', {}).get('username_input', '').split(',')
            username_input = None
            for sel in username_selectors:
                sel = sel.strip()
                if not sel:
                    continue
                element = await self.driver.page.query_selector(sel)
                if element:
                    username_input = sel
                    break

            if not username_input:
                # 尝试更通用的选择器
                logger.info("尝试查找用户名输入框...")
                username_input = await self._find_input_by_placeholder(['username', 'логин', 'email'])
            
            if not username_input:
                # 截图以便调试
                await self.driver.screenshot("data/login_page_debug.png")
                raise LoginError("无法找到用户名输入框")
            
            logger.info(f"找到用户名输入框: {username_input}")
            
            # 输入用户名
            await self.driver.type_safe(username_input, config.clobus.username)
            await asyncio.sleep(0.5)
            
            # 查找密码输入框
            password_selectors = selectors.get('login', {}).get('password_input', '').split(', ')
            password_input = None
            for sel in password_selectors:
                sel = sel.strip()
                element = await self.driver.page.query_selector(sel)
                if element:
                    password_input = sel
                    break
            
            if not password_input:
                password_input = await self._find_input_by_placeholder(['password', 'пароль'])
            
            if not password_input:
                await self.driver.screenshot("data/password_field_debug.png")
                raise LoginError("无法找到密码输入框")
            
            logger.info(f"找到密码输入框: {password_input}")
            
            # 输入密码
            await self.driver.type_safe(password_input, config.clobus.password)
            await asyncio.sleep(0.5)
            
            # 查找提交按钮
            submit_selectors = selectors.get('login', {}).get('submit_button', '').split(', ')
            submit_button = None
            for sel in submit_selectors:
                sel = sel.strip()
                element = await self.driver.page.query_selector(sel)
                if element:
                    submit_button = sel
                    break
            
            if not submit_button:
                submit_button = await self._find_button(['войти', 'вход', 'enter', 'login', 'submit', 'авториз'])
            
            if not submit_button:
                await self.driver.screenshot("data/submit_button_debug.png")
                raise LoginError("无法找到登录按钮")
            
            logger.info(f"找到提交按钮: {submit_button}")
            
            # 点击登录
            await self.driver.page.click(submit_button)
            
            # 等待登录结果
            await asyncio.sleep(3)
            
            # 检查登录是否成功
            if await self._check_login_success():
                logger.info("登录成功!")
                await self.driver.save_session()
                return True
            else:
                await self.driver.screenshot("data/login_failed_debug.png")
                error_msg = await self._get_error_message()
                raise LoginError(f"登录失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"登录过程出错: {e}")
            await self.driver.screenshot("data/login_error.png")
            raise
    
    async def _find_input_by_placeholder(self, keywords: list) -> Optional[str]:
        """根据placeholder查找输入框"""
        # 获取所有input元素
        inputs = await self.driver.page.query_selector_all("input")
        
        for inp in inputs:
            placeholder = await inp.get_attribute("placeholder") or ""
            name = await inp.get_attribute("name") or ""
            inp_type = await inp.get_attribute("type") or ""
            
            placeholder_lower = placeholder.lower()
            name_lower = name.lower()
            
            for keyword in keywords:
                if keyword in placeholder_lower or keyword in name_lower:
                    # 返回完整的选择器表达式
                    if name:
                        return f"input[name='{name}']"
                    else:
                        # 使用 placeholder 属性
                        return f"input[placeholder*='{keyword}']"
        
        return None
    
    async def _find_button(self, keywords: list) -> Optional[str]:
        """根据文本查找按钮"""
        # 查找所有按钮
        buttons = await self.driver.page.query_selector_all("button, input[type='submit'], input[type='button']")
        
        for btn in buttons:
            text = await btn.inner_text() or ""
            value = await btn.get_attribute("value") or ""
            
            text_lower = (text + value).lower()
            
            for keyword in keywords:
                if keyword in text_lower:
                    # 尝试获取ID或类名作为选择器
                    btn_id = await btn.get_attribute("id")
                    if btn_id:
                        return f"button#{btn_id}"
                    
                    class_name = await btn.get_attribute("class")
                    if class_name:
                        return f"button.{class_name.split()[0]}"
                    
                    return "button"
        
        return None
    
    async def _check_login_success(self) -> bool:
        """检查登录是否成功"""
        selectors = self.selectors

        try:
            # 等待页面稳定
            await asyncio.sleep(2)

            # 检查当前URL
            current_url = self.driver.page.url
            logger.info(f"当前URL: {current_url}")

            # 如果URL包含 e1cib，说明已经进入主系统
            if 'e1cib' in current_url or 'oid2rp' in current_url:
                return True

            # 如果还在OpenID登录页，认为登录失败
            if 'openid' in current_url.lower():
                return False

            # 检查是否还在登录页
            login_indicators = [
                "input[name='openid.auth.user']",
                "input[name='openid.auth.pwd']",
                "input#submit_btn"
            ]

            for indicator in login_indicators:
                element = await self.driver.page.query_selector(indicator)
                if element:
                    return False

            return True

        except Exception as e:
            logger.error(f"检查登录状态出错: {e}")
            return False
    
    async def _get_error_message(self) -> str:
        """获取错误消息"""
        selectors = self.selectors
        
        error_selectors = selectors.get('login', {}).get('error_message', '').split(', ')
        
        for sel in error_selectors:
            sel = sel.strip()
            element = await self.driver.page.query_selector(sel)
            if element:
                text = await element.inner_text()
                if text:
                    return text
        
        # 通用错误选择器
        generic_errors = [
            ".alert-danger",
            ".error-message",
            "[class*='error']",
            "[class*='alert']"
        ]
        
        for sel in generic_errors:
            elements = await self.driver.page.query_selector_all(sel)
            for el in elements:
                text = await el.inner_text()
                if text and len(text) > 5:
                    return text
        
        return "未知错误"
    
    async def check_session(self) -> bool:
        """检查会话是否有效"""
        return await self.driver.is_logged_in()
