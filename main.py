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
from src_scraper.scrapers.coordinator import ScraperCoordinator, run_scraper


async def test_login():
    """测试登录功能"""
    print("=" * 60)
    print("1C Clobus 登录测试")
    print("=" * 60)

    try:
        config = load_config()
        print(f"\n配置文件已加载")
        print(f"Clobus URL: {config.clobus.url}")
        print(f"用户名: {config.clobus.username}")
    except Exception as e:
        print(f"加载配置失败: {e}")
        return False

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
            await driver.save_session()
            print("会话已保存")
            print("\n按 Ctrl+C 关闭浏览器")
            while True:
                await asyncio.sleep(1)
        else:
            print("\n❌ 登录失败!")
            return False

    except KeyboardInterrupt:
        print("\n\n用户中断")
    except LoginError as e:
        print(f"\n❌ 登录错误: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        return False
    finally:
        if driver:
            await driver.close()


async def run_sync(task: str = "all", **kwargs):
    """运行数据同步"""
    print("=" * 60)
    print(f"1C Clobus 数据同步 - {task}")
    print("=" * 60)

    setup_logger(log_file="logs/scraper.log", level="INFO")

    try:
        result = await run_scraper(task, **kwargs)

        if result.get('success'):
            print("\n✅ 同步成功!")
            print(f"总记录数: {result.get('total', 0)}")

            if 'results' in result:
                for name, r in result['results'].items():
                    print(f"  {name}: {r.get('count', 0)} 条")
        else:
            print(f"\n❌ 同步失败: {result.get('error', '未知错误')}")

        return result

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="1C Clobus 数据爬虫")
    parser.add_argument(
        "--mode",
        choices=["login", "sync", "interactive"],
        default="login",
        help="运行模式"
    )
    parser.add_argument(
        "--task",
        default="all",
        choices=["all", "customers", "products", "orders"],
        help="同步任务"
    )
    parser.add_argument("--date-from", help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--max-pages", type=int, default=100)

    args = parser.parse_args()

    if args.mode == "login":
        asyncio.run(test_login())
    elif args.mode == "sync":
        kwargs = {
            'max_pages': args.max_pages
        }
        if args.date_from:
            kwargs['date_from'] = args.date_from
        if args.date_to:
            kwargs['date_to'] = args.date_to
        asyncio.run(run_sync(args.task, **kwargs))
    elif args.mode == "interactive":
        asyncio.run(test_login())


if __name__ == "__main__":
    main()
