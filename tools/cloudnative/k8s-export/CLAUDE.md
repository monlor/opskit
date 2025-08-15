# Kubernetes Resource Export Tool

## Description
A comprehensive Kubernetes resource export tool that enables batch export of resources from specified namespaces across clusters. The tool supports multi-namespace selection, resource type filtering, and optional kubectl neat cleaning for production-ready exports.

## Technical Architecture
- **Implementation Language**: Python 3.7+
- **Core Dependencies**: pyyaml, colorama, click
- **System Requirements**: kubectl, krew (optional but recommended for neat plugin)
- **Kubernetes Support**: All Kubernetes versions supported by kubectl

## Key Features
- **Multi-namespace Export**: Interactive selection and export from multiple namespaces
- **Resource Type Filtering**: Choose specific resource types to export
- **kubectl neat Integration**: Optional cleaning with kubectl neat plugin when available
- **Context Switching**: Support for exporting from different clusters using kubectl ctx
- **Organized Output**: Resources exported to organized directory structure by namespace
- **Export Summary**: Detailed summary with statistics and metadata
- **Configurable Cleaning**: Environment variable control over cleaning behavior
- **Interactive Selection**: User-friendly selection interface for contexts, namespaces, and resource types

## Configuration Schema
```yaml
# Export settings
export:
  output_dir: "./k8s-export-YYYYMMDDHHMM"  # Default: current directory with timestamp
  use_neat_default: true
  temp_dir_cleanup: true
  group_by_resource_type: true          # Group exported resources by type in separate folders
  exclude_default_resources: ["kube-root-ca.crt", "default-token", "kubernetes.io/service-account-token"]
  
# kubectl settings
kubectl:
  context_switch_timeout: 30
  neat_plugin_required: false
  validate_cluster_access: true
  
# Output settings
output:
  export_format: yaml
  preserve_comments: false
  create_summary: true

# Resource cleaning settings
cleaning:
  remove_cluster_ip: true      # Remove clusterIP and clusterIPs from Service resources
  remove_node_port: true       # Remove nodePort from Service ports
  remove_resource_version: true # Remove resourceVersion from metadata
  remove_uid: true             # Remove uid from metadata
  remove_managed_fields: true  # Remove managedFields from metadata
```

## Code Structure

### Main Components
- **K8sExportTool Class**: Core tool logic with OpsKit integration
- **KubectlManager**: kubectl command execution and neat plugin integration
- **ResourceSelector**: Interactive UI for multi-resource, namespace, and context selection
- **Resource Discovery**: Automatic discovery of resources by type in selected namespaces

### Key Methods
- `check_dependencies()`: Validate kubectl, krew, and plugins availability
- `select_export_settings()`: Interactive selection of context, namespaces, and resource types
- `discover_resources()`: Find resources by type in specified namespaces
- `export_resources()`: Export clean resources using kubectl neat
- `_clean_resource_data()`: Remove cluster-specific fields from exported resources
- `_create_k8s_resource()`: Create resource objects from kubectl output

## Error Handling Strategy
- **Dependency Errors**: Guide users to install missing kubectl/krew components
- **Connection Errors**: Validate cluster connectivity with helpful error messages
- **Resource Errors**: Handle missing resources and permission issues gracefully
- **Interrupt Handling**: Clean cancellation with Ctrl+C support
- **Export Errors**: Continue export on individual resource failures with summary

## Security Considerations
- **Credential Handling**: Use existing kubectl context credentials, no credential storage
- **Resource Validation**: Validate all resources before export
- **Output Security**: Clean exported files to remove sensitive cluster-specific information
- **Comprehensive Resource Cleaning**: Remove cluster-specific fields with configurable options

## Resource Export Features

### Supported Resource Types
- **Workloads**: Deployment, StatefulSet, DaemonSet, Job, CronJob
- **Services**: Service, Ingress
- **Storage**: PersistentVolumeClaim
- **Configuration**: ConfigMap, Secret
- **Scaling**: HorizontalPodAutoscaler
- **Security**: NetworkPolicy, ServiceAccount, Role, RoleBinding

### Export Organization

#### With Resource Type Grouping (Default)
```
k8s-export-202501151430/
├── namespace-1/
│   ├── deployment/
│   │   └── app1.yaml
│   ├── service/
│   │   └── app1.yaml
│   └── configmap/
│       └── app1-config.yaml
├── namespace-2/
│   ├── statefulset/
│   │   └── database.yaml
│   └── persistentvolumeclaim/
│       └── database-data.yaml
└── export_summary.yaml
```

