# Kubernetes Service Discovery Tool - OpsKit Version

## 功能描述
Kubernetes 服务发现工具，用于显示 K8s 集群中所有服务的环境信息。主要针对 Deployment、DaemonSet、StatefulSet 服务，自动发现对应的 Service、域名、外部访问地址和凭据信息。支持 Bitnami Helm 安装方式的标准化凭据查找。

## 技术架构
- 实现语言: Python 3.7+
- 核心依赖: kubernetes (Python K8s API 客户端), PyYAML (YAML 处理), click (命令行界面)
- 系统要求: kubectl 配置的 Kubernetes 集群访问权限
- OpsKit 集成: 使用 OpsKit 环境变量和临时目录管理
- 安全特性: 自动抑制不安全 HTTPS 连接的 SSL 警告

## 配置项

### OpsKit 环境变量
工具使用以下 OpsKit 内置环境变量：

- **OPSKIT_TOOL_TEMP_DIR**: 工具临时文件夹（即本工具的缓存目录），用于缓存和临时数据存储；无需再创建子目录，缓存文件直接写入该目录
- **OPSKIT_BASE_PATH**: OpsKit 的目录路径
- **OPSKIT_WORKING_DIR**: 用户终端当前所在目录
- **TOOL_NAME**: 工具名称 (k8s-service-discovery)
- **TOOL_VERSION**: 工具版本号

### 可选配置环境变量
- **HIDE_CREDENTIALS**: 设置为 "true" 完全隐藏凭据信息显示
- **MAX_PASSWORD_LENGTH**: 密码显示的最大长度 (默认: 50)
- **DISCOVERY_TIMEOUT**: 服务发现超时时间，秒 (默认: 60)

## 核心功能

### 1. 多集群支持
- 自动检测可用的 kubectl 上下文
- 交互式集群选择
- 安全的集群连接和认证

### 2. 服务发现
- 发现所有类型的 Kubernetes 服务 (ClusterIP, NodePort, LoadBalancer)
- 自动过滤 Headless 服务
- 按命名空间组织显示

### 3. 工作负载映射
- 自动将服务映射到对应的工作负载:
  - Deployment → Service 映射
  - StatefulSet → Service 映射  
  - DaemonSet → Service 映射
- 基于标签选择器的智能匹配

### 4. 访问信息发现 (优化展示)
- **域名访问** (Ingress):
  - 格式: `🌐 https://app.example.com → 80/TCP`
  - 显示域名到内部端口的完整映射关系
- **NodePort 访问**:
  - 有外部IP: `🔗 203.0.113.1:30080 → 80/TCP`
  - 无外部IP: `🔗 NodePort:30080 → 80/TCP (需要外部IP)`
  - 清晰显示外部端口到内部端口的映射
- **LoadBalancer 访问**:
  - 已分配: `🔗 203.0.113.1:80`
  - 等待中: `⏳ LoadBalancer:80 (等待外部IP)`
- **内部访问** (备用):
  - 格式: `🏠 service.namespace.svc.cluster.local:port`
- **智能IP识别**: 自动过滤私网IP段，仅显示真实外部IP

### 5. 结构化缓存（提升展示速度）
- 缓存粒度: 按集群+命名空间保存一个文件，文件内按“服务名”存储条目
- 缓存文件名键: `集群|命名空间`（单文件），文件内容键为 `服务名`
- 缓存内容条目:
  - `workload_type`, `workload_name`
  - `ingress_entries`（包含 url、service、backend_port）与 `ingress_urls`
  - `nodeport_info`, `loadbalancer_info`, `internal_access`
  - `pod_count`
  - `credentials`（仅在未隐藏时缓存）
- 存储位置: `OPSKIT_TOOL_TEMP_DIR`
- 缓存策略:
  - 读取: 运行时按命名空间加载一次缓存文件并预加载所有服务；若全部命中则跳过映射/访问信息/凭据发现
  - 写入: 始终写入（`--no-cache` 仅跳过读取），用于刷新缓存
  - 有效期: 默认 86400 秒（1 天），可通过 `--cache-ttl` 配置；可通过 `--no-cache` 跳过读取并强制刷新写入
  - 不包含: `--external-ip` 等仅渲染期选项不会保存到缓存中

### 6. Bitnami 凭据发现
支持以下 Bitnami Helm Chart 的标准凭据发现:
- **MySQL**: mysql-user, mysql-password, mysql-root-password
- **PostgreSQL**: postgresql-username, postgresql-password
- **Redis**: redis-password
- **MongoDB**: mongodb-username, mongodb-password, mongodb-root-password
- **RabbitMQ**: rabbitmq-username, rabbitmq-password

### 7. 通用凭据发现
- 基于服务名称的 Secret 查找
- 常见用户名/密码字段识别
- Base64 解码和明文显示 (默认不隐藏，可用 --hide-credentials 隐藏)

