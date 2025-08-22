#!/usr/bin/env python3
"""
Icon Converter Tool - OpsKit Version
Automatically convert single icon files to multiple sizes and formats for different development platforms
"""

import os
import sys
import glob
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import concurrent.futures
from datetime import datetime

# Basic interactive helpers (replacing removed interactive/get_input utilities)
def get_input(prompt: str, validator=None, required: bool = True) -> str:
    """Prompt user for input with optional validator.
    - validator: callable that returns True/False for validity
    - required: if True, reprompt until non-empty
    Returns the raw input string.
    """
    while True:
        try:
            val = input(f"{prompt}").strip()
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            return ""
        if not val and required:
            print("❌ 输入不能为空，请重试")
            continue
        if validator and val:
            try:
                if not validator(val):
                    print("❌ 输入无效，请重试")
                    continue
            except Exception:
                print("❌ 校验失败，请重试")
                continue
        return val

def confirm(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        ans = input(f"{prompt} {suffix} ").strip().lower()
    except KeyboardInterrupt:
        print("\n👋 用户取消操作")
        return False
    if ans == "":
        return default
    return ans in ("y", "yes")

def select_from_list(options: List[str], prompt: str) -> Optional[int]:
    """Display numbered options and return selected index (0-based)."""
    if not options:
        print("❌ 没有可选项")
        return None
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    while True:
        try:
            choice = input(f"{prompt} ").strip()
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            return None
        if not choice:
            return None
        if not choice.isdigit():
            print("❌ 请输入有效数字")
            continue
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return idx
        print("❌ 选择超出范围")

def select_multiple_from_list(options: List[str], prompt: str) -> List[int]:
    """Allow user to select multiple indices. Supports formats: '1', '1,3,5', '2-6', 'all'."""
    if not options:
        return []
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    selected = set()
    print("提示: 输入编号切换选择，范围如 2-5，多个如 1,3,5，输入 all 全选，done 完成")
    while True:
        try:
            choice = input(f"{prompt} ").strip().lower()
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            return sorted(selected)
        if not choice:
            return sorted(selected)
        if choice == 'done':
            return sorted(selected)
        if choice == 'all':
            return list(range(len(options)))
        if '-' in choice:
            try:
                start, end = map(int, choice.split('-'))
                selected.update(range(start - 1, end))
                continue
            except Exception:
                print("❌ 范围格式无效")
                continue
        if ',' in choice:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(',')]
            except Exception:
                print("❌ 多选格式无效")
                continue
            for idx in indices:
                if 0 <= idx < len(options):
                    selected.symmetric_difference_update({idx})
            continue
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                selected.symmetric_difference_update({idx})
                continue
        print("❌ 输入无效，请重试")

# 获取 OpsKit 环境变量
OPSKIT_TOOL_TEMP_DIR = os.environ.get('OPSKIT_TOOL_TEMP_DIR', os.path.join(os.getcwd(), '.icon-converter-temp'))
OPSKIT_BASE_PATH = os.environ.get('OPSKIT_BASE_PATH', os.path.expanduser('~/.opskit'))
OPSKIT_WORKING_DIR = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
TOOL_NAME = os.environ.get('TOOL_NAME', 'icon-converter')
TOOL_VERSION = os.environ.get('TOOL_VERSION', '1.0.0')

# 创建临时目录
os.makedirs(OPSKIT_TOOL_TEMP_DIR, exist_ok=True)

# Import OpsKit utils
sys.path.insert(0, os.path.join(OPSKIT_BASE_PATH, 'common/python'))
from utils import get_env_var

# Third-party imports
try:
    from PIL import Image, ImageEnhance
except ImportError as e:
    print(f"❌ 缺少必需依赖: {e}")
    print("请确保所有依赖都已安装")
    sys.exit(1)

