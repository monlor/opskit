#!/usr/bin/env python3
"""
Kubernetes Service Discovery Tool - OpsKit Version
Display comprehensive service environment information for K8s clusters
"""

import os
import sys
import json
import base64
import subprocess
import warnings
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from pathlib import Path
import re
import time

# Suppress SSL warnings for insecure clusters
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Suppress other SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Get OpsKit environment variables
OPSKIT_TOOL_TEMP_DIR = os.environ.get('OPSKIT_TOOL_TEMP_DIR', os.path.join(os.getcwd(), '.k8s-service-discovery-temp'))
OPSKIT_BASE_PATH = os.environ.get('OPSKIT_BASE_PATH', os.path.expanduser('~/.opskit'))
OPSKIT_WORKING_DIR = os.environ.get('OPSKIT_WORKING_DIR', os.getcwd())
TOOL_NAME = os.environ.get('TOOL_NAME', 'k8s-service-discovery')
TOOL_VERSION = os.environ.get('TOOL_VERSION', '1.0.0')

# Create temporary directory (tool-specific cache directory)
os.makedirs(OPSKIT_TOOL_TEMP_DIR, exist_ok=True)

# Simple filesystem cache using OPSKIT_TOOL_TEMP_DIR
class CacheManager:
    """Filesystem cache: one file per (context|namespace), entries per service with TTL."""
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or OPSKIT_TOOL_TEMP_DIR

    def _ns_key_to_path(self, ns_key: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", ns_key)
        return os.path.join(self.base_dir, f"cache_{safe}.json")

    def load(self, ns_key: str) -> dict:
        path = self._ns_key_to_path(ns_key)
        try:
            if not os.path.exists(path):
                return {}
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}

    def save(self, ns_key: str, data: dict) -> None:
        path = self._ns_key_to_path(ns_key)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data or {}, f, ensure_ascii=False)
        except Exception:
            pass

    @staticmethod
    def get_entry_from_map(cache_map: dict, service_name: str, ttl_seconds: int) -> Optional[dict]:
        try:
            entry = (cache_map or {}).get(service_name)
            if not entry:
                return None
            ts = int(entry.get('timestamp') or 0)
            if ts and (ts + int(ttl_seconds)) > int(time.time()):
                return entry.get('payload')
            return None
        except Exception:
            return None

    @staticmethod
    def set_entry_in_map(cache_map: dict, service_name: str, payload: dict) -> None:
        if cache_map is None:
            return
        cache_map[service_name] = {
            'timestamp': int(time.time()),
            'payload': payload or {}
        }

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    import click
    from tabulate import tabulate
except ImportError as e:
    print("❌ 缺少必需依赖:")
    if "kubernetes" in str(e):
        print("请安装依赖: pip install kubernetes")
    elif "click" in str(e):
        print("请安装依赖: pip install click")
    elif "tabulate" in str(e):
        print("请安装依赖: pip install tabulate")
    else:
        print(f"请安装依赖: {e}")
    sys.exit(1)


@dataclass
class ServiceInfo:
    """Service information data structure"""
    name: str
    namespace: str
    service_type: str
    cluster_ip: str
    external_ips: List[str]
    ports: List[Dict]
    selector: Dict[str, str]
    workload_type: str = ""
    workload_name: str = ""
    # New structured access information
    ingress_urls: List[str] = None  # Full Ingress URLs with paths (legacy)
    ingress_entries: List[Dict] = None  # Ingress detailed entries: [{'url','backend_port','service'}]
    nodeport_info: List[Dict] = None  # NodePort info with internal port mapping
    loadbalancer_info: List[Dict] = None  # LoadBalancer info
    internal_access: List[str] = None
    credentials: Dict[str, str] = None
    pod_count: Optional[int] = None
    
    def __post_init__(self):
        if self.ingress_urls is None:
            self.ingress_urls = []
        if self.ingress_entries is None:
            self.ingress_entries = []
        if self.nodeport_info is None:
            self.nodeport_info = []
        if self.loadbalancer_info is None:
            self.loadbalancer_info = []
        if self.internal_access is None:
            self.internal_access = []
        if self.credentials is None:
            self.credentials = {}
        if self.pod_count is None:
            self.pod_count = None


