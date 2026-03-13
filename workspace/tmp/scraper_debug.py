#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站数据抓取脚本 - 调试版
用于检查实际的表格结构和API响应
"""

import time
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://test-admin.zmexing.com/login"

def debug_table_structure(page):
    """调试：检查表格结构"""
    print("\n" + "="*60)
    print("🔍 正在检查表格结构...")
    print("="*60)
    
    # 等待表格加载
    time.sleep(2)
    
    # 获取第一行数据
    try:
        rows = page.locator("table tbody tr").all()
        if rows:
            print(f"\n✅ 找到 {len(rows)} 行数据")
            
            first_row = rows[0]
            cells = first_row.locator("td").all()
            
            print(f"\n第一行有 {len(cells)} 个单元格：")
            for idx, cell in enumerate(cells):
                text = cell.inner_text(timeout=3000).strip()
                html = cell.inner_html(timeout=3000)[:100]
                print(f"  [{idx}] {text[:30]:30s} | HTML: {html}...")
        else:
            print("❌ 没有找到数据行")
    except Exception as e:
        print(f"❌ 检查失败: {e}")

def debug_decrypt_button(page):
    """调试：检查解密按钮和API响应"""
    print("\n" + "="*60)
    print("🔍 正在测试解密按钮...")
    print("="*60)
    
    # 监听所有网络请求
    api_calls = []
    
    def handle_request(request):
        if "getPhone" in request.url or "phone" in request.url.lower():
            api_calls.append(request.url)
            print(f"  📡 API请求: {request.url}")
    
    def handle_response(response):
        if "getPhone" in response.url or "phone" in response.url.lower():
            print(f"  📥 API响应: {response.url}")
            try:
                data = response.json()
                print(f"  📦 响应数据: {data}")
            except:
                print(f"  📦 响应文本: {response.text()[:200]}")
    
    page.on("request", handle_request)
    page.on("response", handle_response)
    
    try:
        rows = page.locator("table tbody tr").all()
        if rows:
            first_row = rows[0]
            cells = first_row.locator("td").all()
            
            # 找到包含手机号的单元格
            for idx, cell in enumerate(cells):
                text = cell.inner_text(timeout=3000)
                if "****" in text:
                    print(f"\n📱 找到手机号单元格 [{idx}]: {text}")
                    
                    # 查找所有可能的按钮
                    buttons = cell.locator("button, i, .el-icon, [class*='icon']").all()
                    print(f"  找到 {len(buttons)} 个可点击元素")
                    
                    for btn_idx, btn in enumerate(buttons):
                        try:
                            class_name = btn.get_attribute("class") or ""
                            tag = btn.evaluate("el => el.tagName")
                            print(f"  [{btn_idx}] <{tag}> class='{class_name}'")
                        except:
                            pass
                    
                    # 尝试点击第一个按钮
                    if buttons:
                        print("\n  🖱️  尝试点击第一个按钮...")
                        buttons[0].click(timeout=3000)
                        time.sleep(3)  # 等待API响应
                        
                        # 再次读取单元格内容
                        new_text = cell.inner_text(timeout=3000)
                        print(f"  📝 点击后内容: {new_text}")
                        
                        # 检查是否有tooltip
                        try:
                            tooltip = page.locator(".el-tooltip__popper, .el-popper, [role='tooltip']").first
                            if tooltip.is_visible(timeout=1000):
                                tooltip_text = tooltip.inner_text(timeout=1000)
                                print(f"  💬 Tooltip内容: {tooltip_text}")
                        except:
                            pass
                    
                    break
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    if not api_calls:
        print("\n⚠️  没有捕获到任何 API 调用")

def main():
    print("\n" + "="*60)
    print("🐛 调试模式启动")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # 打开登录页面
            page.goto(LOGIN_URL, wait_until="networkidle")
            
            # 等待手动登录
            print("\n⏳ 请手动登录...")
            page.wait_for_function(
                "window.location.href.indexOf('login') === -1",
                timeout=0
            )
            time.sleep(2)
            print("✅ 登录成功！")
            
            # 导航到会员列表
            print("\n📍 请手动导航到【会员管理/会员列表】")
            input("完成后按回车继续...")
            
            # 调试表格结构
            debug_table_structure(page)
            
            # 调试解密按钮
            debug_decrypt_button(page)
            
            print("\n" + "="*60)
            print("✅ 调试完成，浏览器保持打开")
            print("="*60)
            
            input("\n按回车关闭浏览器...")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