# Platform configurations
PLATFORM_CONFIGS = {
    'web': {
        'name': 'Web Development',
        'description': 'Favicon, PWA icons',
        'files': [
            {'size': 16, 'name': 'favicon-16x16.png'},
            {'size': 32, 'name': 'favicon-32x32.png'},
            {'size': 48, 'name': 'favicon-48x48.png'},
            {'size': 96, 'name': 'favicon-96x96.png'},
            {'size': 192, 'name': 'android-chrome-192x192.png'},
            {'size': 512, 'name': 'android-chrome-512x512.png'},
            {'size': 32, 'name': 'favicon.ico', 'format': 'ico'}
        ]
    },
    'ios': {
        'name': 'iOS App Development',
        'description': 'iPhone, iPad app icons',
        'files': [
            {'size': 20, 'name': 'icon-20@1x.png'},
            {'size': 40, 'name': 'icon-20@2x.png'},
            {'size': 60, 'name': 'icon-20@3x.png'},
            {'size': 29, 'name': 'icon-29@1x.png'},
            {'size': 58, 'name': 'icon-29@2x.png'},
            {'size': 87, 'name': 'icon-29@3x.png'},
            {'size': 40, 'name': 'icon-40@1x.png'},
            {'size': 80, 'name': 'icon-40@2x.png'},
            {'size': 120, 'name': 'icon-60@2x.png'},
            {'size': 180, 'name': 'icon-60@3x.png'},
            {'size': 76, 'name': 'icon-76@1x.png'},
            {'size': 152, 'name': 'icon-76@2x.png'},
            {'size': 167, 'name': 'icon-83.5@2x.png'},
            {'size': 1024, 'name': 'icon-1024@1x.png'}
        ]
    },
    'android': {
        'name': 'Android App Development',
        'description': 'Android app icons',
        'files': [
            {'size': 36, 'name': 'ic_launcher_36.png', 'density': 'ldpi'},
            {'size': 48, 'name': 'ic_launcher_48.png', 'density': 'mdpi'},
            {'size': 72, 'name': 'ic_launcher_72.png', 'density': 'hdpi'},
            {'size': 96, 'name': 'ic_launcher_96.png', 'density': 'xhdpi'},
            {'size': 144, 'name': 'ic_launcher_144.png', 'density': 'xxhdpi'},
            {'size': 192, 'name': 'ic_launcher_192.png', 'density': 'xxxhdpi'}
        ]
    },
    'chrome-ext': {
        'name': 'Chrome Extension',
        'description': 'Browser extension icons',
        'files': [
            {'size': 16, 'name': 'icon16.png'},
            {'size': 19, 'name': 'icon19.png'},
            {'size': 32, 'name': 'icon32.png'},
            {'size': 38, 'name': 'icon38.png'},
            {'size': 48, 'name': 'icon48.png'},
            {'size': 128, 'name': 'icon128.png'}
        ]
    }
}