class KubernetesClient:
    """Kubernetes API client wrapper"""
    
    def __init__(self):
        self.v1 = None
        self.apps_v1 = None
        self.networking_v1 = None
        
    def connect(self, context: str = None) -> bool:
        """Connect to Kubernetes cluster"""
        try:
            if context:
                contexts, active_context = config.list_kube_config_contexts()
                if context not in [c['name'] for c in contexts]:
                    print(f"❌ 上下文 '{context}' 不存在")
                    return False
                config.load_kube_config(context=context)
            else:
                config.load_kube_config()
            
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.networking_v1 = client.NetworkingV1Api()
            
            # Test connection
            self.v1.list_namespace(limit=1)
            return True
        except Exception as e:
            print(f"❌ 连接 Kubernetes 集群失败: {e}")
            return False
    
    def get_namespaces(self) -> List[str]:
        """Get all namespaces"""
        try:
            namespaces = self.v1.list_namespace()
            return [ns.metadata.name for ns in namespaces.items]
        except Exception as e:
            print(f"❌ 获取命名空间失败: {e}")
            return []
    
    def get_services(self, namespace: str = None) -> List[ServiceInfo]:
        """Get all services in namespace or all namespaces"""
        services = []
        try:
            if namespace:
                svc_list = self.v1.list_namespaced_service(namespace)
            else:
                svc_list = self.v1.list_service_for_all_namespaces()
            
            for svc in svc_list.items:
                # Skip headless services
                if svc.spec.cluster_ip == "None":
                    continue
                    
                ports = []
                for port in svc.spec.ports or []:
                    port_info = {
                        'name': port.name,
                        'port': port.port,
                        'target_port': port.target_port,
                        'protocol': port.protocol,
                        'node_port': getattr(port, 'node_port', None)
                    }
                    ports.append(port_info)
                
                service_info = ServiceInfo(
                    name=svc.metadata.name,
                    namespace=svc.metadata.namespace,
                    service_type=svc.spec.type,
                    cluster_ip=svc.spec.cluster_ip,
                    external_ips=svc.spec.external_i_ps or [],
                    ports=ports,
                    selector=svc.spec.selector or {}
                )
                services.append(service_info)
                
        except Exception as e:
            print(f"❌ 获取服务列表失败: {e}")
        
        return services
    
    def get_workloads(self, namespace: str = None) -> Dict[str, List]:
        """Get all workloads (deployments, daemonsets, statefulsets)"""
        workloads = {
            'deployments': [],
            'daemonsets': [],
            'statefulsets': []
        }
        
        try:
            if namespace:
                workloads['deployments'] = self.apps_v1.list_namespaced_deployment(namespace).items
                workloads['daemonsets'] = self.apps_v1.list_namespaced_daemon_set(namespace).items  
                workloads['statefulsets'] = self.apps_v1.list_namespaced_stateful_set(namespace).items
            else:
                workloads['deployments'] = self.apps_v1.list_deployment_for_all_namespaces().items
                workloads['daemonsets'] = self.apps_v1.list_daemon_set_for_all_namespaces().items
                workloads['statefulsets'] = self.apps_v1.list_stateful_set_for_all_namespaces().items
                
        except Exception as e:
            print(f"❌ 获取工作负载失败: {e}")
        
        return workloads
    
    def get_ingresses(self, namespace: str = None) -> List:
        """Get all ingresses"""
        try:
            if namespace:
                return self.networking_v1.list_namespaced_ingress(namespace).items
            else:
                return self.networking_v1.list_ingress_for_all_namespaces().items
        except Exception as e:
            print(f"❌ 获取 Ingress 失败: {e}")
            return []
    
    def get_secrets(self, namespace: str) -> List:
        """Get secrets in namespace"""
        try:
            return self.v1.list_namespaced_secret(namespace).items
        except Exception as e:
            print(f"❌ 获取 Secret 失败: {e}")
            return []

    def count_pods_by_selector(self, namespace: str, selector: Dict[str, str]) -> int:
        """Count pods that match a label selector in a namespace"""
        if not selector:
            return 0
        try:
            # Build Kubernetes label selector string
            label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])
            pods = self.v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector, limit=500)
            return len(pods.items)
        except Exception as e:
            print(f"❌ 统计 Pod 数量失败: {e}")
            return 0


