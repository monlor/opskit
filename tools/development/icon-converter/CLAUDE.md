# Icon Converter Tool

## 功能描述
自动将单个图标文件转换为多种尺寸和格式，支持Web开发、iOS应用开发、Android应用开发、Chrome浏览器插件等不同平台的图标需求。提供交互式界面，支持多平台选择和批量生成。

## 技术架构
- 实现语言: Python
- 核心依赖: Pillow (图像处理), rich (美化输出), glob (文件搜索)
- 系统要求: Python 3.7+
- 图像处理: Lanczos重采样算法，高质量缩放
- 支持格式: PNG, JPG, JPEG, SVG输入；PNG, ICO输出

## 核心功能
- **多平台支持**: Web、iOS、Android、Chrome扩展
- **交互式文件选择**: 路径输入、目录选择、拖拽文件
- **批量生成**: 一次选择多个平台，自动生成所有尺寸
- **智能输出**: 按平台分类，自动生成使用文档
- **质量优化**: 高质量缩放算法，小尺寸图标特殊处理

## 平台规范

### Web Development (web)
- 16x16px - 浏览器标签页图标
- 32x32px - 书签和地址栏图标
- 48x48px - Windows任务栏图标
- 96x96px - Android Chrome图标
- 192x192px - PWA应用图标
- 512x512px - PWA启动画面
- favicon.ico - 传统网站图标

### iOS App Development (ios)
- 20x20px (@1x), 40x40px (@2x), 60x60px (@3x) - Notification
- 29x29px (@1x), 58x58px (@2x), 87x87px (@3x) - Settings
- 40x40px (@1x), 80x80px (@2x) - Spotlight
- 120x120px (@2x), 180x180px (@3x) - iPhone App
- 76x76px (@1x), 152x152px (@2x) - iPad App
- 167x167px (@2x) - iPad Pro App
- 1024x1024px - App Store

### Android App Development (android)
- 36x36px - ldpi (低密度)
- 48x48px - mdpi (中密度)
- 72x72px - hdpi (高密度)
- 96x96px - xhdpi (超高密度)
- 144x144px - xxhdpi (超超高密度)
- 192x192px - xxxhdpi (超超超高密度)

### Chrome Extension (chrome-ext)
- 16x16px - 扩展页面小图标
- 19x19px - 工具栏图标 (标准)
- 32x32px - 扩展管理页面
- 38x38px - 工具栏图标 (2x)
- 48x48px - 扩展管理页面大图标
- 128x128px - Chrome Web Store

## 配置项
- OUTPUT_DIR: 输出目录 (默认: ./generated-icons, 相对路径将基于OPSKIT_WORKING_DIR)
- QUALITY: 图像质量 (high/medium/low, 默认: high)
- BACKGROUND_COLOR: 背景色 (默认: white)
- THREADS: 并行处理线程数 (默认: 4)
- KEEP_ASPECT_RATIO: 保持宽高比 (默认: true)

**路径处理**:
- 如果OUTPUT_DIR是相对路径，会自动拼接OPSKIT_WORKING_DIR环境变量
- 如果OUTPUT_DIR是绝对路径，直接使用该路径
- 文件选择功能中的"当前目录选择"使用OPSKIT_WORKING_DIR作为搜索目录
- OPSKIT_WORKING_DIR默认为当前工作目录

## 使用示例

### 交互模式 (推荐)
```bash
opskit icon-converter
```
1. 选择输入文件方式 (路径输入/目录选择/拖拽)
2. 选择目标平台 (支持多选)
3. 确认输出目录
4. 自动生成所有图标

### 命令行模式
```bash
# 基础用法
opskit icon-converter --input icon.png --platforms web

# 多平台生成
opskit icon-converter --input icon.png --platforms web,ios,android

# 自定义输出目录
opskit icon-converter --input icon.png --platforms web --output ./my-icons/

# 自定义尺寸
opskit icon-converter --input icon.png --sizes 16,32,64,128
```

## 输出结构
```
generated-icons/
├── web/
│   ├── favicon-16x16.png
│   ├── favicon-32x32.png
│   ├── favicon.ico
│   └── README.md
├── ios/
│   ├── icon-20@1x.png
│   ├── icon-20@2x.png
│   └── README.md
├── android/
│   ├── ic_launcher_36.png
│   ├── ic_launcher_48.png
│   └── README.md
├── chrome-ext/
│   ├── icon16.png
│   ├── icon128.png
│   └── README.md
└── generation-report.json
```

## 开发指南

### 核心类结构
- `IconConverter`: 主控制器，管理整个转换流程
- `PlatformConfig`: 平台配置管理，内置所有平台规范
- `ImageProcessor`: 图像处理引擎，负责缩放和格式转换
- `FileManager`: 文件输入输出管理
- `InteractiveUI`: 交互式用户界面

### 图像处理策略
- 使用Pillow的Lanczos重采样算法确保高质量缩放
- 对小尺寸图标 (<= 32px) 进行特殊处理和锐化
- 保持透明背景，支持背景色填充选项
- 自动检测并处理各种输入格式

### 错误处理
- 文件格式验证和错误提示
- 图像尺寸检查和建议
- 输出目录权限检查
- 磁盘空间不足处理

### 性能优化
- 多线程并行处理多个尺寸
- 智能缓存避免重复处理
- 内存使用优化，及时释放图像对象

## 集成OpsKit框架
- 使用统一的日志系统记录处理过程
- 集成交互式组件提供友好界面
- 使用环境变量管理配置
- 遵循OpsKit工具开发规范

## 扩展计划
- 支持更多图像格式 (WebP, AVIF)
- 添加图像压缩优化选项
- 支持批量文件处理
- 集成图标设计建议功能