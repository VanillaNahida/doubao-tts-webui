import sys
import time
from pathlib import Path

from doubao_tts import save_cookie_to_file

REQUIRED_COOKIES = {"sessionid", "sid_guard", "uid_tt"}
BROWSER_WIDTH=1024
BROWSER_HEIGHT=768
LOGIN_TIMEOUT = 120  # 登录超时时间（秒）


def format_cookie_string(cookies: list) -> str:
    cookie_dict = {}
    for c in cookies:
        name = c.get("name", "")
        value = c.get("value", "")
        if name in REQUIRED_COOKIES:
            cookie_dict[name] = value
    return "; ".join(f"{k}={v}" for k, v in cookie_dict.items())


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("请先安装 Playwright: pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    print("正在启动浏览器...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[f"--window-size={BROWSER_WIDTH},{BROWSER_HEIGHT}"],
        )
        # 限制浏览器窗口大小
        context = browser.new_context(viewport={"width": BROWSER_WIDTH, "height": BROWSER_HEIGHT})
        page = context.new_page()

        page.goto("https://www.doubao.com")

        try:
            login_button = page.get_by_role("button", name="登录")
            login_button.wait_for(state="visible", timeout=15000)
            login_button.click()
            print("已自动点击登录按钮")
        except Exception:
            try:
                login_button = page.locator("button", has_text="登录")
                login_button.wait_for(state="visible", timeout=5000)
                login_button.click()
            except Exception:
                print("未找到登录按钮，可能已登录。")
        
        print("")
        print(f"请在{LOGIN_TIMEOUT}秒内在打开的浏览器中，使用豆包 APP 扫码登录")
        print("登录成功后将自动保存登录信息并关闭浏览器窗口")
        print("")
        print("关闭浏览器则取消登录，按 Ctrl+C 关闭程序。")
        print("")

        found_cookies = set()
        last_display = ""
        start_time = time.time()

        try:
            while True:
                elapsed = int(time.time() - start_time)
                if elapsed > LOGIN_TIMEOUT:
                    print(f"\n登录超时（{LOGIN_TIMEOUT} 秒），未检测到必需 Cookie")
                    print("请确保已登录豆包账号后重试")
                    break

                try:
                    if page.is_closed():
                        print("\n浏览器窗口已关闭，进程将退出...")
                        time.sleep(1)
                        break
                    cookies = context.cookies()
                except Exception:
                    print("\n浏览器连接已断开")
                    break

                current_cookies = {c["name"] for c in cookies}

                newly_found = current_cookies & REQUIRED_COOKIES - found_cookies
                if newly_found:
                    for name in newly_found:
                        print(f"  [+] 已检测到: {name}")
                    found_cookies.update(newly_found)

                if REQUIRED_COOKIES.issubset(current_cookies):
                    cookie_str = format_cookie_string(cookies)
                    save_cookie_to_file(cookie_str)
                    print("=" * 60)
                    print("登录成功！")
                    print("所有必需 Cookie 已检测并保存!")
                    print(f"  文件: {Path(__file__).parent / '.cookie'}")
                    print("=" * 60)
                    break

                remaining = LOGIN_TIMEOUT - elapsed
                progress = f"  [{len(found_cookies)}/3] 等待用户登录中（剩余 {remaining} 秒）..."
                if progress != last_display:
                    print(progress, end="\r")
                    last_display = progress

                time.sleep(1)

        except KeyboardInterrupt:
            print("\n用户取消，退出...")
        finally:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
