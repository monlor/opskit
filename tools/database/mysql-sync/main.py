#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL数据库批量同步脚本 - OpsKit 版本
功能：
1. 交互式输入源库和目标库信息，支持自定义连接名称
2. 缓存账号信息及密码，防止重复输入  
3. 支持单个或多个数据库批量同步
4. 自动过滤系统数据库 (information_schema, mysql, performance_schema, sys)
5. 同步前展示数据库详情确认
6. 安全的数据同步操作及详细的日志记录
7. 支持 Ctrl+C 在任意阶段退出
8. 使用 OpsKit 环境变量和目录管理
"""

import os
import sys
import json
import getpass
import hashlib
import time
from datetime import datetime
from typing import Dict, Optional, Tuple
import pymysql

# 获取 OpsKit 环境变量
OPSKIT_TOOL_TEMP_DIR = os.environ.get('OPSKIT_TOOL_TEMP_DIR', os.path.join(os.getcwd(), '.mysql-sync-temp'))
OPSKIT_BASE_PATH = os.environ.get('OPSKIT_BASE_PATH', os.path.expanduser('~/.opskit'))
OPSKIT_WORKING_DIR = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
TOOL_NAME = os.environ.get('TOOL_NAME', 'mysql-sync')
TOOL_VERSION = os.environ.get('TOOL_VERSION', '1.0.0')


class MySQLSyncTool:
    def __init__(self):
        # 使用 OpsKit 环境变量配置目录
        self.config_dir = OPSKIT_TOOL_TEMP_DIR
        self.config_file = os.path.join(self.config_dir, "connections.json")
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 缓存的连接信息
        self.cached_connections = self.load_cached_connections()
    
    def load_cached_connections(self) -> Dict:
        """加载缓存的连接信息"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"无法加载缓存配置: {e}")
        return {}
    
    def save_connection_cache(self):
        """保存连接信息到缓存文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.cached_connections, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
    def encrypt_password(self, password: str) -> str:
        """简单加密密码"""
        import base64
        return base64.b64encode(password.encode('utf-8')).decode('utf-8')
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码"""
        import base64
        return base64.b64decode(encrypted_password.encode('utf-8')).decode('utf-8')
    
    def get_connection_name(self, name: str) -> str:
        """获取连接名称标识符"""
        return name
    
    def display_cached_connections(self):
        """显示已缓存的连接"""
        if not self.cached_connections:
            print("📝 暂无缓存的连接信息")
            return
        
        print("\n📋 已缓存的连接信息:")
        print("-" * 60)
        for i, (conn_name, conn_info) in enumerate(self.cached_connections.items(), 1):
            print(f"{i}. {conn_name}")
            print(f"   主机: {conn_info['host']}")
            print(f"   端口: {conn_info['port']}")
            print(f"   用户: {conn_info['user']}")
            print(f"   最后使用: {conn_info.get('last_used', '未知')}")
            print()
    
    def select_cached_connection(self) -> Optional[Dict]:
        """选择缓存的连接"""
        if not self.cached_connections:
            return None
        
        while True:
            self.display_cached_connections()

            try:
                choice = input("选择缓存的连接 (输入编号，或按回车添加新的连接): ").strip()
            except KeyboardInterrupt:
                print("\n\n👋 用户取消操作")
                return None

            if not choice:
                return None

            # 数字校验仅限纯数字
            if not choice.isdigit():
                print("❌ 请输入有效的数字或按回车添加新连接")
                continue

            choice_num = int(choice)
            if not (1 <= choice_num <= len(self.cached_connections)):
                print("❌ 无效的选择，请重新选择")
                continue

            conn_name = list(self.cached_connections.keys())[choice_num - 1]
            conn_info = self.cached_connections[conn_name].copy()

            # 解密缓存的密码；若失败，回退为明文
            if 'password' in conn_info:
                try:
                    conn_info['password'] = self.decrypt_password(conn_info['password'])
                except Exception:
                    # 兼容旧缓存：密码可能已是明文
                    pass
                print(f"✅ 使用已缓存的连接: {conn_name}")
            else:
                print(f"❌ 连接 {conn_name} 没有缓存密码")
                continue  # 继续循环让用户重新选择

            # 更新最后使用时间并保存
            conn_info['last_used'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cached_connections[conn_name]['last_used'] = conn_info['last_used']
            self.save_connection_cache()

            return conn_info
    
    def input_connection_info(self, conn_type: str) -> Dict:
        """交互式输入连接信息"""
        print(f"\n🔧 配置{conn_type}数据库连接")
        print("-" * 40)
        
        # 尝试选择缓存的连接
        cached_conn = self.select_cached_connection()
        if cached_conn:
            return cached_conn
        
        # 手动输入连接信息
        while True:
            try:
                conn_name = input("连接名称: ").strip()
                if not conn_name:
                    print("❌ 连接名称不能为空")
                    continue
                
                if conn_name in self.cached_connections:
                    print(f"❌ 连接名称 '{conn_name}' 已存在，请使用其他名称")
                    continue
                
                host = input("主机地址 (默认: localhost): ").strip() or "localhost"
                port = int(input("端口 (默认: 3306): ").strip() or "3306")
                user = input("用户名: ").strip()
                
                if not user:
                    print("❌ 用户名不能为空")
                    continue
                
                password = getpass.getpass("密码: ")
                
                conn_info = {
                    'name': conn_name,
                    'host': host,
                    'port': port,
                    'user': user,
                    'password': password,
                    'last_used': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # 测试连接
                if self.test_connection(conn_info):
                    # 缓存连接信息（包含加密的密码）
                    cache_info = conn_info.copy()
                    cache_info['password'] = self.encrypt_password(password)  # 加密密码
                    self.cached_connections[conn_name] = cache_info
                    self.save_connection_cache()
                    
                    print(f"✅ 连接 '{conn_name}' 已保存")
                    
                    return conn_info
                else:
                    print("❌ 连接测试失败，请重新输入")
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户取消操作")
                sys.exit(0)
            except ValueError:
                print("❌ 端口必须是数字")
            except Exception as e:
                print(f"❌ 输入错误: {e}")
    
    def test_connection(self, conn_info: Dict) -> bool:
        """测试数据库连接"""
        try:
            conn_name = conn_info.get('name', f"{conn_info['user']}@{conn_info['host']}:{conn_info['port']}")
            print(f"🔍 测试连接到 {conn_name}...")
            
            connection = pymysql.connect(
                host=conn_info['host'],
                port=conn_info['port'],
                user=conn_info['user'],
                password=conn_info['password'],
                charset='utf8mb4',
                connect_timeout=10
            )
            connection.close()
            print(f"✅ 连接 {conn_name} 测试成功")
            return True
            
        except Exception as e:
            print(f"❌ 连接 {conn_name} 失败: {e}")
            return False
    
    def get_database_info(self, conn_info: Dict) -> Dict:
        """获取数据库详细信息"""
        # 系统数据库列表，默认跳过
        system_databases = {'information_schema', 'mysql', 'performance_schema', 'sys'}
        
        try:
            connection = pymysql.connect(
                host=conn_info['host'],
                port=conn_info['port'],
                user=conn_info['user'],
                password=conn_info['password'],
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                info = {}
                
                # 服务器版本
                cursor.execute("SELECT VERSION()")
                info['version'] = cursor.fetchone()[0]
                
                # 数据库列表
                cursor.execute("SHOW DATABASES")
                all_databases = [row[0] for row in cursor.fetchall()]
                
                # 过滤系统数据库
                info['databases'] = [db for db in all_databases if db.lower() not in system_databases]
                info['all_databases'] = all_databases
                info['system_databases'] = [db for db in all_databases if db.lower() in system_databases]
                
            connection.close()
            return info
            
        except Exception as e:
            print(f"获取数据库信息失败: {e}")
            return {}
    
    def create_database_if_not_exists(self, conn_info: Dict, database_name: str) -> bool:
        """如果数据库不存在则创建它"""
        try:
            connection = pymysql.connect(
                host=conn_info['host'],
                port=conn_info['port'],
                user=conn_info['user'],
                password=conn_info['password'],
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                # 检查数据库是否存在
                cursor.execute("SHOW DATABASES")
                existing_databases = [row[0] for row in cursor.fetchall()]
                
                if database_name not in existing_databases:
                    print(f"📁 目标数据库 '{database_name}' 不存在，正在创建...")
                    cursor.execute(f"CREATE DATABASE `{database_name}`")
                    print(f"✅ 数据库 '{database_name}' 创建成功")
                else:
                    print(f"📁 目标数据库 '{database_name}' 已存在")
                
            connection.close()
            return True
            
        except Exception as e:
            print(f"❌ 创建数据库 '{database_name}' 失败: {e}")
            return False
    
    def select_databases(self, conn_info: Dict, db_info: Dict, conn_type: str) -> list:
        """选择数据库（支持单个或多个）"""
        print(f"\n📋 {conn_type}数据库选择 - {conn_info.get('name', 'Unknown')}")
        print("-" * 50)
        print(f"🏠 主机: {conn_info['host']}:{conn_info['port']}")
        print(f"👤 用户: {conn_info['user']}")
        print(f"🔢 版本: {db_info.get('version', '未知')}")
        
        databases = db_info.get('databases', [])
        system_databases = db_info.get('system_databases', [])
        
        if not databases:
            print("❌ 没有可用的数据库（已过滤系统数据库）")
            return []
        
        print(f"📊 可用数据库数量: {len(databases)} (已过滤系统数据库)")
        if system_databases:
            print(f"⚠️  已过滤系统数据库: {', '.join(system_databases)}")
        
        print("\n💾 可用数据库列表:")
        for i, db in enumerate(databases, 1):
            print(f"{i}. {db}")
        
        print("\n选择模式:")
        print("1. 输入单个编号 (例: 3)")
        print("2. 输入多个编号，用逗号分隔 (例: 1,3,5)")
        print("3. 输入范围 (例: 1-5)")
        print("4. 输入 'all' 选择所有数据库")
        print("5. 按 Ctrl+C 退出")
        
        while True:
            try:
                choice = input(f"\n请选择{conn_type}数据库: ").strip().lower()
                
                if choice == 'all':
                    print(f"✅ 已选择所有{conn_type}数据库: {', '.join(databases)}")
                    return databases
                
                selected_dbs = []
                
                # 处理范围选择 (1-5)
                if '-' in choice and choice.count('-') == 1:
                    try:
                        start, end = choice.split('-')
                        start_num = int(start.strip())
                        end_num = int(end.strip())
                        if 1 <= start_num <= len(databases) and 1 <= end_num <= len(databases) and start_num <= end_num:
                            for i in range(start_num, end_num + 1):
                                selected_dbs.append(databases[i - 1])
                        else:
                            print("❌ 范围超出有效范围")
                            continue
                    except ValueError:
                        print("❌ 范围格式错误，请使用格式: 1-5")
                        continue
                        
                # 处理逗号分隔的多个选择 (1,3,5)
                elif ',' in choice:
                    try:
                        indices = [int(x.strip()) for x in choice.split(',')]
                        for idx in indices:
                            if 1 <= idx <= len(databases):
                                if databases[idx - 1] not in selected_dbs:
                                    selected_dbs.append(databases[idx - 1])
                            else:
                                print(f"❌ 编号 {idx} 超出范围")
                                selected_dbs = []
                                break
                        if not selected_dbs:
                            continue
                    except ValueError:
                        print("❌ 请输入有效的数字，用逗号分隔")
                        continue
                        
                # 处理单个选择
                else:
                    try:
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(databases):
                            selected_dbs = [databases[choice_num - 1]]
                        else:
                            print("❌ 无效的选择")
                            continue
                    except ValueError:
                        print("❌ 请输入有效的数字、范围或 'all'")
                        continue
                
                if selected_dbs:
                    print(f"✅ 已选择{conn_type}数据库 ({len(selected_dbs)}个): {', '.join(selected_dbs)}")
                    return selected_dbs
                    
            except KeyboardInterrupt:
                print("\n\n👋 用户取消操作")
                return []
    
    def confirm_sync_operation(self, source_info: Dict, target_info: Dict, source_dbs: list, sync_mode: str = 'individual') -> bool:
        """确认同步操作"""
        print("\n" + "=" * 80)
        print("🚨 批量数据库同步确认")
        print("=" * 80)
        
        print("\n📤 源数据库 (FROM):")
        print(f"   连接: {source_info.get('name', 'Unknown')}")
        print(f"   主机: {source_info['host']}:{source_info['port']}")
        print(f"   用户: {source_info['user']}")
        print(f"   数据库 ({len(source_dbs)}个): {', '.join(source_dbs)}")
        
        print("\n📥 目标数据库 (TO):")
        print(f"   连接: {target_info.get('name', 'Unknown')}")
        print(f"   主机: {target_info['host']}:{target_info['port']}")
        print(f"   用户: {target_info['user']}")
        
        if sync_mode == 'individual':
            print(f"   同步模式: 一对一同步 (相同数据库名)")
            print(f"   目标数据库: {', '.join(source_dbs)}")
        else:
            print(f"   同步模式: 自定义映射")
        
        print("\n⚠️  警告信息:")
        print("   • 此操作将批量同步多个数据库")
        print("   • 目标数据库的现有数据可能会被覆盖")
        print("   • 请确保你已经备份了重要数据")
        print("   • 建议先在测试环境中验证")
        print(f"   • 将同步 {len(source_dbs)} 个数据库")
        
        # 安全检查：防止同库操作
        if source_info['host'] == target_info['host'] and source_info['port'] == target_info['port']:
            print("\n⚠️  注意: 源和目标在同一服务器上，请确保数据库名不同！")
        
        print("\n📝 请仔细确认以上信息！")
        print("   输入 'YES' 继续批量同步")
        print("   输入其他任何内容取消操作")
        
        try:
            confirmation = input("\n确认批量同步操作: ").strip()
            
            if confirmation == 'YES':
                print("✅ 用户确认批量同步操作")
                return True
            else:
                print("❌ 用户取消批量同步操作")
                return False
        except KeyboardInterrupt:
            print("\n\n👋 用户取消操作")
            return False
    
    def sync_single_database(self, source_info: Dict, target_info: Dict, source_db: str) -> bool:
        """同步单个数据库"""
        target_db = source_db  # 默认目标数据库名与源数据库名相同
        
        try:
            # 确保目标数据库存在
            if not self.create_database_if_not_exists(target_info, target_db):
                print(f"❌ 无法创建目标数据库 {target_db}")
                return False
            
            # 构建mysqldump命令，使用单引号包裹密码
            dump_cmd = (
                f"mysqldump "
                f"-h{source_info['host']} "
                f"-P{source_info['port']} "
                f"-u{source_info['user']} "
                f"-p'{source_info['password']}' "
                f"--single-transaction "
                f"--skip-routines "
                f"--triggers "
                f"--set-gtid-purged=OFF "
                f"{source_db}"
            )
            
            # 构建mysql导入命令，使用单引号包裹密码
            import_cmd = (
                f"mysql "
                f"-h{target_info['host']} "
                f"-P{target_info['port']} "
                f"-u{target_info['user']} "
                f"-p'{target_info['password']}' "
                f"{target_db}"
            )
            
            # 执行同步命令
            full_cmd = f"{dump_cmd} | {import_cmd}"
            
            print(f"📊 正在导出 {source_db}...")
            print(f"📥 正在导入到 {target_db}...")
            
            result = os.system(full_cmd)
            
            if result == 0:
                print(f"✅ {source_db} 同步成功！")
                return True
            else:
                print(f"❌ {source_db} 同步失败 (返回码: {result})")
                return False
                
        except Exception as e:
            print(f"❌ {source_db} 同步过程出现错误: {e}")
            return False
    
    def perform_batch_sync(self, source_info: Dict, target_info: Dict, source_dbs: list) -> bool:
        """执行批量数据库同步（支持自动重试）"""
        print(f"\n🚀 开始批量数据库同步... (共 {len(source_dbs)} 个数据库)")
        print("🔄 支持自动重试机制 (失败时最多重试3次)")
        
        success_count = 0
        failed_dbs = []
        max_retries = 3
        
        for i, source_db in enumerate(source_dbs, 1):
            target_db = source_db  # 默认目标数据库名与源数据库名相同
            
            print(f"\n[{i}/{len(source_dbs)}] 🔄 同步数据库: {source_db} -> {target_db}")
            print("-" * 60)
            
            # 重试机制
            sync_success = False
            for attempt in range(1, max_retries + 1):
                try:
                    if attempt > 1:
                        print(f"🔄 第 {attempt} 次重试同步 {source_db}...")
                        # 重试前等待一段时间，避免网络问题
                        retry_delay = min(5 * (attempt - 1), 15)  # 5s, 10s, 15s
                        if retry_delay > 0:
                            print(f"⏳ 等待 {retry_delay} 秒后重试...")
                            time.sleep(retry_delay)
                    
                    # 执行同步
                    if self.sync_single_database(source_info, target_info, source_db):
                        print(f"✅ [{i}/{len(source_dbs)}] {source_db} 同步成功！")
                        success_count += 1
                        sync_success = True
                        break
                    else:
                        if attempt < max_retries:
                            print(f"⚠️ 第 {attempt} 次尝试失败，准备重试...")
                        else:
                            print(f"❌ [{i}/{len(source_dbs)}] {source_db} 同步失败 (已重试 {max_retries} 次)")
                    
                except KeyboardInterrupt:
                    print(f"\n\n👋 用户中断同步操作")
                    raise
                except Exception as e:
                    print(f"❌ 同步过程出现异常: {e}")
                    if attempt >= max_retries:
                        break
            
            # 如果所有重试都失败了
            if not sync_success:
                failed_dbs.append(source_db)
        
        # 统计结果
        print("\n" + "=" * 80)
        print("📊 批量同步统计结果")
        print("=" * 80)
        print(f"✅ 成功: {success_count}/{len(source_dbs)} 个数据库")
        print(f"❌ 失败: {len(failed_dbs)}/{len(source_dbs)} 个数据库")
        
        if failed_dbs:
            print(f"\n失败的数据库: {', '.join(failed_dbs)}")
        
        return len(failed_dbs) == 0
    
    def run(self):
        """主运行函数"""
        print("🔄 MySQL数据库批量同步工具")
        print("=" * 50)
        print("✨ 支持单个或多个数据库批量同步")
        print("⚠️  自动过滤系统数据库 (information_schema, mysql, performance_schema, sys)")
        
        try:
            # 获取源数据库连接信息
            source_info = self.input_connection_info("源")
            if not source_info:
                return
            
            # 获取目标数据库连接信息  
            target_info = self.input_connection_info("目标")
            if not target_info:
                return
            
            # 获取数据库详细信息
            print("\n🔍 正在获取数据库信息...")
            source_db_info = self.get_database_info(source_info)
            target_db_info = self.get_database_info(target_info)
            
            if not source_db_info.get('databases'):
                print("❌ 源数据库没有可用的数据库")
                return
            
            # 选择源数据库（支持多选）
            source_dbs = self.select_databases(source_info, source_db_info, "源")
            if not source_dbs:
                print("\n👋 未选择数据库，操作已取消")
                return
            
            # 确认同步操作
            if not self.confirm_sync_operation(source_info, target_info, source_dbs):
                print("\n👋 批量同步操作已取消")
                return
            
            # 执行批量同步
            success = self.perform_batch_sync(source_info, target_info, source_dbs)
            
            if success:
                print(f"\n🎉 批量同步全部成功！")
            else:
                print(f"\n⚠️  批量同步部分失败")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断操作")
        except Exception as e:
            print(f"\n❌ 程序错误: {e}")


if __name__ == "__main__":
    # 检查依赖
    try:
        import pymysql
    except ImportError:
        print("❌ 缺少依赖包 pymysql")
        print("请运行: pip install pymysql")
        sys.exit(1)
    
    # 检查系统命令
    if os.system("which mysqldump > /dev/null 2>&1") != 0:
        print("❌ 未找到 mysqldump 命令")
        print("请安装 MySQL 客户端工具")
        sys.exit(1)
    
    # 运行同步工具
    sync_tool = MySQLSyncTool()
    sync_tool.run()
