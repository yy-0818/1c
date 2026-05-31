"""1C Web导航辅助模块"""
import asyncio
import re
from typing import Dict, List, Optional, Any

from playwright.async_api import Page, Locator

from ..utils.logger import get_logger

logger = get_logger("navigation")


class NavigationHelper:
    """
    1C Web云版本导航辅助类

    页面结构：
    - #themesCell: 左侧边栏（分类菜单）
    - #themesCell_theme_N: 各菜单项
    - .themeBox: 菜单项容器
    - #modalSurface: 模态遮罩层（需要隐藏）
    - #openedCell: 展开的子菜单容器

    导航方式：
    1. 隐藏modalSurface遮罩
    2. 点击侧边栏分类菜单
    3. 等待子菜单出现
    4. 点击子菜单项进入目标模块
    """

    # 侧边栏主题项映射
    NAV_MAP: Dict[str, Dict] = {
        "customers": {
            "parent": "справочники",  # 先点击的父菜单
            "child": "контрагенты",   # 子菜单项
            "keywords": ["контрагент", "контраг"],
        },
        "products": {
            "parent": "справочники",
            "child": "номенклатура",
            "keywords": ["номенклатура", "номен", "товар"],
        },
        "orders": {
            "parent": "продажи",  # 或者其他包含订单的菜单
            "child": "заказ",
            "keywords": ["заказ", "счет"],
        },
    }

    def __init__(self, page: Page):
        self.page = page
        self._loaded = False
        self._current_form = None
        self.logger = logger  # 使用模块级logger

    async def navigate_to(self, section: str) -> bool:
        """
        导航到指定模块

        Args:
            section: 模块名 (customers/products/orders)

        Returns:
            是否导航成功
        """
        if section not in self.NAV_MAP:
            logger.error(f"未知模块: {section}")
            return False

        config = self.NAV_MAP[section]

        # 隐藏modal遮罩
        await self._hide_modal()

        # 方法: 通过侧边栏导航（点击父菜单 -> 点击子菜单）
        success = await self._navigate_via_sidebar(
            config["parent"],
            config["child"],
            config["keywords"]
        )

        if success:
            logger.info(f"导航到 {section} 成功")
            return True

        logger.error(f"导航到 {section} 失败")
        return False

    async def _hide_modal(self) -> None:
        """隐藏模态遮罩层"""
        try:
            modal = await self.page.query_selector("#modalSurface")
            if modal:
                display = await modal.evaluate("el => el.style.display")
                if display != "none":
                    logger.debug("隐藏 modalSurface")
                    await self.page.evaluate(
                        "document.getElementById('modalSurface').style.display = 'none'"
                    )
                    await asyncio.sleep(0.5)
        except Exception as e:
            logger.debug(f"隐藏modal失败: {e}")

    async def _navigate_via_sidebar(
        self,
        parent_text: str,
        child_text: str,
        keywords: List[str]
    ) -> bool:
        """
        通过侧边栏导航：先点击父菜单，再点击子菜单

        Args:
            parent_text: 父菜单文本（如"справочники"）
            child_text: 子菜单文本（如"контрагенты"）
            keywords: 子菜单关键词列表

        Returns:
            是否导航成功
        """
        try:
            # 查找侧边栏
            sidebar = await self.page.query_selector("#themesCell")
            if not sidebar:
                logger.debug("未找到侧边栏 #themesCell")
                return False

            # 查找所有themeBox
            theme_items = await self.page.query_selector_all(".themeBox")
            if not theme_items:
                logger.debug("未找到 .themeBox")
                return False

            logger.debug(f"找到 {len(theme_items)} 个菜单项")

            # 找到并点击父菜单
            parent_item = None
            for item in theme_items:
                text = (await item.inner_text()).strip().lower()
                if parent_text.lower() in text:
                    parent_item = item
                    logger.info(f"找到父菜单: {text}")
                    break

            if not parent_item:
                logger.warning(f"未找到父菜单: {parent_text}")
                return False

            # 点击父菜单
            await parent_item.click()
            logger.info(f"已点击父菜单: {parent_text}")
            await asyncio.sleep(2)  # 等待子菜单出现

            # 重新获取页面内容，查找子菜单
            # 子菜单项可能在DOM中出现，需要等待动态加载
            for attempt in range(3):
                # 检查页面是否包含目标子菜单文本
                body_text = await self.page.inner_text("body")
                if child_text.lower() in body_text.lower():
                    logger.info(f"子菜单已出现: {child_text}")
                    break
                await asyncio.sleep(1)

            # 查找并点击子菜单
            # 子菜单项可能是普通元素，不一定是特定class
            success = await self._click_submenu_item(child_text, keywords)
            if success:
                await asyncio.sleep(3)  # 等待目标页面加载
                return True

            return False

        except Exception as e:
            logger.error(f"侧边栏导航失败: {e}")
            return False

    async def _click_submenu_item(self, target_text: str, keywords: List[str]) -> bool:
        """
        点击子菜单项

        Args:
            target_text: 目标菜单文本
            keywords: 关键词列表

        Returns:
            是否成功点击
        """
        try:
            # 遍历页面所有元素查找匹配的文本
            all_elements = await self.page.query_selector_all("*")

            # 首先尝试精确匹配
            for el in all_elements:
                try:
                    text = (await el.inner_text()).strip()

                    # 精确匹配目标文本（排除包含其他内容的元素）
                    if text.lower() == target_text.lower():
                        is_visible = await el.is_visible()
                        is_clickable = await el.evaluate("""
                            node => {
                                const style = window.getComputedStyle(node);
                                return style.display !== 'none' &&
                                       style.visibility !== 'hidden' &&
                                       node.offsetParent !== null;
                            }
                        """)

                        if is_visible and is_clickable:
                            logger.info(f"点击子菜单项(精确): {text}")
                            await el.click()
                            return True

                except:
                    continue

            # 如果精确匹配失败，尝试关键词匹配（但要更精确）
            for el in all_elements:
                try:
                    text = (await el.inner_text()).strip()

                    # 匹配关键词，但排除包含换行符或多个菜单项的元素
                    for kw in keywords:
                        if kw.lower() in text.lower():
                            # 只匹配单行文本（不含换行）
                            if '\n' not in text and '\r' not in text:
                                is_visible = await el.is_visible()
                                is_clickable = await el.evaluate("""
                                    node => {
                                        const style = window.getComputedStyle(node);
                                        return style.display !== 'none' &&
                                               style.visibility !== 'hidden' &&
                                               node.offsetParent !== null;
                                    }
                                """)

                                if is_visible and is_clickable:
                                    logger.info(f"点击子菜单项(关键词): {text}")
                                    await el.click()
                                    return True

                except:
                    continue

            logger.warning(f"未找到子菜单项: {target_text}")
            return False

        except Exception as e:
            logger.error(f"点击子菜单失败: {e}")
            return False

    async def _wait_for_content(self, timeout: int = 15000) -> bool:
        """等待工作区内容加载"""
        try:
            # 等待加载指示器消失
            try:
                preloader = self.page.locator("#pages_preloader:not([style*='display: none'])")
                if await preloader.count() > 0:
                    logger.debug("等待加载指示器消失...")
                    await preloader.wait_for(state="hidden", timeout=timeout)
            except:
                pass

            # 等待表单出现
            try:
                await self.page.wait_for_selector(".IWeb, #form0_container, [class*='mainGroup']", timeout=timeout)
            except:
                pass

            # 等待至少有一些内容
            await asyncio.sleep(2)

            return True

        except Exception as e:
            logger.debug(f"等待内容加载超时: {e}")
            return False

    async def extract_form_data(self) -> Dict[str, Any]:
        """
        从当前工作区提取表单数据

        Returns:
            Dict包含:
                - headers: List[str] 列标题
                - rows: List[Dict] 数据行
                - html: str 原始HTML
                - text: str 纯文本
        """
        result = {
            "headers": [],
            "rows": [],
            "html": "",
            "text": ""
        }

        try:
            # 尝试找到表单内容
            form = await self.page.query_selector(".IWeb, #form0_container, .mainGroup, table")
            if form:
                result["html"] = await form.inner_html()
                result["text"] = await form.inner_text()

                # 提取表格数据
                tables = await form.query_selector_all("table")
                for table in tables:
                    rows = await table.query_selector_all("tbody tr, tr")
                    for row in rows:
                        cells = await row.query_selector_all("td, th")
                        if cells:
                            cell_texts = []
                            for cell in cells:
                                cell_texts.append((await cell.inner_text()).strip())

                            # 第一行通常是表头
                            if not result["headers"]:
                                result["headers"] = cell_texts
                            else:
                                result["rows"].append(cell_texts)

                # 尝试提取动态表格（1C的表格结构）
                grids = await form.query_selector_all(".dataGrid, [class*='grid'], table.dataGrid")
                for grid in grids:
                    rows = await grid.query_selector_all("tbody tr, tr:not(.header)")
                    for row in rows:
                        cells = await row.query_selector_all("td")
                        if len(cells) >= 2:
                            row_data = {}
                            for i, cell in enumerate(cells):
                                text = (await cell.inner_text()).strip()
                                if text:
                                    row_data[f"col_{i}"] = text
                            if row_data:
                                result["rows"].append(row_data)

            # 备用：从整个页面提取
            if not result["text"]:
                body = await self.page.query_selector("body")
                if body:
                    result["text"] = await body.inner_text()

        except Exception as e:
            logger.error(f"提取表单数据失败: {e}")

        return result

    async def extract_all_tables(self) -> List[Dict[str, Any]]:
        """
        提取页面上所有表格数据

        Returns:
            表格列表，每个包含 headers 和 rows
        """
        tables_data = []

        try:
            # 查找所有表格
            all_tables = await self.page.query_selector_all("table")
            logger.info(f"找到 {len(all_tables)} 个表格")

            for idx, table in enumerate(all_tables):
                table_data = {"index": idx, "headers": [], "rows": []}

                # 检查是否是数据表
                classes = await table.get_attribute("class") or ""
                if "dataGrid" in classes or "grid" in classes.lower():
                    table_data["type"] = "dataGrid"
                else:
                    table_data["type"] = "regular"

                # 提取行
                rows = await table.query_selector_all("tbody tr, tr")

                for row_idx, row in enumerate(rows):
                    # 检查是否是表头行
                    is_header = "header" in (await row.get_attribute("class") or "").lower()

                    cells = await row.query_selector_all("td, th")
                    cell_texts = []

                    for cell in cells:
                        text = (await cell.inner_text()).strip()
                        # 清理文本
                        text = re.sub(r'\s+', ' ', text)
                        cell_texts.append(text)

                    if cell_texts:
                        if is_header or row_idx == 0:
                            table_data["headers"].extend([h for h in cell_texts if h])
                        else:
                            if cell_texts:
                                table_data["rows"].append(cell_texts)

                if table_data["rows"] or table_data["headers"]:
                    tables_data.append(table_data)
                    logger.info(f"表格 {idx}: {len(table_data['headers'])} 列, {len(table_data['rows'])} 行")

        except Exception as e:
            logger.error(f"提取表格失败: {e}")

        return tables_data

    async def get_page_snapshot(self) -> Dict[str, Any]:
        """
        获取当前页面快照，用于调试

        Returns:
            页面状态快照
        """
        snapshot = {
            "url": self.page.url,
            "title": await self.page.title(),
            "sidebar_items": [],
            "opened_tabs": [],
            "content_preview": ""
        }

        try:
            # 侧边栏项
            sidebar = await self.page.query_selector("#themesCell")
            if sidebar:
                items = await sidebar.query_selector_all(".themeBox")
                for item in items[:15]:  # 限制数量
                    text = (await item.inner_text()).strip()
                    if text:
                        snapshot["sidebar_items"].append(text[:50])

            # 已打开的标签
            opened = await self.page.query_selector_all("#openedCell .openedItem, #openedCell .openedItemTitle")
            for tab in opened[:10]:
                text = (await tab.inner_text()).strip()
                if text:
                    snapshot["opened_tabs"].append(text[:50])

            # 内容预览
            main_content = await self.page.query_selector("#pages, .mainGroup, #form0_container")
            if main_content:
                snapshot["content_preview"] = (await main_content.inner_text())[:500]

        except Exception as e:
            logger.error(f"获取页面快照失败: {e}")

        return snapshot

    async def expand_all_groups(self, max_depth: int = 3) -> int:
        """
        展开所有分组层级，获取完整数据

        Args:
            max_depth: 最大展开深度

        Returns:
            展开的项数
        """
        expanded_count = 0

        try:
            self.logger.info("开始展开分组层级...")

            for depth in range(max_depth):
                # 查找所有可展开的行（有+图标的）
                expandable_rows = await self.page.query_selector_all(
                    '.gridLine [class*="gridListH"], '  # 层级图标
                    '.gridLine [class*="zoomI"][level="true"], '  # 可展开图标
                    '.gridBoxImg [class*="gridListH"]'  # 展开按钮
                )

                if not expandable_rows:
                    self.logger.info(f"第 {depth + 1} 层：无可展开项")
                    break

                self.logger.info(f"第 {depth + 1} 层：找到 {len(expandable_rows)} 个可展开项")

                # 点击每个可展开项
                for row in expandable_rows:
                    try:
                        # 检查是否已经展开（图标样式）
                        parent = await row.query_selector("xpath=..")
                        if parent:
                            parent_class = await parent.get_attribute("class") or ""

                        # 点击展开
                        await row.click()
                        await asyncio.sleep(0.3)  # 短暂等待
                        expanded_count += 1

                    except Exception as e:
                        continue

                # 等待子项加载
                await asyncio.sleep(1)

            self.logger.info(f"共展开 {expanded_count} 个分组项")

        except Exception as e:
            self.logger.error(f"展开分组失败: {e}")

        return expanded_count

    async def expand_all_hierarchical_items(self) -> int:
        """
        使用JavaScript批量展开所有层级项目

        Returns:
            展开的项数
        """
        try:
            result = await self.page.evaluate("""() => {
                let expanded = 0;
                const maxIterations = 100;
                let iterations = 0;

                // 查找所有带层级图标的行
                const findAndExpand = () => {
                    // 查找带+图标的行（可展开）
                    const rows = document.querySelectorAll('.gridLine');
                    let found = false;

                    rows.forEach(row => {
                        // 检查是否有层级图标
                        const zoomIcon = row.querySelector('.zoomI[level="true"]');
                        const listIcon = row.querySelector('.gridListH');

                        if (zoomIcon || listIcon) {
                            // 检查是否是折叠状态
                            const hasPlus = zoomIcon?.textContent?.includes('+') ||
                                           listIcon?.textContent?.includes('+');
                            const hasMinus = zoomIcon?.textContent?.includes('-') ||
                                            listIcon?.textContent?.includes('-');

                            if (hasPlus) {
                                // 点击展开
                                const box = row.querySelector('.gridBox');
                                if (box) {
                                    box.click();
                                    found = true;
                                }
                            }
                        }
                    });

                    return found;
                };

                // 循环展开直到没有更多可展开项
                while (findAndExpand() && iterations < maxIterations) {
                    iterations++;
                }

                return { expanded: iterations, totalRows: document.querySelectorAll('.gridLine').length };
            }""")

            self.logger.info(f"层级展开结果: {result}")
            return result.get('expanded', 0)

        except Exception as e:
            self.logger.error(f"JS展开失败: {e}")
            return 0

    async def go_to_next_page(self) -> bool:
        """
        点击下一页按钮

        Returns:
            是否成功跳转
        """
        try:
            self.logger.info("尝试点击下一页...")

            # 尝试多种方式查找下一页按钮
            selectors = [
                'button[title*="следущ"]',  # 俄语变体
                'button[title*="следующ"]',  # 俄语
                'button[title*="next"]',  # 英语
                'button[name*="next"]',
                '[class*="pager"] button:last-child',
                '.gridPager button:last-child',
                '.pagination button:last-child',
                '[class*="pagerNext"]',
                '[class*="nextPage"]',
                '[title*="Вперед"]',  # 俄语"前进"
                '[title*="Forward"]',
            ]

            next_btn = None
            for sel in selectors:
                try:
                    btn = await self.page.query_selector(sel)
                    if btn:
                        is_disabled = await btn.get_attribute("disabled")
                        if is_disabled is None:
                            next_btn = btn
                            self.logger.info(f"找到下一页按钮: {sel}")
                            break
                except:
                    continue

            if not next_btn:
                self.logger.info("未找到可用的下一页按钮")
                return False

            # 点击
            await next_btn.click()
            await asyncio.sleep(1.5)  # 等待数据加载

            return True

        except Exception as e:
            self.logger.error(f"下一页点击失败: {e}")
            return False

    async def has_next_page(self) -> bool:
        """
        检查是否有下一页

        Returns:
            是否有下一页
        """
        try:
            # 先尝试通过分页器文本判断
            pager_info = await self.get_current_page_info()
            if pager_info.get('total', 1) > pager_info.get('current', 1):
                self.logger.info(f"分页器显示还有更多页面: {pager_info}")
                return True

            # 如果文本判断失败，尝试查找按钮
            selectors = [
                'button[title*="следущ"]',
                'button[title*="следующ"]',
                'button[title*="next"]',
                'button[name*="next"]',
                '[class*="pager"] button:last-child:not([disabled])',
                '.gridPager button:last-child:not([disabled])',
                '[class*="pagerNext"]:not([disabled])',
            ]

            for sel in selectors:
                try:
                    btn = await self.page.query_selector(sel)
                    if btn:
                        is_disabled = await btn.get_attribute("disabled")
                        if is_disabled is None:
                            self.logger.info(f"找到下一页按钮: {sel}")
                            return True
                except:
                    continue

            self.logger.info("没有找到下一页按钮")
            return False

        except Exception as e:
            self.logger.error(f"检查下一页失败: {e}")
            return False

    async def get_current_page_info(self) -> Dict[str, Any]:
        """
        获取当前页信息

        Returns:
            页码信息
        """
        try:
            info = await self.page.evaluate("""() => {
                // 查找分页信息 - 1C常见分页器类名
                const selectors = [
                    '.gridPager',
                    '[class*="pager"]',
                    '.pagination',
                    '[class*="pagination"]'
                ];

                for (const sel of selectors) {
                    const pager = document.querySelector(sel);
                    if (pager) {
                        const text = pager.innerText || pager.textContent || '';

                        // 尝试解析 "X из Y" 或 "X / Y" 或 "X of Y"
                        const match = text.match(/(\\d+)\\s*(?:из|of|/)\\s*(\\d+)/i) ||
                                      text.match(/(\\d+)\\s*[-–]\\s*(\\d+)/);

                        if (match) {
                            return { current: parseInt(match[1]), total: parseInt(match[2]) };
                        }

                        // 查找当前页按钮（有特殊样式）
                        const currentBtn = pager.querySelector('[class*="current"], [class*="active"], button[disabled]');
                        if (currentBtn) {
                            const allBtns = pager.querySelectorAll('button:not([disabled])');
                            return { current: 1, total: allBtns.length + 1 };
                        }
                    }
                }

                return { current: 1, total: 1 };
            }""")

            return info

        except Exception as e:
            self.logger.debug(f"获取页码信息失败: {e}")
            return {"current": 1, "total": 1}

    async def scroll_to_load_all(self, max_scrolls: int = 50, scroll_delay: float = 1.5) -> Dict[str, Any]:
        """
        滚动表格加载所有数据

        Args:
            max_scrolls: 最大滚动次数
            scroll_delay: 每次滚动后的等待时间（秒）

        Returns:
            滚动结果信息
        """
        result = {
            "scroll_count": 0,
            "total_rows": 0,
            "new_rows_loaded": 0
        }

        try:
            self.logger.info("开始滚动加载数据...")

            # 获取初始行数
            initial_rows = await self.page.evaluate("""() => {
                return document.querySelectorAll('.gridLine').length;
            }""")
            self.logger.info(f"初始行数: {initial_rows}")

            last_row_count = initial_rows

            # 查找grid容器
            grid_info = await self.page.evaluate("""() => {
                const selectors = [
                    '.gridBody',
                    '.gridBody > div',
                    '[class*="gridBody"]',
                    '[class*="GridBody"]',
                    '[class*="dataGrid"] tbody'
                ];

                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        return {
                            selector: sel,
                            scrollHeight: el.scrollHeight,
                            clientHeight: el.clientHeight,
                            canScroll: el.scrollHeight > el.clientHeight
                        };
                    }
                }
                return { selector: null };
            }""")

            self.logger.info(f"Grid容器: {grid_info}")

            for i in range(max_scrolls):
                # 方法1: 使用键盘 End 键滚动到底部
                await self.page.evaluate("""() => {
                    const selectors = [
                        '.gridBody',
                        '.gridBody > div',
                        '[class*="gridBody"]',
                        '[class*="GridBody"]'
                    ];

                    let container = null;
                    for (const sel of selectors) {
                        container = document.querySelector(sel);
                        if (container) break;
                    }

                    if (container) {
                        // 聚焦并按 End 键
                        container.focus();
                        container.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
                    }
                }""")

                await asyncio.sleep(scroll_delay)

                # 方法2: 滚动到最底部
                await self.page.evaluate("""() => {
                    const selectors = [
                        '.gridBody',
                        '[class*="gridBody"]'
                    ];

                    for (const sel of selectors) {
                        const container = document.querySelector(sel);
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                            break;
                        }
                    }
                }""")

                await asyncio.sleep(0.5)

                # 检查当前行数
                current_rows = await self.page.evaluate("""() => {
                    return document.querySelectorAll('.gridLine').length;
                }""")

                result["scroll_count"] = i + 1
                result["total_rows"] = current_rows

                if current_rows > last_row_count:
                    new_rows = current_rows - last_row_count
                    result["new_rows_loaded"] += new_rows
                    self.logger.info(f"滚动 {i + 1}: 新增 {new_rows} 行 (总计 {current_rows})")
                    last_row_count = current_rows
                elif current_rows == last_row_count:
                    self.logger.info(f"滚动 {i + 1}: 行数未变化 ({current_rows})")

                    # 连续5次行数不变，停止
                    if i > 3:
                        self.logger.info("连续多页行数未变化，已加载全部数据")
                        break
                else:
                    self.logger.warning(f"滚动 {i + 1}: 行数减少 {current_rows}")

            self.logger.info(f"滚动加载完成: 共滚动 {result['scroll_count']} 次, 最终 {result['total_rows']} 行")

        except Exception as e:
            self.logger.error(f"滚动加载失败: {e}")

        return result

    async def debug_pagination(self) -> Dict[str, Any]:
        """
        调试分页信息，查找页面上的分页元素

        Returns:
            调试信息
        """
        try:
            info = await self.page.evaluate("""() => {
                const result = {
                    pagerElements: [],
                    buttons: [],
                    text: ''
                };

                // 查找所有可能的分页器
                const selectors = [
                    '.gridPager',
                    '[class*="pager"]',
                    '.pagination',
                    'table[class*="pager"]'
                ];

                for (const sel of selectors) {
                    const elements = document.querySelectorAll(sel);
                    if (elements.length > 0) {
                        result.pagerElements.push({
                            selector: sel,
                            count: elements.length,
                            text: elements[0].innerText?.substring(0, 200)
                        });
                    }
                }

                // 查找所有按钮
                const buttons = document.querySelectorAll('button');
                buttons.forEach(btn => {
                    const title = btn.getAttribute('title') || '';
                    const text = btn.innerText?.trim() || '';
                    if (title || text) {
                        result.buttons.push({
                            title,
                            text,
                            disabled: btn.disabled
                        });
                    }
                });

                return result;
            }""")

            self.logger.info("=== 分页调试信息 ===")
            self.logger.info(f"分页器元素: {info.get('pagerElements')}")
            self.logger.info(f"按钮数量: {len(info.get('buttons', []))}")

            # 打印前10个按钮
            for btn in info.get('buttons', [])[:15]:
                self.logger.info(f"  按钮: title='{btn['title']}', text='{btn['text']}', disabled={btn['disabled']}")

            return info

        except Exception as e:
            self.logger.error(f"调试分页失败: {e}")
            return {}


def create_navigation_helper(page: Page) -> NavigationHelper:
    """创建导航辅助实例"""
    return NavigationHelper(page)


# 调试工具：在页面加载后调用此函数查找滚动容器
async def debug_grid_scroll(page):
    """调试grid滚动容器（独立函数）"""
    info = await page.evaluate("""() => {
        const result = { containers: [], rows: 0 };
        result.rows = document.querySelectorAll('.gridLine').length;

        const selectors = [
            '.gridBody',
            '.gridBody > div',
            '[class*="gridBody"]',
            '[class*="dataGrid"]'
        ];

        for (const sel of selectors) {
            const els = document.querySelectorAll(sel);
            els.forEach(el => {
                if (el.scrollHeight > el.clientHeight) {
                    result.containers.push({
                        selector: sel,
                        scrollHeight: el.scrollHeight,
                        clientHeight: el.clientHeight
                    });
                }
            });
        }
        return result;
    }""")
    return info