## 开发指南

### 核心架构
- **ServiceDiscoveryTool 类**: 主工具逻辑和用户交互
- **KubernetesClient 类**: K8s API 客户端封装
- **ServiceMapper 类**: 服务到工作负载映射和访问信息发现
- **CredentialDiscovery 类**: 凭据发现和 Bitnami 模式匹配
- **ServiceInfo 数据类**: 服务信息数据结构

### 关键功能实现

**服务映射策略**:
```python
def map_services_to_workloads(self, services, workloads):
    # 1. 获取服务的标签选择器
    # 2. 遍历 Deployment/StatefulSet/DaemonSet  
    # 3. 匹配 Pod 模板标签与服务选择器
    # 4. 建立服务 → 工作负载映射关系
```

**访问信息发现**:
```python
def discover_access_info(self, services, ingresses):
    # 1. 构建 Ingress → Service 映射表
    # 2. 获取集群节点列表 (用于 NodePort)
    # 3. 按优先级生成访问 URL:
    #    - Ingress (最高优先级)
    #    - NodePort + 节点 IP
    #    - LoadBalancer IP
    #    - ExternalIPs
    # 4. 生成内部访问 DNS 域名
```

**Bitnami 凭据发现**:
```python
def discover_bitnami_credentials(self, service, service_type):
    # 1. 根据服务类型获取凭据模式
    # 2. 尝试多种 Secret 命名模式:
    #    - {service-name}-{type}
    #    - {service-name}
    #    - {type}-secret
    # 3. 在 Secret 中查找标准键名
    # 4. Base64 解码凭据信息
```

### 错误处理策略
- Kubernetes API 连接失败处理
- 权限不足的优雅降级
- Secret 解码错误处理
- 用户中断 (Ctrl+C) 支持
- 网络超时和重试机制

### 输出格式化
- **表格化展示**: 使用 tabulate 库提供清晰的表格格式
- **按命名空间分组**: 每个命名空间独立表格
- **访问方式优化**: 清晰区分域名访问、NodePort 和 LoadBalancer
- **端口映射显示**: NodePort 显示 `外部端口 → 内部端口/协议` 的映射关系
- **域名映射显示**: Ingress 显示 `域名 → 内部端口/协议` 的映射关系
- **统计信息摘要**: 分类统计各种访问方式的数量

## 命令行参数

### 支持的参数
```bash
# 显示帮助信息
opskit run k8s-service-discovery --help

# 基本参数
-c, --context TEXT        指定 kubectl 上下文 (集群)
-n, --namespace TEXT      指定命名空间  
-A, --all-namespaces      扫描所有命名空间
--external-ip TEXT        指定外部访问IP地址，用于 NodePort 服务访问
--cache-ttl INTEGER      缓存有效期（秒），默认 86400（1 天）
--no-cache               跳过读取缓存，并刷新写入
--hide-credentials        隐藏凭据信息
-h, --help               显示帮助信息
--version                显示版本信息
```

### 参数验证
- `--namespace` 和 `--all-namespaces` 不能同时使用
- `--external-ip` 参数接受IPv4地址，用于NodePort服务的外部访问显示
- 无效的上下文或命名空间会显示可用选项
- 所有参数都是可选的，支持完全交互式模式

## 使用示例

### 命令行模式 (推荐)
```bash
# 交互式模式 - 引导选择集群和命名空间
opskit run k8s-service-discovery

# 指定集群和命名空间
opskit run k8s-service-discovery -c my-cluster -n production

# 扫描指定集群的所有命名空间
opskit run k8s-service-discovery -c staging-cluster --all-namespaces

# 指定外部IP显示完整的NodePort访问地址
opskit run k8s-service-discovery -c my-cluster -n production --external-ip 203.0.113.100

# 调整/禁用缓存
opskit run k8s-service-discovery --cache-ttl 120
opskit run k8s-service-discovery --no-cache

# 隐藏敏感的凭据信息
opskit run k8s-service-discovery -c prod-cluster -n database --hide-credentials

# 显示帮助信息
opskit run k8s-service-discovery --help
```

### 交互式模式流程
当不提供命令行参数时，工具将引导您完成以下步骤：
1. 选择 Kubernetes 集群上下文
2. 选择目标命名空间 (或选择全部)  
3. 自动发现服务和工作负载
4. 显示完整的服务环境信息

