"""登录认证模块"""
import asyncio
from typing import Optional

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from ..core.config_loader import get_config, get_selectors
from ..utils.logger import get_logger
from .driver import BrowserDriver

logger = get_logger("auth")


class LoginError(Exception):
    """登录错误"""
    pass


class PageState:
    """页面状态枚举"""
    LOADING = "loading"
    LOGIN_FORM = "login_form"
    LOGGED_IN = "logged_in"
    ERROR = "error"
    UNKNOWN = "unknown"


class AuthManager:
    """认证管理器"""
    
    def __init__(self, driver: BrowserDriver):
        self.driver = driver
        self.config = get_config()
        self.selectors = get_selectors()
    
    async def login(self, max_retries: int = 3) -> bool:
        """
        执行登录流程
        
        核心策略：
        1. 先判断是否已登录（通过1C主界面特征）
        2. 已登录：直接返回True
        3. 未登录：进入登录表单流程
        4. 遇到加载状态：等待加载完成后再判断
        """
        config = self.config
        selectors = self.selectors
        
        login_url = f"{config.clobus.url}{selectors.get('login', {}).get('url', '/')}"
        
        logger.info(f"正在访问: {login_url}")
        
        # 访问页面
        await self.driver.page.goto(login_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        for attempt in range(1, max_retries + 1):
            logger.info(f"检查状态 {attempt}/{max_retries}")
            
            # 分析当前页面状态（带重试，处理导航冲突）
            state = await self._safe_analyze_state()
            logger.info(f"页面状态: {state}")
            
            if state == PageState.LOGGED_IN:
                logger.info("已登录!")
                await self.driver.save_session()
                return True
            
            elif state == PageState.LOADING:
                # 正在加载，等待
                logger.info("页面加载中，等待...")
                if await self._wait_for_loading_complete(timeout=30000):
                    state = await self._safe_analyze_state()
                    logger.info(f"加载完成，状态: {state}")
                    if state == PageState.LOGGED_IN:
                        await self.driver.save_session()
                        return True
                    elif state == PageState.LOGIN_FORM:
                        pass  # 继续登录
                else:
                    logger.warning("等待加载超时")
            
            # 执行登录
            try:
                success = await self._do_login()
                if success:
                    return True
            except LoginError as e:
                logger.warning(f"登录失败: {e}")
            
            if attempt < max_retries:
                await asyncio.sleep(3)
        
        raise LoginError("登录失败")
    
    async def _safe_analyze_state(self) -> str:
        """安全地分析页面状态（处理导航冲突）"""
        try:
            return await self._analyze_page_state()
        except PlaywrightError as e:
            if "Execution context was destroyed" in str(e) or "Navigation" in str(e):
                logger.warning("页面正在导航，等待稳定...")
                await asyncio.sleep(2)
                try:
                    return await self._analyze_page_state()
                except Exception:
                    return PageState.LOADING
            raise
        except Exception as e:
            logger.warning(f"分析状态异常: {e}")
            return PageState.UNKNOWN
    
    async def _analyze_page_state(self) -> str:
        """分析当前页面状态"""
        page = self.driver.page
        current_url = page.url
        page_title = await page.title()
        
        # === 优先检查1C主界面特征 ===
        
        # 1. 检查标题
        if '1C:Enterprise' in page_title or '1С:Предприятие' in page_title:
            logger.info(f"检测到1C标题: {page_title}")
            return PageState.LOGGED_IN
        
        # 2. 检查captionbar（1C顶部栏）
        captionbar = await page.query_selector("#captionbar")
        if captionbar:
            is_visible = await captionbar.is_visible()
            if is_visible:
                logger.info("检测到captionbar（1C顶部栏）")
                return PageState.LOGGED_IN
        
        # 3. 检查mainSurface（1C主内容区）
        main_surface = await page.query_selector("#mainSurface")
        if main_surface:
            is_visible = await main_surface.is_visible()
            if is_visible:
                logger.info("检测到mainSurface（1C主内容区）")
                return PageState.LOGGED_IN
        
        # 4. URL包含e1cib
        if 'e1cib' in current_url:
            return PageState.LOGGED_IN
        
        # === 检查加载状态 ===
        if await self._check_loading():
            return PageState.LOADING
        
        # === 检查登录表单 ===
        login_form = await page.query_selector("#form")
        username_input = await page.query_selector("input[name='openid.auth.user']")
        
        if login_form and username_input:
            try:
                form_visible = await login_form.is_visible()
                input_visible = await username_input.is_visible()
                if form_visible and input_visible:
                    return PageState.LOGIN_FORM
            except PlaywrightError:
                return PageState.LOADING
        
        # === 检查错误 ===
        error_element = await page.query_selector("#login_error")
        if error_element:
            text = await error_element.inner_text()
            if text and len(text.strip()) > 1:
                return PageState.ERROR
        
        return PageState.UNKNOWN
    
    async def _check_loading(self) -> bool:
        """检查是否正在加载"""
        page = self.driver.page
        
        try:
            # 检查预加载器
            for selector in ["#pages_preloader", "#execArea_preloader"]:
                el = await page.query_selector(selector)
                if el:
                    style = await el.get_attribute("style") or ""
                    if "display: none" not in style and "display:none" not in style:
                        return True
            
            # 检查页面内容是否过少
            body = await page.query_selector("body")
            if body:
                children = await body.query_selector_all("*")
                if len(children) < 10:
                    return True
                    
        except PlaywrightError:
            return True  # 导航中认为在加载
        except Exception:
            pass
        return False
    
    async def _wait_for_loading_complete(self, timeout: int = 30000) -> bool:
        """等待加载完成"""
        start = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start) * 1000 < timeout:
            try:
                if not await self._check_loading():
                    await asyncio.sleep(0.5)
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        
        return not await self._check_loading()
    
    async def _do_login(self) -> bool:
        """执行登录操作"""
        logger.info("执行登录...")
        
        # 查找用户名输入框
        username_input = await self._find_username_input()
        if not username_input:
            raise LoginError("无法找到用户名输入框")
        
        logger.info(f"找到用户名输入框: {username_input}")
        
        # 清空并输入用户名
        await self.driver.page.fill(username_input, "")
        await self.driver.page.fill(username_input, self.config.clobus.username)
        await asyncio.sleep(0.3)
        
        # 查找密码输入框
        password_input = await self._find_password_input()
        if not password_input:
            raise LoginError("无法找到密码输入框")
        
        logger.info(f"找到密码输入框: {password_input}")
        
        # 输入密码
        await self.driver.page.fill(password_input, self.config.clobus.password)
        await asyncio.sleep(0.3)
        
        # 查找提交按钮
        submit_button = await self._find_submit_button()
        if not submit_button:
            raise LoginError("无法找到登录按钮")
        
        logger.info(f"找到提交按钮: {submit_button}")
        
        # 点击登录
        await self.driver.page.click(submit_button)
        logger.info("已点击登录，等待处理...")
        
        # 等待登录处理（给足够时间让页面跳转）
        await asyncio.sleep(5)
        
        # 等待页面稳定
        try:
            await self.driver.page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        
        # 等待加载完成
        if await self._check_loading():
            logger.info("登录后页面加载中...")
            await self._wait_for_loading_complete(timeout=30000)
        
        # 检查登录结果
        state = await self._safe_analyze_state()
        logger.info(f"登录后状态: {state}")
        
        return state == PageState.LOGGED_IN
    
    async def _find_username_input(self) -> Optional[str]:
        """查找用户名输入框"""
        selectors = [
            "input[name='openid.auth.user']",
            "input#userName",
            "input.authEditBox",
        ]
        
        for sel in selectors:
            el = await self.driver.page.query_selector(sel)
            if el:
                try:
                    if await el.is_visible():
                        return sel
                except Exception:
                    pass
        return None
    
    async def _find_password_input(self) -> Optional[str]:
        """查找密码输入框"""
        selectors = [
            "input[name='openid.auth.pwd']",
            "input#userPassword",
        ]
        
        for sel in selectors:
            el = await self.driver.page.query_selector(sel)
            if el:
                try:
                    if await el.is_visible():
                        return sel
                except Exception:
                    pass
        return None
    
    async def _find_submit_button(self) -> Optional[str]:
        """查找提交按钮"""
        selectors = [
            "input#submit_btn",
            "input.enterButton",
            "input[type='submit']",
        ]
        
        for sel in selectors:
            el = await self.driver.page.query_selector(sel)
            if el:
                try:
                    if await el.is_visible():
                        return sel
                except Exception:
                    pass
        return None
