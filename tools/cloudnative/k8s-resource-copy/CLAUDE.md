# Kubernetes Resource Copy Tool

## Description
A comprehensive Kubernetes resource copying tool that enables safe, intelligent copying of resources between clusters and namespaces with automatic resource relationship detection. The tool uses kubectl neat to clean resource definitions and supports batch operations with mandatory user confirmation.

## Technical Architecture
- **Implementation Language**: Python 3.7+
- **Core Dependencies**: pyyaml, colorama, click
- **System Requirements**: kubectl, krew (optional but recommended for neat plugin)
- **Kubernetes Support**: All Kubernetes versions supported by kubectl

## Key Features
- **Multi-resource Selection**: Interactive selection of multiple Kubernetes resources
- **Automatic Relationship Discovery**: Auto-detect related resources using labels (e.g., Deployment → Service + PVC)
- **Advanced Resource Cleaning**: Remove cluster-specific fields including clusterIP, nodePort, resourceVersion, and more
- **kubectl neat Integration**: Additional cleaning with kubectl neat plugin when available
- **Cross-cluster/namespace Operations**: Support copying between different clusters and namespaces
- **Dependency Management**: Auto-install krew plugins (neat, ctx, ns) if available
- **Batch Operations**: Process multiple resource sets with progress tracking
- **Safety Features**: Mandatory user confirmation before applying resources
- **Configurable Cleaning**: Environment variable control over which fields to remove
- **Temporary File Management**: Use OPSKIT_TOOL_TEMP_DIR for secure temporary storage

## Configuration Schema
```yaml
# Resource relationship detection
relationships:
  default_labels: [app, service, component, name]
  auto_discover: true
  include_secrets: true
  include_configmaps: true

# Operation settings
operations:
  temp_dir_cleanup: true
  max_resources_per_batch: 50
  confirmation_timeout: 300
  dry_run_default: true
  
# kubectl settings
kubectl:
  context_switch_timeout: 30
  neat_plugin_required: false
  validate_cluster_access: true
  
# Output settings
output:
  show_resource_diff: true
  export_format: yaml
  preserve_comments: false

# Resource cleaning settings (additional to kubectl neat)
cleaning:
  remove_cluster_ip: true      # Remove clusterIP and clusterIPs from Service resources
  remove_node_port: true       # Remove nodePort from Service ports (configurable)
```

## Code Structure

### Main Components
- **K8sResourceCopyTool Class**: Core tool logic with OpsKit integration
- **ResourceDiscoverer**: Automatic relationship detection using labels and selectors
- **KubectlManager**: kubectl command execution and neat plugin integration
- **ResourceSelector**: Interactive UI for multi-resource selection
- **ClusterManager**: Context switching and cluster validation
- **TempFileManager**: Secure temporary file operations using OPSKIT_TOOL_TEMP_DIR

### Key Methods
- `check_dependencies()`: Validate kubectl, krew, and plugins availability
- `discover_resources()`: Find resources and their relationships using labels
- `select_resources()`: Interactive multi-resource selection interface
- `export_resources()`: Export clean resources using kubectl neat
- `validate_target()`: Check target cluster and namespace accessibility
- `copy_resources()`: Execute the resource copying operation
- `cleanup_temp_files()`: Clean up temporary files after operation

## Error Handling Strategy
- **Dependency Errors**: Guide users to install missing kubectl/krew components
- **Connection Errors**: Validate cluster connectivity with helpful error messages
- **Resource Errors**: Handle missing resources and permission issues gracefully
- **Interrupt Handling**: Clean cancellation with Ctrl+C support and temp file cleanup
- **Validation Errors**: Comprehensive resource and target validation with clear feedback

## Security Considerations
- **Temporary File Security**: All temporary files stored in OPSKIT_TOOL_TEMP_DIR
- **Credential Handling**: Use existing kubectl context credentials, no credential storage
- **Resource Validation**: Validate all resources before applying to target clusters
- **Confirmation Required**: Mandatory user confirmation for all destructive operations
- **Advanced Resource Cleaning**: Comprehensive removal of cluster-specific fields with configurable options

## Resource Relationship Detection

### Automatic Discovery Rules
1. **Label-based Discovery**: Use common labels (app, service, component) to group resources
2. **Selector-based Discovery**: Follow Service selectors to find related Pods/Deployments
3. **Volume-based Discovery**: Detect PVC relationships through volume mounts
4. **ConfigMap/Secret Discovery**: Find ConfigMaps and Secrets referenced in resource specs

### Supported Resource Relationships
- **Deployment** → Service, PVC, ConfigMap, Secret
- **StatefulSet** → Service, PVC, ConfigMap, Secret
- **Service** → Deployment, StatefulSet, Pod
- **Ingress** → Service, Secret (TLS)
- **PVC** → StorageClass (reference only)
- **HPA** → Deployment, StatefulSet

## Testing Approach
- **Unit Tests**: Core functionality and resource discovery logic
- **Integration Tests**: End-to-end resource copying across test clusters
- **kubectl Tests**: Various kubectl versions and neat plugin integration
- **Error Scenarios**: Network failures, permission errors, missing resources
- **Multi-cluster Tests**: Cross-cluster copying and context switching

## Usage Examples

### Basic Resource Copy
```bash
opskit k8s-resource-copy
# Interactive mode:
# 1. Select source cluster context
# 2. Select source namespace  
# 3. Choose resources to copy
# 4. Select target cluster context
# 5. Select target namespace
# 6. Confirm and execute
```

### Batch Resource Copy
```bash
# Copy deployment with related resources
Select resources:
[✓] deployment/mysql
[✓] service/mysql (auto-detected)
[✓] pvc/mysql-data (auto-detected)
[✓] secret/mysql-credentials (auto-detected)

Target: production-cluster/mysql-namespace
Confirm copy? (YES): YES
```

### Cross-cluster Migration
```bash
# Copy from staging to production
Source: staging-cluster/app-staging
Target: production-cluster/app-production

Resources to copy:
- deployment/web-app
- service/web-app-service  
- ingress/web-app-ingress
- secret/web-app-tls
- configmap/web-app-config

Preview changes? (y/n): y
Apply to target? (YES): YES
```

## Dependency Management

### Required Dependencies
- **kubectl**: Kubernetes command-line tool (required)
- **krew**: kubectl plugin manager (recommended)

### Optional Plugins (auto-installed via krew if available)
- **kubectl neat**: Clean resource definitions
- **kubectl ctx**: Quick context switching  
- **kubectl ns**: Quick namespace switching

### Installation Guidance
```bash
# If krew is not installed
echo "krew is not installed. Please install krew first:"
echo "https://krew.sigs.k8s.io/docs/user-guide/setup/install/"

# Auto-install plugins if krew is available
kubectl krew install neat ctx ns
```

## Development Notes
- Uses OpsKit common libraries for logging and storage
- Integrates with OpsKit configuration management
- Follows OpsKit tool development standards  
- English-only code and comments as per project requirements
- All temporary files managed through OPSKIT_TOOL_TEMP_DIR
- Comprehensive error handling with user-friendly messages
- Supports both interactive and batch operation modes