### 典型输出示例
```
🌐 Kubernetes 服务环境信息
============================================================================

📁 命名空间: production
----------------------------------------------------------------------------------------------
+---------------------+--------------+------------------------------------------+----------------------------------+
| 服务名              | 类型         | 访问方式                                | 凭据                             |
+=====================+==============+==========================================+==================================+
| mysql-primary (2)   | StatefulSet  | 🏠 mysql-primary.production.svc.cluster | 用户: admin                      |
|                     |              | .local:3306                             | 密码: MySecretPassword123        |
+---------------------+--------------+------------------------------------------+----------------------------------+
| web-app (5)         | Deployment   | 🌐 https://app.example.com → 80/TCP    | -                                |
|                     |              | 🔗 203.0.113.100:30080 → 80/TCP        |                                  |
|                     |              | 🔗 203.0.113.100:30443 → 443/TCP       |                                  |
+---------------------+--------------+------------------------------------------+----------------------------------+
| redis-cache (3)     | Deployment   | 🔗 203.0.113.100:31000 → 6379/TCP      | 用户: redis                      |
|                     |              |                                          | 密码: redis123                   |
+---------------------+--------------+------------------------------------------+----------------------------------+

📊 统计信息:
项目                    数量
--------------------  ----
总服务数                 3
域名访问 (Ingress)       1
NodePort 访问            2
LoadBalancer 访问        0
已发现凭据               2
```

**使用 --external-ip 参数的效果**:
- NodePort 服务会显示 `🔗 203.0.113.100:30080 → 80/TCP` 
- 不再显示 "需要外部IP" 提示
- 每个端口单独一行显示
- 凭据信息也分行显示，便于阅读

### 使用场景
1. **开发环境检查**: `opskit run k8s-service-discovery -c dev-cluster -n myapp`
2. **生产环境审计**: `opskit run k8s-service-discovery -c prod-cluster --all-namespaces --hide-credentials`
3. **NodePort服务访问**: `opskit run k8s-service-discovery -c cluster -n production --external-ip 192.168.1.100`
4. **服务迁移准备**: `opskit run k8s-service-discovery -c source-cluster -n app-namespace`
5. **故障排查**: `opskit run k8s-service-discovery -c cluster -n problematic-namespace`

### SSL 警告处理
工具已自动配置忽略以下 SSL 警告，适合不安装证书的测试集群：
- `InsecureRequestWarning: Unverified HTTPS request`
- `urllib3.exceptions.InsecureRequestWarning`

无需额外配置，工具会自动抑制这些警告信息。

## Bitnami 支持详情

### 支持的 Bitnami Chart
- **bitnami/mysql**: 自动发现 MySQL 用户名和密码
- **bitnami/postgresql**: 自动发现 PostgreSQL 凭据
- **bitnami/redis**: 自动发现 Redis 认证密码
- **bitnami/mongodb**: 自动发现 MongoDB 用户凭据
- **bitnami/rabbitmq**: 自动发现 RabbitMQ 用户凭据

### Secret 命名规则
工具会尝试以下 Secret 命名模式 (按优先级):
1. `{service-name}-{database-type}` (例: myapp-mysql)
2. `{service-name}` (例: myapp)
3. `{database-type}-secret` (例: mysql-secret)

### 凭据字段映射
每种数据库类型有预定义的凭据字段映射:
```yaml
mysql:
  username: [mysql-user, username, user]
  password: [mysql-password, password, mysql-root-password, root-password]

postgresql:
  username: [postgresql-username, username, user, postgres-user]
  password: [postgresql-password, password, postgres-password]
```

## 系统要求
- Python 3.7+ 环境
- kubectl 已配置且可访问目标集群
- 对目标集群有足够的读取权限:
  - services (核心权限)
  - deployments, daemonsets, statefulsets (工作负载映射)
  - ingresses (外部访问发现)
  - secrets (凭据发现)
- OpsKit 环境 (提供必要的环境变量)

## 故障排除

### 常见问题
1. **连接集群失败**: 检查 kubectl 配置和集群可访问性
2. **权限不足**: 确保 ServiceAccount 有足够权限读取相关资源
3. **凭据发现失败**: 检查 Secret 命名是否符合 Bitnami 标准
4. **服务映射失败**: 检查服务选择器和 Pod 标签匹配情况

### 权限要求
最小 RBAC 权限设置:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: service-discovery
rules:
- apiGroups: [""]
  resources: ["services", "secrets", "nodes"]
  verbs: ["get", "list"]
- apiGroups: ["apps"]
  resources: ["deployments", "daemonsets", "statefulsets"]
  verbs: ["get", "list"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list"]
```

### 性能优化
- 大型集群建议选择特定命名空间而非全集群扫描
- 工具会自动过滤 Headless 服务以提高性能
- 凭据发现仅在发现服务类型匹配时执行

## 安全注意事项
- 凭据默认以明文显示，便于直接使用
- 可使用 --hide-credentials 参数完全隐藏敏感信息
- 不会将凭据信息写入任何日志文件
- 仅在内存中处理敏感信息
- 生产环境建议使用 --hide-credentials 选项