class ServiceMapper:
    """Map services to workloads and discover access information"""
    
    def __init__(self, k8s_client: KubernetesClient):
        self.k8s = k8s_client
        
    def map_services_to_workloads(self, services: List[ServiceInfo], workloads: Dict[str, List]) -> List[ServiceInfo]:
        """Map services to their corresponding workloads"""
        print("🔍 正在映射服务到工作负载...")
        
        for service in services:
            if not service.selector:
                continue
                
            # Check deployments
            for deployment in workloads['deployments']:
                if (deployment.metadata.namespace == service.namespace and
                    self._labels_match_selector(deployment.spec.template.metadata.labels or {}, service.selector)):
                    service.workload_type = "Deployment"
                    service.workload_name = deployment.metadata.name
                    break
            
            # Check statefulsets if no deployment found
            if not service.workload_name:
                for sts in workloads['statefulsets']:
                    if (sts.metadata.namespace == service.namespace and
                        self._labels_match_selector(sts.spec.template.metadata.labels or {}, service.selector)):
                        service.workload_type = "StatefulSet"
                        service.workload_name = sts.metadata.name
                        break
            
            # Check daemonsets if no other workload found
            if not service.workload_name:
                for ds in workloads['daemonsets']:
                    if (ds.metadata.namespace == service.namespace and
                        self._labels_match_selector(ds.spec.template.metadata.labels or {}, service.selector)):
                        service.workload_type = "DaemonSet"
                        service.workload_name = ds.metadata.name
                        break
        
        mapped_count = len([s for s in services if s.workload_name])
        print(f"✅ 成功映射 {mapped_count}/{len(services)} 个服务到工作负载")
        return services
    
    def discover_access_info(self, services: List[ServiceInfo], ingresses: List) -> List[ServiceInfo]:
        """Discover access information for services"""
        print("🔍 正在发现服务访问信息...")
        
        # Create ingress map with detailed info
        ingress_map = {}
        for ing in ingresses:
            for rule in ing.spec.rules or []:
                host = rule.host
                for path in rule.http.paths or []:
                    backend_service = path.backend.service.name
                    backend_port = path.backend.service.port.number if hasattr(path.backend.service.port, 'number') else path.backend.service.port.name
                    
                    if backend_service not in ingress_map:
                        ingress_map[backend_service] = []
                    
                    url = f"https://{host}" if host else f"http://{host}"
                    if path.path and path.path != "/":
                        url += path.path
                    
                    ingress_info = {
                        'url': url,
                        'host': host,
                        'path': path.path or "/",
                        'backend_port': backend_port,
                        'service': backend_service
                    }
                    ingress_map[backend_service].append(ingress_info)
        
        # Get cluster nodes for NodePort services
        cluster_nodes = self._get_cluster_nodes()
        
        for service in services:
            # Ingress URLs and detailed entries
            if service.name in ingress_map:
                service.ingress_entries = ingress_map[service.name]
                service.ingress_urls = [info['url'] for info in ingress_map[service.name]]
            
            # NodePort information with internal port mapping
            if service.service_type == "NodePort":
                for port in service.ports:
                    if port['node_port']:
                        nodeport_entry = {
                            'node_port': port['node_port'],
                            'internal_port': port['port'],
                            'protocol': port['protocol'],
                            'port_name': port['name'],
                            'has_external_ip': len(cluster_nodes) > 0,
                            'external_ips': cluster_nodes if cluster_nodes else []
                        }
                        service.nodeport_info.append(nodeport_entry)
            
            # LoadBalancer information
            elif service.service_type == "LoadBalancer":
                for port in service.ports:
                    lb_entry = {
                        'port': port['port'],
                        'protocol': port['protocol'],
                        'port_name': port['name'],
                        'external_ips': [ip for ip in (service.external_ips or []) if self._is_external_ip(ip)],
                        'pending': len([ip for ip in (service.external_ips or []) if self._is_external_ip(ip)]) == 0
                    }
                    service.loadbalancer_info.append(lb_entry)
            
            # Internal access (ClusterIP)
            for port in service.ports:
                service.internal_access.append(f"{service.name}.{service.namespace}.svc.cluster.local:{port['port']}")
        
        print(f"✅ 服务访问信息发现完成")
        return services
    
    def _is_external_ip(self, ip: str) -> bool:
        """Check if IP is truly external (not in private ranges)"""
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            
            # Check if it's in private ranges
            private_ranges = [
                ipaddress.ip_network('10.0.0.0/8'),
                ipaddress.ip_network('172.16.0.0/12'), 
                ipaddress.ip_network('192.168.0.0/16'),
                ipaddress.ip_network('127.0.0.0/8'),  # localhost
            ]
            
            for private_range in private_ranges:
                if ip_obj in private_range:
                    return False
            return True
        except Exception:
            return False
    
    def _labels_match_selector(self, labels: Dict[str, str], selector: Dict[str, str]) -> bool:
        """Check if labels match selector"""
        for key, value in selector.items():
            if labels.get(key) != value:
                return False
        return True
    
    def _get_cluster_nodes(self) -> List[str]:
        """Get cluster node IPs/names, prefer external IPs only"""
        try:
            nodes = self.k8s.v1.list_node()
            external_ips = []
            
            for node in nodes.items:
                # Only collect actual external IPs (public IPs)
                for addr in node.status.addresses or []:
                    if addr.type == "ExternalIP" and addr.address:
                        # Check if it's a real external IP (not private ranges)
                        if self._is_external_ip(addr.address):
                            external_ips.append(addr.address)
            
            return external_ips
        except Exception:
            return []
    
    def _is_external_ip(self, ip: str) -> bool:
        """Check if IP is truly external (not in private ranges)"""
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            
            # Check if it's in private ranges
            private_ranges = [
                ipaddress.ip_network('10.0.0.0/8'),
                ipaddress.ip_network('172.16.0.0/12'), 
                ipaddress.ip_network('192.168.0.0/16'),
                ipaddress.ip_network('127.0.0.0/8'),  # localhost
            ]
            
            for private_range in private_ranges:
                if ip_obj in private_range:
                    return False
            return True
        except Exception:
            return False


