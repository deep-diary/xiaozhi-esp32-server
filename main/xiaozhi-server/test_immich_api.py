"""
Immich API 测试脚本

用于测试 immich_api.py 的功能，验证与 Immich 服务器的连接和 API 调用。
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config_loader import load_config
from core.utils.immich_api import ImmichAPI
from core.utils.immich_logic import ImmichLogic
from immich_python_sdk.models.asset_media_size import AssetMediaSize
from immich_python_sdk.models.asset_visibility import AssetVisibility


async def test_get_asset(asset_id: str):
    """
    测试获取资产信息
    
    Args:
        asset_id: 要测试的资产ID
    """
    print("=" * 80)
    print("Immich API 测试脚本")
    print("=" * 80)
    print()
    
    # 1. 加载配置
    print("步骤 1: 加载配置文件...")
    try:
        config = load_config()
        print(f"✓ 配置文件加载成功")
    except Exception as e:
        print(f"✗ 配置文件加载失败: {e}")
        return
    
    # 2. 获取 Immich 配置
    print("\n步骤 2: 获取 Immich 配置...")
    immich_config = config.get("Immich", {})
    if not immich_config:
        print("✗ 未找到 Immich 配置，请检查配置文件")
        return
    
    api_url = immich_config.get("api_url", "")
    api_key = immich_config.get("api_key", "")
    
    print(f"  API URL: {api_url}")
    print(f"  API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key else '未配置'}")
    
    if not api_url or not api_key:
        print("✗ Immich 配置不完整，请检查配置文件")
        return
    
    print("✓ Immich 配置获取成功")
    
    # 3. 创建 ImmichAPI 实例
    print("\n步骤 3: 初始化 ImmichAPI 客户端...")
    try:
        immich_api = ImmichAPI(immich_config)
        if not immich_api.enabled:
            print("✗ ImmichAPI 客户端未启用，请检查配置")
            return
        print("✓ ImmichAPI 客户端初始化成功")
    except Exception as e:
        print(f"✗ ImmichAPI 客户端初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. 测试获取资产信息
    print(f"\n步骤 4: 获取资产信息 (asset_id: {asset_id})...")
    try:
        asset = await immich_api.get_asset(asset_id)
        
        if asset:
            print("✓ 成功获取资产信息")
            print("\n" + "=" * 80)
            print("资产信息详情:")
            print("=" * 80)
            
            # 格式化输出资产信息
            print(f"\n基本信息:")
            print(f"  ID: {asset.get('id', 'N/A')}")
            print(f"  设备资产ID: {asset.get('deviceAssetId', 'N/A')}")
            print(f"  设备ID: {asset.get('deviceId', 'N/A')}")
            print(f"  原始文件名: {asset.get('originalFileName', 'N/A')}")
            print(f"  原始路径: {asset.get('originalPath', 'N/A')}")
            print(f"  类型: {asset.get('type', 'N/A')}")
            print(f"  可见性: {asset.get('visibility', 'N/A')}")
            
            print(f"\n状态信息:")
            print(f"  是否收藏: {asset.get('isFavorite', False)}")
            print(f"  是否归档: {asset.get('isArchived', False)}")
            print(f"  是否已删除: {asset.get('isTrashed', False)}")
            print(f"  是否离线: {asset.get('isOffline', False)}")
            
            print(f"\n时间信息:")
            print(f"  文件创建时间: {asset.get('fileCreatedAt', 'N/A')}")
            print(f"  文件修改时间: {asset.get('fileModifiedAt', 'N/A')}")
            print(f"  本地日期时间: {asset.get('localDateTime', 'N/A')}")
            print(f"  更新时间: {asset.get('updatedAt', 'N/A')}")
            
            # 人物信息
            people = asset.get('people', [])
            if people:
                print(f"\n人物信息 (共 {len(people)} 个):")
                for i, person in enumerate(people, 1):
                    person_name = person.get('name', '未命名') if isinstance(person, dict) else getattr(person, 'name', '未命名')
                    person_id = person.get('id', 'N/A') if isinstance(person, dict) else getattr(person, 'id', 'N/A')
                    print(f"  {i}. {person_name} (ID: {person_id})")
            else:
                print(f"\n人物信息: 未检测到人物")
            
            # EXIF 信息
            exif_info = asset.get('exifInfo')
            if exif_info:
                print(f"\nEXIF 信息:")
                if isinstance(exif_info, dict):
                    print(f"  相机: {exif_info.get('make', 'N/A')} {exif_info.get('model', 'N/A')}")
                    print(f"  拍摄时间: {exif_info.get('dateTimeOriginal', 'N/A')}")
                    print(f"  尺寸: {exif_info.get('exifImageWidth', 'N/A')} x {exif_info.get('exifImageHeight', 'N/A')}")
                else:
                    print(f"  {exif_info}")
            
            # 标签信息
            tags = asset.get('tags', [])
            if tags:
                print(f"\n标签信息 (共 {len(tags)} 个):")
                tag_names = []
                for tag in tags:
                    if isinstance(tag, dict):
                        tag_names.append(tag.get('name', 'N/A'))
                    else:
                        tag_names.append(getattr(tag, 'name', 'N/A'))
                print(f"  {', '.join(tag_names)}")
            
            print("\n" + "=" * 80)
            print("完整 JSON 数据:")
            print("=" * 80)
            print(json.dumps(asset, indent=2, ensure_ascii=False, default=str))
            
        else:
            print("✗ 获取资产信息失败，返回 None")
            print("  可能的原因:")
            print("  - 资产ID不存在")
            print("  - API 认证失败")
            print("  - 网络连接问题")
            print("  - 服务器错误")
            
    except Exception as e:
        print(f"✗ 获取资产信息时发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


async def test_search_smart():
    """
    测试智能搜索功能
    """
    print("=" * 80)
    print("Immich API 智能搜索测试")
    print("=" * 80)
    print()
    
    # 1. 加载配置
    print("步骤 1: 加载配置文件...")
    try:
        config = load_config()
        print(f"✓ 配置文件加载成功")
    except Exception as e:
        print(f"✗ 配置文件加载失败: {e}")
        return
    
    # 2. 获取 Immich 配置
    print("\n步骤 2: 获取 Immich 配置...")
    immich_config = config.get("Immich", {})
    if not immich_config:
        print("✗ 未找到 Immich 配置，请检查配置文件")
        return
    
    api_url = immich_config.get("api_url", "")
    api_key = immich_config.get("api_key", "")
    
    print(f"  API URL: {api_url}")
    print(f"  API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key else '未配置'}")
    
    if not api_url or not api_key:
        print("✗ Immich 配置不完整，请检查配置文件")
        return
    
    print("✓ Immich 配置获取成功")
    
    # 3. 创建 ImmichAPI 实例
    print("\n步骤 3: 初始化 ImmichAPI 客户端...")
    try:
        immich_api = ImmichAPI(immich_config)
        if not immich_api.enabled:
            print("✗ ImmichAPI 客户端未启用，请检查配置")
            return
        print("✓ ImmichAPI 客户端初始化成功")
    except Exception as e:
        print(f"✗ ImmichAPI 客户端初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. 准备搜索参数
    print("\n步骤 4: 准备搜索参数...")
    from immich_python_sdk.models.asset_visibility import AssetVisibility
    
    search_params = {
        "query": "travel by bike",
        "page": 1,
        "size": 5,
        "with_exif": True,
        "language": "zh-CN",
        "person_ids": ["8e4f5acf-aaf2-408b-b0b1-16ebfcc8ce96"],
        "taken_after": datetime.fromisoformat("2012-01-18T00:00:00.000Z".replace('Z', '+00:00')),
        "taken_before": datetime.fromisoformat("2025-12-17T23:59:59.999Z".replace('Z', '+00:00')),
        "visibility": AssetVisibility.TIMELINE,  # 将 isVisible: true 映射为 visibility: TIMELINE（可见的资产）
        "city": "Dawsonville"
    }
    
    print("搜索参数:")
    print(f"  查询字符串: {search_params['query']}")
    print(f"  页码: {search_params['page']}")
    print(f"  包含EXIF: {search_params['with_exif']}")
    print(f"  语言: {search_params['language']}")
    print(f"  人物ID: {search_params['person_ids']}")
    print(f"  拍摄时间范围: {search_params['taken_after']} 到 {search_params['taken_before']}")
    print("✓ 搜索参数准备完成")
    
    # 5. 执行智能搜索
    print(f"\n步骤 5: 执行智能搜索...")
    try:
        results = await immich_api.search_smart(**search_params)
        
        if results:
            print("✓ 搜索成功")
            print("\n" + "=" * 80)
            print("搜索结果详情:")
            print("=" * 80)
            
            # 处理资产结果
            assets_data = results.get('assets', {})
            if assets_data:
                assets_items = assets_data.get('items', [])
                assets_total = assets_data.get('total', 0)
                assets_page = assets_data.get('page', 0)
                assets_size = assets_data.get('pages', 0)
                
                print(f"\n资产搜索结果:")
                print(f"  总数: {assets_total}")
                print(f"  当前页: {assets_page}")
                print(f"  每页数量: {len(assets_items)}")
                print(f"  总页数: {assets_size}")
                
                if assets_items:
                    print(f"\n  找到 {len(assets_items)} 个资产:")
                    for i, asset in enumerate(assets_items[:10], 1):  # 只显示前10个
                        asset_id = asset.get('id', 'N/A')
                        asset_name = asset.get('originalFileName', 'N/A')
                        asset_type = asset.get('type', 'N/A')
                        is_favorite = asset.get('isFavorite', False)
                        print(f"    {i}. [{asset_type}] {asset_name} (ID: {asset_id[:8]}...) {'⭐' if is_favorite else ''}")
                    
                    if len(assets_items) > 10:
                        print(f"    ... 还有 {len(assets_items) - 10} 个资产未显示")
                else:
                    print("  未找到匹配的资产")
            else:
                print("\n资产搜索结果: 无")
            
            # 处理相册结果
            albums_data = results.get('albums', {})
            if albums_data:
                albums_items = albums_data.get('items', [])
                albums_total = albums_data.get('total', 0)
                
                print(f"\n相册搜索结果:")
                print(f"  总数: {albums_total}")
                
                if albums_items:
                    print(f"\n  找到 {len(albums_items)} 个相册:")
                    for i, album in enumerate(albums_items[:10], 1):  # 只显示前10个
                        album_id = album.get('id', 'N/A')
                        album_name = album.get('albumName', 'N/A')
                        album_count = album.get('assetCount', 0)
                        print(f"    {i}. {album_name} ({album_count} 张) (ID: {album_id[:8]}...)")
                    
                    if len(albums_items) > 10:
                        print(f"    ... 还有 {len(albums_items) - 10} 个相册未显示")
                else:
                    print("  未找到匹配的相册")
            else:
                print("\n相册搜索结果: 无")
            
            print("\n" + "=" * 80)
            print("完整 JSON 数据:")
            print("=" * 80)
            print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
            
        else:
            print("✗ 搜索失败，返回 None")
            print("  可能的原因:")
            print("  - 没有匹配的结果")
            print("  - API 认证失败")
            print("  - 网络连接问题")
            print("  - 服务器错误")
            
    except Exception as e:
        print(f"✗ 执行搜索时发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


async def _init_immich_api():
    """
    初始化 ImmichAPI 客户端的辅助函数
    
    Returns:
        ImmichAPI 实例，如果初始化失败返回 None
    """
    # 1. 加载配置
    print("步骤 1: 加载配置文件...")
    try:
        config = load_config()
        print(f"✓ 配置文件加载成功")
    except Exception as e:
        print(f"✗ 配置文件加载失败: {e}")
        return None
    
    # 2. 获取 Immich 配置
    print("\n步骤 2: 获取 Immich 配置...")
    immich_config = config.get("Immich", {})
    if not immich_config:
        print("✗ 未找到 Immich 配置，请检查配置文件")
        return None
    
    api_url = immich_config.get("api_url", "")
    api_key = immich_config.get("api_key", "")
    
    print(f"  API URL: {api_url}")
    print(f"  API Key: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key else '未配置'}")
    
    if not api_url or not api_key:
        print("✗ Immich 配置不完整，请检查配置文件")
        return None
    
    print("✓ Immich 配置获取成功")
    
    # 3. 创建 ImmichAPI 实例
    print("\n步骤 3: 初始化 ImmichAPI 客户端...")
    try:
        immich_api = ImmichAPI(immich_config)
        if not immich_api.enabled:
            print("✗ ImmichAPI 客户端未启用，请检查配置")
            return None
        print("✓ ImmichAPI 客户端初始化成功")
        return immich_api
    except Exception as e:
        print(f"✗ ImmichAPI 客户端初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_download_asset(asset_id: str):
    """
    测试下载资产原始文件（未经处理的原始文件）
    
    注意：此方法返回的是服务器上存储的完全原始文件，与用户上传时完全一致。
    与 view_asset(size=FULLSIZE) 的区别：
    - download_asset: 返回原始文件，格式、大小、元数据完全不变
    - view_asset(size=FULLSIZE): 返回完整大小的图片，但可能经过格式转换或优化处理
    
    Args:
        asset_id: 要测试的资产ID
    """
    print("=" * 80)
    print("Immich API 下载原始文件测试")
    print("=" * 80)
    print()
    print("注意：此测试下载的是完全原始的文件（未经任何处理）")
    print()
    
    # 初始化 API 客户端
    immich_api = await _init_immich_api()
    if not immich_api:
        return
    
    # 测试下载原始文件
    print(f"\n步骤 4: 下载资产原始文件 (asset_id: {asset_id})...")
    try:
        asset_data = await immich_api.download_asset(asset_id)
        
        if asset_data:
            print("✓ 成功下载资产原始文件")
            print(f"\n文件信息:")
            print(f"  大小: {len(asset_data):,} 字节 ({len(asset_data) / 1024 / 1024:.2f} MB)")
            
            # 尝试保存文件（可选）
            save_dir = project_root / "tmp"
            save_dir.mkdir(exist_ok=True)
            
            # 先获取资产信息以确定文件扩展名
            asset_info = await immich_api.get_asset(asset_id)
            if asset_info:
                original_filename = asset_info.get('originalFileName', 'unknown')
                file_extension = Path(original_filename).suffix or '.bin'
            else:
                file_extension = '.bin'
            
            save_path = save_dir / f"{asset_id}_original{file_extension}"
            
            print(f"\n保存文件到: {save_path}")
            with open(save_path, 'wb') as f:
                f.write(asset_data)
            print(f"✓ 文件已保存")
            
            print("\n" + "=" * 80)
            print("下载测试完成")
            print("=" * 80)
        else:
            print("✗ 下载资产原始文件失败，返回 None")
            print("  可能的原因:")
            print("  - 资产ID不存在")
            print("  - API 认证失败")
            print("  - 网络连接问题")
            print("  - 服务器错误")
            
    except Exception as e:
        print(f"✗ 下载资产原始文件时发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


async def test_view_asset(asset_id: str):
    """
    测试下载资产缩略图/预览图（经过处理的图片）
    
    注意：此方法返回的图片可能经过格式转换或优化处理。
    与 download_asset 的区别：
    - download_asset: 返回原始文件，格式、大小、元数据完全不变
    - view_asset(size=FULLSIZE): 返回完整大小的图片，但可能经过格式转换或优化处理
    
    Args:
        asset_id: 要测试的资产ID
    """
    print("=" * 80)
    print("Immich API 下载缩略图/预览图测试")
    print("=" * 80)
    print()
    print("注意：此测试下载的是经过处理的图片（可能经过格式转换或优化）")
    print()
    
    # 初始化 API 客户端
    immich_api = await _init_immich_api()
    if not immich_api:
        return
    
    # 测试下载不同尺寸的缩略图
    sizes_to_test = [
        (AssetMediaSize.THUMBNAIL, "缩略图"),
        (AssetMediaSize.PREVIEW, "预览图"),
        (AssetMediaSize.FULLSIZE, "完整大小"),
        (None, "默认尺寸")
    ]
    
    save_dir = project_root / "tmp"
    save_dir.mkdir(exist_ok=True)
    
    # 先获取资产信息以确定文件扩展名
    print(f"\n步骤 4: 获取资产信息以确定文件类型...")
    asset_info = await immich_api.get_asset(asset_id)
    if asset_info:
        original_filename = asset_info.get('originalFileName', 'unknown')
        file_extension = Path(original_filename).suffix or '.jpg'
        print(f"✓ 文件类型: {file_extension}")
    else:
        file_extension = '.jpg'
        print(f"⚠ 无法获取资产信息，使用默认扩展名: {file_extension}")
    
    print(f"\n步骤 5: 测试下载不同尺寸的图片...")
    
    for size, size_name in sizes_to_test:
        print(f"\n--- 测试下载 {size_name} ---")
        try:
            # 使用 view_asset_with_info 获取响应信息（包括 Content-Type）
            from core.utils.immich_api import _detect_image_format
            
            response_info = await immich_api.view_asset_with_info(asset_id, size=size)
            
            if response_info and response_info.get('data'):
                image_data = response_info['data']
                content_type = response_info.get('content_type', '')
                
                # 根据 Content-Type 或文件内容检测文件格式
                detected_extension = _detect_image_format(image_data, content_type)
                
                print(f"✓ 成功下载 {size_name}")
                print(f"  大小: {len(image_data):,} 字节 ({len(image_data) / 1024:.2f} KB)")
                print(f"  Content-Type: {content_type or '未提供'}")
                print(f"  检测到的格式: {detected_extension}")
                
                # 保存文件（使用检测到的格式）
                size_suffix = size.value if size else "default"
                save_path = save_dir / f"{asset_id}_{size_suffix}{detected_extension}"
                
                print(f"  保存到: {save_path}")
                with open(save_path, 'wb') as f:
                    f.write(image_data)
                print(f"  ✓ 文件已保存")
            else:
                print(f"✗ 下载 {size_name} 失败，返回 None")
                
        except Exception as e:
            print(f"✗ 下载 {size_name} 时发生异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


async def test_upload_asset(file_path: str):
    """
    测试上传资产（图片或视频）到 Immich 服务器
    
    Args:
        file_path: 要上传的文件路径
    """
    print("=" * 80)
    print("Immich API 上传资产测试")
    print("=" * 80)
    print()
    
    # 检查文件是否存在
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        print(f"✗ 文件不存在: {file_path}")
        return
    
    print(f"要上传的文件: {file_path}")
    print(f"文件大小: {file_path_obj.stat().st_size:,} 字节 ({file_path_obj.stat().st_size / 1024 / 1024:.2f} MB)")
    print()
    
    # 初始化 API 客户端
    immich_api = await _init_immich_api()
    if not immich_api:
        return
    
    # 准备上传参数
    print(f"\n步骤 4: 准备上传参数...")
    from datetime import datetime
    
    upload_params = {
        "is_favorite": False,
        "visibility": AssetVisibility.TIMELINE,  # 设置为可见
    }
    
    print("上传参数:")
    print(f"  文件路径: {file_path}")
    print(f"  是否收藏: {upload_params['is_favorite']}")
    print(f"  可见性: {upload_params['visibility'].value}")
    print("✓ 上传参数准备完成")
    
    # 执行上传
    print(f"\n步骤 5: 开始上传文件...")
    try:
        upload_result = await immich_api.upload_asset(file_path, **upload_params)
        
        if upload_result:
            print("✓ 上传成功")
            print("\n" + "=" * 80)
            print("上传结果详情:")
            print("=" * 80)
            
            asset_id = upload_result.get('id', 'N/A')
            duplicate = upload_result.get('duplicate', False)
            status = upload_result.get('status', 'N/A')
            
            print(f"\n基本信息:")
            print(f"  资产ID: {asset_id}")
            print(f"  是否重复: {duplicate}")
            print(f"  状态: {status}")
            
            if duplicate:
                print("\n⚠ 注意: 这是一个重复的文件，Immich 检测到已存在相同的文件")
            
            # 显示完整的返回数据
            print("\n" + "=" * 80)
            print("完整 JSON 数据:")
            print("=" * 80)
            print(json.dumps(upload_result, indent=2, ensure_ascii=False, default=str))
            
            # 如果上传成功，可以尝试获取资产信息验证
            if asset_id != 'N/A' and not duplicate:
                print("\n" + "=" * 80)
                print("验证上传结果: 获取资产信息...")
                print("=" * 80)
                await asyncio.sleep(2)  # 等待服务器处理
                asset_info = await immich_api.get_asset(asset_id)
                if asset_info:
                    print("✓ 成功获取资产信息，上传验证成功")
                    print(f"  文件名: {asset_info.get('originalFileName', 'N/A')}")
                    print(f"  类型: {asset_info.get('type', 'N/A')}")
                    print(f"  可见性: {asset_info.get('visibility', 'N/A')}")
                else:
                    print("⚠ 无法立即获取资产信息，可能需要等待服务器处理")
            
            print("\n" + "=" * 80)
            print("上传测试完成")
            print("=" * 80)
        else:
            print("✗ 上传失败，返回 None")
            print("  可能的原因:")
            print("  - API 认证失败")
            print("  - 网络连接问题")
            print("  - 服务器错误")
            print("  - 文件格式不支持")
            
    except Exception as e:
        print(f"✗ 上传文件时发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


async def test_search_and_download_thumbnails():
    """
    测试搜索资产并下载缩略图业务逻辑
    """
    print("=" * 80)
    print("Immich 业务逻辑测试: 搜索并下载缩略图")
    print("=" * 80)
    print()
    
    # 初始化 API 客户端
    immich_api = await _init_immich_api()
    if not immich_api:
        return
    
    # 创建业务逻辑处理器
    print("\n步骤 4: 初始化业务逻辑处理器...")
    immich_logic = ImmichLogic(immich_api)
    print("✓ 业务逻辑处理器初始化成功")
    
    # 准备搜索和下载参数
    print("\n步骤 5: 准备搜索和下载参数...")
    save_dir = project_root / "tmp" / "thumbnails"
    search_query = "travel by bike"
    
    print("搜索参数:")
    print(f"  查询字符串: {search_query}")
    print(f"  保存目录: {save_dir}")
    print(f"  缩略图尺寸: {AssetMediaSize.THUMBNAIL.value}")
    print(f"  最大下载数量: 10")
    print("✓ 参数准备完成")
    
    # 执行搜索和下载
    print(f"\n步骤 6: 执行搜索并下载缩略图...")
    try:
        result = await immich_logic.search_and_download_thumbnails(
            query=search_query,
            save_dir=save_dir,
            thumbnail_size=AssetMediaSize.THUMBNAIL,
            max_count=10,
            page=1,
            size=10
        )
        
        print("\n" + "=" * 80)
        print("执行结果:")
        print("=" * 80)
        
        print(f"\n统计信息:")
        print(f"  是否成功: {result.get('success', False)}")
        print(f"  找到资产总数: {result.get('total_found', 0)}")
        print(f"  成功下载: {result.get('downloaded', 0)}")
        print(f"  下载失败: {result.get('failed', 0)}")
        
        saved_files = result.get('saved_files', [])
        if saved_files:
            print(f"\n已保存的文件 ({len(saved_files)} 个):")
            for i, file_path in enumerate(saved_files[:10], 1):  # 只显示前10个
                file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                print(f"  {i}. {Path(file_path).name} ({file_size:,} 字节)")
            if len(saved_files) > 10:
                print(f"  ... 还有 {len(saved_files) - 10} 个文件未显示")
        
        errors = result.get('errors', [])
        if errors:
            print(f"\n错误信息 ({len(errors)} 个):")
            for i, error in enumerate(errors[:5], 1):  # 只显示前5个错误
                print(f"  {i}. {error}")
            if len(errors) > 5:
                print(f"  ... 还有 {len(errors) - 5} 个错误未显示")
        
        print("\n" + "=" * 80)
        print("完整结果数据:")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        
    except Exception as e:
        print(f"✗ 执行搜索和下载时发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


async def test_search_person(person_name: str):
    """
    测试根据人名搜索人物信息并获取person_id
    
    Args:
        person_name: 要搜索的人物名称
    """
    print("=" * 80)
    print("Immich API 搜索人物测试")
    print("=" * 80)
    print()
    
    # 初始化 API 客户端
    immich_api = await _init_immich_api()
    if not immich_api:
        return
    
    # 测试API层的search_person方法
    print(f"\n步骤 4: 搜索人物信息 (person_name: '{person_name}')...")
    try:
        persons = await immich_api.search_person(name=person_name)
        
        if persons:
            print("✓ 成功搜索到人物信息")
            print("\n" + "=" * 80)
            print("人物信息详情:")
            print("=" * 80)
            
            print(f"\n找到 {len(persons)} 个人物:")
            for i, person in enumerate(persons, 1):
                person_id = person.get('id', 'N/A')
                person_name_found = person.get('name', 'N/A')
                is_hidden = person.get('isHidden', False)
                thumbnail_path = person.get('thumbnailPath', 'N/A')
                
                print(f"\n  {i}. {person_name_found}")
                print(f"     ID: {person_id}")
                print(f"     是否隐藏: {is_hidden}")
                print(f"     缩略图路径: {thumbnail_path}")
            
            # 提取所有人物ID
            person_ids = [p.get('id') for p in persons if p.get('id')]
            print(f"\n人物ID列表: {person_ids}")
            
            print("\n" + "=" * 80)
            print("完整 JSON 数据:")
            print("=" * 80)
            print(json.dumps(persons, indent=2, ensure_ascii=False, default=str))
            
        else:
            print("✗ 搜索人物失败，返回 None")
            print("  可能的原因:")
            print("  - 人物名称不存在")
            print("  - API 认证失败")
            print("  - 网络连接问题")
            print("  - 服务器错误")
            
    except Exception as e:
        print(f"✗ 搜索人物时发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试逻辑层的search_person_by_name方法
    print("\n" + "=" * 80)
    print("测试业务逻辑层: 根据人名获取person_id列表")
    print("=" * 80)
    print()
    
    # 创建业务逻辑处理器
    print("\n步骤 5: 初始化业务逻辑处理器...")
    immich_logic = ImmichLogic(immich_api)
    print("✓ 业务逻辑处理器初始化成功")
    
    print(f"\n步骤 6: 通过业务逻辑层搜索人物ID (person_name: '{person_name}')...")
    try:
        person_ids = await immich_logic.search_person_by_name(person_name, timeout=5.0)
        
        if person_ids:
            print("✓ 成功获取人物ID列表")
            print(f"\n人物ID列表: {person_ids}")
            print(f"  数量: {len(person_ids)}")
        else:
            print("✗ 获取人物ID失败，返回 None")
            print("  可能的原因:")
            print("  - 人物名称不存在")
            print("  - 搜索超时")
            print("  - API调用失败")
            
    except Exception as e:
        print(f"✗ 获取人物ID时发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


async def main():
    """主函数"""
    # 默认测试的资产ID
    default_asset_id = "714f6b35-9f62-44f7-bc83-b8f29baf1296"
    
    # 检查命令行参数决定运行哪个测试
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "search" or test_type == "smart":
            # 运行智能搜索测试
            await test_search_smart()
        elif test_type == "download" or test_type == "original":
            # 运行下载原始文件测试
            asset_id = sys.argv[2] if len(sys.argv) > 2 else default_asset_id
            print(f"使用资产ID: {asset_id}")
            await test_download_asset(asset_id)
        elif test_type == "view" or test_type == "thumbnail":
            # 运行下载缩略图测试
            asset_id = sys.argv[2] if len(sys.argv) > 2 else default_asset_id
            print(f"使用资产ID: {asset_id}")
            await test_view_asset(asset_id)
        elif test_type == "upload":
            # 运行上传测试
            file_path = sys.argv[2] if len(sys.argv) > 2 else str(project_root / "tmp" / "demo.png")
            print(f"使用文件路径: {file_path}")
            await test_upload_asset(file_path)
        elif test_type == "logic" or test_type == "search_download":
            # 运行业务逻辑测试（搜索并下载缩略图）
            await test_search_and_download_thumbnails()
        elif test_type == "person" or test_type == "search_person":
            # 运行搜索人物测试
            person_name = sys.argv[2] if len(sys.argv) > 2 else "Jason"
            print(f"使用人物名称: {person_name}")
            await test_search_person(person_name)
        elif test_type == "all":
            # 运行所有下载相关测试
            asset_id = sys.argv[2] if len(sys.argv) > 2 else default_asset_id
            print(f"使用资产ID: {asset_id}")
            print("\n" + "=" * 80)
            print("运行所有下载测试")
            print("=" * 80)
            await test_download_asset(asset_id)
            print("\n\n")
            await test_view_asset(asset_id)
        else:
            # 运行获取资产测试（使用第一个参数作为资产ID）
            asset_id = sys.argv[1]
            print(f"使用命令行参数提供的资产ID: {asset_id}")
            await test_get_asset(asset_id)
    else:
        # 默认运行下载缩略图测试
        print(f"使用默认资产ID: {default_asset_id}")
        await test_view_asset(default_asset_id)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())