class IconConverter:
    """Icon converter with OpsKit integration"""
    
    def __init__(self):
        self.tool_name = "Icon Converter"
        self.description = "Convert icons to multiple sizes for different platforms"
        
        # Load configuration from environment variables
        output_dir = get_env_var('OUTPUT_DIR', './generated-icons')
        
        # Handle relative paths by joining with OPSKIT_WORKING_DIR
        if not os.path.isabs(output_dir):
            working_dir = get_env_var('OPSKIT_WORKING_DIR', os.getcwd())
            self.output_dir = os.path.normpath(os.path.join(working_dir, output_dir))
        else:
            self.output_dir = output_dir
            
        self.quality = get_env_var('QUALITY', 'high')
        self.background_color = get_env_var('BACKGROUND_COLOR', 'white')
        self.threads = get_env_var('THREADS', 4, int)
        self.keep_aspect_ratio = get_env_var('KEEP_ASPECT_RATIO', True, bool)
        
        print(f"🚀 启动 {self.tool_name}")
        print(f"⚙️  配置 - 输出目录: {self.output_dir}, 质量: {self.quality}")
    
    def validate_image_file(self, file_path: str) -> bool:
        """Validate image file"""
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return False
        
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                print(f"✅ 已加载: {os.path.basename(file_path)} ({width}x{height})")
                return True
        except Exception as e:
            print(f"❌ 无法打开图像文件: {e}")
            return False
    
    def get_input_file(self) -> Optional[str]:
        """Get input file from user"""
        print("📁 选择图标文件:")
        print("1. 直接输入文件路径（可拖拽至终端）")
        print("2. 从当前目录选择")
        
        choice = get_input("Choose method (1-2): ", 
                          validator=lambda x: x in ['1', '2'])
        
        if choice == '1':
            return self._input_file_path()
        else:
            return self._select_from_directory()
    
    def _input_file_path(self) -> Optional[str]:
        """Direct file path input"""
        print("💡 提示: 可以将文件拖拽到终端")
        while True:
            file_path = get_input("输入文件路径")
            file_path = file_path.strip().strip('"\'')
            
            if self.validate_image_file(file_path):
                return file_path
            else:
                print("❌ 无效的图片文件")
                if not confirm("重试吗?"):
                    return None
    
    def _select_from_directory(self) -> Optional[str]:
        """Select file from current directory"""
        # Use OPSKIT_WORKING_DIR instead of current working directory
        current_dir = get_env_var('OPSKIT_WORKING_DIR', os.getcwd())
        image_files = []
        
        extensions = ['.png', '.jpg', '.jpeg', '.svg', '.ico', '.bmp', '.tiff']
        for ext in extensions:
            pattern = os.path.join(current_dir, f"*{ext}")
            image_files.extend(glob.glob(pattern))
            pattern_upper = os.path.join(current_dir, f"*{ext.upper()}")
            image_files.extend(glob.glob(pattern_upper))
        
        if not image_files:
            print("❌ 当前目录未找到图片文件")
            return None
        
        # Show file details
        print(f"可用图片文件: {current_dir}:")
        file_details = []
        display_names = []
        
        for file_path in image_files:
            file_name = os.path.basename(file_path)
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    file_details.append((file_path, f"{width}x{height}"))
                    display_names.append(f"{file_name} ({width}x{height})")
            except:
                file_details.append((file_path, "Unknown"))
                display_names.append(f"{file_name} (Unknown size)")
        
        # Log the files for user information
        for i, display_name in enumerate(display_names, 1):
            print(f"{i}. {display_name}")
        
        selected_idx = select_from_list(display_names, "Select image file:")
        if selected_idx is not None:
            selected_file_path = image_files[selected_idx]
            return selected_file_path
        return None
    
    
    def select_platforms(self) -> List[str]:
        """Select target platforms"""
        print("🎯 选择目标平台:")
        
        platform_choices = []
        for key, config in PLATFORM_CONFIGS.items():
            icon_count = len(config['files'])
            platform_choices.append(f"{config['name']} ({icon_count} icons)")
        
        platform_choices.append("Custom sizes")
        
        selected_indices = select_multiple_from_list(
            platform_choices,
            "Select platforms (multiple allowed):"
        )
        
        selected_platforms = []
        platform_keys = list(PLATFORM_CONFIGS.keys())
        
        for idx in selected_indices:
            if idx < len(platform_keys):
                selected_platforms.append(platform_keys[idx])
            else:
                # Custom sizes option
                custom_sizes = self._get_custom_sizes()
                if custom_sizes:
                    selected_platforms.append('custom')
                    self._custom_config = custom_sizes
        
        return selected_platforms
    
    def _get_custom_sizes(self) -> Optional[Dict]:
        """Get custom sizes from user"""
        sizes_input = get_input("Enter custom sizes (comma-separated, e.g., 16,32,64,128): ")
        
        try:
            sizes = [int(s.strip()) for s in sizes_input.split(',')]
            files = []
            for size in sizes:
                files.append({'size': size, 'name': f'icon-{size}x{size}.png'})
            
            return {
                'name': 'Custom Sizes',
                'description': f'Custom sizes: {", ".join(map(str, sizes))}',
                'files': files
            }
        except ValueError:
            print("❌ 尺寸格式无效")
            return None
    
    def show_generation_summary(self, platforms: List[str]) -> bool:
        """Show what will be generated"""
        print("📋 生成摘要:")
        
        total_icons = 0
        for platform in platforms:
            if platform == 'custom':
                config = self._custom_config
            else:
                config = PLATFORM_CONFIGS[platform]
            
            icon_count = len(config['files'])
            total_icons += icon_count
            print(f"• {config['name']}: {icon_count} 个图标")
        
        print(f"📊 总计: {total_icons} 个图标")
        print(f"📂 输出目录: {self.output_dir}")
        
        return confirm("是否开始生成?")
    
    def resize_image(self, source_image: Image.Image, target_size: int) -> Image.Image:
        """Resize image with high quality using safer approach"""
        try:
            # Always create a fresh copy to avoid any reference issues
            source_copy = source_image.copy()
            
            # Ensure RGBA mode for consistent processing
            if source_copy.mode != 'RGBA':
                source_copy = source_copy.convert('RGBA')
            
            # Calculate resize dimensions
            original_width, original_height = source_copy.size
            
            if self.keep_aspect_ratio:
                # Calculate scaling factor to fit within target size
                scale = min(target_size / original_width, target_size / original_height)
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
                
                # Use resize instead of thumbnail for more control
                resized = source_copy.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Create new image with target size and transparent background
                final_image = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 0))
                
                # Center the resized image
                x = (target_size - new_width) // 2
                y = (target_size - new_height) // 2
                final_image.paste(resized, (x, y), resized)
                
                return final_image
            else:
                # Direct resize to exact dimensions
                resized = source_copy.resize((target_size, target_size), Image.Resampling.LANCZOS)
                
                # Apply sharpening for small icons if requested
                if target_size <= 32 and self.quality == 'high':
                    try:
                        enhancer = ImageEnhance.Sharpness(resized)
                        resized = enhancer.enhance(1.1)  # Reduced enhancement factor
                    except Exception as e:
                        pass
                        # Continue without sharpening if it fails
                
                return resized
                
        except Exception as e:
            print(f"❌ 调整大小失败 {target_size}px: {e}")
            # Return a basic resized image as fallback
            try:
                fallback = source_image.resize((target_size, target_size), Image.Resampling.NEAREST)
                if fallback.mode != 'RGBA':
                    fallback = fallback.convert('RGBA')
                return fallback
            except Exception as fallback_error:
                print(f"❌ 回退调整也失败: {fallback_error}")
                return None
    
    def generate_icon(self, source_image: Image.Image, file_config: Dict, platform_dir: str) -> bool:
        """Generate single icon file"""
        filename = file_config.get('name', 'unknown')
        try:
            target_size = file_config['size']
            format_type = file_config.get('format', 'png')
            output_path = os.path.join(platform_dir, filename)
            
            # Resize image (this creates a copy internally to avoid threading issues)
            resized_image = self.resize_image(source_image, target_size)
            
            # Validate resized image
            if resized_image is None:
                print(f"❌ 尺寸调整失败: {filename}")
                return False
            
            # Handle different formats with safer saving approach
            if format_type.lower() == 'ico':
                # ICO format for favicons - convert to RGB first for ICO compatibility
                try:
                    ico_image = resized_image.convert('RGB')
                    ico_image.save(output_path, format='ICO', sizes=[(target_size, target_size)])
                except Exception as ico_error:
                    print(f"⚠️  ICO 保存失败，尝试 PNG: {ico_error}")
                    # Fallback to PNG if ICO fails
                    png_path = output_path.replace('.ico', '.png')
                    resized_image.save(png_path, format='PNG')
            else:
                # PNG format with enhanced safety measures
                try:
                    # Ensure consistent RGBA mode
                    if resized_image.mode != 'RGBA':
                        resized_image = resized_image.convert('RGBA')
                    
                    # Create a completely new image to avoid any reference issues
                    clean_image = Image.new('RGBA', resized_image.size, (0, 0, 0, 0))
                    clean_image.paste(resized_image, (0, 0), resized_image)
                    
                    # Save with basic PNG parameters (avoid optimization that might cause issues)
                    clean_image.save(output_path, format='PNG')
                except Exception as png_error:
                    print(f"⚠️  PNG 增强保存失败，尝试基础保存: {png_error}")
                    # Fallback to most basic PNG save
                    try:
                        basic_image = resized_image.convert('RGB')
                        basic_image.save(output_path, format='PNG')
                    except Exception as basic_error:
                        print(f"❌ PNG 所有保存方式均失败: {filename}: {basic_error}")
                        return False
            
            # Verify the generated file
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                # 生成成功
                return True
            else:
                print(f"❌ 生成的文件为空或缺失: {filename}")
                return False
            
        except Exception as e:
            print(f"❌ 生成失败 {filename}: {e}")
            return False
    
    def generate_platform_readme(self, platform: str, platform_dir: str):
        """Generate platform-specific README"""
        readme_content = {
            'web': """# Web Development Icons

## Usage
1. Copy all PNG files to your project root directory
2. Add the following to your HTML:

```html
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="192x192" href="/android-chrome-192x192.png">
<link rel="manifest" href="/site.webmanifest">
```

## PWA Manifest (site.webmanifest)
```json
{
  "icons": [
    {
      "src": "/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/android-chrome-512x512.png", 
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```
""",
            'ios': """# iOS App Development Icons

## Usage
1. Open Assets.xcassets in Xcode
2. Create new App Icon set
3. Drag corresponding icons to appropriate slots

## Icon Size Guide
- 20pt: icon-20@1x.png (20x20), icon-20@2x.png (40x40), icon-20@3x.png (60x60)
- 29pt: icon-29@1x.png (29x29), icon-29@2x.png (58x58), icon-29@3x.png (87x87)
- 40pt: icon-40@1x.png (40x40), icon-40@2x.png (80x80)
- 60pt: icon-60@2x.png (120x120), icon-60@3x.png (180x180)
- 76pt: icon-76@1x.png (76x76), icon-76@2x.png (152x152)
- 83.5pt: icon-83.5@2x.png (167x167)
- App Store: icon-1024@1x.png (1024x1024)
""",
            'android': """# Android App Development Icons

## Usage
Place icons in corresponding drawable directories:

- ic_launcher_36.png → res/mipmap-ldpi/ic_launcher.png
- ic_launcher_48.png → res/mipmap-mdpi/ic_launcher.png
- ic_launcher_72.png → res/mipmap-hdpi/ic_launcher.png
- ic_launcher_96.png → res/mipmap-xhdpi/ic_launcher.png
- ic_launcher_144.png → res/mipmap-xxhdpi/ic_launcher.png
- ic_launcher_192.png → res/mipmap-xxxhdpi/ic_launcher.png

## AndroidManifest.xml
Ensure your manifest includes:
```xml
<application android:icon="@mipmap/ic_launcher">
```
""",
            'chrome-ext': """# Chrome Extension Icons

## Usage
Add to your manifest.json:

```json
{
  "icons": {
    "16": "icon16.png",
    "32": "icon32.png",
    "48": "icon48.png", 
    "128": "icon128.png"
  },
  "action": {
    "default_icon": {
      "19": "icon19.png",
      "38": "icon38.png"
    }
  }
}
```

## Icon Usage
- 16px: Extension pages small icon
- 19px: Toolbar icon (standard DPI)
- 32px: Extension management page
- 38px: Toolbar icon (2x DPI)
- 48px: Extension management page large icon
- 128px: Chrome Web Store listing
""",
            'custom': """# Custom Icons

Generated custom-sized icons for your project.

## Usage
Use these icons according to your specific requirements.
Each icon maintains the original aspect ratio and quality.
"""
        }
        
        readme_path = os.path.join(platform_dir, 'README.md')
        content = readme_content.get(platform, readme_content['custom'])
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def generate_icons_for_platform(self, source_image: Image.Image, platform: str) -> Dict:
        """Generate all icons for a platform"""
        if platform == 'custom':
            config = self._custom_config
        else:
            config = PLATFORM_CONFIGS[platform]
        
        platform_dir = os.path.join(self.output_dir, platform)
        os.makedirs(platform_dir, exist_ok=True)
        
        print(f"🔄 正在生成 {config['name']} 图标...")
        
        success_count = 0
        total_count = len(config['files'])
        
        # Use sequential processing to avoid any threading issues
        for file_config in config['files']:
            # 逐个生成
            if self.generate_icon(source_image, file_config, platform_dir):
                success_count += 1
            else:
                print(f"⚠️  生成失败: {file_config['name']}")
        
        # Generate README
        self.generate_platform_readme(platform, platform_dir)
        
        print(f"✅ {config['name']}: {success_count}/{total_count} 个图标已生成")
        
        return {
            'platform': platform,
            'total': total_count,
            'success': success_count,
            'failed': total_count - success_count
        }
    
    def generate_report(self, results: List[Dict], source_file: str, start_time: datetime):
        """Generate generation report"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        total_icons = sum(r['total'] for r in results)
        success_icons = sum(r['success'] for r in results)
        failed_icons = sum(r['failed'] for r in results)
        
        report = {
            'source_file': source_file,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'output_directory': self.output_dir,
            'summary': {
                'total_icons': total_icons,
                'success_icons': success_icons,
                'failed_icons': failed_icons,
                'success_rate': f"{(success_icons/total_icons*100):.1f}%" if total_icons > 0 else "0%"
            },
            'platforms': results,
            'configuration': {
                'quality': self.quality,
                'background_color': self.background_color,
                'keep_aspect_ratio': self.keep_aspect_ratio,
                'threads': self.threads
            }
        }
        
        report_path = os.path.join(self.output_dir, 'generation-report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Display summary
        print(f"✅ 生成完成！")
        print(f"📊 成功: {success_icons}/{total_icons} 个图标")
        print(f"⏱️  用时: {duration:.1f} 秒")
        print(f"📁 输出目录: {self.output_dir}")
        
        if failed_icons > 0:
            print(f"⚠️  失败: {failed_icons} 个图标")
    
    def main_operation(self, input_file: str, platforms: List[str]):
        """Main icon generation operation"""
        start_time = datetime.now()
        
        # Load source image
        with Image.open(input_file) as source_image:
            # Convert to RGBA for transparency support
            if source_image.mode != 'RGBA':
                source_image = source_image.convert('RGBA')
            
            # Create output directory
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Generate icons for each platform
            results = []
            for platform in platforms:
                result = self.generate_icons_for_platform(source_image, platform)
                results.append(result)
            
            # Generate report
            self.generate_report(results, input_file, start_time)
    
    def run(self):
        """Main tool execution"""
        try:
            # Display welcome
            print("🎨 Icon Converter Tool")
            print("将单图标生成多平台规格")
            
            # Get input file
            input_file = self.get_input_file()
            if not input_file:
                print("未选择输入文件")
                return
            
            # Select platforms
            platforms = self.select_platforms()
            if not platforms:
                print("未选择平台")
                return
            
            # Show summary and confirm
            if not self.show_generation_summary(platforms):
                print("操作已取消")
                return
            
            # Generate icons
            self.main_operation(input_file, platforms)
            
        except KeyboardInterrupt:
            print("❌ 用户取消操作")
        except Exception as e:
            print(f"❌ 程序错误: {e}")
            sys.exit(1)


def main():
    """Entry point"""
    tool = IconConverter()
    tool.run()


if __name__ == '__main__':
    main()