class CredentialDiscovery:
    """Discover service credentials, especially for Bitnami Helm charts"""
    
    def __init__(self, k8s_client: KubernetesClient):
        self.k8s = k8s_client
        
        # Bitnami common credential patterns
        self.bitnami_patterns = {
            'mysql': {
                'secret_name_patterns': ['{name}-mysql', '{name}', 'mysql-secret'],
                'username_keys': ['mysql-user', 'username', 'user'],
                'password_keys': ['mysql-password', 'password', 'mysql-root-password', 'root-password']
            },
            'postgresql': {
                'secret_name_patterns': ['{name}-postgresql', '{name}', 'postgresql-secret'],
                'username_keys': ['postgresql-username', 'username', 'user', 'postgres-user'],
                'password_keys': ['postgresql-password', 'password', 'postgres-password']
            },
            'redis': {
                'secret_name_patterns': ['{name}-redis', '{name}', 'redis-secret'],
                'username_keys': ['username'],
                'password_keys': ['redis-password', 'password', 'auth']
            },
            'mongodb': {
                'secret_name_patterns': ['{name}-mongodb', '{name}', 'mongodb-secret'],
                'username_keys': ['mongodb-username', 'username'],
                'password_keys': ['mongodb-password', 'password', 'mongodb-root-password']
            },
            'rabbitmq': {
                'secret_name_patterns': ['{name}-rabbitmq', '{name}', 'rabbitmq-secret'],
                'username_keys': ['rabbitmq-username', 'username'],
                'password_keys': ['rabbitmq-password', 'password']
            }
        }
    
    def discover_credentials(self, services: List[ServiceInfo]) -> List[ServiceInfo]:
        """Discover credentials for services"""
        print("🔍 正在发现服务凭据...")
        
        discovered_count = 0
        
        for service in services:
            secrets = self.k8s.get_secrets(service.namespace)
            service_type = self._detect_service_type(service)
            
            if service_type and service_type in self.bitnami_patterns:
                credentials = self._find_bitnami_credentials(service, secrets, service_type)
                if credentials:
                    service.credentials = credentials
                    discovered_count += 1
            else:
                # Generic credential discovery
                credentials = self._find_generic_credentials(service, secrets)
                if credentials:
                    service.credentials = credentials
                    discovered_count += 1
        
        if discovered_count > 0:
            print(f"✅ 发现 {discovered_count} 个服务的凭据信息")
        else:
            print("ℹ️ 未发现支持的服务凭据")
        
        return services
    
    def _detect_service_type(self, service: ServiceInfo) -> Optional[str]:
        """Detect service type based on name, labels, or ports"""
        name_lower = service.name.lower()
        
        # Check by service name
        for service_type in self.bitnami_patterns.keys():
            if service_type in name_lower:
                return service_type
        
        # Check by common ports
        ports = [p['port'] for p in service.ports]
        if 3306 in ports or 3307 in ports:
            return 'mysql'
        elif 5432 in ports:
            return 'postgresql'
        elif 6379 in ports:
            return 'redis'
        elif 27017 in ports:
            return 'mongodb'
        elif 5672 in ports or 15672 in ports:
            return 'rabbitmq'
        
        return None
    
    def _find_bitnami_credentials(self, service: ServiceInfo, secrets: List, service_type: str) -> Dict[str, str]:
        """Find credentials using Bitnami patterns"""
        patterns = self.bitnami_patterns[service_type]
        
        # Try different secret name patterns
        for pattern in patterns['secret_name_patterns']:
            secret_name = pattern.format(name=service.name)
            secret = self._find_secret_by_name(secrets, secret_name)
            
            if secret:
                credentials = {}
                
                # Find username
                for key in patterns['username_keys']:
                    if key in secret.data:
                        credentials['username'] = base64.b64decode(secret.data[key]).decode('utf-8')
                        break
                
                # Find password  
                for key in patterns['password_keys']:
                    if key in secret.data:
                        credentials['password'] = base64.b64decode(secret.data[key]).decode('utf-8')
                        break
                
                if credentials:
                    return credentials
        
        return {}
    
    def _find_generic_credentials(self, service: ServiceInfo, secrets: List) -> Dict[str, str]:
        """Generic credential discovery"""
        # Look for secrets with service name
        for secret in secrets:
            if service.name in secret.metadata.name:
                credentials = {}
                for key, value in secret.data.items():
                    if any(keyword in key.lower() for keyword in ['user', 'username', 'login']):
                        credentials['username'] = base64.b64decode(value).decode('utf-8')
                    elif any(keyword in key.lower() for keyword in ['pass', 'password', 'secret']):
                        credentials['password'] = base64.b64decode(value).decode('utf-8')
                
                if credentials:
                    return credentials
        
        return {}
    
    def _find_secret_by_name(self, secrets: List, name: str):
        """Find secret by name"""
        for secret in secrets:
            if secret.metadata.name == name:
                return secret
        return None


