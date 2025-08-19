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

# Import OpsKit common libraries
sys.path.insert(0, os.path.join(os.environ['OPSKIT_BASE_PATH'], 'common/python'))

from logger import get_logger
from storage import get_storage
from utils import run_command, timestamp, get_env_var
from interactive import get_input, confirm, select_from_list, select_multiple_from_list, delete_confirm

# Third-party imports
try:
    from PIL import Image, ImageEnhance
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please ensure all dependencies are installed.")
    sys.exit(1)

# Initialize OpsKit components
logger = get_logger(__name__)
storage = get_storage('icon-converter')

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
        
        logger.info(f"🚀 Starting {self.tool_name}")
        logger.debug(f"Configuration - output: {self.output_dir}, quality: {self.quality}")
    
    def validate_image_file(self, file_path: str) -> bool:
        """Validate image file"""
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return False
        
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                logger.info(f"✅ File loaded: {os.path.basename(file_path)} ({width}x{height})")
                return True
        except Exception as e:
            logger.error(f"Cannot open image file: {e}")
            return False
    
    def get_input_file(self) -> Optional[str]:
        """Get input file from user"""
        logger.info("📁 Select icon file:")
        logger.info("1. Enter file path (you can drag file to terminal)")
        logger.info("2. Select from current directory")
        
        choice = get_input("Choose method (1-2): ", 
                          validator=lambda x: x in ['1', '2'])
        
        if choice == '1':
            return self._input_file_path()
        else:
            return self._select_from_directory()
    
    def _input_file_path(self) -> Optional[str]:
        """Direct file path input"""
        logger.info("💡 Tip: You can drag and drop file to terminal window")
        while True:
            file_path = get_input("Enter file path: ")
            file_path = file_path.strip().strip('"\'')
            
            if self.validate_image_file(file_path):
                return file_path
            else:
                logger.error("❌ Invalid image file")
                if not confirm("Try again?"):
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
            logger.error("❌ No image files found in current directory")
            return None
        
        # Show file details
        logger.info(f"Available Image Files in {current_dir}:")
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
            logger.info(f"{i}. {display_name}")
        
        selected_idx = select_from_list(display_names, "Select image file:")
        if selected_idx is not None:
            selected_file_path = image_files[selected_idx]
            return selected_file_path
        return None
    
    
    def select_platforms(self) -> List[str]:
        """Select target platforms"""
        logger.info("🎯 Select target platforms:")
        
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
            logger.error("❌ Invalid size format")
            return None
    
    def show_generation_summary(self, platforms: List[str]) -> bool:
        """Show what will be generated"""
        logger.info("📋 Generation Summary:")
        
        total_icons = 0
        for platform in platforms:
            if platform == 'custom':
                config = self._custom_config
            else:
                config = PLATFORM_CONFIGS[platform]
            
            icon_count = len(config['files'])
            total_icons += icon_count
            logger.info(f"• {config['name']}: {icon_count} icons")
        
        logger.info(f"📊 Total: {total_icons} icons")
        logger.info(f"📂 Output directory: {self.output_dir}")
        
        return confirm("Proceed with generation?")
    
    def resize_image(self, source_image: Image.Image, target_size: int) -> Image.Image:
        """Resize image with high quality"""
        # Use high-quality resampling
        resample = Image.Resampling.LANCZOS
        
        if self.keep_aspect_ratio:
            # Resize maintaining aspect ratio
            source_image.thumbnail((target_size, target_size), resample)
            
            # Create new image with target size and paste centered
            new_image = Image.new('RGBA', (target_size, target_size), (255, 255, 255, 0))
            x = (target_size - source_image.width) // 2
            y = (target_size - source_image.height) // 2
            new_image.paste(source_image, (x, y), source_image if source_image.mode == 'RGBA' else None)
            return new_image
        else:
            # Direct resize
            resized = source_image.resize((target_size, target_size), resample)
            
            # Enhance small icons
            if target_size <= 32 and self.quality == 'high':
                enhancer = ImageEnhance.Sharpness(resized)
                resized = enhancer.enhance(1.2)
            
            return resized
    
    def generate_icon(self, source_image: Image.Image, file_config: Dict, platform_dir: str) -> bool:
        """Generate single icon file"""
        try:
            target_size = file_config['size']
            filename = file_config['name']
            format_type = file_config.get('format', 'png')
            
            # Resize image
            resized_image = self.resize_image(source_image, target_size)
            
            # Handle different formats
            output_path = os.path.join(platform_dir, filename)
            
            if format_type.lower() == 'ico':
                # ICO format for favicons
                resized_image.save(output_path, format='ICO', sizes=[(target_size, target_size)])
            else:
                # PNG format
                if resized_image.mode != 'RGBA':
                    resized_image = resized_image.convert('RGBA')
                resized_image.save(output_path, format='PNG', optimize=True)
            
            logger.debug(f"Generated: {filename} ({target_size}x{target_size})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate {filename}: {e}")
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
        
        logger.info(f"🔄 Generating {config['name']} icons...")
        
        success_count = 0
        total_count = len(config['files'])
        
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = []
            
            for file_config in config['files']:
                future = executor.submit(self.generate_icon, source_image, file_config, platform_dir)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    success_count += 1
        
        # Generate README
        self.generate_platform_readme(platform, platform_dir)
        
        logger.info(f"✅ {config['name']}: {success_count}/{total_count} icons generated")
        
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
        logger.info(f"✅ Generation completed!")
        logger.info(f"📊 Success: {success_icons}/{total_icons} icons")
        logger.info(f"⏱️  Duration: {duration:.1f} seconds")
        logger.info(f"📁 Output: {self.output_dir}")
        
        if failed_icons > 0:
            logger.warning(f"⚠️  Failed: {failed_icons} icons")
    
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
            logger.info("🎨 Icon Converter Tool")
            logger.info("Convert icons for multiple platforms")
            
            # Get input file
            input_file = self.get_input_file()
            if not input_file:
                logger.info("No input file selected")
                return
            
            # Select platforms
            platforms = self.select_platforms()
            if not platforms:
                logger.info("No platforms selected")
                return
            
            # Show summary and confirm
            if not self.show_generation_summary(platforms):
                logger.info("Operation cancelled by user")
                return
            
            # Generate icons
            self.main_operation(input_file, platforms)
            
        except KeyboardInterrupt:
            logger.info("❌ Operation cancelled by user")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            sys.exit(1)


def main():
    """Entry point"""
    tool = IconConverter()
    tool.run()


if __name__ == '__main__':
    main()