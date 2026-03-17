#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
河北科技大学校园网自动登录脚本
适用系统：Srun（深澜）
实现方式：Playwright 模拟浏览器操作，规避 JS 加密流程

作者：北纬之风

用法：
  登录  python hebust_login.py -u <学号> -p <密码>
  注销  python hebust_login.py --logout
  调试  追加 --show-browser 可显示浏览器窗口

依赖：首次运行自动安装 Playwright 及 Chromium（约 150 MB，需联网）

作者：北纬之风
GitHub：https://github.com/Norsyd
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path

# ─────────────────────────────────────────────
#  配置区
# ─────────────────────────────────────────────
LOGIN_URL        = "https://172.18.250.31/srun_portal_pc?ac_id=11&theme=pro"
LOGOUT_URL       = "https://172.18.250.31/srun_portal_success?ac_id=11&theme=pro"
TIMEOUT_MS       = 30_000
HEADLESS_DEFAULT = True

# ─────────────────────────────────────────────
#  自动安装依赖
# ─────────────────────────────────────────────

def ensure_dependencies():
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("[安装] 正在安装 playwright ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "playwright"],
            stdout=subprocess.DEVNULL,
        )
        print("[安装] playwright 安装完成。")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            if not Path(p.chromium.executable_path).exists():
                raise FileNotFoundError
    except Exception:
        print("[安装] 正在下载 Playwright Chromium（约 150 MB，请耐心等待）...")
        subprocess.check_call(
            [sys.executable, "-m", "playwright", "install", "chromium"]
        )
        print("[安装] Chromium 安装完成。")

# ─────────────────────────────────────────────
#  浏览器上下文工厂
# ─────────────────────────────────────────────