class ServiceDiscoveryTool:
    """Main Kubernetes Service Discovery Tool"""
    
    def __init__(self, context: Optional[str] = None, namespace: Optional[str] = None, 
                 all_namespaces: bool = False, hide_credentials: bool = False,
                 external_ip: Optional[str] = None,
                 cache_ttl: int = 86400,
                 disable_cache: bool = False,
                 name_like: Optional[str] = None):
        self.k8s = KubernetesClient()
        self.mapper = ServiceMapper(self.k8s)
        self.credential_discovery = CredentialDiscovery(self.k8s)
        
        # Command line parameters
        self.context = context
        self.namespace = namespace
        self.all_namespaces = all_namespaces
        self.hide_credentials = hide_credentials
        self.external_ip = external_ip
        self.cache_ttl = int(cache_ttl) if cache_ttl is not None else 86400
        self.disable_cache = bool(disable_cache)
        self.active_context = None
        self.cache = CacheManager()
        self.name_like = name_like
        
    def get_available_contexts(self) -> List[str]:
        """Get available kubectl contexts"""
        try:
            contexts, active_context = config.list_kube_config_contexts()
            return [ctx['name'] for ctx in contexts]
        except Exception as e:
            print(f"❌ 获取 kubectl 上下文失败: {e}")
            return []
    
    def select_context(self, contexts: List[str]) -> Optional[str]:
        """Interactive context selection"""
        if not contexts:
            print("❌ 没有可用的 kubectl 上下文")
            return None
        
        print("\n🔧 选择 Kubernetes 集群:")
        print("-" * 40)
        for i, ctx in enumerate(contexts, 1):
            print(f"{i}. {ctx}")
        
        while True:
            try:
                choice = input("\n请选择集群上下文 (输入编号): ").strip()
                if not choice:
                    continue
                
                idx = int(choice) - 1
                if 0 <= idx < len(contexts):
                    return contexts[idx]
                else:
                    print("❌ 无效的选择，请重新输入")
            except KeyboardInterrupt:
                print("\n👋 用户取消操作")
                return None
            except ValueError:
                print("❌ 请输入有效的数字")
    
    def select_namespace(self, namespaces: List[str]) -> Optional[str]:
        """Interactive namespace selection"""
        if not namespaces:
            print("❌ 没有可用的命名空间")
            return None
        
        print("\n📋 选择命名空间:")
        print("-" * 40)
        print("0. 全部命名空间")
        for i, ns in enumerate(namespaces, 1):
            print(f"{i}. {ns}")
        
        while True:
            try:
                choice = input("\n请选择命名空间 (输入编号): ").strip()
                if not choice:
                    continue
                
                idx = int(choice)
                if idx == 0:
                    return None  # All namespaces
                elif 1 <= idx <= len(namespaces):
                    return namespaces[idx - 1]
                else:
                    print("❌ 无效的选择，请重新输入")
            except KeyboardInterrupt:
                print("\n👋 用户取消操作")
                return None
            except ValueError:
                print("❌ 请输入有效的数字")
    
    def display_services(self, services: List[ServiceInfo]):
        """Display service information in a formatted table"""
        if not services:
            print("ℹ️ 没有发现服务")
            return
        
        print("\n" + "=" * 140)
        print("🌐 Kubernetes 服务环境信息")
        print("=" * 140)
        
        # Group by namespace
        services_by_ns = {}
        for service in services:
            if service.namespace not in services_by_ns:
                services_by_ns[service.namespace] = []
            services_by_ns[service.namespace].append(service)
        
        for namespace, ns_services in services_by_ns.items():
            print(f"\n📁 命名空间: {namespace}")
            print("-" * 120)
            
            # Create table data
            table_data = []
            for service in ns_services:
                # Truncate long service names (allow longer display width)
                service_name = service.name
                if len(service_name) > 30:
                    service_name = service_name[:27] + "..."
                
                # Append pod count to service name (just number) - use cached if available
                pod_count = service.pod_count if service.pod_count is not None else self.k8s.count_pods_by_selector(service.namespace, service.selector)
                service.pod_count = pod_count
                service_name = f"{service_name} ({pod_count})"
                
                # External access information - each line shows one port/domain
                external_access = []
                
                # Ingress URLs (domain access) - two lines per entry: URL then backend service:port
                if getattr(service, 'ingress_entries', None):
                    for entry in service.ingress_entries:
                        display_url = entry.get('url', '')
                        if len(display_url) > 50:
                            display_url = display_url[:47] + '...'
                        external_access.append(f"🌐 {display_url}")
                        # second line shows mapping to backend service + port
                        backend_port = entry.get('backend_port', '-')
                        backend_svc = entry.get('service', service.name)
                        external_access.append(f"  → {backend_svc}:{backend_port}")
                elif service.ingress_urls:
                    # Fallback: legacy list of URLs without backend port info
                    for url in service.ingress_urls:
                        display_url = url
                        if len(display_url) > 50:
                            display_url = display_url[:47] + '...'
                        external_access.append(f"🌐 {display_url}")
                
                # NodePort access - one line per nodeport (no IP fan-out)
                if service.nodeport_info:
                    for np_info in service.nodeport_info:
                        if self.external_ip:
                            external_access.append(
                                f"🔗 {self.external_ip}:{np_info['node_port']} → {np_info['internal_port']}/{np_info['protocol']}"
                            )
                        else:
                            external_access.append(
                                f"🔗 NodePort {np_info['node_port']} → {np_info['internal_port']}/{np_info['protocol']}"
                            )
                
                # LoadBalancer access - one per line
                if service.loadbalancer_info:
                    for lb_info in service.loadbalancer_info:
                        if lb_info['pending']:
                            external_access.append(f"⏳ LoadBalancer:{lb_info['port']} (等待外部IP)")
                        else:
                            for ext_ip in lb_info['external_ips']:
                                external_access.append(f"🔗 {ext_ip}:{lb_info['port']} → {lb_info['port']}/{lb_info['protocol']}")
                
                # If no external access, show internal - one per line
                if not external_access and service.internal_access:
                    for internal in service.internal_access[:2]:  # Show max 2 internal access
                        external_access.append(f"🏠 {internal}")

                # Keep each access method on its own line (no intra-item wrap)
                
                # Credentials - each on separate line
                credentials_list = []
                if service.credentials and not self.hide_credentials:
                    if 'username' in service.credentials:
                        credentials_list.append(f"用户: {service.credentials['username']}")
                    if 'password' in service.credentials:
                        credentials_list.append(f"密码: {service.credentials['password']}")
                    credentials = "\n".join(credentials_list)
                elif service.credentials and self.hide_credentials:
                    credentials = "[已隐藏]"
                else:
                    credentials = "-"
                
                # Workload type - show full name
                wl_type = service.workload_type or "-"

                # Add row to table (include 类型 column for workload type)
                # Do not slice lines; keep domain + backend mapping together
                access_text = "\n".join(external_access) if external_access else "-"
                row = [
                    service_name,
                    wl_type,
                    access_text,
                    credentials
                ]
                table_data.append(row)

                # no table-level caching here; structured caching is handled in run()
            
            # Display table with better column widths
            headers = ["服务名", "类型", "访问方式", "凭据"]
            print(tabulate(
                table_data,
                headers=headers,
                tablefmt="grid",
                stralign="left",
                disable_numparse=True
            ))
        
        # Summary statistics
        print(f"\n📊 统计信息:")
        ingress_count = len([s for s in services if s.ingress_urls])
        nodeport_count = len([s for s in services if s.nodeport_info])
        lb_count = len([s for s in services if s.loadbalancer_info])
        credential_count = len([s for s in services if s.credentials])
        
        summary_data = [
            ["总服务数", len(services)],
            ["域名访问 (Ingress)", ingress_count],
            ["NodePort 访问", nodeport_count], 
            ["LoadBalancer 访问", lb_count],
            ["已发现凭据", credential_count]
        ]
        print(tabulate(summary_data, headers=["项目", "数量"], tablefmt="simple"))
    
    def run(self):
        """Main tool execution"""
        print("🚀 Kubernetes 服务发现工具")
        print("=" * 50)
        
        try:
            # Handle context selection
            if self.context:
                # Context provided via command line
                contexts = self.get_available_contexts()
                if self.context not in contexts:
                    print(f"❌ 指定的上下文 '{self.context}' 不存在")
                    print(f"可用上下文: {', '.join(contexts)}")
                    return
                selected_context = self.context
            else:
                # Interactive context selection
                contexts = self.get_available_contexts()
                if not contexts:
                    return
                selected_context = self.select_context(contexts)
                if not selected_context:
                    return
            
            print(f"\n🔍 连接到集群: {selected_context}")
            if not self.k8s.connect(selected_context):
                return
            self.active_context = selected_context
            
            # Handle namespace selection
            if self.all_namespaces:
                # All namespaces mode
                selected_namespace = None
                print("📋 扫描所有命名空间")
            elif self.namespace:
                # Namespace provided via command line
                namespaces = self.k8s.get_namespaces()
                if self.namespace not in namespaces:
                    print(f"❌ 指定的命名空间 '{self.namespace}' 不存在")
                    print(f"可用命名空间: {', '.join(namespaces)}")
                    return
                selected_namespace = self.namespace
                print(f"📋 扫描命名空间: {selected_namespace}")
            else:
                # Interactive namespace selection
                namespaces = self.k8s.get_namespaces()
                if not namespaces:
                    print("❌ 无法获取命名空间")
                    return
                selected_namespace = self.select_namespace(namespaces)
                if selected_namespace is None and not self.all_namespaces:
                    selected_namespace = None  # All namespaces
            
            # Discovery phase
            print("\n🔍 正在发现服务...")
            services = self.k8s.get_services(selected_namespace)

            if not services:
                ns_info = selected_namespace or "所有命名空间"
                print(f"ℹ️ 在 {ns_info} 中没有发现服务")
                return

            # Optional: fuzzy name filter (case-insensitive substring)
            if self.name_like:
                keyword = self.name_like.strip().lower()
                if keyword:
                    before_count = len(services)
                    services = [s for s in services if keyword in (s.name or '').lower()]
                    print(f"🔎 按名称模糊匹配 '{self.name_like}' 过滤: {len(services)}/{before_count}")
                    if not services:
                        print("ℹ️ 没有匹配到任何服务")
                        return

            print(f"✅ 发现 {len(services)} 个服务")

            # Try namespace-level structured cache; preload fields if available
            cached_mask = [False] * len(services)
            ns_cache_maps: Dict[str, dict] = {}
            ns_dirty: Set[str] = set()
            if not self.disable_cache and services:
                for idx, svc in enumerate(services):
                    ns_key = f"{self.active_context or self.context or 'default'}|{svc.namespace}"
                    if ns_key not in ns_cache_maps:
                        ns_cache_maps[ns_key] = self.cache.load(ns_key)
                    payload = CacheManager.get_entry_from_map(ns_cache_maps[ns_key], svc.name, self.cache_ttl)
                    if payload:
                        svc.workload_type = payload.get('workload_type', svc.workload_type)
                        svc.workload_name = payload.get('workload_name', svc.workload_name)
                        svc.ingress_entries = payload.get('ingress_entries', svc.ingress_entries)
                        svc.ingress_urls = payload.get('ingress_urls', svc.ingress_urls)
                        svc.nodeport_info = payload.get('nodeport_info', svc.nodeport_info)
                        svc.loadbalancer_info = payload.get('loadbalancer_info', svc.loadbalancer_info)
                        svc.internal_access = payload.get('internal_access', svc.internal_access)
                        svc.pod_count = payload.get('pod_count', svc.pod_count)
                        if not self.hide_credentials:
                            svc.credentials = payload.get('credentials', svc.credentials)
                        cached_mask[idx] = True

            # If all services hydrated from cache, skip expensive discovery
            if services and all(cached_mask):
                print("⚡ 使用缓存渲染表格（跳过映射/访问信息/凭据发现）")
                self.display_services(services)
                return
            
            # Get workloads for mapping (only if any service missing mapping)
            workloads = self.k8s.get_workloads(selected_namespace)
            
            # Map services to workloads (only uncached or missing mapping)
            targets = [s for i, s in enumerate(services) if not cached_mask[i]]
            if targets:
                self.mapper.map_services_to_workloads(targets, workloads)
            
            # Discover access information
            ingresses = self.k8s.get_ingresses(selected_namespace)
            if targets:
                self.mapper.discover_access_info(targets, ingresses)
            
            # Discover credentials (only if not hidden)
            if not self.hide_credentials and targets:
                self.credential_discovery.discover_credentials(targets)

            # Compute and cache structured data for targets
            for svc in targets:
                # compute pod count
                svc.pod_count = svc.pod_count if svc.pod_count is not None else self.k8s.count_pods_by_selector(svc.namespace, svc.selector)
                # build payload (exclude external-ip; it's a render-time option)
                payload = {
                    'workload_type': svc.workload_type,
                    'workload_name': svc.workload_name,
                    'ingress_entries': svc.ingress_entries,
                    'ingress_urls': svc.ingress_urls,
                    'nodeport_info': svc.nodeport_info,
                    'loadbalancer_info': svc.loadbalancer_info,
                    'internal_access': svc.internal_access,
                    'pod_count': svc.pod_count,
                }
                if not self.hide_credentials:
                    payload['credentials'] = svc.credentials
                ns_key = f"{self.active_context or self.context or 'default'}|{svc.namespace}"
                if ns_key not in ns_cache_maps:
                    ns_cache_maps[ns_key] = {}
                CacheManager.set_entry_in_map(ns_cache_maps[ns_key], svc.name, payload)
                ns_dirty.add(ns_key)

            # Save updated namespace caches
            for ns_key in ns_dirty:
                self.cache.save(ns_key, ns_cache_maps.get(ns_key, {}))
            
            # Display results
            self.display_services(services)
            
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
        except Exception as e:
            print(f"\n❌ 程序错误: {e}")


