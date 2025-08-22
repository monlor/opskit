#!/usr/bin/env python3
"""
Kubernetes Resource Export Tool - OpsKit Version
Export Kubernetes resources from specified namespaces with optional kubectl neat cleaning
"""

import os
import sys
import json
import yaml
import subprocess
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import click
import logging
from dataclasses import dataclass
from datetime import datetime

# 获取 OpsKit 环境变量
OPSKIT_TOOL_TEMP_DIR = os.environ.get('OPSKIT_TOOL_TEMP_DIR', os.path.join(os.getcwd(), '.k8s-export-temp'))
OPSKIT_BASE_PATH = os.environ.get('OPSKIT_BASE_PATH', os.path.expanduser('~/.opskit'))
OPSKIT_WORKING_DIR = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
TOOL_NAME = os.environ.get('TOOL_NAME', 'k8s-export')
TOOL_VERSION = os.environ.get('TOOL_VERSION', '1.0.0')

# 创建临时目录
os.makedirs(OPSKIT_TOOL_TEMP_DIR, exist_ok=True)

"""
最小化对 OpsKit 内部库依赖：允许使用 env 和 common/python/utils（如可用），
其他统一用简单的 print/input，输出风格参考 mysql-sync。
"""

# Import OpsKit utils (保留基础工具函数)，不可用时提供兜底实现
try:
    sys.path.insert(0, os.path.join(OPSKIT_BASE_PATH, 'common/python'))
    from utils import run_command, get_env_var
except Exception:
    # 简单的命令执行函数
    def run_command(cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0, result.stdout, result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False, "", str(e)

    # 简单的环境变量获取函数
    def get_env_var(name: str, default=None, var_type=str):
        value = os.environ.get(name, default)
        if var_type == bool and isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        elif var_type == int and isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return value

# Minimal logger setup (used for debug/info/warn messages)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def timestamp() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class SimpleInteractive:
    def section(self, title: str):
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)
    def subsection(self, title: str):
        print(f"\n—— {title} ——")
    def info(self, msg: str):
        print(msg)
    def warning_msg(self, msg: str):
        print(f"⚠️  {msg}")
    def success(self, msg: str):
        print(f"✅ {msg}")
    def failure(self, msg: str):
        print(f"❌ {msg}")
    def operation_start(self, title: str, extra: str = ""):
        print(f"\n🔄 {title} {extra}".rstrip())
        print("-" * 60)
    def confirm(self, prompt: str, default: bool = True) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        try:
            ans = input(f"{prompt} {suffix}: ").strip().lower()
            if ans == "":
                return default
            return ans in ("y", "yes")
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            return False
    def get_input(self, prompt: str, required: bool = True) -> str:
        while True:
            try:
                val = input(f"{prompt}: ")
            except KeyboardInterrupt:
                print("\n👋 用户取消操作")
                return ""
            val = val.strip()
            if val or not required:
                return val
            logger.warning("输入不能为空，请重试")
    def with_loading(self, func, message: str, *args, **kwargs):
        print(f"⏳ {message}...")
        return func(*args, **kwargs)
    def user_cancelled(self, action: str = ""):
        print(f"\n👋 用户取消{action}操作" if action else "\n👋 用户取消操作")

def get_interactive(*_args, **_kwargs) -> SimpleInteractive:
    return SimpleInteractive()

# 全局交互实例，避免依赖外部 interactive 库
interactive = SimpleInteractive()

# Third-party imports with error handling
try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init()
except Exception:
    # 缺失 colorama 不影响运行
    class _No:
        RESET_ALL = ""
    Fore = Back = Style = _No()


@dataclass
class K8sResource:
    """Kubernetes resource representation"""
    kind: str
    name: str
    namespace: str
    labels: Dict[str, str]
    
    @property
    def identifier(self) -> str:
        """Get unique resource identifier"""
        return f"{self.kind.lower()}/{self.name}"
    
    @property
    def full_identifier(self) -> str:
        """Get full resource identifier with namespace"""
        return f"{self.namespace}/{self.identifier}"


