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
from dataclasses import dataclass

# Import OpsKit common libraries
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../common/python'))

from logger import get_logger
from storage import get_storage
from utils import run_command, get_user_input, timestamp, get_env_var

# Third-party imports
try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init()
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please ensure all dependencies are installed.")
    sys.exit(1)

# Initialize OpsKit components
logger = get_logger(__name__)
storage = get_storage('k8s-resource-copy')


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
        success, stdout, stderr = run_command(['kubectl', 'version', '--client'])
        if success:
            self.kubectl_path = 'kubectl'
            logger.info("✅ kubectl is available")
            return True
        else:
            logger.error("❌ kubectl not found in PATH")
            return False
    
    def check_krew(self) -> bool:
        """Check if krew is available"""
        success, stdout, stderr = run_command(['kubectl', 'krew', 'version'])
        if success:
            self.krew_available = True
            logger.info("✅ krew is available")
            return True
        else:
            logger.warning("⚠️ krew is not available")
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
                logger.error(f"Failed to parse resource JSON: {resource_type}/{name}")
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
                logger.error(f"Failed to parse resources JSON: {resource_type}")
        return []
    
    def export_resource_clean(self, resource_type: str, name: str, namespace: str, output_file: str, target_namespace: str = None) -> bool:
        """Export resource with kubectl neat to remove cluster-specific fields"""
        # First get the resource
        cmd = ['kubectl', 'get', resource_type, name, '-o', 'yaml']
        if namespace:
            cmd.extend(['-n', namespace])
        
        success, stdout, stderr = run_command(cmd)
        if not success:
            logger.error(f"Failed to export resource: {stderr}")
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
            logger.error(f"Failed to write resource to file: {e}")
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
            logger.info(f"✅ Resource applied successfully")
            return True
        else:
            logger.error(f"❌ Failed to apply resource: {stderr}")
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
    
    def select_resources(self, resources: List[K8sResource]) -> List[K8sResource]:
        """Interactive multi-resource selection"""
        if not resources:
            print("No resources found.")
            return []
        
        print(f"\n{Fore.CYAN}Available Resources:{Style.RESET_ALL}")
        print("=" * 50)
        
        selected = set()
        
        while True:
            self._display_resources(resources, selected)
            
            choice = input(f"\n{Fore.YELLOW}Select resources (number/range/all/done): {Style.RESET_ALL}").strip().lower()
            
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
                    print(f"{Fore.RED}Invalid range format{Style.RESET_ALL}")
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
                    print(f"{Fore.RED}Invalid selection format{Style.RESET_ALL}")
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(resources):
                        if idx in selected:
                            selected.remove(idx)
                        else:
                            selected.add(idx)
                    else:
                        print(f"{Fore.RED}Invalid resource number{Style.RESET_ALL}")
                except ValueError:
                    print(f"{Fore.RED}Invalid input{Style.RESET_ALL}")
        
        selected_resources = [resources[i] for i in selected]
        
        # Auto-include relationships
        if selected_resources:
            auto_included = self._include_relationships(selected_resources, resources)
            if auto_included:
                print(f"\n{Fore.GREEN}Auto-included related resources:{Style.RESET_ALL}")
                for resource in auto_included:
                    print(f"  + {resource.full_identifier}")
                selected_resources.extend(auto_included)
        
        return selected_resources
    
    def _display_resources(self, resources: List[K8sResource], selected: Set[int]):
        """Display resources with selection status"""
        print()
        for i, resource in enumerate(resources):
            status = f"{Fore.GREEN}[✓]{Style.RESET_ALL}" if i in selected else f"{Fore.RED}[ ]{Style.RESET_ALL}"
            relationships = f" ({len(resource.relationships)} related)" if resource.relationships else ""
            print(f"{status} {i + 1:2}. {resource.full_identifier}{relationships}")
        
        if selected:
            print(f"\n{Fore.CYAN}Selected: {len(selected)} resources{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}Commands:{Style.RESET_ALL}")
        print("  - Number: Toggle resource selection")
        print("  - Range (1-5): Select range of resources") 
        print("  - Multiple (1,3,5): Select multiple resources")
        print("  - 'all': Select all resources")
        print("  - 'clear': Clear all selections")
        print("  - 'done': Finish selection")
    
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
            print("No contexts available")
            return None
        
        print(f"\n{Fore.CYAN}Available Contexts:{Style.RESET_ALL}")
        for i, context in enumerate(contexts):
            current_mark = " (current)" if context == current else ""
            print(f"  {i + 1}. {context}{current_mark}")
        
        while True:
            try:
                choice = input(f"\n{Fore.YELLOW}Select context (number): {Style.RESET_ALL}")
                if not choice:
                    return current
                
                idx = int(choice) - 1
                if 0 <= idx < len(contexts):
                    return contexts[idx]
                else:
                    print(f"{Fore.RED}Invalid context number{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number{Style.RESET_ALL}")
            except KeyboardInterrupt:
                return None
    
    def select_namespace(self, namespaces: List[str]) -> Optional[str]:
        """Select namespace"""
        if not namespaces:
            print("No namespaces available")
            return None
        
        print(f"\n{Fore.CYAN}Available Namespaces:{Style.RESET_ALL}")
        for i, ns in enumerate(namespaces):
            print(f"  {i + 1}. {ns}")
        
        while True:
            try:
                choice = input(f"\n{Fore.YELLOW}Select namespace (number): {Style.RESET_ALL}")
                idx = int(choice) - 1
                if 0 <= idx < len(namespaces):
                    return namespaces[idx]
                else:
                    print(f"{Fore.RED}Invalid namespace number{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number{Style.RESET_ALL}")
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
            logger.error("OPSKIT_TOOL_TEMP_DIR not available")
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
        
        logger.info(f"🚀 Starting {self.tool_name}")
        logger.info(f"📁 Temporary directory: {self.temp_dir}")
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        logger.info("🔍 Checking dependencies...")
        
        # Check kubectl
        if not self.kubectl.check_kubectl():
            print(f"{Fore.RED}❌ kubectl is required but not found{Style.RESET_ALL}")
            print("Please install kubectl: https://kubernetes.io/docs/tasks/tools/")
            return False
        
        # Check krew (optional but recommended)
        if self.kubectl.check_krew():
            plugins = self.kubectl.check_plugins()
            
            # Auto-install missing plugins
            for plugin_name, available in plugins.items():
                if not available:
                    logger.info(f"Installing missing plugin: {plugin_name}")
                    self.kubectl.install_plugin(plugin_name)
        else:
            print(f"{Fore.YELLOW}⚠️ krew is not installed - some features may be limited{Style.RESET_ALL}")
            print("Install krew for enhanced functionality: https://krew.sigs.k8s.io/docs/user-guide/setup/install/")
        
        # Verify cluster access
        contexts = self.kubectl.get_contexts()
        if not contexts:
            print(f"{Fore.RED}❌ No kubectl contexts found{Style.RESET_ALL}")
            print("Please configure kubectl with at least one cluster context")
            return False
        
        logger.info("✅ All required dependencies are available")
        return True
    
    def get_source_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get source cluster context and namespace"""
        contexts = self.kubectl.get_contexts()
        current_context = self.kubectl.get_current_context()
        
        print(f"\n{Fore.CYAN}=== Source Selection ==={Style.RESET_ALL}")
        
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
        
        print(f"\n{Fore.CYAN}=== Target Selection ==={Style.RESET_ALL}")
        
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
        print(f"\n{Fore.CYAN}🔍 Discovering resources in namespace: {namespace}{Style.RESET_ALL}")
        
        resources = self.discoverer.discover_resources(self.resource_types, namespace)
        
        if not resources:
            print(f"{Fore.YELLOW}⚠️ No resources found in namespace: {namespace}{Style.RESET_ALL}")
            return []
        
        logger.info(f"Found {len(resources)} resources with relationships")
        
        # Display discovery summary
        print(f"\n{Fore.GREEN}Discovery Summary:{Style.RESET_ALL}")
        resource_counts = {}
        for resource in resources:
            kind = resource.kind.lower()
            resource_counts[kind] = resource_counts.get(kind, 0) + 1
        
        for kind, count in sorted(resource_counts.items()):
            print(f"  {kind}: {count}")
        
        return self.selector.select_resources(resources)
    
    def export_resources(self, resources: List[K8sResource], source_context: str, target_namespace: str = None) -> Dict[str, str]:
        """Export selected resources to temporary files"""
        print(f"\n{Fore.CYAN}📦 Exporting resources...{Style.RESET_ALL}")
        
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
            
            logger.info(f"Exporting {resource.full_identifier}")
            
            if self.kubectl.export_resource_clean(
                resource.kind.lower(), 
                resource.name, 
                resource.namespace, 
                filepath,
                target_namespace
            ):
                exported_files[resource.full_identifier] = filepath
                print(f"  ✅ {resource.full_identifier}")
                if target_namespace and target_namespace != resource.namespace:
                    print(f"    🔄 Namespace updated: {resource.namespace} → {target_namespace}")
            else:
                print(f"  ❌ Failed to export {resource.full_identifier}")
        
        logger.info(f"Exported {len(exported_files)} resources to {export_dir}")
        return exported_files
    
    def preview_changes(self, exported_files: Dict[str, str], target_namespace: str) -> bool:
        """Preview changes that will be applied"""
        print(f"\n{Fore.CYAN}👁️ Resource Preview:{Style.RESET_ALL}")
        print("=" * 60)
        
        for identifier, filepath in exported_files.items():
            print(f"\n{Fore.YELLOW}Resource: {identifier}{Style.RESET_ALL}")
            print(f"File: {filepath}")
            print(f"Target: {target_namespace}")
            
            # Show first few lines of the resource
            try:
                with open(filepath, 'r') as f:
                    lines = f.readlines()[:10]
                    for line in lines:
                        print(f"  {line.rstrip()}")
                    if len(lines) >= 10:
                        print("  ...")
            except Exception as e:
                print(f"  Error reading file: {e}")
        
        print("=" * 60)
        return True
    
    def confirm_operation(self, resources: List[K8sResource], source_context: str, 
                         source_namespace: str, target_context: str, target_namespace: str) -> bool:
        """Get user confirmation for the copy operation"""
        print(f"\n{Fore.RED}⚠️ CONFIRMATION REQUIRED ⚠️{Style.RESET_ALL}")
        print("=" * 50)
        print(f"Source: {source_context}/{source_namespace}")
        print(f"Target: {target_context}/{target_namespace}")
        print(f"Resources to copy: {len(resources)}")
        
        print(f"\n{Fore.YELLOW}Resources:{Style.RESET_ALL}")
        for resource in resources:
            print(f"  • {resource.full_identifier}")
        
        print("=" * 50)
        print(f"{Fore.RED}This operation will apply resources to the target cluster.{Style.RESET_ALL}")
        print(f"{Fore.RED}Existing resources with the same name may be modified.{Style.RESET_ALL}")
        
        confirmation = get_user_input(
            f"\n{Fore.YELLOW}Type 'YES' to confirm this operation{Style.RESET_ALL}",
            validator=lambda x: x == 'YES'
        )
        
        return confirmation == 'YES'
    
    def apply_resources(self, exported_files: Dict[str, str], target_context: str, 
                       target_namespace: str, dry_run: bool = True) -> bool:
        """Apply resources to target cluster"""
        # Switch to target context
        if not self.kubectl.switch_context(target_context):
            logger.error(f"Failed to switch to target context: {target_context}")
            return False
        
        mode = "dry-run" if dry_run else "apply"
        print(f"\n{Fore.CYAN}🚀 {mode.title()} resources to {target_context}/{target_namespace}...{Style.RESET_ALL}")
        
        success_count = 0
        total_count = len(exported_files)
        
        for identifier, filepath in exported_files.items():
            logger.info(f"Applying {identifier}")
            
            if self.kubectl.apply_resource(filepath, None, dry_run):
                success_count += 1
                print(f"  ✅ {identifier}")
            else:
                print(f"  ❌ Failed to apply {identifier}")
        
        print(f"\n{Fore.GREEN}Results: {success_count}/{total_count} resources processed successfully{Style.RESET_ALL}")
        
        if dry_run and success_count > 0:
            print(f"{Fore.YELLOW}This was a dry-run. No changes were applied.{Style.RESET_ALL}")
            apply_for_real = get_user_input(
                "Apply resources for real? (y/N)",
                default="n",
                validator=lambda x: x.lower() in ['y', 'yes', 'n', 'no']
            )
            
            if apply_for_real.lower() in ['y', 'yes']:
                return self.apply_resources(exported_files, target_context, target_namespace, dry_run=False)
        
        return success_count == total_count
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        if self.temp_dir_cleanup:
            logger.info("🧹 Cleaning up temporary files...")
            try:
                import shutil
                export_dir = os.path.join(self.temp_dir, 'exported_resources')
                if os.path.exists(export_dir):
                    shutil.rmtree(export_dir)
                    logger.info("✅ Temporary files cleaned up")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up temporary files: {e}")
    
    def run(self):
        """Main tool execution"""
        try:
            print(f"{Fore.CYAN}🚀 {self.tool_name}{Style.RESET_ALL}")
            print("=" * 60)
            
            # Check dependencies
            if not self.check_dependencies():
                sys.exit(1)
            
            # Get source information
            source_context, source_namespace = self.get_source_info()
            if not source_context or not source_namespace:
                logger.error("Source selection cancelled")
                return
            
            # Discover and select resources
            resources = self.discover_and_select_resources(source_namespace)
            if not resources:
                logger.info("No resources selected for copying")
                return
            
            if len(resources) > self.max_resources_per_batch:
                logger.error(f"Too many resources selected ({len(resources)} > {self.max_resources_per_batch})")
                return
            
            # Get target information
            target_context, target_namespace = self.get_target_info()
            if not target_context or not target_namespace:
                logger.error("Target selection cancelled")
                return
            
            # Export resources
            exported_files = self.export_resources(resources, source_context, target_namespace)
            if not exported_files:
                logger.error("Failed to export resources")
                return
            
            # Preview changes
            self.preview_changes(exported_files, target_namespace)
            
            # Get confirmation
            if not self.confirm_operation(resources, source_context, source_namespace, 
                                        target_context, target_namespace):
                logger.info("Operation cancelled by user")
                return
            
            # Apply resources (with dry-run by default)
            success = self.apply_resources(exported_files, target_context, target_namespace, 
                                         dry_run=self.dry_run_default)
            
            if success:
                logger.info("✅ Resource copy operation completed successfully")
                print(f"\n{Fore.GREEN}🎉 Operation completed successfully!{Style.RESET_ALL}")
            else:
                logger.error("❌ Resource copy operation completed with errors")
                print(f"\n{Fore.RED}❌ Operation completed with errors{Style.RESET_ALL}")
            
        except KeyboardInterrupt:
            logger.info("❌ Operation cancelled by user")
            print(f"\n{Fore.YELLOW}Operation cancelled by user{Style.RESET_ALL}")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            print(f"\n{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
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