#### Flat Structure (GROUP_BY_RESOURCE_TYPE=false)
```
k8s-export-202501151430/
├── namespace-1/
│   ├── deployment_app1.yaml
│   ├── service_app1.yaml
│   └── configmap_app1-config.yaml
├── namespace-2/
│   ├── statefulset_database.yaml
│   └── persistentvolumeclaim_database-data.yaml
└── export_summary.yaml
```

## Testing Approach
- **Unit Tests**: Core functionality and resource discovery logic
- **Integration Tests**: End-to-end resource export across test clusters
- **kubectl Tests**: Various kubectl versions and neat plugin integration
- **Error Scenarios**: Network failures, permission errors, missing resources
- **Multi-cluster Tests**: Cross-cluster export and context switching

## Usage Examples

### Basic Multi-Namespace Export
```bash
opskit k8s-export
# Interactive mode:
# 1. Select cluster context
# 2. Select multiple namespaces
# 3. Choose resource types to export
# 4. Confirm and execute export
```

### Export with Custom Output Directory
```bash
opskit k8s-export --output-dir /path/to/exports
```

### Export without kubectl neat
```bash
opskit k8s-export --no-neat
```

### Typical Export Workflow
```bash
# Select resources to export:
Available Namespaces:
  1. default
  2. kube-system
  3. monitoring
  4. application

Select namespaces: 1,3,4

Available Resource Types:
  1. deployment
  2. service
  3. configmap
  4. secret

Select resource types: 1,2,3

Export Summary:
- Total resources found: 25
- Namespaces: 3
  default: 5 resources
  monitoring: 8 resources
  application: 12 resources

Proceed with export? (Y/n): Y
```

## Dependency Management

### Required Dependencies
- **kubectl**: Kubernetes command-line tool (required)
- **krew**: kubectl plugin manager (recommended)

### Optional Plugins (enhanced functionality)
- **kubectl neat**: Clean resource definitions
- **kubectl ctx**: Quick context switching  
- **kubectl ns**: Quick namespace switching

### Installation Guidance
```bash
# If krew is not installed
echo "krew is not installed. Please install krew first:"
echo "https://krew.sigs.k8s.io/docs/user-guide/setup/install/"

# Plugins are automatically detected and recommended
# No auto-installation to maintain user control
```

## Environment Variables

### Export Configuration
```bash
# Output directory for exports (default: ./k8s-export-YYYYMMDDHHMM in user's working directory)
K8S_EXPORT_OUTPUT_DIR="./custom-export-dir"

# User's working directory (automatically set by OpsKit CLI)
# This ensures exports go to the directory where user ran opskit, not the tool's directory
OPSKIT_WORKING_DIR="/path/to/user/current/directory"

# Default kubectl neat usage
USE_NEAT_DEFAULT="true"

# Cleanup temporary files
TEMP_DIR_CLEANUP="true"

# Progress display
SHOW_PROGRESS="true"

# Color output
COLOR_OUTPUT="true"

# Export organization - group resources by type in separate folders
GROUP_BY_RESOURCE_TYPE="true"

# Resource filtering - exclude Kubernetes default/system resources (comma-separated)
EXCLUDE_DEFAULT_RESOURCES="kube-root-ca.crt,default-token,kubernetes.io/service-account-token"

# Resource types discovery - use dynamic discovery to get all resources including CRDs
USE_DYNAMIC_RESOURCE_TYPES="false"
```

## Development Notes
- Uses OpsKit common libraries for logging and interactive components
- Integrates with OpsKit configuration management via interactive.py
- Follows OpsKit tool development standards
- English-only code and comments as per project requirements
- Comprehensive error handling with user-friendly messages
- Supports both interactive and batch operation modes
- Clean separation between export logic and user interface

## Comparison with k8s-resource-copy

### Key Differences
- **Purpose**: Export vs Copy - focused on extracting resources rather than copying between clusters
- **Multi-namespace**: Designed for bulk export operations across multiple namespaces
- **Output Organization**: Structured directory layout with namespace separation
- **Workflow**: Simplified workflow focused on export rather than complex copy operations
- **Use Cases**: Backup, migration preparation, resource auditing, and documentation

### Shared Features
- kubectl neat integration
- Interactive resource selection
- Context switching support
- Comprehensive error handling
- OpsKit integration with logging and interactive components