#!/usr/bin/env python3
"""
测试Immich图片上传功能
"""
import asyncio
import sys
import os
import aiohttp
from io import BytesIO

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def print_log(message):
    """简单的日志输出"""
    print(f"[INFO] {message}")

def print_error(message):
    """错误日志输出"""
    print(f"[ERROR] {message}")

def print_warning(message):
    """警告日志输出"""
    print(f"[WARNING] {message}")

async def test_upload_direct():
    """直接测试上传图片到Immich（不依赖项目模块）"""
    api_url = "http://127.0.0.1:2283/api"
    api_key = "ZbQpVHwESQC4chEUJyVYoIyP6pVUFJvpRh1llIOYbw"
    email = "deep-diary@qq.com"
    password = "deep-diary666"
    
    # 先尝试登录获取accessToken
    print_log("尝试登录获取accessToken...")
    login_url = f"{api_url}/auth/login"
    timeout = aiohttp.ClientTimeout(total=30)
    
    access_token = None
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                login_url,
                json={"email": email, "password": password},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200 or response.status == 201:
                    login_result = await response.json()
                    access_token = login_result.get("accessToken")
                    if access_token:
                        print_log(f"✅ 登录成功，获取到accessToken: {access_token[:20]}...")
                    else:
                        print_warning("登录成功但未获取到accessToken")
                else:
                    print_warning(f"登录失败: HTTP {response.status}")
                    response_text = await response.text()
                    print_warning(f"响应: {response_text}")
    except Exception as e:
        print_error(f"登录异常: {e}")
    
    # 准备headers，优先使用accessToken，否则使用api_key
    if access_token:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        print_log("使用Bearer token进行认证")
    else:
        headers = {
            "x-api-key": api_key,
            "Accept": "application/json"
        }
        print_log("使用x-api-key进行认证")
    
    # 读取测试图片
    image_path = os.path.join(current_dir, "config", "assets", "IMG_20251101_105817.jpg")
    
    if not os.path.exists(image_path):
        print_error(f"测试图片不存在: {image_path}")
        return
    
    print_log(f"读取测试图片: {image_path}")
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    print_log(f"图片大小: {len(image_data)} bytes ({len(image_data)/1024/1024:.2f} MB)")
    
    headers = {
        "x-api-key": api_key,
        "Accept": "application/json"
    }
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    # 先测试API根路径是否可访问
    print_log(f"\n测试API根路径: {api_url}")
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{api_url}", headers=headers) as response:
                print_log(f"API根路径响应: {response.status}")
                if response.status == 200:
                    root_info = await response.text()
                    print_log(f"API信息: {root_info[:200]}")
    except Exception as e:
        print_warning(f"无法访问API根路径: {e}")
    
    # 测试不同的API路径和认证方式
    base_url = api_url.rstrip('/api') if api_url.endswith('/api') else api_url
    
    # 准备不同的headers组合
    test_configs = []
    if access_token:
        test_configs.append({
            "url": f"{api_url}/asset/upload",
            "headers": {"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            "name": "Bearer token + /api/asset/upload"
        })
        test_configs.append({
            "url": f"{base_url}/api/asset/upload",
            "headers": {"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            "name": "Bearer token + base/api/asset/upload"
        })
    
    # 也测试x-api-key方式
    test_configs.append({
        "url": f"{api_url}/asset/upload",
        "headers": {"x-api-key": api_key, "Accept": "application/json"},
        "name": "x-api-key + /api/asset/upload"
    })
    test_configs.append({
        "url": f"{base_url}/api/asset/upload",
        "headers": {"x-api-key": api_key, "Accept": "application/json"},
        "name": "x-api-key + base/api/asset/upload"
    })
    
    for test_config in test_configs:
        upload_url = test_config["url"]
        test_headers = test_config["headers"]
        test_name = test_config["name"]
        
        print_log(f"\n尝试上传 ({test_name}): {upload_url}")
        
        try:
            data = aiohttp.FormData()
            data.add_field(
                'assetData',
                BytesIO(image_data),
                filename='image.jpg',
                content_type='image/jpeg'
            )
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(upload_url, headers=test_headers, data=data) as response:
                    response_text = await response.text()
                    print_log(f"响应状态: {response.status}")
                    print_log(f"响应内容: {response_text[:200]}")
                    
                    if response.status == 200 or response.status == 201:
                        result = await response.json()
                        asset_id = result.get("id")
                        print_log(f"✅ 上传成功！资产ID: {asset_id}")
                        
                        # 测试获取资产详情
                        asset_url = f"{api_url}/asset/{asset_id}"
                        print_log(f"\n测试获取资产详情: {asset_url}")
                        async with session.get(asset_url, headers=test_headers) as asset_response:
                            if asset_response.status == 200:
                                asset = await asset_response.json()
                                print_log(f"✅ 获取资产详情成功")
                                print_log(f"   资产类型: {asset.get('type')}")
                                print_log(f"   人物数量: {len(asset.get('people', []))}")
                                print_log(f"   人脸数量: {len(asset.get('faces', []))}")
                                
                                if asset.get('people'):
                                    print_log(f"\n识别到的人物:")
                                    for person in asset.get('people', []):
                                        print_log(f"   - {person.get('name', '未命名')} (ID: {person.get('id')})")
                            else:
                                print_warning(f"获取资产详情失败: HTTP {asset_response.status}")
                        
                        return  # 成功就退出
                    else:
                        print_warning(f"上传失败: HTTP {response.status}")
                        
        except aiohttp.ClientError as e:
            print_error(f"网络错误: {e}")
        except Exception as e:
            print_error(f"异常: {e}")
    
    # 如果都失败了，提供诊断信息
    print_error("\n❌ 所有上传尝试都失败了")
    print_log("\n诊断信息:")
    print_log(f"1. API URL配置: {api_url}")
    print_log(f"2. 尝试的配置:")
    for config in test_configs:
        print_log(f"   - {config['name']}: {config['url']}")
    print_log("3. 请检查:")
    print_log("   - Immich服务是否正在运行 (检查 http://127.0.0.1:2283)")
    print_log("   - Immich版本和API路径是否正确")
    print_log("   - 可能需要查看Immich的OpenAPI文档确认正确的端点")
    print_log("   - 尝试访问: http://127.0.0.1:2283/api/doc 查看API文档")

if __name__ == "__main__":
    asyncio.run(test_upload_direct())

