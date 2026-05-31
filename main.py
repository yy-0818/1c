"""1C Clobus 爬虫主入口"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src_scraper.core.config_loader import load_config
from src_scraper.utils.logger import setup_logger, get_logger
from src_scraper.browser.driver import BrowserDriver
from src_scraper.browser.auth import AuthManager, LoginError
from src_scraper.scrapers.coordinator import ScraperCoordinator


async def interactive_mode():
    """交互模式：登录后提供操作选项"""
    print("=" * 60)
    print("1C Clobus 数据管理")
    print("=" * 60)
    
    try:
        config = load_config()
        print(f"\n配置文件已加载")
        print(f"Clobus URL: {config.clobus.url}")
    except Exception as e:
        print(f"加载配置失败: {e}")
        return
    
    setup_logger(log_file=config.logging.file, level=config.logging.level)
    driver = None
    
    try:
        print("\n正在初始化浏览器...")
        driver = BrowserDriver()
        await driver.initialize()
        print("浏览器初始化完成")
        
        print("\n正在检查登录状态...")
        auth = AuthManager(driver)
        success = await auth.login()
        
        if not success:
            print("\n❌ 登录失败!")
            return
        
        print("\n✅ 登录成功!")
        print(f"当前页面标题: {await driver.page.title()}")
        print(f"当前URL: {driver.page.url}")
        
        while True:
            print("\n" + "=" * 40)
            print("请选择操作：")
            print("=" * 40)
            print("1. 同步客户数据 (customers)")
            print("2. 同步产品数据 (products)")
            print("3. 同步订单数据 (orders)")
            print("4. 同步全部数据 (all)")
            print("5. 截图保存")
            print("6. 重新登录")
            print("0. 退出")
            print("=" * 40)
            
            choice = input("\n请输入选项 (0-6): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                await run_sync(driver, "customers", skip_login=True, keep_browser_open=True)
            elif choice == "2":
                await run_sync(driver, "products", skip_login=True, keep_browser_open=True)
            elif choice == "3":
                await run_sync(driver, "orders", skip_login=True, keep_browser_open=True)
            elif choice == "4":
                await run_sync(driver, "all", skip_login=True, keep_browser_open=True)
            elif choice == "5":
                path = await driver.screenshot("manual_screenshot.png")
                print(f"截图已保存: {path}")
            elif choice == "6":
                print("\n正在重新登录...")
                success = await auth.login()
                if success:
                    print("✅ 重新登录成功!")
                else:
                    print("❌ 重新登录失败")
            else:
                print("无效选项，请重新选择")
    
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    finally:
        if driver:
            await driver.close()


async def run_sync(driver: BrowserDriver, task: str, skip_login: bool = False, keep_browser_open: bool = False):
    """运行数据同步

    Args:
        driver: 浏览器驱动
        task: 任务类型
        skip_login: 是否跳过登录检查
        keep_browser_open: 是否保持浏览器打开
    """
    print(f"\n正在同步 {task}...")

    try:
        coordinator = ScraperCoordinator(driver=driver, skip_login_check=skip_login)
        await coordinator.__aenter__()

        if task == "all":
            result = await coordinator.scrape_all()
        elif task == "customers":
            result = await coordinator.scrape_customers()
        elif task == "products":
            result = await coordinator.scrape_products()
        elif task == "orders":
            result = await coordinator.scrape_orders()
        else:
            result = {"success": False, "error": "未知任务"}

        # 只有在需要时才关闭浏览器
        if not keep_browser_open:
            await coordinator.__aexit__(None, None, None)

        if result.get('success'):
            print(f"\n✅ {task} 同步成功!")
            # 显示正确的记录数
            if 'results' in result:
                for name, r in result['results'].items():
                    count = r.get('count', 0)
                    pages = r.get('pages', 1)
                    print(f"  {name}: {count} 条 (共 {pages} 页)")
                    if r.get('data'):
                        print(f"    数据已保存")
            else:
                count = result.get('count', 0)
                pages = result.get('pages', 1)
                print(f"  总记录数: {count} 条 (共 {pages} 页)")
                if result.get('data'):
                    print(f"    数据已保存")
        else:
            print(f"\n❌ {task} 同步失败: {result.get('error', '未知错误')}")

    except Exception as e:
        print(f"\n❌ 同步出错: {e}")
        if not keep_browser_open:
            try:
                await coordinator.__aexit__(None, None, None)
            except:
                pass


def main():
    parser = argparse.ArgumentParser(description="1C Clobus 数据爬虫")
    parser.add_argument(
        "--mode",
        choices=["interactive", "login", "sync"],
        default="interactive",
        help="运行模式: interactive(交互模式), login(仅登录), sync(同步)"
    )
    parser.add_argument(
        "--task",
        default="all",
        choices=["all", "customers", "products", "orders"],
        help="同步任务"
    )
    
    args = parser.parse_args()
    
    if args.mode == "interactive":
        asyncio.run(interactive_mode())
    elif args.mode == "login":
        asyncio.run(login_only())
    elif args.mode == "sync":
        asyncio.run(sync_only(args.task))


async def login_only():
    """仅登录模式"""
    print("=" * 60)
    print("1C Clobus 登录测试")
    print("=" * 60)
    
    try:
        config = load_config()
        print(f"\n配置文件已加载")
    except Exception as e:
        print(f"加载配置失败: {e}")
        return
    
    setup_logger(log_file=config.logging.file, level=config.logging.level)
    driver = None
    
    try:
        print("\n正在初始化浏览器...")
        driver = BrowserDriver()
        await driver.initialize()
        print("浏览器初始化完成")
        
        print("\n正在执行登录...")
        auth = AuthManager(driver)
        success = await auth.login()
        
        if success:
            print("\n✅ 登录成功!")
            print(f"\n当前页面标题: {await driver.page.title()}")
            print(f"当前URL: {driver.page.url}")
            print("\n浏览器将保持打开...")
            print("按 Ctrl+C 关闭浏览器")
            while True:
                await asyncio.sleep(1)
        else:
            print("\n❌ 登录失败!")
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except LoginError as e:
        print(f"\n❌ 登录错误: {e}")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    finally:
        if driver:
            await driver.close()


async def sync_only(task: str):
    """仅同步模式"""
    print("=" * 60)
    print(f"1C Clobus 数据同步 - {task}")
    print("=" * 60)
    
    setup_logger(log_file="logs/scraper.log", level="INFO")
    
    try:
        driver = BrowserDriver()
        await driver.initialize()
        
        coordinator = ScraperCoordinator(driver=driver)
        await coordinator.__aenter__()
        
        if task == "all":
            result = await coordinator.scrape_all()
        elif task == "customers":
            result = await coordinator.scrape_customers()
        elif task == "products":
            result = await coordinator.scrape_products()
        elif task == "orders":
            result = await coordinator.scrape_orders()
        else:
            result = {"success": False, "error": "未知任务"}
        
        await coordinator.__aexit__(None, None, None)
        
        if result.get('success'):
            print("\n✅ 同步成功!")
            print(f"总记录数: {result.get('total', 0)}")
            if 'results' in result:
                for name, r in result['results'].items():
                    print(f"  {name}: {r.get('count', 0)} 条")
        else:
            print(f"\n❌ 同步失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")


if __name__ == "__main__":
    main()