@click.command()
@click.option('--context', '-c', help='指定 kubectl 上下文 (集群)')
@click.option('--namespace', '-n', help='指定命名空间')
@click.option('--all-namespaces', '-A', is_flag=True, help='扫描所有命名空间')
@click.option('--hide-credentials', is_flag=True, help='隐藏凭据信息')
@click.option('--external-ip', help='指定外部访问IP地址，用于 NodePort 服务访问')
@click.option('--cache-ttl', type=int, default=86400, show_default=True, help='缓存有效期（秒）')
@click.option('--no-cache', is_flag=True, help='跳过读取缓存并强制刷新写入')
@click.option('--name-like', '-m', help='按服务名模糊匹配筛选（子串匹配，忽略大小写）')
@click.version_option(version='1.0.0', prog_name='k8s-service-discovery')
@click.help_option('--help', '-h')
def main(context, namespace, all_namespaces, hide_credentials, external_ip, cache_ttl, no_cache, name_like):
    """
    Kubernetes 服务发现工具
    
    发现并显示 K8s 集群中的服务环境信息，包括工作负载映射、访问地址和凭据信息。
    
    \b
    示例用法:
      # 交互式模式
      python main.py
      
      # 指定集群和命名空间
      python main.py -c my-cluster -n production
      
      # 扫描所有命名空间
      python main.py -c my-cluster --all-namespaces
      
      # 指定外部IP显示NodePort完整访问地址
      python main.py -c my-cluster -n production --external-ip 203.0.113.100
      
      # 隐藏凭据信息
      python main.py -c my-cluster -n production --hide-credentials

      # 仅显示名称包含关键字的服务（模糊匹配）
      python main.py -c my-cluster -n production -m web
    """
    
    # Validate conflicting options
    if namespace and all_namespaces:
        click.echo("❌ 不能同时指定 --namespace 和 --all-namespaces", err=True)
        sys.exit(1)
    
    # Create and run tool
    tool = ServiceDiscoveryTool(
        context=context,
        namespace=namespace, 
        all_namespaces=all_namespaces,
        hide_credentials=hide_credentials,
        external_ip=external_ip,
        cache_ttl=cache_ttl,
        disable_cache=no_cache,
        name_like=name_like
    )
    tool.run()


if __name__ == '__main__':
    main()