def _new_browser_context(playwright, headless: bool):
    browser = playwright.chromium.launch(
        headless=headless,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--no-sandbox",
        ],
    )
    context = browser.new_context(
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    return browser, context

# ─────────────────────────────────────────────
#  工具：等待页面出现实质内容
# ─────────────────────────────────────────────

def _wait_for_content(page, timeout_s: int = 5) -> str:
    """
    轮询 body.innerText，直到出现非空内容或超时。
    返回最终的页面文本（可能为空字符串）。
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            text = page.inner_text("body", timeout=500).strip()
            if text:
                return text
        except Exception:
            pass
        time.sleep(0.1)
    return ""

# ─────────────────────────────────────────────
#  登录
# ─────────────────────────────────────────────

def login(username: str, password: str, headless: bool = HEADLESS_DEFAULT):
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    print(f"[登录] 目标地址：{LOGIN_URL}")
    print(f"[登录] 用户名：{username}")
    print(f"[登录] 浏览器模式：{'无头(后台)' if headless else '显示窗口'}\n")

    with sync_playwright() as p:
        browser, context = _new_browser_context(p, headless)
        page = context.new_page()

        print("[步骤 1/4] 正在打开登录页面...")
        try:
            page.goto(LOGIN_URL, timeout=TIMEOUT_MS, wait_until="load")
        except PWTimeout:
            # networkidle 超时后降级，继续尝试
            pass  # 降级忽略

        print("[步骤 2/4] 正在等待页面内容渲染...")
        _wait_for_content(page, timeout_s=5)

        username_selectors = [
            'input[name="username"]',
            'input[id="username"]',
            'input[placeholder*="账号"]',
            'input[placeholder*="用户名"]',
            'input[type="text"]:visible',
        ]
        password_selectors = [
            'input[name="password"]',
            'input[id="password"]',
            'input[placeholder*="密码"]',
            'input[type="password"]:visible',
        ]

        username_input = None
        for sel in username_selectors:
            try:
                page.wait_for_selector(sel, timeout=3_000)
                username_input = page.locator(sel).first
                print(f"  找到用户名输入框：{sel}")
                break
            except PWTimeout:
                continue

        if not username_input:
            page.screenshot(path="debug_page.png")
            print("[错误] 未找到用户名输入框，截图已保存至 debug_page.png。")
            browser.close()
            return False

        password_input = None
        for sel in password_selectors:
            try:
                page.wait_for_selector(sel, timeout=3_000)
                password_input = page.locator(sel).first
                print(f"  找到密码输入框：{sel}")
                break
            except PWTimeout:
                continue

        if not password_input:
            page.screenshot(path="debug_page.png")
            print("[错误] 未找到密码输入框，截图已保存至 debug_page.png。")
            browser.close()
            return False

        print("[步骤 3/4] 正在填写账号密码...")
        username_input.click()
        username_input.fill("")
        username_input.type(username, delay=50)

        password_input.click()
        password_input.fill("")
        password_input.type(password, delay=50)

        login_button_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("登录")',
            'a:has-text("登录")',
            '.login-btn',
            '#login-account',
            'button.btn-login',
        ]
        clicked = False
        for sel in login_button_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible():
                    btn.click()
                    clicked = True
                    print(f"  点击登录按钮：{sel}")
                    break
            except Exception:
                continue

        if not clicked:
            print("  未找到登录按钮，尝试按 Enter 提交...")
            password_input.press("Enter")

        print("[步骤 4/4] 等待登录结果...")
        # 出现注销按钮即视为登录成功
        logout_confirm_selectors = [
            'button:has-text("注销")',
            'a:has-text("注销")',
            'button:has-text("logout")',
            'a:has-text("logout")',
            'button:has-text("下线")',
            'a:has-text("下线")',
            '#logout-link',
            '.logout-btn',
        ]
        result = False
        deadline = __import__('time').time() + 5
        while __import__('time').time() < deadline:
            for sel in logout_confirm_selectors:
                try:
                    if page.locator(sel).first.is_visible(timeout=300):
                        print(f"\n[OK] 登录成功！（检测到注销按钮：{sel}）")
                        result = True
                        break
                except Exception:
                    continue
            if result:
                break
            __import__('time').sleep(0.1)
        if not result:
            page.screenshot(path="login_result.png")
            print("\n[FAIL] 登录失败或超时，截图已保存至 login_result.png，请人工确认。")

        browser.close()
        return result

# ─────────────────────────────────────────────
#  注销
# ─────────────────────────────────────────────

def logout(headless: bool = HEADLESS_DEFAULT):
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    print(f"[注销] 目标地址：{LOGOUT_URL}")
    print(f"[注销] 浏览器模式：{'无头(后台)' if headless else '显示窗口'}\n")

    with sync_playwright() as p:
        browser, context = _new_browser_context(p, headless)
        page = context.new_page()

        # ── 1. 打开注销页，等待 JS 渲染完成 ───────────
        print("[步骤 1/3] 正在打开注销页面...")
        try:
            page.goto(LOGOUT_URL, timeout=TIMEOUT_MS, wait_until="load")
        except PWTimeout:
            # networkidle 超时后降级，继续尝试
            pass  # 降级忽略

        # 等待页面出现实质内容（修复纯白 BUG 的核心）
        print("[步骤 2/3] 正在等待页面内容渲染...")
        page_text = _wait_for_content(page, timeout_s=5)

        if not page_text:
            page.screenshot(path="logout_blank.png")
            print("[错误] 页面持续为空白，截图已保存至 logout_blank.png，请人工确认。")
            browser.close()
            return False

        # ── 2. 注册浏览器原生弹窗自动接受（window.confirm / alert）─────
        #    必须在点击按钮前注册，否则弹窗出现后无人处理会导致超时
        page.on("dialog", lambda dialog: (
            print(f"  [弹窗] 检测到 {dialog.type}：'{dialog.message}'，自动确认..."),
            dialog.accept()
        ))

        # ── 3. 寻找并点击注销按钮 ─────────────────────
        logout_button_selectors = [
            'button:has-text("注销")',
            'a:has-text("注销")',
            'button:has-text("logout")',
            'a:has-text("logout")',
            'button:has-text("下线")',
            'a:has-text("下线")',
            'input[value="注销"]',
            '#logout-link',
            '.logout-btn',
            '[onclick*="logout"]',
        ]

        clicked = False
        for sel in logout_button_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1_000):
                    # 优先正常点击，失败则用 JS 点击兜底
                    try:
                        btn.click(timeout=2_000)
                    except Exception:
                        page.evaluate("el => el.click()", btn.element_handle())
                    clicked = True
                    print(f"  点击注销按钮：{sel}")
                    break
            except Exception:
                continue

        if not clicked:
            print("  未找到注销按钮，页面可能已自动完成注销。")
            browser.close()
            return True

        # ── 4. 处理自定义 HTML 确认弹窗 ───────────────
        #    若页面弹出的是自定义模态框而非原生 confirm()，自动点击确认按钮
        confirm_button_selectors = [
            'button:has-text("确认")',
            'button:has-text("确定")',
            'button:has-text("是")',
            'button:has-text("OK")',
            'button:has-text("Yes")',
            '.modal button:has-text("注销")',
            '.dialog button:has-text("注销")',
            '.confirm-btn',
            '[class*="confirm"] button',
            '[class*="modal"] button:not(:has-text("取消")):not(:has-text("cancel"))',
        ]
        for sel in confirm_button_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1_000):
                    btn.click(timeout=2_000)
                    print(f"  [弹窗] 点击自定义确认按钮：{sel}")
                    break
            except Exception:
                continue

        # ── 5. 等待页面响应后判断结果 ─────────────────
        print("[步骤 3/3] 等待注销结果...")
        # 出现登录按钮即视为注销成功
        login_confirm_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("登录")',
            'a:has-text("登录")',
            '.login-btn',
            '#login-account',
            'button.btn-login',
            'input[name="username"]',
        ]
        result = False
        deadline = __import__('time').time() + 5
        while __import__('time').time() < deadline:
            for sel in login_confirm_selectors:
                try:
                    if page.locator(sel).first.is_visible(timeout=300):
                        print(f"\n[OK] 注销成功！（检测到登录按钮：{sel}）")
                        result = True
                        break
                except Exception:
                    continue
            if result:
                break
            __import__('time').sleep(0.1)
        if not result:
            page.screenshot(path="logout_result.png")
            print("\n[FAIL] 注销失败或超时，截图已保存至 logout_result.png，请人工确认。")

        browser.close()
        return result

# ─────────────────────────────────────────────
#  命令行入口
# ─────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="河北科技大学校园网自动登录/注销工具 v11（Srun / Playwright）",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-u", "--username", help="学号/账号")
    parser.add_argument("-p", "--password", help="密码")
    parser.add_argument(
        "--logout",
        action="store_true",
        help="执行注销操作（无需账号密码）",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="显示浏览器窗口（调试用）",
    )
    return parser.parse_args()


def main():
    print()
    print("=" * 50)
    print()
    print("  河北科技大学 校园网自动登录工具")
    print("  基于 Playwright 浏览器模拟")
    print()
    print("  作者：北纬之风")
    print("  GitHub：https://github.com/Norsyd")
    print()
    print("=" * 50)
    print()

    ensure_dependencies()

    args = parse_args()
    headless = not args.show_browser

    if args.logout:
        result = logout(headless=headless)
        sys.exit(0 if result else 1)

    if not args.username or not args.password:
        print("[错误] 登录模式需要通过 -u 和 -p 参数传入账号与密码。")
        print("  示例：python hebust_login_v11.py -u 你的学号 -p 你的密码")
        print("  注销：python hebust_login_v11.py --logout")
        sys.exit(1)

    result = login(args.username, args.password, headless=headless)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
