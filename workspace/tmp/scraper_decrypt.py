#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站数据抓取脚本 - 强制解密手机号版
确保每条记录都获取解密后的手机号
"""

import time
import csv
import os
import re
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "/Users/yanxin/.openclaw/workspace/tmp/user.csv"

# 全局变量存储解密后的手机号
last_decrypted_phone = None

def setup_api_listener(page):
    """监听解密API响应"""
    def handle_response(response):
        global last_decrypted_phone
        
        # 监听所有包含 queryCustomerByCopy 的请求
        if "queryCustomerByCopy" in response.url:
            try:
                data = response.json()
                print(f"      📡 API响应: {data}")
                
                # 尝试多种可能的响应格式
                if "data" in data:
                    if "phone1" in data["data"]:
                        last_decrypted_phone = data["data"]["phone1"]
                        print(f"      ✅ 捕获到解密手机号: {last_decrypted_phone}")
                    elif "phone" in data["data"]:
                        last_decrypted_phone = data["data"]["phone"]
                        print(f"      ✅ 捕获到解密手机号: {last_decrypted_phone}")
            except Exception as e:
                print(f"      ⚠️  解析API响应失败: {e}")
    
    page.on("response", handle_response)

def extract_masked_phone(cell):
    """提取脱敏手机号"""
    try:
        phone_elem = cell.locator("a.Show_Data_In_A_Row").first
        if phone_elem.count() > 0:
            title = phone_elem.get_attribute("title")
            if title and "****" in title:
                return title.strip()
            
            text = phone_elem.inner_text(timeout=500)
            if text and "****" in text:
                return text.strip()
    except:
        pass
    
    try:
        all_text = cell.inner_text(timeout=500)
        match = re.search(r'\d{3}\*{4}\d{4}', all_text)
        if match:
            return match.group()
    except:
        pass
    
    return "空"

def click_decrypt_button(page, cell, masked_phone):
    """点击解密按钮并获取解密后的手机号"""
    global last_decrypted_phone
    
    try:
        # 查找解密按钮（title="复制联系电话"）
        decrypt_btn = cell.locator('i[title="复制联系电话"]').first
        
        if decrypt_btn.count() > 0 and decrypt_btn.is_visible(timeout=500):
            # 重置全局变量
            last_decrypted_phone = None
            
            # 点击按钮
            decrypt_btn.click(timeout=1000)
            print(f"      🖱️  已点击解密按钮", end="", flush=True)
            
            # 等待API响应（最多等待5秒）
            for i in range(10):
                time.sleep(0.5)
                if last_decrypted_phone:
                    print(f" ✓")
                    return last_decrypted_phone
                print(".", end="", flush=True)
            
            print(" ⏱️")
            print(f"      ⚠️  未捕获到API响应，等待超时")
            
    except Exception as e:
        print(f"      ❌ 点击解密按钮失败: {e}")
    
    return "空"

def parse_cell_text(cell, default="空"):
    """解析单元格文本"""
    try:
        elem = cell.locator("[title]").first
        if elem.count() > 0:
            text = elem.get_attribute("title")
            if text and text.strip():
                return text.strip()
        
        text = cell.inner_text(timeout=500).strip()
        text = text.replace("\xa0", "").strip()
        return text if text else default
    except:
        return default

def scrape_page(page):
    """抓取当前页"""
    members = []
    time.sleep(2)
    
    try:
        rows = page.locator(".ant-table-row.ant-table-row-level-0").all()
        if not rows:
            print("   ⚠️  当前页没有数据")
            return members
        
        print(f"   找到 {len(rows)} 条记录\n")
        
        for idx, row in enumerate(rows, 1):
            try:
                cells = row.locator("td").all()
                
                if len(cells) < 23:
                    continue
                
                # 提取联系电话（索引3）
                phone_cell = cells[3]
                masked_phone = extract_masked_phone(phone_cell)
                
                if masked_phone == "空":
                    print(f"   [{idx:2d}] ⚠️  无法提取脱敏手机号，跳过该行")
                    continue
                
                # 点击解密按钮
                print(f"   [{idx:2d}] 正在处理 {parse_cell_text(cells[6]):10s}", end="")
                decrypted_phone = click_decrypt_button(page, phone_cell, masked_phone)
                
                # 如果解密失败，使用脱敏手机号
                final_phone = decrypted_phone if decrypted_phone != "空" else masked_phone
                
                if decrypted_phone == "空":
                    print(f"      ⚠️  解密失败，使用脱敏号码: {masked_phone}")
                
                fields = {
                    "联系电话": final_phone,
                    "意向度": parse_cell_text(cells[4]),
                    "来源名称": parse_cell_text(cells[5]),
                    "姓名": parse_cell_text(cells[6]),
                    "微信": parse_cell_text(cells[7]),
                    "QQ": parse_cell_text(cells[8]),
                    "咨询项目": parse_cell_text(cells[9]),
                    "省份": parse_cell_text(cells[10]),
                    "地域": parse_cell_text(cells[11]),
                    "首次咨询时间": parse_cell_text(cells[12]),
                    "过期时间": parse_cell_text(cells[13]),
                    "最后咨询时间": parse_cell_text(cells[14]),
                    "下次回访时间": parse_cell_text(cells[15]),
                    "分配类型": parse_cell_text(cells[16]),
                    "备注": parse_cell_text(cells[17]),
                    "标签": parse_cell_text(cells[18]),
                    "当日外呼次数": parse_cell_text(cells[19]),
                    "当日呼通的次数": parse_cell_text(cells[20]),
                    "当日接通时长": parse_cell_text(cells[21]),
                    "广告商": parse_cell_text(cells[22])
                }
                
                members.append(fields)
                print(f"      📱 {masked_phone} -> {final_phone}")
                
                # 间隔1秒，避免触发限频
                time.sleep(1)
                
            except Exception as e:
                print(f"   [{idx:2d}] ❌ 处理失败: {e}")
                continue
        
    except Exception as e:
        print(f"   ❌ 抓取失败: {e}")
    
    return members

def next_page(page):
    """翻页"""
    try:
        btn = page.locator(".ant-pagination-next:not(.ant-pagination-disabled)").first
        if btn.count() > 0 and btn.is_visible(timeout=1000) and btn.is_enabled(timeout=1000):
            btn.click()
            print("   🔄 已翻到下一页")
            time.sleep(2)
            return True
        print("   ℹ️  已到最后一页")
        return False
    except:
        return False

def save_csv(data, filename):
    """保存CSV"""
    if not data:
        print("\n⚠️  没有数据可保存")
        return False
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
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
    print("\n" + "="*60)
    print("🚀 网站数据抓取工具（强制解密手机号版）")
    print("="*60)
    
    with sync_playwright() as p:
        print("\n🌐 正在启动浏览器...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        setup_api_listener(page)
        
        try:
            page.goto("https://hbsxzxjykjyxgs.n4.bjmantis.cn/", wait_until="networkidle")
            
            print("\n" + "="*60)
            print("⚠️  请手动完成：")
            print("   1. 登录系统")
            print("   2. 导航到【电销客户管理/我的客户/回访】")
            print("   3. 确认页面已显示表格数据")
            print("="*60)
            
            input("\n✅ 完成后按回车开始抓取...")
            
            all_members = []
            page_num = 1
            
            print(f"\n🔍 开始抓取数据（带解密手机号）...\n")
            
            while True:
                print("="*60)
                print(f"📄 第 {page_num} 页")
                print("="*60)
                
                members = scrape_page(page)
                all_members.extend(members)
                
                print("\n   🔄 准备翻页...")
                if not next_page(page):
                    break
                
                page_num += 1
                time.sleep(1)
            
            if all_members:
                save_csv(all_members, OUTPUT_FILE)
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
            except:
                pass
            browser.close()

if __name__ == "__main__":
    main()
