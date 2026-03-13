#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本 - 检查表格结构
"""

import time
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://hbsxzxjykjyxgs.n4.bjmantis.cn/"

def main():
    print("\n🔍 调试模式 - 检查表格结构\n")
    
    # 获取登录信息
    username = input("账号: ").strip()
    password = input("密码: ").strip()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # 登录
            page.goto(LOGIN_URL, wait_until="networkidle")
            
            page.locator("input[type='text'], input[placeholder*='账号']").first.fill(username)
            page.locator("input[type='password']").first.fill(password)
            page.locator("button:has-text('登录')").first.click()
            
            print("✅ 登录成功，等待3秒...")
            time.sleep(3)
            
            # 导航
            print("\n📍 请手动导航到【电销客户管理/我的客户/回访】")
            input("完成后按回车继续...")
            
            # 检查表格结构
            print("\n" + "="*60)
            print("🔍 正在检查表格结构...")
            print("="*60)
            
            # 等待表格加载
            time.sleep(2)
            
            # 检查不同的选择器
            selectors = [
                ".ant-table-row",
                ".ant-table-row.table-select-row",
                ".ant-table-row.ant-table-row-level-0",
                ".ant-table-row.table-select-row.ant-table-row-level-0",
                "tr.ant-table-row",
                "table tbody tr"
            ]
            
            for selector in selectors:
                count = page.locator(selector).count()
                print(f"\n选择器: {selector}")
                print(f"  找到: {count} 个元素")
                
                if count > 0:
                    first_row = page.locator(selector).first
                    cells = first_row.locator("td").all()
                    print(f"  第一行有 {len(cells)} 个单元格")
                    
                    if cells:
                        print("  前3个单元格内容:")
                        for i, cell in enumerate(cells[:3]):
                            try:
                                text = cell.inner_text(timeout=1000).strip()[:50]
                                print(f"    [{i}] {text}")
                            except:
                                print(f"    [{i}] <无法读取>")
            
            # 检查表格是否真的有数据
            print("\n" + "="*60)
            print("📊 检查表格容器...")
            print("="*60)
            
            table = page.locator(".ant-table-body, table").first
            if table.is_visible():
                print("✅ 表格可见")
                html = table.inner_html()[:500]
                print(f"\n表格HTML预览:\n{html}")
            else:
                print("❌ 表格不可见")
            
            print("\n" + "="*60)
            print("🔍 检查联系电话单元格...")
            print("="*60)
            
            # 检查是否有包含****的手机号
            phone_elements = page.locator("text=/\\d{3}\\*{4}\\d{4}/").all()
            print(f"\n找到 {len(phone_elements)} 个脱敏手机号")
            
            if phone_elements:
                for i, elem in enumerate(phone_elements[:3]):
                    try:
                        text = elem.inner_text(timeout=1000)
                        parent = elem.evaluate("el => el.parentElement.outerHTML")
                        print(f"\n[{i+1}] {text}")
                        print(f"    父元素: {parent[:200]}")
                    except:
                        pass
            
            print("\n\n💡 浏览器保持打开，可以手动检查")
            input("\n按回车关闭浏览器...")
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            input("\n按回车关闭浏览器...")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