class KubectlManager:
    """Manages kubectl operations and plugin integration"""
    
    def __init__(self):
        self.kubectl_path = None
        self.krew_available = False
        self.neat_available = False
        self.ctx_available = False
        self.ns_available = False
        
    def check_kubectl(self) -> bool:
        """Check if kubectl is available"""
        success, stdout, stderr = run_command(['kubectl', 'version', '--client'])
        if success:
            self.kubectl_path = 'kubectl'
            return True
        else:
            return False
    
    def check_krew(self) -> bool:
        """Check if krew is available"""
        success, stdout, stderr = run_command(['kubectl', 'krew', 'version'])
        if success:
            self.krew_available = True
            return True
        else:
            return False
    
    def check_plugins(self) -> Dict[str, bool]:
        """Check availability of kubectl plugins"""
        plugins = {}
        
        # Check neat plugin
        success, _, _ = run_command(['kubectl', 'neat', 'version'])
        plugins['neat'] = success
        self.neat_available = success
        
        # Check ctx plugin  
        success, _, _ = run_command(['kubectl', 'ctx', '--help'])
        plugins['ctx'] = success
        self.ctx_available = success
        
        # Check ns plugin
        success, _, _ = run_command(['kubectl', 'ns', '--help'])
        plugins['ns'] = success
        self.ns_available = success
        
        return plugins
    
    def get_contexts(self) -> List[str]:
        """Get available kubectl contexts"""
        success, stdout, stderr = run_command(['kubectl', 'config', 'get-contexts', '-o', 'name'])
        if success:
            return [ctx.strip() for ctx in stdout.strip().split('\n') if ctx.strip()]
        return []
    
    def get_current_context(self) -> Optional[str]:
        """Get current kubectl context"""
        success, stdout, stderr = run_command(['kubectl', 'config', 'current-context'])
        if success:
            return stdout.strip()
        return None
    
    def switch_context(self, context: str) -> bool:
        """Switch kubectl context"""
        if self.ctx_available:
            success, stdout, stderr = run_command(['kubectl', 'ctx', context])
        else:
            success, stdout, stderr = run_command(['kubectl', 'config', 'use-context', context])
        
        if success:
            logger.info(f"✅ Switched to context: {context}")
            return True
        else:
            logger.error(f"❌ Failed to switch context: {stderr}")
            return False
    
    def get_namespaces(self, context: str = None) -> List[str]:
        """Get namespaces in current or specified context"""
        if context:
            original_context = self.get_current_context()
            if not self.switch_context(context):
                return []
        
        success, stdout, stderr = run_command(['kubectl', 'get', 'namespaces', '-o', 'jsonpath={.items[*].metadata.name}'])
        
        if context and original_context:
            self.switch_context(original_context)
        
        if success:
            return stdout.strip().split()
        return []
    
    def get_resources_by_type(self, resource_type: str, namespace: str = None) -> List[Dict]:
        """Get all resources of specified type"""
        cmd = ['kubectl', 'get', resource_type, '-o', 'json']
        if namespace:
            cmd.extend(['-n', namespace])
        
        success, stdout, stderr = run_command(cmd)
        if success:
            try:
                data = json.loads(stdout)
                items = data.get('items', [])
                logger.debug(f"Retrieved {len(items)} {resource_type} from {namespace or 'cluster'}")
                return items
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse {resource_type} JSON: {e}")
        else:
            # Log the specific error for debugging
            if "forbidden" in stderr.lower():
                logger.debug(f"Permission denied: {resource_type} in {namespace or 'cluster'}: {stderr}")
            elif "not found" in stderr.lower() or "no resources found" in stderr.lower():
                logger.debug(f"No {resource_type} found in {namespace or 'cluster'}")
            else:
                logger.debug(f"Failed to get {resource_type} from {namespace or 'cluster'}: {stderr}")
        return []
    
    def get_available_resource_types(self, use_dynamic: bool = False) -> List[str]:
        """Get resource types - either fixed common list or all available resources from cluster"""
        
        if not use_dynamic:
            # Return fixed common resource types
            return [
                'deployments', 'statefulsets', 'daemonsets',
                'services', 'ingresses',
                'persistentvolumeclaims',
                'configmaps', 'secrets',
                'horizontalpodautoscalers',
                'jobs', 'cronjobs',
                'networkpolicies',
                'serviceaccounts',
                'roles', 'rolebindings'
            ]
        
        # Dynamic discovery: get all available namespaced resources including CRDs
        cmd = ['kubectl', 'api-resources', '--verbs=list', '--namespaced=true', '-o', 'name']
        success, stdout, stderr = run_command(cmd)
        
        if not success:
            logger.error(f"Failed to get api-resources: {stderr}")
            raise RuntimeError(f"Cannot discover resource types: {stderr}")
        
        # Parse and return all available resource types
        all_types = [line.strip() for line in stdout.strip().split('\n') if line.strip()]
        
        # Sort for consistent display (common types first, then alphabetically)
        priority_types = [
            'deployments', 'statefulsets', 'daemonsets',
            'services', 'ingresses',
            'persistentvolumeclaims',
            'configmaps', 'secrets',
            'horizontalpodautoscalers',
            'jobs', 'cronjobs',
            'networkpolicies',
            'serviceaccounts',
            'roles', 'rolebindings'
        ]
        
        # Start with available priority types in order
        sorted_types = []
        for ptype in priority_types:
            if ptype in all_types:
                sorted_types.append(ptype)
                all_types.remove(ptype)
        
        # Add remaining types alphabetically (including CRDs)
        sorted_types.extend(sorted(all_types))
        
        return sorted_types
    
    def export_resource_clean(self, resource_type: str, name: str, namespace: str, output_file: str, use_neat: bool = True) -> bool:
        """Export resource with optional kubectl neat cleaning"""
        # First get the resource
        cmd = ['kubectl', 'get', resource_type, name, '-o', 'yaml']
        if namespace:
            cmd.extend(['-n', namespace])
        
        success, stdout, stderr = run_command(cmd)
        if not success:
            logger.error(f"Failed to export resource: {stderr}")
            return False
        
        # Apply neat if available and requested
        if use_neat and self.neat_available:
            try:
                # Use subprocess to pipe kubectl get output to kubectl neat
                get_cmd = ['kubectl', 'get', resource_type, name, '-o', 'yaml']
                if namespace:
                    get_cmd.extend(['-n', namespace])
                
                neat_cmd = ['kubectl', 'neat']
                
                # Create the pipeline: kubectl get | kubectl neat
                get_process = subprocess.Popen(get_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                neat_process = subprocess.Popen(neat_cmd, stdin=get_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                get_process.stdout.close()  # Allow get_process to receive a SIGPIPE if neat_process exits.
                
                stdout, stderr = neat_process.communicate()
                
                if neat_process.returncode != 0:
                    logger.warning(f"kubectl neat failed, using original output: {stderr}")
                    # Fall back to original output if neat fails
                    success, stdout, stderr = run_command(cmd)
                    if not success:
                        return False
                        
            except Exception as e:
                logger.warning(f"kubectl neat execution failed, using original output: {e}")
                # Fall back to original output
                success, stdout, stderr = run_command(cmd)
                if not success:
                    return False
        
        try:
            # Always parse YAML for basic cleaning
            resource_data = yaml.safe_load(stdout)
            
            # Basic cleaning - remove cluster-specific fields
            self._clean_resource_data(resource_data)
            
            # Convert back to YAML
            stdout = yaml.dump(resource_data, default_flow_style=False, allow_unicode=True)
            
            with open(output_file, 'w') as f:
                f.write(stdout)
            return True
        except Exception as e:
            logger.error(f"Failed to write resource to file: {e}")
            return False
    
    def _clean_resource_data(self, resource_data: Dict) -> None:
        """Clean cluster-specific fields"""
        # Remove metadata fields that are cluster-specific
        if 'metadata' in resource_data:
            metadata = resource_data['metadata']
            # Remove cluster-specific metadata
            metadata.pop('resourceVersion', None)
            metadata.pop('uid', None)
            metadata.pop('selfLink', None)
            metadata.pop('generation', None)
            metadata.pop('creationTimestamp', None)
            metadata.pop('managedFields', None)
        
        # Remove status section completely
        resource_data.pop('status', None)
        
        # Clean spec fields based on resource kind
        kind = resource_data.get('kind', '').lower()
        
        if kind == 'service' and 'spec' in resource_data:
            spec = resource_data['spec']
            # Remove cluster IP fields
            spec.pop('clusterIP', None)
            spec.pop('clusterIPs', None)
            # Remove nodePort for NodePort services  
            if 'ports' in spec:
                for port in spec['ports']:
                    port.pop('nodePort', None)
        
        elif kind == 'persistentvolume' and 'spec' in resource_data:
            # Remove PV specific cluster fields
            spec = resource_data['spec']
            spec.pop('claimRef', None)
        
        elif kind == 'persistentvolumeclaim' and 'spec' in resource_data:
            # Remove PVC volume name
            spec = resource_data['spec']
            spec.pop('volumeName', None)


class ResourceSelector:
    """Interactive resource selection interface"""
    
    def __init__(self, kubectl_manager):
        self.show_colors = get_env_var('COLOR_OUTPUT', True, bool)
        self.interactive = get_interactive(__name__, 'k8s-export')
        self.kubectl = kubectl_manager
    
    def _create_k8s_resource(self, raw_data: Dict) -> Optional[K8sResource]:
        """Create K8sResource from raw Kubernetes resource data"""
        try:
            metadata = raw_data.get('metadata', {})
            return K8sResource(
                kind=raw_data.get('kind', 'Unknown'),
                name=metadata.get('name', 'unknown'),
                namespace=metadata.get('namespace', 'default'),
                labels=metadata.get('labels', {})
            )
        except Exception as e:
            logger.error(f"Failed to create K8sResource: {e}")
            return None
    
    def _should_include_resource(self, resource: K8sResource, exclude_resources: List[str]) -> bool:
        """Check if resource should be included in export (filter out default/system resources)"""
        if not exclude_resources:
            return True
        
        # Check resource name against exclude patterns
        for exclude_pattern in exclude_resources:
            if exclude_pattern.lower() in resource.name.lower():
                logger.debug(f"Excluding resource {resource.kind}/{resource.name} (matches pattern: {exclude_pattern})")
                return False
        
        return True
    
    def select_context(self, contexts: List[str], current: str = None) -> Optional[str]:
        """Select kubectl context"""
        if not contexts:
            self.interactive.warning_msg("No contexts available")
            return None
        
        self.interactive.info("\nAvailable Contexts:")
        for i, context in enumerate(contexts):
            current_mark = " (current)" if context == current else ""
            self.interactive.info(f"  {i + 1}. {context}{current_mark}")
        
        while True:
            try:
                choice = self.interactive.get_input("Select context (number or enter for current)", required=False).strip()
                if not choice:
                    return current
                
                idx = int(choice) - 1
                if 0 <= idx < len(contexts):
                    return contexts[idx]
                else:
                    self.interactive.warning_msg("Invalid context number")
            except ValueError:
                self.interactive.warning_msg("Please enter a valid number")
            except KeyboardInterrupt:
                return None
    
    def select_namespaces(self, namespaces: List[str]) -> List[str]:
        """Select multiple namespaces"""
        if not namespaces:
            self.interactive.warning_msg("No namespaces available")
            return []
        
        self.interactive.info("\nAvailable Namespaces:")
        for i, ns in enumerate(namespaces):
            self.interactive.info(f"  {i + 1}. {ns}")
        
        selected = set()
        
        while True:
            self.interactive.info("\nCommands:")
            self.interactive.info("  - Number: Toggle namespace selection")
            self.interactive.info("  - Range (1-5): Select range of namespaces") 
            self.interactive.info("  - Multiple (1,3,5): Select multiple namespaces")
            self.interactive.info("  - 'all': Select all namespaces")
            self.interactive.info("  - 'clear': Clear all selections")
            self.interactive.info("  - 'done': Finish selection")
            
            if selected:
                selected_names = [namespaces[i] for i in selected]
                self.interactive.info(f"\nSelected namespaces: {', '.join(selected_names)}")
            
            try:
                choice = self.interactive.get_input("Select namespaces").strip().lower()
                
                if choice == 'done':
                    break
                elif choice == 'all':
                    selected.update(range(len(namespaces)))
                elif choice == 'clear':
                    selected.clear()
                elif '-' in choice:
                    try:
                        start, end = map(int, choice.split('-'))
                        selected.update(range(start - 1, end))
                    except ValueError:
                        self.interactive.warning_msg("Invalid range format")
                elif ',' in choice:
                    try:
                        indices = [int(x.strip()) - 1 for x in choice.split(',')]
                        for idx in indices:
                            if 0 <= idx < len(namespaces):
                                if idx in selected:
                                    selected.remove(idx)
                                else:
                                    selected.add(idx)
                    except ValueError:
                        self.interactive.warning_msg("Invalid selection format")
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(namespaces):
                            if idx in selected:
                                selected.remove(idx)
                            else:
                                selected.add(idx)
                        else:
                            self.interactive.warning_msg("Invalid namespace number")
                    except ValueError:
                        self.interactive.warning_msg("Invalid input")
            except KeyboardInterrupt:
                return []
        
        return [namespaces[i] for i in selected]
    
    def select_resource_types(self, available_types: List[str], namespaces: List[str], exclude_resources: List[str]) -> List[str]:
        """Select resource types to export with resource count display"""
        
        # Get resource counts for each type across all selected namespaces with loading spinner
        def count_resources():
            resource_counts = {}
            for i, resource_type in enumerate(available_types):
                # Update spinner message to show progress
                current_spinner_msg = f"Counting {resource_type} resources... ({i+1}/{len(available_types)})"
                
                total_count = 0
                for namespace in namespaces:
                    try:
                        resources = self.kubectl.get_resources_by_type(resource_type, namespace)
                        logger.debug(f"Found {len(resources)} raw {resource_type} resources in {namespace}")
                        
                        # Filter out excluded resources
                        filtered_count = 0
                        for resource in resources:
                            k8s_resource = self._create_k8s_resource(resource)
                            if k8s_resource and self._should_include_resource(k8s_resource, exclude_resources):
                                filtered_count += 1
                        
                        total_count += filtered_count
                        logger.debug(f"After filtering: {filtered_count} {resource_type} resources in {namespace}")
                        
                    except Exception as e:
                        logger.debug(f"Failed to get {resource_type} resources from {namespace}: {e}")
                        continue
                resource_counts[resource_type] = total_count
                if total_count > 0:
                    logger.debug(f"Total {resource_type}: {total_count} resources across all namespaces")
            return resource_counts
        
        # Execute resource counting with loading spinner
        self.interactive.info(f"\nScanning {len(available_types)} resource types across {len(namespaces)} namespaces...")
        resource_counts = self.interactive.with_loading(
            count_resources, 
            f"Counting resources across {len(namespaces)} namespaces"
        )
        
        # Filter out resource types with 0 resources
        non_empty_types = [(rt, resource_counts[rt]) for rt in available_types if resource_counts.get(rt, 0) > 0]
        empty_types = [(rt, resource_counts[rt]) for rt in available_types if resource_counts.get(rt, 0) == 0]
        
        # Show non-empty types first, then empty ones
        display_types = []
        display_counts = {}
        
        if non_empty_types:
            self.interactive.info(f"\nResource Types with Resources ({len(non_empty_types)} types):")
            for i, (resource_type, count) in enumerate(non_empty_types):
                display_types.append(resource_type)
                display_counts[resource_type] = count
                self.interactive.info(f"  {len(display_types)}. {resource_type} ({count} resources)")
        
        if empty_types and len(empty_types) <= 10:  # Only show first 10 empty types to avoid clutter
            self.interactive.info(f"\nEmpty Resource Types ({len(empty_types)} types):")
            for resource_type, count in empty_types:
                display_types.append(resource_type)
                display_counts[resource_type] = count
                self.interactive.info(f"  {len(display_types)}. {resource_type} (0 resources)")
        elif empty_types:
            self.interactive.info(f"\nNote: {len(empty_types)} additional resource types have no resources")
            # Add empty types to available list but don't display all of them
            for resource_type, count in empty_types:
                display_types.append(resource_type)
                display_counts[resource_type] = count
        
        available_types = display_types
        resource_counts = display_counts
        
        selected = set()
        
        while True:
            self.interactive.info("\nCommands:")
            self.interactive.info("  - Number: Toggle resource type selection")
            self.interactive.info("  - Range (1-5): Select range of types") 
            self.interactive.info("  - Multiple (1,3,5): Select multiple types")
            self.interactive.info("  - 'all': Select all types")
            self.interactive.info("  - 'non-empty': Select only types with resources")
            self.interactive.info("  - 'clear': Clear all selections")
            self.interactive.info("  - 'done': Finish selection")
            
            if selected:
                selected_types = [available_types[i] for i in selected]
                total_resources = sum(resource_counts.get(available_types[i], 0) for i in selected)
                self.interactive.info(f"\nSelected types: {', '.join(selected_types)}")
                self.interactive.info(f"Total resources in selected types: {total_resources}")
            
            try:
                choice = self.interactive.get_input("Select resource types").strip().lower()
                
                if choice == 'done':
                    break
                elif choice == 'all':
                    selected.update(range(len(available_types)))
                elif choice == 'non-empty':
                    selected.update(i for i, resource_type in enumerate(available_types) 
                                  if resource_counts.get(resource_type, 0) > 0)
                elif choice == 'clear':
                    selected.clear()
                elif '-' in choice:
                    try:
                        start, end = map(int, choice.split('-'))
                        selected.update(range(start - 1, end))
                    except ValueError:
                        self.interactive.warning_msg("Invalid range format")
                elif ',' in choice:
                    try:
                        indices = [int(x.strip()) - 1 for x in choice.split(',')]
                        for idx in indices:
                            if 0 <= idx < len(available_types):
                                if idx in selected:
                                    selected.remove(idx)
                                else:
                                    selected.add(idx)
                    except ValueError:
                        self.interactive.warning_msg("Invalid selection format")
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(available_types):
                            if idx in selected:
                                selected.remove(idx)
                            else:
                                selected.add(idx)
                        else:
                            self.interactive.warning_msg("Invalid resource type number")
                    except ValueError:
                        self.interactive.warning_msg("Invalid input")
            except KeyboardInterrupt:
                return []
        
        return [available_types[i] for i in selected]


class K8sExportTool:
    """Kubernetes Resource Export Tool with OpsKit integration"""
    
    def __init__(self, 
                 output_dir=None,
                 use_neat=None,
                 temp_cleanup=None,
                 show_progress=None,
                 show_colors=None,
                 group_by_type=None,
                 exclude_resources=None,
                 exclude_defaults=None,
                 dynamic_resources=None):
        # Tool metadata
        self.tool_name = "Kubernetes Resource Export Tool"
        self.description = "Export Kubernetes resources from specified namespaces with optional kubectl neat cleaning"
        
        # Configuration with parameter > environment variable > default priority
        self.temp_dir_cleanup = self._resolve_config(temp_cleanup, 'TEMP_DIR_CLEANUP', True, bool)
        self.show_progress = self._resolve_config(show_progress, 'SHOW_PROGRESS', True, bool)
        self.use_neat_default = self._resolve_config(use_neat, 'USE_NEAT_DEFAULT', True, bool)
        self.group_by_resource_type = self._resolve_config(group_by_type, 'GROUP_BY_RESOURCE_TYPE', True, bool)
        self.show_colors = self._resolve_config(show_colors, 'COLOR_OUTPUT', True, bool)
        
        # Get output directory with priority: parameter > environment > None
        self.custom_output_dir = self._resolve_config(output_dir, 'K8S_EXPORT_OUTPUT_DIR', None)
        
        # Resource filtering configuration
        if exclude_resources is not None:
            # Parameter provided - use it directly
            if exclude_resources:
                self.exclude_resources = [r.strip() for r in exclude_resources.split(',') if r.strip()]
            else:
                self.exclude_resources = []
        elif exclude_defaults is not None:
            # exclude_defaults flag provided
            if exclude_defaults:
                # Keep default exclusion patterns
                exclude_resources_str = get_env_var('EXCLUDE_DEFAULT_RESOURCES', 'kube-root-ca.crt,default-token,kubernetes.io/service-account-token')
                self.exclude_resources = [r.strip() for r in exclude_resources_str.split(',') if r.strip()]
            else:
                # Clear exclusion patterns
                self.exclude_resources = []
        else:
            # No parameters, use environment variable or default
            exclude_resources_str = get_env_var('EXCLUDE_DEFAULT_RESOURCES', 'kube-root-ca.crt,default-token,kubernetes.io/service-account-token')
            self.exclude_resources = [r.strip() for r in exclude_resources_str.split(',') if r.strip()]
        
        # Resource types discovery configuration - default to False for faster startup (common types only)
        self.use_dynamic_resource_types = self._resolve_config(dynamic_resources, 'USE_DYNAMIC_RESOURCE_TYPES', False, bool)
        
        # Initialize components
        self.kubectl = KubectlManager()
        self.selector = ResourceSelector(self.kubectl)
        
        # Get resource types based on configuration
        self.resource_types = self.kubectl.get_available_resource_types(self.use_dynamic_resource_types)
        
        if self.use_dynamic_resource_types:
            print(f"🔍 已发现 {len(self.resource_types)} 种资源类型（包含 CRD）")
        else:
            print(f"📋 使用常见资源类型，共 {len(self.resource_types)} 种")
        
        print(f"🚀 启动 {self.tool_name}")
    
    def _resolve_config(self, param_value, env_var_name, default_value, value_type=None):
        """Resolve configuration with priority: parameter > environment variable > default"""
        if param_value is not None:
            # Parameter provided - use it directly
            return param_value
        
        # No parameter, check environment variable
        return get_env_var(env_var_name, default_value, value_type)
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        print("🔍 Checking dependencies for k8s-export...")
        
        # Check kubectl
        if self.kubectl.check_kubectl():
            print("✅ kubectl 可用")
        else:
            interactive.failure("kubectl is required but not found")
            interactive.info("Please install kubectl: https://kubernetes.io/docs/tasks/tools/")
            return False
        
        # Check krew (optional but recommended)
        if self.kubectl.check_krew():
            plugins = self.kubectl.check_plugins()
            print("✅ krew 可用")
            # Report plugin status
            for plugin_name, available in plugins.items():
                if available:
                    interactive.success(f"kubectl {plugin_name} plugin is available")
                else:
                    interactive.warning_msg(f"kubectl {plugin_name} plugin is not available")
        else:
            interactive.warning_msg("krew is not installed - some features may be limited")
            interactive.info("Install krew for enhanced functionality: https://krew.sigs.k8s.io/docs/user-guide/setup/install/")
        
        # Verify cluster access
        contexts = self.kubectl.get_contexts()
        if not contexts:
            interactive.failure("No kubectl contexts found")
            interactive.info("Please configure kubectl with at least one cluster context")
            return False
        
        print("✅ All dependencies satisfied for k8s-export")
        return True
    
    def select_export_settings(self) -> Dict:
        """Select export settings"""
        settings = {}
        
        # Select context
        contexts = self.kubectl.get_contexts()
        current_context = self.kubectl.get_current_context()
        
        interactive.section("Cluster Selection")
        selected_context = self.selector.select_context(contexts, current_context)
        if not selected_context:
            return None
        
        settings['context'] = selected_context
        
        # Switch to selected context
        if selected_context != current_context:
            if not self.kubectl.switch_context(selected_context):
                return None
        
        # Select namespaces
        interactive.section("Namespace Selection")
        namespaces = self.kubectl.get_namespaces()
        selected_namespaces = self.selector.select_namespaces(namespaces)
        if not selected_namespaces:
            interactive.warning_msg("No namespaces selected")
            return None
        
        settings['namespaces'] = selected_namespaces
        
        # Select resource types
        interactive.section("Resource Type Selection")
        selected_types = self.selector.select_resource_types(self.resource_types, selected_namespaces, self.exclude_resources)
        if not selected_types:
            interactive.warning_msg("No resource types selected")
            return None
        
        settings['resource_types'] = selected_types
        
        # Ask about kubectl neat usage
        if self.kubectl.neat_available:
            use_neat = interactive.confirm("Use kubectl neat to clean exported resources?", default=True)
            settings['use_neat'] = use_neat
        else:
            settings['use_neat'] = False
            interactive.warning_msg("kubectl neat not available, using basic cleaning")
        
        return settings
    
    def discover_resources(self, namespaces: List[str], resource_types: List[str]) -> Dict[str, List[K8sResource]]:
        """Discover resources in specified namespaces"""
        def discover_all_resources():
            all_resources = {}
            
            for namespace in namespaces:
                namespace_resources = []
                
                for resource_type in resource_types:
                    raw_resources = self.kubectl.get_resources_by_type(resource_type, namespace)
                    for raw_resource in raw_resources:
                        resource = self.selector._create_k8s_resource(raw_resource)
                        if resource and self.selector._should_include_resource(resource, self.exclude_resources):
                            namespace_resources.append(resource)
                
                if namespace_resources:
                    all_resources[namespace] = namespace_resources
            
            return all_resources
        
        # Execute resource discovery with loading spinner
        interactive.info(f"正在发现 {len(namespaces)} 个命名空间中的资源...")
        all_resources = interactive.with_loading(
            discover_all_resources,
            f"发现 {len(namespaces)} 个命名空间中的资源"
        )
        
        # Display summary after discovery
        for namespace, ns_resources in all_resources.items():
            interactive.info(f"  📦 {namespace}: {len(ns_resources)} 个资源")
        
        return all_resources
    
    
    def export_resources(self, resources: Dict[str, List[K8sResource]], use_neat: bool, context: str) -> Dict[str, int]:
        """Export resources to files"""
        interactive.operation_start("资源导出")
        
        # Create output directory structure
        if self.custom_output_dir:
            # User specified custom directory
            export_base_dir = self.custom_output_dir
        else:
            # Default: create k8s-export-YYYYMMDDHHMM in user's working directory
            # Use OPSKIT_WORKING_DIR if available (when called via opskit), otherwise current directory
            user_working_dir = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
            # Format current time to YYYYMMDDHHMM (precise to minute)
            from datetime import datetime
            date_time_str = datetime.now().strftime("%Y%m%d%H%M")
            export_base_dir = os.path.join(user_working_dir, f"k8s-export-{date_time_str}")
        
        os.makedirs(export_base_dir, exist_ok=True)
        
        export_stats = {}
        total_exported = 0
        
        for namespace, ns_resources in resources.items():
            namespace_dir = os.path.join(export_base_dir, namespace)
            os.makedirs(namespace_dir, exist_ok=True)
            
            exported_count = 0
            
            for resource in ns_resources:
                # Determine file path based on resource type grouping configuration
                if self.group_by_resource_type:
                    # Create resource type subdirectory
                    resource_type_dir = os.path.join(namespace_dir, resource.kind.lower())
                    os.makedirs(resource_type_dir, exist_ok=True)
                    filename = f"{resource.name}.yaml"
                    filepath = os.path.join(resource_type_dir, filename)
                else:
                    # Use flat structure with resource type prefix
                    filename = f"{resource.kind.lower()}_{resource.name}.yaml"
                    filepath = os.path.join(namespace_dir, filename)
                
                if self.kubectl.export_resource_clean(
                    resource.kind.lower(), 
                    resource.name, 
                    resource.namespace, 
                    filepath,
                    use_neat
                ):
                    exported_count += 1
                    total_exported += 1
                    interactive.success(f"{resource.full_identifier}")
                else:
                    interactive.failure(f"Failed to export {resource.full_identifier}")
            
            export_stats[namespace] = exported_count
            if exported_count > 0:
                interactive.info(f"📂 Namespace {namespace}: {exported_count} resources exported to {namespace_dir}")
        
        interactive.subsection("Export Summary")
        interactive.info(f"  Total resources exported: {total_exported}")
        interactive.info(f"  Export directory: {export_base_dir}")
        interactive.info(f"  kubectl neat used: {'Yes' if use_neat else 'No'}")
        
        # Create export summary file
        summary = {
            'context': context,
            'timestamp': timestamp(),
            'total_resources': total_exported,
            'namespaces': export_stats,
            'neat_used': use_neat,
            'export_directory': export_base_dir
        }
        
        summary_file = os.path.join(export_base_dir, 'export_summary.yaml')
        with open(summary_file, 'w') as f:
            yaml.dump(summary, f, default_flow_style=False)
        
        interactive.info(f"  📄 Summary saved to: {summary_file}")
        
        return export_stats
    
    def run(self):
        """Main tool execution"""
        try:
            interactive.section(self.tool_name)
            
            # Check dependencies
            if not self.check_dependencies():
                sys.exit(1)
            
            # Select export settings
            settings = self.select_export_settings()
            if not settings:
                logger.error("Export settings selection cancelled")
                return
            
            # Discover resources
            interactive.section("Resource Discovery")
            resources = self.discover_resources(settings['namespaces'], settings['resource_types'])
            
            if not resources:
                interactive.warning_msg("No resources found to export")
                return
            
            # Show discovery summary
            total_resources = sum(len(ns_resources) for ns_resources in resources.values())
            interactive.subsection("发现摘要")
            interactive.info(f"  发现资源总数: {total_resources}")
            interactive.info(f"  命名空间数量: {len(resources)}")
            for namespace, ns_resources in resources.items():
                interactive.info(f"    {namespace}: {len(ns_resources)} 个资源")
            
            # Confirm export
            proceed = interactive.confirm("是否继续导出?", default=True)
            if not proceed:
                interactive.user_cancelled("导出")
                return
            
            # Export resources
            export_stats = self.export_resources(resources, settings['use_neat'], settings['context'])
            
            # Final success message
            total_exported = sum(export_stats.values())
            if total_exported > 0:
                print("✅ 资源导出完成")
                interactive.success("导出成功！")
                interactive.info(f"  从 {len(export_stats)} 个命名空间导出 {total_exported} 个资源")
            else:
                print("❌ 未导出任何资源")
                interactive.failure("未导出任何资源")
            
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            interactive.user_cancelled()
        except Exception as e:
            print(f"\n❌ 程序错误: {e}")
            interactive.failure(f"程序错误: {e}")
            sys.exit(1)


@click.command()
@click.option('--output-dir', '-o', 
              help='Output directory for exported resources (default: ./k8s-export-YYYY-MM-DD)')
@click.option('--neat/--no-neat', default=None,
              help='Enable/disable kubectl neat cleaning')
@click.option('--cleanup/--no-cleanup', default=None,
              help='Enable/disable cleanup of temporary files after export')
@click.option('--progress/--no-progress', default=None,
              help='Enable/disable progress display during operations')
@click.option('--color/--no-color', default=None,
              help='Enable/disable colored output in terminal')
@click.option('--group-by-type/--flat-structure', default=None,
              help='Group exported resources by type in folders vs flat structure')
@click.option('--exclude-resources', metavar='PATTERNS',
              help='Comma-separated list of resource name patterns to exclude from export')
@click.option('--exclude-defaults/--include-defaults', default=None,
              help='Exclude/include default Kubernetes system resources')
@click.option('--dynamic-resources/--common-resources-only', default=None,
              help='Use dynamic discovery (all resources including CRDs) vs common resources only')
def main(output_dir, neat, cleanup, progress, color, group_by_type, exclude_resources, exclude_defaults, dynamic_resources):
    """Export Kubernetes resources from specified namespaces with optional kubectl neat cleaning."""
    
    # Create tool instance with parameters passed directly
    tool = K8sExportTool(
        output_dir=output_dir,
        use_neat=neat,
        temp_cleanup=cleanup,
        show_progress=progress,
        show_colors=color,
        group_by_type=group_by_type,
        exclude_resources=exclude_resources,
        exclude_defaults=exclude_defaults,
        dynamic_resources=dynamic_resources
    )
    tool.run()


if __name__ == '__main__':
    main()
