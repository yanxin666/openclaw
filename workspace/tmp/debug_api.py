#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本 - 查看实际的API调用
"""

import time
from playwright.sync_api import sync_playwright

def main():
    print("\n🔍 调试模式 - 查看API调用\n")
    
    with sync_playwright() as p:
        print("🌐 正在启动浏览器...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # 监听所有网络请求
        all_requests = []
        all_responses = []
        
        def handle_request(request):
            url = request.url
            if "phone" in url.lower() or "customer" in url.lower() or "copy" in url.lower():
                all_requests.append({
                    'url': url,
                    'method': request.method,
                    'headers': dict(request.headers)
                })
                print(f"\n📤 请求: {request.method} {url}")
        
        def handle_response(response):
            url = response.url
            if "phone" in url.lower() or "customer" in url.lower() or "copy" in url.lower():
                try:
                    text = response.text()
                    all_responses.append({
                        'url': url,
                        'status': response.status,
                        'body': text[:500]
                    })
                    print(f"\n📥 响应 [{response.status}]: {url}")
                    print(f"   内容: {text[:500]}")
                except:
                    pass
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        try:
            page.goto("https://hbsxzxjykjyxgs.n4.bjmantis.cn/", wait_until="networkidle")
            
            print("\n" + "="*60)
            print("⚠️  请手动完成：")
            print("   1. 登录系统")
            print("   2. 导航到【电销客户管理/我的客户/回访】")
            print("   3. 手动点击一个解密按钮")
            print("="*60)
            
            input("\n✅ 完成后按回车查看结果...")
            
            print("\n" + "="*60)
            print("📊 网络请求汇总：")
            print("="*60)
            
            print(f"\n共捕获 {len(all_requests)} 个相关请求")
            for i, req in enumerate(all_requests, 1):
                print(f"\n[{i}] {req['method']} {req['url']}")
                if 'headers' in req and 'Cookie' in req['headers']:
                    print(f"   Cookie: {req['headers']['Cookie'][:100]}...")
            
            print(f"\n\n共捕获 {len(all_responses)} 个相关响应")
            for i, resp in enumerate(all_responses, 1):
                print(f"\n[{i}] [{resp['status']}] {resp['url']}")
                print(f"   {resp['body']}")
            
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
