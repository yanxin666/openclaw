#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站数据抓取脚本 - 第二版
功能：自动登录并抓取客户列表数据，包含解密手机号
"""

import time
import csv
import os
import json
from playwright.sync_api import sync_playwright

# 配置
LOGIN_URL = "https://hbsxzxjykjyxgs.n4.bjmantis.cn/"
OUTPUT_FILE = "/Users/yanxin/.openclaw/workspace/tmp/user.csv"
DECRYPT_API = "https://b1003.n8.bjmantis.cn/msp-war/customer/queryCustomerByCopy.do"

# 全局变量存储解密后的手机号
decrypted_phones = {}

def setup_api_listener(page):
    """监听解密API响应"""
    def handle_response(response):
        if DECRYPT_API in response.url:
            try:
                data = response.json()
                if "data" in data and "phone1" in data["data"]:
                    phone = data["data"]["phone1"]
                    # 存储到字典中
                    decrypted_phones[response.url] = phone
                    print(f"      📱 捕获到解密手机号: {phone}")
            except Exception as e:
                print(f"      ⚠️  解析API响应失败: {e}")
    
    page.on("response", handle_response)

def login(page, username, password):
    """登录系统"""
    print("\n🔐 正在登录...")
    
    try:
        # 等待页面加载
        page.wait_for_load_state("networkidle", timeout=10000)
        
        # 输入账号
        username_input = page.locator("input[type='text'], input[placeholder*='账号'], input[placeholder*='用户名']").first
        username_input.fill(username, timeout=5000)
        print("   ✅ 已输入账号")
        time.sleep(0.5)
        
        # 输入密码
        password_input = page.locator("input[type='password']").first
        password_input.fill(password, timeout=5000)
        print("   ✅ 已输入密码")
        time.sleep(0.5)
        
        # 点击登录按钮
        login_btn = page.locator("button:has-text('登录'), button[type='submit']").first
        login_btn.click(timeout=5000)
        print("   🖱️  已点击登录按钮")
        
        # 等待登录成功
        time.sleep(3)
        page.wait_for_load_state("networkidle", timeout=10000)
        
        print("✅ 登录成功！")
        return True
        
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return False

def navigate_to_customer_list(page):
    """导航到客户列表页面"""
    print("\n📍 正在导航到【电销客户管理/我的客户/回访】...")
    
    try:
        # 尝试自动点击菜单
        menu_items = [
            "电销客户管理",
            "我的客户",
            "回访"
        ]
        
        for menu_text in menu_items:
            try:
                menu = page.locator(f"text={menu_text}").first
                if menu.is_visible(timeout=3000):
                    menu.click()
                    print(f"   ✅ 已点击【{menu_text}】")
                    time.sleep(1)
            except:
                pass
        
        # 等待列表加载
        time.sleep(2)
        page.wait_for_load_state("networkidle", timeout=10000)
        
        print("✅ 已进入客户列表页面")
        return True
        
    except Exception as e:
        print(f"⚠️  自动导航失败: {e}")
        print("💡 请手动导航到【电销客户管理/我的客户/回访】")
        input("   完成后按回车继续...")
        return True

def parse_table_cell(cell, default="空"):
    """解析表格单元格内容"""
    try:
        text = cell.inner_text(timeout=2000).strip()
        return text if text else default
    except:
        return default

def scrape_current_page(page):
    """抓取当前页的数据"""
    members = []
    
    # 等待表格加载
    time.sleep(2)
    
    try:
        # 查找所有表格行
        rows = page.locator(".ant-table-row.table-select-row.ant-table-row-level-0").all()
        
        if not rows:
            print("   ⚠️  当前页没有数据")
            return members
        
        print(f"   找到 {len(rows)} 条记录\n")
        
        for idx, row in enumerate(rows, 1):
            try:
                print(f"   [{idx:2d}] 正在处理...")
                
                # 获取所有单元格
                cells = row.locator("td").all()
                
                # 解析各字段（根据实际的列顺序调整）
                # 假设列顺序：联系电话、意向度、来源名称、姓名、微信、QQ、咨询项目、省份、地域、首次咨询时间、过期时间、最后咨询时间、下次回访时间、分配类型、备注、标签、当日外呼次数、当日呼通的次数、当日接通时长、广告商
                
                field_names = [
                    "联系电话", "意向度", "来源名称", "姓名", "微信", "QQ", 
                    "咨询项目", "省份", "地域", "首次咨询时间", "过期时间", 
                    "最后咨询时间", "下次回访时间", "分配类型", "备注", "标签",
                    "当日外呼次数", "当日呼通的次数", "当日接通时长", "广告商"
                ]
                
                # 解析所有字段
                fields = {}
                for i, field_name in enumerate(field_names):
                    if i < len(cells):
                        fields[field_name] = parse_table_cell(cells[i])
                    else:
                        fields[field_name] = "空"
                
                # 点击解密按钮获取完整手机号
                decrypted_phone = "空"
                try:
                    # 查找联系电话单元格中的解密按钮
                    phone_cell = cells[0]  # 假设联系电话在第一列
                    decrypt_btn = phone_cell.locator("span[style*='position: relative']").first
                    
                    if decrypt_btn.is_visible(timeout=1000):
                        # 清空之前的记录
                        decrypted_phones.clear()
                        
                        # 点击解密按钮
                        decrypt_btn.click(timeout=2000)
                        print(f"      🖱️  已点击解密按钮")
                        
                        # 等待API响应
                        time.sleep(1.5)
                        
                        # 从捕获的响应中获取手机号
                        if decrypted_phones:
                            decrypted_phone = list(decrypted_phones.values())[0]
                            print(f"      ✅ 解密成功: {fields['联系电话']} -> {decrypted_phone}")
                        else:
                            decrypted_phone = fields['联系电话']  # 使用原始脱敏号码
                            print(f"      ⚠️  未捕获到API响应，使用脱敏号码")
                    
                except Exception as e:
                    decrypted_phone = fields['联系电话']
                    print(f"      ⚠️  解密失败: {e}")
                
                # 更新联系电话为解密后的号码
                fields['联系电话'] = decrypted_phone
                
                members.append(fields)
                
                # 模拟真人操作，间隔1秒
                time.sleep(1)
                
            except Exception as e:
                print(f"   ❌ 第{idx}行处理失败: {e}")
                continue
        
    except Exception as e:
        print(f"   ❌ 抓取失败: {e}")
    
    return members

def go_to_next_page(page):
    """翻到下一页"""
    try:
        # 查找下一页按钮（Ant Design 分页）
        next_btn = page.locator(".ant-pagination-next:not(.ant-pagination-disabled)").first
        
        if next_btn.is_visible(timeout=2000) and next_btn.is_enabled(timeout=2000):
            next_btn.click()
            print("   🔄 已翻到下一页")
            time.sleep(2)  # 等待页面加载
            return True
        else:
            print("   ℹ️  已到最后一页")
            return False
            
    except Exception as e:
        print(f"   ⚠️  翻页失败: {e}")
        return False

def save_to_csv(data, filename):
    """保存数据到CSV文件"""
    if not data:
        print("\n⚠️  没有数据可保存")
        return False
    
    # 确保目录存在
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # CSV字段名
    fieldnames = [
        "联系电话", "意向度", "来源名称", "姓名", "微信", "QQ", 
        "咨询项目", "省份", "地域", "首次咨询时间", "过期时间", 
        "最后咨询时间", "下次回访时间", "分配类型", "备注", "标签",
        "当日外呼次数", "当日呼通的次数", "当日接通时长", "广告商"
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"\n✅ 数据已保存到: {filename}")
    print(f"📊 共保存 {len(data)} 条记录")
    return True

def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 网站数据抓取工具启动（第二版）")
    print("="*60)
    
    # 获取登录信息
    print("\n📝 请输入登录信息：")
    username = input("   账号: ").strip()
    password = input("   密码: ").strip()
    
    if not username or not password:
        print("❌ 账号和密码不能为空")
        return
    
    with sync_playwright() as p:
        # 启动浏览器
        print("\n🌐 正在启动浏览器...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 设置API监听
        setup_api_listener(page)
        
        try:
            # 1. 打开登录页面
            print(f"\n📍 正在打开登录页面...")
            page.goto(LOGIN_URL, wait_until="networkidle")
            
            # 2. 登录
            if not login(page, username, password):
                raise Exception("登录失败")
            
            # 3. 导航到客户列表
            navigate_to_customer_list(page)
            
            # 4. 抓取数据（自动翻页）
            all_members = []
            page_num = 1
            
            print(f"\n🔍 开始抓取数据...\n")
            print("="*60)
            
            while True:
                print(f"\n📄 第 {page_num} 页")
                print("="*60)
                
                # 抓取当前页
                members = scrape_current_page(page)
                all_members.extend(members)
                
                # 尝试翻页
                if not go_to_next_page(page):
                    break
                
                page_num += 1
                time.sleep(1)  # 翻页间隔
            
            # 5. 保存数据
            if all_members:
                save_to_csv(all_members, OUTPUT_FILE)
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
            print("\n💡 浏览器将保持打开...")
            try:
                input("按回车关闭浏览器并退出...")
            except KeyboardInterrupt:
                pass
            
            browser.close()

if __name__ == "__main__":
    main()
