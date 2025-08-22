#!/usr/bin/env python3
"""
Kubernetes Resource Copy Tool - OpsKit Version
Copy Kubernetes resources between clusters and namespaces with automatic relationship detection
"""

import os
import sys
import json
import yaml
import subprocess
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
import tempfile
import logging
from dataclasses import dataclass


class _LocalInteractive:
    """Minimal interactive helper following mysql-sync style (print/input)."""
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
            print("输入不能为空，请重试")

# Global interactive instance for module-level usage
interactive = _LocalInteractive()

# 获取 OpsKit 环境变量
OPSKIT_TOOL_TEMP_DIR = os.environ.get('OPSKIT_TOOL_TEMP_DIR', os.path.join(os.getcwd(), '.k8s-resource-copy-temp'))
OPSKIT_BASE_PATH = os.environ.get('OPSKIT_BASE_PATH', os.path.expanduser('~/.opskit'))
OPSKIT_WORKING_DIR = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
TOOL_NAME = os.environ.get('TOOL_NAME', 'k8s-resource-copy')
TOOL_VERSION = os.environ.get('TOOL_VERSION', '1.0.0')

# 创建临时目录
os.makedirs(OPSKIT_TOOL_TEMP_DIR, exist_ok=True)

# Import OpsKit utils (保留基础工具函数)
try:
    sys.path.insert(0, os.path.join(OPSKIT_BASE_PATH, 'common/python'))
    from utils import run_command, get_env_var
