#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站数据抓取脚本 - 修正版
根据实际HTML结构修正
"""

import time
import csv
import os
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
        if DECRYPT_API in response.url or "queryCustomerByCopy" in response.url:
            try:
                data = response.json()
                if "data" in data and "phone1" in data["data"]:
                    phone = data["data"]["phone1"]
                    decrypted_phones[response.url] = phone
                    print(f"      📱 捕获到解密手机号: {phone}")
            except Exception as e:
                pass
    
    page.on("response", handle_response)

def parse_cell_text(cell, default="空"):
    """解析单元格文本"""
    try:
        # 尝试从 title 属性获取
        elem = cell.locator("[title]").first
        if elem.is_visible(timeout=500):
            text = elem.get_attribute("title")
            if text and text.strip():
                return text.strip()
        
        # 如果没有title，直接获取文本
        text = cell.inner_text(timeout=1000).strip()
        # 过滤掉 &nbsp; 和空格
        text = text.replace("\xa0", "").strip()
        return text if text else default
    except:
        return default

def login(page, username, password):
    """登录系统"""
    print("\n🔐 正在登录...")
    
    try:
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
        menu_items = ["电销客户管理", "我的客户", "回访"]
        
        for menu_text in menu_items:
            try:
                menu = page.locator(f"text={menu_text}").first
                if menu.is_visible(timeout=3000):
                    menu.click()
                    print(f"   ✅ 已点击【{menu_text}】")
                    time.sleep(1)
            except:
                pass
        
        time.sleep(2)
        page.wait_for_load_state("networkidle", timeout=10000)
        
        print("✅ 已进入客户列表页面")
        return True
        
    except Exception as e:
        print(f"⚠️  自动导航失败: {e}")
        print("💡 请手动导航到【电销客户管理/我的客户/回访】")
        input("   完成后按回车继续...")
        return True

def scrape_current_page(page):
    """抓取当前页的数据"""
    members = []
    
    # 等待表格加载
    time.sleep(2)
    
    try:
        # 使用正确的选择器
        rows = page.locator(".ant-table-row.ant-table-row-level-0").all()
        
        if not rows:
            print("   ⚠️  当前页没有数据")
            return members
        
        print(f"   找到 {len(rows)} 条记录\n")
        
        for idx, row in enumerate(rows, 1):
            try:
                print(f"   [{idx:2d}] 正在处理...", end="")
                
                # 获取所有单元格
                cells = row.locator("td").all()
                
                # 根据实际列顺序提取字段
                # 第4列（索引3）：联系电话
                # 第5列（索引4）：意向度
                # 第6列（索引5）：来源名称
                # 第7列（索引6）：姓名
                # 第8列（索引7）：微信
                # 第9列（索引8）：QQ
                # 第10列（索引9）：咨询项目
                # 第11列（索引10）：省份
                # 第12列（索引11）：地域
                # 第13列（索引12）：首次咨询时间
                # 第14列（索引13）：过期时间
                # 第15列（索引14）：最后咨询时间
                # 第16列（索引15）：下次回访时间
                # 第17列（索引16）：分配类型
                # 第18列（索引17）：备注
                # 第19列（索引18）：标签
                # 第20列（索引19）：当日外呼次数
                # 第21列（索引20）：当日呼通的次数
                # 第22列（索引21）：当日接通时长
                # 第23列（索引22）：广告商
                
                fields = {}
                
                # 联系电话（第4列，索引3）
                phone_cell = cells[3] if len(cells) > 3 else None
                masked_phone = "空"
                decrypted_phone = "空"
                
                if phone_cell:
                    try:
                        # 获取脱敏手机号
                        phone_link = phone_cell.locator("a.Show_Data_In_A_Row").first
                        if phone_link.is_visible(timeout=1000):
                            masked_phone = phone_link.get_attribute("title") or phone_link.inner_text(timeout=1000)
                            masked_phone = masked_phone.strip()
                        
                        # 点击解密按钮
                        try:
                            decrypt_btn = phone_cell.locator("span[style*='position: relative'] i.anticon-copy").first
                            if decrypt_btn.is_visible(timeout=1000):
                                # 清空之前的记录
                                decrypted_phones.clear()
                                
                                # 点击按钮
                                decrypt_btn.click(timeout=2000)
                                
                                # 等待API响应
                                time.sleep(1.5)
                                
                                # 获取解密后的手机号
                                if decrypted_phones:
                                    decrypted_phone = list(decrypted_phones.values())[0]
                        except Exception as e:
                            pass
                    except:
                        pass
                
                fields["联系电话"] = decrypted_phone if decrypted_phone != "空" else masked_phone
                
                # 其他字段
                field_mappings = {
                    4: "意向度",
                    5: "来源名称",
                    6: "姓名",
                    7: "微信",
                    8: "QQ",
                    9: "咨询项目",
                    10: "省份",
                    11: "地域",
                    12: "首次咨询时间",
                    13: "过期时间",
                    14: "最后咨询时间",
                    15: "下次回访时间",
                    16: "分配类型",
                    17: "备注",
                    18: "标签",
                    19: "当日外呼次数",
                    20: "当日呼通的次数",
                    21: "当日接通时长",
                    22: "广告商"
                }
                
                for cell_idx, field_name in field_mappings.items():
                    if cell_idx < len(cells):
                        fields[field_name] = parse_cell_text(cells[cell_idx])
                    else:
                        fields[field_name] = "空"
                
                members.append(fields)
                
                # 显示进度
                print(f" {fields['姓名']:10s} | {masked_phone} -> {decrypted_phone}")
                
                # 模拟真人操作，间隔1秒
                time.sleep(1)
                
            except Exception as e:
                print(f" ❌ 失败: {e}")
                continue
        
    except Exception as e:
        print(f"   ❌ 抓取失败: {e}")
    
    return members

def go_to_next_page(page):
    """翻到下一页"""
    try:
        next_btn = page.locator(".ant-pagination-next:not(.ant-pagination-disabled)").first
        
        if next_btn.is_visible(timeout=2000) and next_btn.is_enabled(timeout=2000):
            next_btn.click()
            print("   🔄 已翻到下一页")
            time.sleep(2)
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
    print("🚀 网站数据抓取工具启动（修正版）")
    print("="*60)
    
    # 获取登录信息
    username = "sy-yanjin1"
    password = "Aa888888"
    
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
