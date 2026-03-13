#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网站数据抓取脚本 - 手动导航版
适用于已经手动导航到目标页面的情况
"""

import time
import csv
import os
from playwright.sync_api import sync_playwright

# 配置
OUTPUT_FILE = "/Users/yanxin/.openclaw/workspace/tmp/user.csv"
DECRYPT_API = "https://b1003.n8.bjmantis.cn/msp-war/customer/queryCustomerByCopy.do"

# 全局变量存储解密后的手机号
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
        text = text.replace("\xa0", "").strip()
        return text if text else default
    except:
        return default

def scrape_current_page(page):
    """抓取当前页的数据"""
    members = []
    
    # 等待表格加载
    time.sleep(3)
    
    try:
        # 使用正确的选择器
        rows = page.locator(".ant-table-row.ant-table-row-level-0").all()
        
        if not rows:
            print("   ⚠️  当前页没有数据")
            return members
        
        print(f"   找到 {len(rows)} 条记录\n")
        
        for idx, row in enumerate(rows, 1):
            try:
                print(f"   [{idx:2d}] 正在处理...", end="", flush=True)
                
                # 获取所有单元格
                cells = row.locator("td").all()
                
                if len(cells) < 23:
                    print(f" ⚠️  单元格数量不足 ({len(cells)}/23)")
                    continue
                
                fields = {}
                
                # 联系电话（第4列，索引3）
                phone_cell = cells[3]
                masked_phone = "空"
                decrypted_phone = "空"
                
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
    print("🚀 网站数据抓取工具启动（手动导航版）")
    print("="*60)
    
    with sync_playwright() as p:
        # 启动浏览器
        print("\n🌐 正在启动浏览器...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 设置API监听
        setup_api_listener(page)
        
        try:
            # 打开登录页面
            print(f"\n📍 正在打开登录页面...")
            page.goto("https://hbsxzxjykjyxgs.n4.bjmantis.cn/", wait_until="networkidle")
            
            # 等待用户手动操作
            print("\n" + "="*60)
            print("⚠️  请手动完成以下操作：")
            print("   1. 登录系统")
            print("   2. 导航到【电销客户管理/我的客户/回访】页面")
            print("   3. 确认页面已显示表格数据")
            print("="*60)
            
            input("\n✅ 完成后按回车开始抓取...")
            
            # 开始抓取
            all_members = []
            page_num = 1
            
            print(f"\n🔍 开始抓取数据...\n")
            
            while True:
                print("="*60)
                print(f"📄 第 {page_num} 页")
                print("="*60)
                
                # 抓取当前页
                members = scrape_current_page(page)
                all_members.extend(members)
                
                # 尝试翻页
                print("\n   🔄 准备翻页...")
                if not go_to_next_page(page):
                    break
                
                page_num += 1
                time.sleep(1)  # 翻页间隔
            
            # 保存数据
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