except ImportError:
    print("⚠️  OpsKit utils 不可用，使用简单实现")
    # 简单的命令执行函数
    def run_command(cmd: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """简单的命令执行函数"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0, result.stdout, result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False, "", str(e)

    # 简单的环境变量获取函数
    def get_env_var(name: str, default=None, var_type=str):
        """获取环境变量"""
        value = os.environ.get(name, default)
        if var_type == bool and isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif var_type == int and isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return value

# Third-party imports with error handling
try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init()
except ImportError as e:
    print(f"❌ 缺少必需依赖: {e}")
    print("请确保所有依赖都已安装")
    sys.exit(1)

# Minimal logger setup for parity with mysql-sync style
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class K8sResource:
    """Kubernetes resource representation"""
    kind: str
    name: str
    namespace: str
    labels: Dict[str, str]
    raw_data: Dict
    relationships: List['K8sResource'] = None
    
    def __post_init__(self):
        if self.relationships is None:
            self.relationships = []
    
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
        try:
            result = subprocess.run(['kubectl', 'version', '--client'], 
                                 capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.kubectl_path = 'kubectl'
                print("✅ kubectl 可用")
                return True
            else:
                print("❌ kubectl 未在 PATH 中找到")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ kubectl 未在 PATH 中找到")
            return False
    
    def check_krew(self) -> bool:
        """Check if krew is available"""
        success, stdout, stderr = run_command(['kubectl', 'krew', 'version'])
        if success:
            self.krew_available = True
            print("✅ krew 可用")
            return True
        else:
            print("⚠️  krew 不可用")
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
    
    def install_plugin(self, plugin_name: str) -> bool:
        """Install kubectl plugin via krew"""
        if not self.krew_available:
            logger.error("❌ krew is required to install plugins")
            return False
        
        logger.info(f"Installing kubectl {plugin_name} plugin...")
        success, stdout, stderr = run_command(['kubectl', 'krew', 'install', plugin_name])
        
        if success:
            logger.info(f"✅ Successfully installed kubectl {plugin_name}")
            return True
        else:
            logger.error(f"❌ Failed to install kubectl {plugin_name}: {stderr}")
            return False
    
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
            print(f"✅ 已切换上下文: {context}")
            return True
        else:
            print(f"❌ 切换上下文失败: {stderr}")
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
    
    def get_resource(self, resource_type: str, name: str, namespace: str = None) -> Optional[Dict]:
        """Get Kubernetes resource as dictionary"""
        cmd = ['kubectl', 'get', resource_type, name, '-o', 'json']
        if namespace:
            cmd.extend(['-n', namespace])
        
        success, stdout, stderr = run_command(cmd)
        if success:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                print(f"❌ 解析资源 JSON 失败: {resource_type}/{name}")
        return None
    
    def get_resources_by_type(self, resource_type: str, namespace: str = None) -> List[Dict]:
        """Get all resources of specified type"""
        cmd = ['kubectl', 'get', resource_type, '-o', 'json']
        if namespace:
            cmd.extend(['-n', namespace])
        
        success, stdout, stderr = run_command(cmd)
        if success:
            try:
                data = json.loads(stdout)
                return data.get('items', [])
            except json.JSONDecodeError:
                print(f"❌ 解析 JSON 失败: {resource_type}")
        return []
    
    def export_resource_clean(self, resource_type: str, name: str, namespace: str, output_file: str, target_namespace: str = None) -> bool:
        """Export resource with kubectl neat to remove cluster-specific fields"""
        # First get the resource
        cmd = ['kubectl', 'get', resource_type, name, '-o', 'yaml']
        if namespace:
            cmd.extend(['-n', namespace])
        
        success, stdout, stderr = run_command(cmd)
        if not success:
            print(f"❌ 导出资源失败: {stderr}")
            return False
        
        # Apply neat if available
        if self.neat_available:
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
                    print(f"⚠️  kubectl neat 失败，使用原始输出: {stderr}")
                    # Fall back to original output if neat fails
                    success, stdout, stderr = run_command(cmd)
                    if not success:
                        return False
                        
            except Exception as e:
                print(f"⚠️  kubectl neat 执行失败，使用原始输出: {e}")
                # Fall back to original output
                success, stdout, stderr = run_command(cmd)
                if not success:
                    return False
        
        try:
            # Always parse YAML for cleaning and namespace modification
            resource_data = yaml.safe_load(stdout)
            
            # Clean cluster-specific fields
            self._clean_resource_data(resource_data)
            
            # Update namespace in metadata if target namespace is different
            if target_namespace and target_namespace != namespace:
                if 'metadata' in resource_data:
                    resource_data['metadata']['namespace'] = target_namespace
            
            # Convert back to YAML
            stdout = yaml.dump(resource_data, default_flow_style=False, allow_unicode=True)
            
            with open(output_file, 'w') as f:
                f.write(stdout)
            return True
        except Exception as e:
            print(f"❌ 写入资源到文件失败: {e}")
            return False
    
    def _clean_resource_data(self, resource_data: Dict) -> None:
        """Clean additional cluster-specific fields that kubectl neat might miss"""
        # Get configuration for field removal
        remove_cluster_ip = get_env_var('REMOVE_CLUSTER_IP', True, bool)
        remove_node_port = get_env_var('REMOVE_NODE_PORT', True, bool)
        
        # Clean spec fields based on resource kind
        kind = resource_data.get('kind', '').lower()
        
        if kind == 'service' and 'spec' in resource_data:
            spec = resource_data['spec']
            
            # Remove cluster IP fields (kubectl neat doesn't always remove these)
            if remove_cluster_ip:
                spec.pop('clusterIP', None)
                spec.pop('clusterIPs', None)
            
            # Remove nodePort if configured
            if remove_node_port and 'ports' in spec:
                for port in spec['ports']:
                    port.pop('nodePort', None)
        
        elif kind in ['deployment', 'statefulset', 'daemonset'] and 'spec' in resource_data:
            # Clean deployment-like resources - let target cluster decide replicas
            spec = resource_data['spec']
            # Only remove replicas if it's not explicitly set (preserve user intention)
            # spec.pop('replicas', None)  # Commented out - let user decide
            pass
    
    def apply_resource(self, file_path: str, namespace: str = None, dry_run: bool = True) -> bool:
        """Apply resource from file"""
        cmd = ['kubectl', 'apply', '-f', file_path]
        # Don't specify namespace since it's already in the YAML file
        # if namespace:
        #     cmd.extend(['-n', namespace])
        if dry_run:
            cmd.append('--dry-run=client')
        
        success, stdout, stderr = run_command(cmd)
        if success:
            print("✅ 资源应用成功")
            return True
        else:
            print(f"❌ 应用资源失败: {stderr}")
            return False


class ResourceDiscoverer:
    """Discovers Kubernetes resources and their relationships"""
    
    def __init__(self, kubectl_manager: KubectlManager):
        self.kubectl = kubectl_manager
        self.relationship_labels = get_env_var('DEFAULT_RELATIONSHIP_LABELS', 'app,service,component,name').split(',')
        self.auto_discover = get_env_var('AUTO_DISCOVER_RELATIONSHIPS', True, bool)
        self.include_secrets = get_env_var('INCLUDE_SECRETS', True, bool)
        self.include_configmaps = get_env_var('INCLUDE_CONFIGMAPS', True, bool)
    
    def discover_resources(self, resource_types: List[str], namespace: str) -> List[K8sResource]:
        """Discover resources in namespace"""
        resources = []
        
        for resource_type in resource_types:
            raw_resources = self.kubectl.get_resources_by_type(resource_type, namespace)
            for raw_resource in raw_resources:
                resource = self._create_k8s_resource(raw_resource)
                if resource:
                    resources.append(resource)
        
        # Discover relationships if enabled
        if self.auto_discover:
            self._discover_relationships(resources, namespace)
        
        return resources
    
    def _create_k8s_resource(self, raw_data: Dict) -> Optional[K8sResource]:
        """Create K8sResource from raw Kubernetes resource data"""
        try:
            metadata = raw_data.get('metadata', {})
            return K8sResource(
                kind=raw_data.get('kind', 'Unknown'),
                name=metadata.get('name', 'unknown'),
                namespace=metadata.get('namespace', 'default'),
                labels=metadata.get('labels', {}),
                raw_data=raw_data
            )
        except Exception as e:
            logger.error(f"Failed to create K8sResource: {e}")
            return None
    
    def _discover_relationships(self, resources: List[K8sResource], namespace: str):
        """Discover relationships between resources"""
        # Create lookup maps
        resource_map = {r.identifier: r for r in resources}
        
        for resource in resources:
            self._find_related_resources(resource, resource_map, namespace)
    
    def _find_related_resources(self, resource: K8sResource, resource_map: Dict[str, K8sResource], namespace: str):
        """Find resources related to the given resource"""
        # Label-based relationships
        for label_key in self.relationship_labels:
            if label_key in resource.labels:
                label_value = resource.labels[label_key]
                self._find_by_label(resource, resource_map, label_key, label_value)
        
        # Specific resource type relationships
        if resource.kind.lower() == 'deployment':
            self._find_deployment_relationships(resource, resource_map, namespace)
        elif resource.kind.lower() == 'service':
            self._find_service_relationships(resource, resource_map, namespace)
        elif resource.kind.lower() == 'ingress':
            self._find_ingress_relationships(resource, resource_map, namespace)
    
    def _find_by_label(self, resource: K8sResource, resource_map: Dict[str, K8sResource], 
                      label_key: str, label_value: str):
        """Find resources with matching label"""
        for other_resource in resource_map.values():
            if (other_resource != resource and 
                label_key in other_resource.labels and 
                other_resource.labels[label_key] == label_value):
                if other_resource not in resource.relationships:
                    resource.relationships.append(other_resource)
    
    def _find_deployment_relationships(self, deployment: K8sResource, resource_map: Dict[str, K8sResource], namespace: str):
        """Find resources related to deployment"""
        # Look for services with matching selector
        app_label = deployment.labels.get('app', deployment.name)
        
        # Find matching services
        for resource in resource_map.values():
            if resource.kind.lower() == 'service':
                service_selector = resource.raw_data.get('spec', {}).get('selector', {})
                if service_selector.get('app') == app_label:
                    if resource not in deployment.relationships:
                        deployment.relationships.append(resource)
        
        # Find PVCs mentioned in volumes
        spec = deployment.raw_data.get('spec', {})
        template = spec.get('template', {})
        volumes = template.get('spec', {}).get('volumes', [])
        
        for volume in volumes:
            if 'persistentVolumeClaim' in volume:
                pvc_name = volume['persistentVolumeClaim']['claimName']
                pvc_resource = resource_map.get(f'persistentvolumeclaim/{pvc_name}')
                if pvc_resource and pvc_resource not in deployment.relationships:
                    deployment.relationships.append(pvc_resource)
    
    def _find_service_relationships(self, service: K8sResource, resource_map: Dict[str, K8sResource], namespace: str):
        """Find resources related to service"""
        selector = service.raw_data.get('spec', {}).get('selector', {})
        
        # Find deployments/statefulsets with matching labels
        for resource in resource_map.values():
            if resource.kind.lower() in ['deployment', 'statefulset']:
                if self._labels_match_selector(resource.labels, selector):
                    if resource not in service.relationships:
                        service.relationships.append(resource)
    
    def _find_ingress_relationships(self, ingress: K8sResource, resource_map: Dict[str, K8sResource], namespace: str):
        """Find resources related to ingress"""
        spec = ingress.raw_data.get('spec', {})
        
        # Find services mentioned in rules
        rules = spec.get('rules', [])
        for rule in rules:
            http = rule.get('http', {})
            paths = http.get('paths', [])
            for path in paths:
                backend = path.get('backend', {})
                service_name = backend.get('service', {}).get('name')
                if service_name:
                    service_resource = resource_map.get(f'service/{service_name}')
                    if service_resource and service_resource not in ingress.relationships:
                        ingress.relationships.append(service_resource)
        
        # Find TLS secrets
        tls_configs = spec.get('tls', [])
        for tls_config in tls_configs:
            secret_name = tls_config.get('secretName')
            if secret_name:
                secret_resource = resource_map.get(f'secret/{secret_name}')
                if secret_resource and secret_resource not in ingress.relationships:
                    ingress.relationships.append(secret_resource)
    
    def _labels_match_selector(self, labels: Dict[str, str], selector: Dict[str, str]) -> bool:
        """Check if labels match selector"""
        for key, value in selector.items():
            if labels.get(key) != value:
                return False
        return True


class ResourceSelector:
    """Interactive resource selection interface"""
    
    def __init__(self):
        self.show_colors = get_env_var('COLOR_OUTPUT', True, bool)
        # Build a SimpleInteractive-like local interface using print/input
        self.interactive = _LocalInteractive()
    
    def select_resources(self, resources: List[K8sResource]) -> List[K8sResource]:
        """Interactive multi-resource selection"""
        if not resources:
            self.interactive.warning_msg("No resources found.")
            return []
        
        self.interactive.subsection("Available Resources")
        
        selected = set()
        
        while True:
            self._display_resources(resources, selected)
            
            choice = self.interactive.get_input("Select resources (number/range/all/done)").lower()
            
            if choice == 'done':
                break
            elif choice == 'all':
                selected.update(range(len(resources)))
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
                        if 0 <= idx < len(resources):
                            if idx in selected:
                                selected.remove(idx)
                            else:
                                selected.add(idx)
                except ValueError:
                    self.interactive.warning_msg("Invalid selection format")
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(resources):
                        if idx in selected:
                            selected.remove(idx)
                        else:
                            selected.add(idx)
                    else:
                        self.interactive.warning_msg("Invalid resource number")
                except ValueError:
                    self.interactive.warning_msg("Invalid input")
        
        selected_resources = [resources[i] for i in selected]
        
        # Auto-include relationships
        if selected_resources:
            auto_included = self._include_relationships(selected_resources, resources)
            if auto_included:
                self.interactive.info("Auto-included related resources:")
                for resource in auto_included:
                    self.interactive.info(f"  + {resource.full_identifier}")
                selected_resources.extend(auto_included)
        
        return selected_resources
    
    def _display_resources(self, resources: List[K8sResource], selected: Set[int]):
        """Display resources with selection status"""
        self.interactive.info("")
        for i, resource in enumerate(resources):
            status = "✓" if i in selected else " "
            relationships = f" ({len(resource.relationships)} related)" if resource.relationships else ""
            self.interactive.info(f"[{status}] {i + 1:2}. {resource.full_identifier}{relationships}")
        
        if selected:
            self.interactive.info(f"\nSelected: {len(selected)} resources")
        
        self.interactive.info("\nCommands:")
        self.interactive.info("  - Number: Toggle resource selection")
        self.interactive.info("  - Range (1-5): Select range of resources") 
        self.interactive.info("  - Multiple (1,3,5): Select multiple resources")
        self.interactive.info("  - 'all': Select all resources")
        self.interactive.info("  - 'clear': Clear all selections")
        self.interactive.info("  - 'done': Finish selection")
    
    def _include_relationships(self, selected_resources: List[K8sResource], 
                             all_resources: List[K8sResource]) -> List[K8sResource]:
        """Include related resources automatically"""
        auto_included = []
        all_resources_map = {r.identifier: r for r in all_resources}
        selected_identifiers = {r.identifier for r in selected_resources}
        
        for resource in selected_resources:
            for related in resource.relationships:
                if (related.identifier not in selected_identifiers and 
                    related not in auto_included):
                    auto_included.append(related)
                    selected_identifiers.add(related.identifier)
        
        return auto_included
    
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
                choice = self.interactive.get_input("Select context (number or enter for current)")
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
    
    def select_namespace(self, namespaces: List[str]) -> Optional[str]:
        """Select namespace"""
        if not namespaces:
            self.interactive.warning_msg("No namespaces available")
            return None
        
        self.interactive.info("\nAvailable Namespaces:")
        for i, ns in enumerate(namespaces):
            self.interactive.info(f"  {i + 1}. {ns}")
        
        while True:
            try:
                choice = self.interactive.get_input("Select namespace (number)")
                idx = int(choice) - 1
                if 0 <= idx < len(namespaces):
                    return namespaces[idx]
                else:
                    self.interactive.warning_msg("Invalid namespace number")
            except ValueError:
                self.interactive.warning_msg("Please enter a valid number")
            except KeyboardInterrupt:
                return None


class K8sResourceCopyTool:
    """Kubernetes Resource Copy Tool with OpsKit integration"""
    
    def __init__(self):
        # Tool metadata
        self.tool_name = "Kubernetes Resource Copy Tool"
        self.description = "Copy Kubernetes resources between clusters and namespaces with automatic relationship detection"
        
        # Load configuration from environment variables
        self.temp_dir_cleanup = get_env_var('TEMP_DIR_CLEANUP', True, bool)
        self.max_resources_per_batch = get_env_var('MAX_RESOURCES_PER_BATCH', 50, int)
        self.confirmation_timeout = get_env_var('CONFIRMATION_TIMEOUT', 300, int)
        self.dry_run_default = get_env_var('DRY_RUN_DEFAULT', True, bool)
        self.interactive_mode = get_env_var('INTERACTIVE_MODE', True, bool)
        self.show_progress = get_env_var('SHOW_PROGRESS', True, bool)
        
        # Get OpsKit managed temporary directory
        self.temp_dir = get_env_var('OPSKIT_TOOL_TEMP_DIR')
        if not self.temp_dir:
            print("❌ OPSKIT_TOOL_TEMP_DIR 不可用")
            sys.exit(1)
        
        # Initialize components
        self.kubectl = KubectlManager()
        self.discoverer = ResourceDiscoverer(self.kubectl)
        self.selector = ResourceSelector()
        
        # Common resource types for discovery
        self.resource_types = [
            'deployment', 'statefulset', 'daemonset',
            'service', 'ingress',
            'persistentvolumeclaim',
            'configmap', 'secret',
            'horizontalpodautoscaler'
        ]
        
        print(f"🚀 启动 {self.tool_name}")
        print(f"📁 临时目录: {self.temp_dir}")
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        print("🔍 正在检查依赖...")
        
        # Check kubectl
        if not self.kubectl.check_kubectl():
            interactive.failure("需要 kubectl，但未找到")
            interactive.info("请安装 kubectl: https://kubernetes.io/docs/tasks/tools/")
            return False
        
        # Check krew (optional but recommended)
        if self.kubectl.check_krew():
            plugins = self.kubectl.check_plugins()
            
            # Auto-install missing plugins
            for plugin_name, available in plugins.items():
                if not available:
                    print(f"🔧 正在安装缺失插件: {plugin_name}")
                    self.kubectl.install_plugin(plugin_name)
        else:
            interactive.warning_msg("krew 未安装，部分功能将受限")
            interactive.info("安装 krew 可获得更多功能: https://krew.sigs.k8s.io/docs/user-guide/setup/install/")
        
        # Verify cluster access
        contexts = self.kubectl.get_contexts()
        if not contexts:
            interactive.failure("未找到任何 kubectl 上下文")
            interactive.info("请至少配置一个集群上下文")
            return False
        
        print("✅ 依赖检查通过")
        return True
    
    def get_source_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get source cluster context and namespace"""
        contexts = self.kubectl.get_contexts()
        current_context = self.kubectl.get_current_context()
        
        interactive.section("Source Selection")
        
        # Select source context
        source_context = self.selector.select_context(contexts, current_context)
        if not source_context:
            return None, None
        
        if source_context != current_context:
            if not self.kubectl.switch_context(source_context):
                return None, None
        
        # Select source namespace
        namespaces = self.kubectl.get_namespaces()
        source_namespace = self.selector.select_namespace(namespaces)
        
        return source_context, source_namespace
    
    def get_target_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get target cluster context and namespace"""
        contexts = self.kubectl.get_contexts()
        
        interactive.section("Target Selection")
        
        # Select target context
        target_context = self.selector.select_context(contexts)
        if not target_context:
            return None, None
        
        # Switch to target context to get namespaces
        original_context = self.kubectl.get_current_context()
        if not self.kubectl.switch_context(target_context):
            return None, None
        
        # Select target namespace
        namespaces = self.kubectl.get_namespaces()
        target_namespace = self.selector.select_namespace(namespaces)
        
        # Switch back to original context
        if original_context:
            self.kubectl.switch_context(original_context)
        
        return target_context, target_namespace
    
    def discover_and_select_resources(self, namespace: str) -> List[K8sResource]:
        """Discover and select resources for copying"""
        interactive.operation_start("Resource Discovery", f"namespace: {namespace}")
        
        resources = self.discoverer.discover_resources(self.resource_types, namespace)
        
        if not resources:
            interactive.warning_msg(f"No resources found in namespace: {namespace}")
            return []
        
        print(f"🔎 发现 {len(resources)} 个资源（含依赖关系）")
        
        # Display discovery summary
        interactive.subsection("发现摘要")
        resource_counts = {}
        for resource in resources:
            kind = resource.kind.lower()
            resource_counts[kind] = resource_counts.get(kind, 0) + 1
        
        for kind, count in sorted(resource_counts.items()):
            interactive.info(f"  {kind}: {count}")
        
        return self.selector.select_resources(resources)
    
    def export_resources(self, resources: List[K8sResource], source_context: str, target_namespace: str = None) -> Dict[str, str]:
        """Export selected resources to temporary files"""
        interactive.operation_start("资源导出")
        
        # Ensure we're in the correct context
        if not self.kubectl.switch_context(source_context):
            raise Exception(f"Failed to switch to source context: {source_context}")
        
        export_dir = os.path.join(self.temp_dir, 'exported_resources')
        os.makedirs(export_dir, exist_ok=True)
        
        exported_files = {}
        
        for resource in resources:
            # Use target namespace in filename if specified
            ns_for_filename = target_namespace if target_namespace else resource.namespace
            filename = f"{resource.kind.lower()}_{resource.name}_{ns_for_filename}.yaml"
            filepath = os.path.join(export_dir, filename)
            
            print(f"导出 {resource.full_identifier}")
            
            if self.kubectl.export_resource_clean(
                resource.kind.lower(), 
                resource.name, 
                resource.namespace, 
                filepath,
                target_namespace
            ):
                exported_files[resource.full_identifier] = filepath
                interactive.success(f"{resource.full_identifier}")
                if target_namespace and target_namespace != resource.namespace:
                    interactive.info(f"    Namespace updated: {resource.namespace} → {target_namespace}")
            else:
                interactive.failure(f"Failed to export {resource.full_identifier}")
        
        print(f"已导出 {len(exported_files)} 个资源到 {export_dir}")
        return exported_files
    
    def preview_changes(self, exported_files: Dict[str, str], target_namespace: str) -> bool:
        """Preview changes that will be applied"""
        interactive.subsection("资源预览")
        
        for identifier, filepath in exported_files.items():
            interactive.info(f"\nResource: {identifier}")
            interactive.info(f"File: {filepath}")
            interactive.info(f"Target: {target_namespace}")
            
            # Show first few lines of the resource
            try:
                with open(filepath, 'r') as f:
                    lines = f.readlines()[:10]
                    for line in lines:
                        interactive.info(f"  {line.rstrip()}")
                    if len(lines) >= 10:
                        interactive.info("  ...")
            except Exception as e:
                interactive.warning_msg(f"读取文件失败: {e}")
        return True
    
    def confirm_operation(self, resources: List[K8sResource], source_context: str, 
                         source_namespace: str, target_context: str, target_namespace: str) -> bool:
        """Get user confirmation for the copy operation"""
        interactive.warning_msg("需要确认")
        interactive.info(f"源: {source_context}/{source_namespace}")
        interactive.info(f"目标: {target_context}/{target_namespace}")
        interactive.info(f"待复制资源数: {len(resources)}")
        
        interactive.info("\n资源列表:")
        for resource in resources:
            interactive.info(f"  • {resource.full_identifier}")
        
        interactive.warning_msg("此操作将向目标集群应用资源")
        interactive.warning_msg("同名资源可能被修改")
        
        try:
            confirmation = input("输入 'YES' 确认执行: ").strip()
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            return False
        return confirmation == 'YES'
    
    def apply_resources(self, exported_files: Dict[str, str], target_context: str, 
                       target_namespace: str, dry_run: bool = True) -> bool:
        """Apply resources to target cluster"""
        # Switch to target context
        if not self.kubectl.switch_context(target_context):
            print(f"❌ 切换到目标上下文失败: {target_context}")
            return False
        
        mode = "dry-run" if dry_run else "apply"
        interactive.operation_start(f"{mode.title()} resources", f"target: {target_context}/{target_namespace}")
        
        success_count = 0
        total_count = len(exported_files)
        
        for identifier, filepath in exported_files.items():
            print(f"应用 {identifier}")
            
            if self.kubectl.apply_resource(filepath, None, dry_run):
                success_count += 1
                interactive.success(f"{identifier}")
            else:
                interactive.failure(f"Failed to apply {identifier}")
        
        interactive.info(f"\n结果: {success_count}/{total_count} 个资源处理成功")
        
        if dry_run and success_count > 0:
            interactive.info("当前为 dry-run，未对集群做出更改")
            apply_for_real = interactive.confirm("是否正式应用资源?", default=False)
            
            if apply_for_real:
                return self.apply_resources(exported_files, target_context, target_namespace, dry_run=False)
        
        return success_count == total_count
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        if self.temp_dir_cleanup:
            print("🧹 清理临时文件...")
            try:
                import shutil
                export_dir = os.path.join(self.temp_dir, 'exported_resources')
                if os.path.exists(export_dir):
                    shutil.rmtree(export_dir)
                    print("✅ 临时文件已清理")
            except Exception as e:
                print(f"⚠️  清理临时文件失败: {e}")
    
    def run(self):
        """Main tool execution"""
        try:
            interactive.section(self.tool_name)
            
            # Check dependencies
            if not self.check_dependencies():
                sys.exit(1)
            
            # Get source information
            source_context, source_namespace = self.get_source_info()
            if not source_context or not source_namespace:
                print("❌ 源信息选择已取消")
                return
            
            # Discover and select resources
            resources = self.discover_and_select_resources(source_namespace)
            if not resources:
                print("ℹ️ 未选择需要复制的资源")
                return
            
            if len(resources) > self.max_resources_per_batch:
                print(f"❌ 选择的资源过多 ({len(resources)} > {self.max_resources_per_batch})")
                return
            
            # Get target information
            target_context, target_namespace = self.get_target_info()
            if not target_context or not target_namespace:
                print("❌ 目标信息选择已取消")
                return
            
            # Export resources
            exported_files = self.export_resources(resources, source_context, target_namespace)
            if not exported_files:
                print("❌ 导出资源失败")
                return
            
            # Preview changes
            self.preview_changes(exported_files, target_namespace)
            
            # Get confirmation
            if not self.confirm_operation(resources, source_context, source_namespace, 
                                        target_context, target_namespace):
                print("👋 用户取消操作")
                return
            
            # Apply resources (with dry-run by default)
            success = self.apply_resources(exported_files, target_context, target_namespace, 
                                         dry_run=self.dry_run_default)
            
            if success:
                print("✅ 资源复制操作完成")
                interactive.success("操作成功！")
            else:
                print("❌ 资源复制操作存在失败")
                interactive.failure("操作存在失败")
            
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            interactive.user_cancelled()
        except Exception as e:
            print(f"\n❌ 程序错误: {e}")
            interactive.failure(f"程序错误: {e}")
            sys.exit(1)
        finally:
            # Cleanup temporary files
            self.cleanup_temp_files()


def main():
    """Entry point"""
    tool = K8sResourceCopyTool()
    tool.run()


if __name__ == '__main__':
    main()
