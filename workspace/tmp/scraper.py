#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站数据抓取脚本 - 增强版
功能：自动登录并抓取会员列表数据（前3页），自动捕获API响应
"""

import time
import csv
import os
import json
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# 配置
LOGIN_URL = "https://test-admin.zmexing.com/login"
OUTPUT_FILE = os.path.expanduser("~/workspace/tmp/user.csv")
MAX_PAGES = 3

# 全局变量存储API响应
api_responses = {}

def setup_network_listener(page):
    """监听网络请求，捕获API响应"""
    def handle_response(response):
        url = response.url
        # 监听获取手机号的API
        if "/admin/member/getPhone" in url:
            try:
                data = response.json()
                # 从URL参数中提取 memberId 或其他标识
                # 假设返回格式：{"data": {"phone": "13800138000"}}
                if "data" in data and "phone" in data["data"]:
                    phone = data["data"]["phone"]
                    # 存储到字典中
                    api_responses[url] = phone
                    print(f"   📱 捕获到解密手机号: {phone}")
            except:
                pass
    
    page.on("response", handle_response)

def wait_for_login(page):
    """等待用户手动登录"""
    print("\n" + "="*60)
    print("🔐 请在浏览器中手动完成登录：")
    print("   1. 输入账号")
    print("   2. 输入密码")
    print("   3. 输入验证码（数字）")
    print("   4. 点击登录按钮")
    print("="*60)
    print("\n⏳ 等待登录成功...")
    
    # 等待URL不再包含 'login'
    try:
        page.wait_for_function(
            "window.location.href.indexOf('login') === -1",
            timeout=0  # 无限等待
        )
    except:
        pass
    
    time.sleep(2)
    print("✅ 登录成功！")

def navigate_to_member_list(page):
    """导航到会员列表页面"""
    print("\n📍 正在导航到【会员管理/会员列表】...")
    
    try:
        # 尝试找到菜单
        member_menu = page.locator("text=会员管理").first
        if member_menu.is_visible(timeout=5000):
            member_menu.click()
            time.sleep(0.5)
            
            member_list = page.locator("text=会员列表").first
            if member_list.is_visible(timeout=3000):
                member_list.click()
                time.sleep(2)
                print("✅ 已进入会员列表页面")
                return True
    except:
        pass
    
    print("💡 请手动点击菜单【会员管理/会员列表】")
    input("完成后按回车继续...")
    return True

def scrape_page(page):
    """抓取当前页的数据"""
    members = []
    
    # 等待表格加载
    time.sleep(2)
    
    try:
        # 获取表格所有行
        rows = page.locator("table tbody tr").all()
        
        if not rows:
            print("   ⚠️  当前页没有数据")
            return members
        
        print(f"   找到 {len(rows)} 条记录")
        
        for idx, row in enumerate(rows, 1):
            try:
                cells = row.locator("td").all()
                if len(cells) < 5:
                    continue
                
                # 提取基本信息（根据实际列顺序调整）
                member_id = cells[0].inner_text(timeout=3000).strip()
                role = cells[1].inner_text(timeout=3000).strip()
                nickname = cells[2].inner_text(timeout=3000).strip()
                real_name = cells[3].inner_text(timeout=3000).strip()
                masked_phone = cells[4].inner_text(timeout=3000).strip()
                
                # 点击解密按钮
                decrypted_phone = ""
                try:
                    # 查找解密按钮
                    decrypt_btn = cells[4].locator(".el-icon, i[class*='el-icon']").first
                    
                    if decrypt_btn.is_visible(timeout=2000):
                        # 清空之前的API响应
                        api_responses.clear()
                        
                        # 点击按钮
                        decrypt_btn.click(timeout=3000)
                        
                        # 等待API响应
                        time.sleep(1.5)
                        
                        # 从捕获的API响应中获取手机号
                        if api_responses:
                            decrypted_phone = list(api_responses.values())[0]
                        else:
                            # 如果没有捕获到API响应，尝试从页面读取
                            try:
                                # 可能显示在tooltip或其他地方
                                tooltip = page.locator(".el-tooltip__popper, .el-popper").first
                                if tooltip.is_visible(timeout=1000):
                                    decrypted_phone = tooltip.inner_text(timeout=1000).strip()
                            except:
                                decrypted_phone = "未捕获到API响应"
                except Exception as e:
                    decrypted_phone = f"获取失败: {str(e)[:20]}"
                
                member_data = {
                    "用户Id": member_id,
                    "角色": role,
                    "昵称": nickname,
                    "姓名": real_name,
                    "脱敏手机号": masked_phone,
                    "解密手机号": decrypted_phone
                }
                
                members.append(member_data)
                print(f"   [{idx:2d}] {real_name:10s} | {masked_phone} -> {decrypted_phone}")
                
            except Exception as e:
                print(f"   ❌ 第{idx}行处理失败: {e}")
                continue
        
    except Exception as e:
        print(f"   ❌ 抓取失败: {e}")
    
    return members

def scrape_member_data(page, max_pages=3):
    """抓取会员数据（多页）"""
    all_members = []
    current_page = 1
    
    print(f"\n🔍 开始抓取数据（共{max_pages}页）...\n")
    
    while current_page <= max_pages:
        print(f"\n{'='*60}")
        print(f"📄 第 {current_page}/{max_pages} 页")
        print('='*60)
        
        # 抓取当前页
        members = scrape_page(page)
        all_members.extend(members)
        
        # 翻页
        if current_page < max_pages:
            print(f"\n   🔄 准备翻到下一页...")
            try:
                # 查找下一页按钮（Element UI）
                next_btn = page.locator(".el-pagination .btn-next").first
                
                if next_btn.is_enabled(timeout=3000):
                    next_btn.click()
                    current_page += 1
                    time.sleep(2)
                else:
                    print("   ⚠️  已到最后一页")
                    break
            except Exception as e:
                print(f"   ❌ 翻页失败: {e}")
                print("   💡 请手动翻页后按回车继续...")
                input()
                current_page += 1
        else:
            break
    
    return all_members

def save_to_csv(data, filename):
    """保存数据到CSV文件"""
    if not data:
        print("\n⚠️  没有数据可保存")
        return False
    
    # 确保目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=["用户Id", "角色", "昵称", "姓名", "脱敏手机号", "解密手机号"])
        writer.writeheader()
        writer.writerows(data)
    
    print(f"\n✅ 数据已保存到: {filename}")
    print(f"📊 共保存 {len(data)} 条记录")
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 网站数据抓取工具启动")
    print(f"📋 目标：抓取前 {MAX_PAGES} 页会员数据")
    print("="*60)
    
    with sync_playwright() as p:
        # 启动浏览器
        print("\n🌐 正在启动浏览器...")
        browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized']  # 最大化窗口
        )
        context = browser.new_context(
            viewport=None  # 使用实际窗口大小
        )
        page = context.new_page()
        
        # 设置网络监听
        setup_network_listener(page)
        
        try:
            # 1. 打开登录页面
            print(f"\n📍 正在打开登录页面...")
            page.goto(LOGIN_URL, wait_until="networkidle")
            
            # 2. 等待用户手动登录
            wait_for_login(page)
            
            # 3. 导航到会员列表
            navigate_to_member_list(page)
            
            # 4. 抓取数据
            members = scrape_member_data(page, MAX_PAGES)
            
            # 5. 保存数据
            if members:
                save_to_csv(members, OUTPUT_FILE)
            else:
                print("\n❌ 未抓取到任何数据")
            
            print("\n" + "="*60)
            print("✨ 抓取任务完成！")
            print("="*60)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断操作")
        except Exception as e:
            print(f"\n\n❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n💡 浏览器将保持打开，可以查看数据...")
            try:
                input("按回车关闭浏览器并退出...")
            except KeyboardInterrupt:
                pass
            
            browser.close()

if __name__ == "__main__":
    main()
