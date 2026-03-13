#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站数据抓取脚本 - 强制提取手机号版
确保手机号提取成功
"""

import time
import csv
import os
import re
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "/Users/yanxin/.openclaw/workspace/tmp/user.csv"

decrypted_phones = {}

def setup_api_listener(page):
    """监听解密API响应"""
    def handle_response(response):
        if "queryCustomerByCopy" in response.url:
            try:
                data = response.json()
                if "data" in data and "phone1" in data["data"]:
                    phone = data["data"]["phone1"]
                    decrypted_phones[response.url] = phone
            except:
                pass
    page.on("response", handle_response)

def extract_phone_from_cell(cell):
    """从单元格中提取手机号（强制版本）"""
    phone = "空"
    
    # 方法1：从 a.Show_Data_In_A_Row 标签提取
    try:
        phone_elem = cell.locator("a.Show_Data_In_A_Row").first
        if phone_elem.count() > 0:
            # 优先从 title 属性获取
            title = phone_elem.get_attribute("title")
            if title and "****" in title:
                phone = title.strip()
                return phone
            
            # 如果没有title，从文本获取
            text = phone_elem.inner_text(timeout=500)
            if text and "****" in text:
                phone = text.strip()
                return phone
    except:
        pass
    
    # 方法2：从单元格所有文本中提取
    try:
        all_text = cell.inner_text(timeout=500)
        match = re.search(r'\d{3}\*{4}\d{4}', all_text)
        if match:
            phone = match.group()
            return phone
    except:
        pass
    
    # 方法3：从HTML中提取
    try:
        html = cell.inner_html()
        match = re.search(r'title="(\d{3}\*{4}\d{4})"', html)
        if match:
            phone = match.group(1)
            return phone
    except:
        pass
    
    return phone

def click_decrypt_and_get_phone(page, cell):
    """点击解密按钮并获取解密后的手机号"""
    try:
        # 查找 title="复制联系电话" 的按钮
        decrypt_btn = cell.locator('i[title="复制联系电话"]').first
        
        if decrypt_btn.count() > 0 and decrypt_btn.is_visible(timeout=500):
            # 清空之前的记录
            decrypted_phones.clear()
            
            # 点击按钮
            decrypt_btn.click(timeout=1000)
            
            # 等待API响应
            time.sleep(1.5)
            
            # 返回解密后的手机号
            if decrypted_phones:
                return list(decrypted_phones.values())[0]
    except:
        pass
    
    return "空"

def parse_cell_text(cell, default="空"):
    """解析单元格文本"""
    try:
        # 尝试从 title 属性获取
        elem = cell.locator("[title]").first
        if elem.count() > 0:
            text = elem.get_attribute("title")
            if text and text.strip():
                return text.strip()
        
        # 直接获取文本
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
                masked_phone = extract_phone_from_cell(phone_cell)
                decrypted_phone = click_decrypt_and_get_phone(page, phone_cell)
                
                # 如果解密失败，使用脱敏手机号
                final_phone = decrypted_phone if decrypted_phone != "空" else masked_phone
                
                # 如果还是空，打印警告
                if final_phone == "空":
                    print(f"   [{idx:2d}] ⚠️  手机号提取失败，跳过该行")
                    continue
                
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
                print(f"   [{idx:2d}] {fields['姓名']:10s} | {masked_phone} -> {final_phone}")
                time.sleep(1)
                
            except Exception as e:
                print(f"   [{idx:2d}] ❌ 失败: {e}")
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
    print("🚀 网站数据抓取工具（强制提取手机号版）")
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
            
            print(f"\n🔍 开始抓取数据...\n")
            
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
