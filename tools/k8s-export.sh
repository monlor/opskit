#!/bin/bash

set -euo pipefail

# K8s Resource Export Tool
# Export Kubernetes resources including Helm and non-Helm managed resources

# Default export directory - can be overridden by environment variable or flag
DEFAULT_EXPORT_DIR="$HOME/Downloads"
EXPORT_BASE_DIR="${OPSKIT_K8S_EXPORT_DIR:-$DEFAULT_EXPORT_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
EXPORT_DIR="$EXPORT_BASE_DIR/k8s-export-$TIMESTAMP"
HELM_DIR="$EXPORT_DIR/helm-values"
RESOURCE_DIR="$EXPORT_DIR/non-helm-resources"
INSTALL_FILE="$EXPORT_DIR/helm-install-all.sh"

# Configurable exclude patterns
HELM_EXCLUDE_REGEX="${OPSKIT_HELM_EXCLUDE_REGEX:-}"
K8S_EXCLUDE_REGEX="${OPSKIT_K8S_EXCLUDE_REGEX:-^(.*role-template-.*|.*helm.release.*|.*kube-root-ca.*|secret/default-token-.*|serviceaccount/default)$}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage
show_usage() {
    cat << EOF
K8s Resource Export Tool

USAGE:
    $(basename "$0") <command> [options]

COMMANDS:
    export              Export all resources (default - interactive mode)
    helm-only           Export only Helm resources (interactive mode)
    resources-only      Export only non-Helm resources (interactive mode)
    check               Check prerequisites and configuration

OPTIONS:
    --namespace, -n <ns>         Target namespace (skip interactive namespace selection)
    --all-namespaces, -A         Export from all namespaces (skip interactive selection)
    --output-dir, -o <dir>       Export directory (skip interactive directory selection)
    --dry-run                    Show what would be exported without actually exporting
    --exclude-helm <regex>       Regex pattern to exclude Helm releases
    --exclude-k8s <regex>        Regex pattern to exclude K8s resources
    --non-interactive            Run in non-interactive mode with current settings
    --help, -h                   Show this help

INTERACTIVE MODE (default):
    - Select namespace or all namespaces
    - Review and confirm cluster information
    - Choose export directory (with default suggestion)
    - Confirm export settings before proceeding

EXAMPLES:
    $(basename "$0") export                                    # Interactive mode
    $(basename "$0") export --namespace kube-system           # Export specific namespace
    $(basename "$0") export --all-namespaces                 # Export all namespaces
    $(basename "$0") export --output-dir /tmp/k8s-backup     # Custom directory
    $(basename "$0") export --non-interactive                # Skip all prompts

ENVIRONMENT VARIABLES:
    OPSKIT_K8S_EXPORT_DIR        Default export directory
    OPSKIT_HELM_EXCLUDE_REGEX    Default Helm exclude pattern
    OPSKIT_K8S_EXCLUDE_REGEX     Default K8s exclude pattern
EOF
}

# Check prerequisites
check_prerequisites() {
    local missing_deps=()
    
    if ! command -v kubectl >/dev/null 2>&1; then
        missing_deps+=("kubectl")
    fi
    
    if ! command -v helm >/dev/null 2>&1; then
        missing_deps+=("helm")
    fi
    
    if ! command -v yq >/dev/null 2>&1; then
        missing_deps+=("yq")
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_info "Please install the missing dependencies and try again"
        return 1
    fi
    
    # Test kubectl connectivity
    if ! kubectl cluster-info >/dev/null 2>&1; then
        log_error "Cannot connect to Kubernetes cluster"
        log_info "Please check your kubeconfig and cluster connectivity"
        return 1
    fi
    
    log_success "All prerequisites are met"
    return 0
}

# Parse command line arguments
parse_args() {
    COMMAND="${1:-export}"
    shift 2>/dev/null || true
    
    NAMESPACE=""
    OUTPUT_DIR=""
    DRY_RUN=false
    ALL_NAMESPACES=false
    NON_INTERACTIVE=false
    CUSTOM_HELM_EXCLUDE=""
    CUSTOM_K8S_EXCLUDE=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --namespace|-n)
                NAMESPACE="$2"
                shift 2
                ;;
            --all-namespaces|-A)
                ALL_NAMESPACES=true
                shift
                ;;
            --output-dir|-o)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --exclude-helm)
                CUSTOM_HELM_EXCLUDE="$2"
                shift 2
                ;;
            --exclude-k8s)
                CUSTOM_K8S_EXCLUDE="$2"
                shift 2
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Override defaults with custom values
    if [[ -n "$OUTPUT_DIR" ]]; then
        EXPORT_BASE_DIR="$OUTPUT_DIR"
        EXPORT_DIR="$EXPORT_BASE_DIR/k8s-export-$TIMESTAMP"
        HELM_DIR="$EXPORT_DIR/helm-values"
        RESOURCE_DIR="$EXPORT_DIR/non-helm-resources"
        INSTALL_FILE="$EXPORT_DIR/helm-install-all.sh"
    fi
    
    if [[ -n "$CUSTOM_HELM_EXCLUDE" ]]; then
        HELM_EXCLUDE_REGEX="$CUSTOM_HELM_EXCLUDE"
    fi
    
    if [[ -n "$CUSTOM_K8S_EXCLUDE" ]]; then
        K8S_EXCLUDE_REGEX="$CUSTOM_K8S_EXCLUDE"
    fi
}

# Show cluster information
show_cluster_info() {
    log_info "当前 Kubernetes 集群信息："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Get cluster info
    local cluster_info
    cluster_info=$(kubectl config current-context 2>/dev/null || echo "unknown")
    echo "🏭 集群上下文: ${BLUE}${cluster_info}${NC}"
    
    # Get cluster server
    local server
    server=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null || echo "unknown")
    echo "🌐 集群地址: ${BLUE}${server}${NC}"
    
    # Get current user
    local user
    user=$(kubectl config view --minify -o jsonpath='{.users[0].name}' 2>/dev/null || echo "unknown")
    echo "👤 用户: ${BLUE}${user}${NC}"
    
    # Get current namespace
    local current_ns
    current_ns=$(kubectl config view --minify -o jsonpath='{..namespace}' 2>/dev/null || echo "default")
    echo "📁 默认命名空间: ${BLUE}${current_ns:-default}${NC}"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Interactive namespace selection
select_namespace() {
    if [[ "$ALL_NAMESPACES" == true ]]; then
        echo "all-namespaces"
        return 0
    fi
    
    if [[ -n "$NAMESPACE" ]]; then
        echo "$NAMESPACE"
        return 0
    fi
    
    if [[ "$NON_INTERACTIVE" == true ]]; then
        local ns
        ns=$(kubectl config view --minify -o jsonpath='{..namespace}' 2>/dev/null || echo "default")
        echo "${ns:-default}"
        return 0
    fi
    
    log_info "请选择要导出的命名空间："
    echo ""
    
    # Get available namespaces
    local namespaces
    if ! namespaces=$(kubectl get namespaces -o name 2>/dev/null | sed 's/namespace\///'); then
        log_error "无法获取命名空间列表"
        return 1
    fi
    
    local current_ns
    current_ns=$(kubectl config view --minify -o jsonpath='{..namespace}' 2>/dev/null || echo "default")
    current_ns="${current_ns:-default}"
    
    echo "可用选项："
    echo "0. 所有命名空间 (--all-namespaces)"
    echo "1. 当前命名空间: ${BLUE}${current_ns}${NC} [推荐]"
    
    # Build namespace list and display options
    local ns_array=("all-namespaces" "$current_ns")
    local index=2
    
    while read -r ns; do
        if [[ -n "$ns" && "$ns" != "$current_ns" ]]; then
            echo "$index. $ns"
            ns_array+=("$ns")
            ((index++))
        fi
    done <<< "$namespaces"
    
    echo ""
    while true; do
        read -p "请选择 (0-$((${#ns_array[@]}-1))) [默认: 1]: " choice
        choice=${choice:-1}
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [[ "$choice" -ge 0 ]] && [[ "$choice" -lt "${#ns_array[@]}" ]]; then
            echo "${ns_array[$choice]}"
            return 0
        else
            log_error "无效选择，请输入 0-$((${#ns_array[@]}-1)) 之间的数字"
        fi
    done
}

# Interactive export directory selection
select_export_directory() {
    if [[ -n "$OUTPUT_DIR" ]]; then
        return 0  # Directory already set via command line
    fi
    
    if [[ "$NON_INTERACTIVE" == true ]]; then
        return 0  # Use default directory
    fi
    
    log_info "请选择导出目录："
    echo ""
    echo "默认目录: ${BLUE}${EXPORT_BASE_DIR}${NC}"
    echo ""
    
    while true; do
        read -p "使用默认目录？[Y/n] 或输入自定义路径: " dir_choice
        
        if [[ -z "$dir_choice" ]] || [[ "$dir_choice" =~ ^[Yy]$ ]]; then
            # Use default directory
            break
        elif [[ "$dir_choice" =~ ^[Nn]$ ]]; then
            # Ask for custom directory
            read -p "请输入自定义导出目录: " custom_dir
            if [[ -n "$custom_dir" ]]; then
                # Expand ~ to home directory
                custom_dir="${custom_dir/#\~/$HOME}"
                EXPORT_BASE_DIR="$custom_dir"
                EXPORT_DIR="$EXPORT_BASE_DIR/k8s-export-$TIMESTAMP"
                HELM_DIR="$EXPORT_DIR/helm-values"
                RESOURCE_DIR="$EXPORT_DIR/non-helm-resources"
                INSTALL_FILE="$EXPORT_DIR/helm-install-all.sh"
                log_success "导出目录已设置为: ${EXPORT_BASE_DIR}"
                break
            else
                log_error "目录不能为空"
            fi
        else
            # Treat as custom directory path
            dir_choice="${dir_choice/#\~/$HOME}"
            EXPORT_BASE_DIR="$dir_choice"
            EXPORT_DIR="$EXPORT_BASE_DIR/k8s-export-$TIMESTAMP"
            HELM_DIR="$EXPORT_DIR/helm-values"
            RESOURCE_DIR="$EXPORT_DIR/non-helm-resources"
            INSTALL_FILE="$EXPORT_DIR/helm-install-all.sh"
            log_success "导出目录已设置为: ${EXPORT_BASE_DIR}"
            break
        fi
    done
}

# Confirm export settings
confirm_export_settings() {
    if [[ "$NON_INTERACTIVE" == true ]]; then
        return 0
    fi
    
    local selected_ns="$1"
    
    log_info "导出设置确认："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 导出类型: ${BLUE}${COMMAND}${NC}"
    
    if [[ "$selected_ns" == "all-namespaces" ]]; then
        echo "📁 命名空间: ${YELLOW}所有命名空间${NC}"
    else
        echo "📁 命名空间: ${BLUE}${selected_ns}${NC}"
    fi
    
    echo "📂 导出目录: ${BLUE}${EXPORT_DIR}${NC}"
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "🔍 模式: ${YELLOW}试运行 (不实际导出)${NC}"
    else
        echo "🔍 模式: ${GREEN}实际导出${NC}"
    fi
    
    if [[ -n "$HELM_EXCLUDE_REGEX" ]]; then
        echo "⚠️  Helm排除规则: ${YELLOW}${HELM_EXCLUDE_REGEX}${NC}"
    fi
    
    if [[ -n "$K8S_EXCLUDE_REGEX" ]]; then
        echo "⚠️  K8s排除规则: ${YELLOW}${K8S_EXCLUDE_REGEX}${NC}"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    while true; do
        read -p "确认开始导出？[Y/n]: " confirm
        confirm=${confirm:-Y}
        
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            return 0
        elif [[ "$confirm" =~ ^[Nn]$ ]]; then
            log_info "导出已取消"
            return 1
        else
            log_error "请输入 Y 或 n"
        fi
    done
}

# Get current namespace (fallback function)
get_namespace() {
    if [[ "$ALL_NAMESPACES" == true ]]; then
        echo "all-namespaces"
    elif [[ -n "$NAMESPACE" ]]; then
        echo "$NAMESPACE"
    else
        local ns
        ns=$(kubectl config view --minify -o jsonpath='{..namespace}' 2>/dev/null || echo "default")
        echo "${ns:-default}"
    fi
}

# Confirm export directory
confirm_export_dir() {
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would create export directory: $EXPORT_DIR"
        return 0
    fi
    
    if [[ -d "$EXPORT_DIR" ]]; then
        log_warning "Export directory already exists: $EXPORT_DIR"
        read -p "Remove existing directory and continue? [y/N] " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$EXPORT_DIR"
            log_success "Removed existing directory"
        else
            log_error "Export cancelled"
            return 1
        fi
    fi
    
    mkdir -p "$HELM_DIR" "$RESOURCE_DIR"
    log_success "Created export directory: $EXPORT_DIR"
}

# Export Helm resources
export_helm_resources() {
    local ns="$1"
    
    if [[ "$ns" == "all-namespaces" ]]; then
        log_info "导出所有命名空间的 Helm 资源"
        export_helm_all_namespaces
        return $?
    fi
    
    log_info "导出命名空间 $ns 的 Helm 资源"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[试运行] 将创建 Helm 安装脚本: $INSTALL_FILE"
    else
        echo "#!/bin/bash" > "$INSTALL_FILE"
        echo "# Helm installation script generated on $(date)" >> "$INSTALL_FILE"
        echo "# Namespace: $ns" >> "$INSTALL_FILE"
        echo "" >> "$INSTALL_FILE"
    fi
    
    local releases
    if ! releases=$(helm list -n "$ns" -o json 2>/dev/null); then
        log_warning "命名空间 $ns 中未找到 Helm release"
        return 0
    fi
    
    if [[ "$(echo "$releases" | jq '. | length')" -eq 0 ]]; then
        log_warning "命名空间 $ns 中未找到 Helm release"
        return 0
    fi
    
    echo "$releases" | jq -r '.[].name' | while read -r release; do
        export_single_helm_release "$release" "$ns"
    done
    
    if [[ "$DRY_RUN" == false ]] && [[ -f "$INSTALL_FILE" ]]; then
        chmod +x "$INSTALL_FILE"
        log_success "创建 Helm 安装脚本: ${INSTALL_FILE##*/}"
    fi
}

# Export Helm resources from all namespaces
export_helm_all_namespaces() {
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[试运行] 将创建 Helm 安装脚本: $INSTALL_FILE"
    else
        echo "#!/bin/bash" > "$INSTALL_FILE"
        echo "# Helm installation script generated on $(date)" >> "$INSTALL_FILE"
        echo "# All namespaces" >> "$INSTALL_FILE"
        echo "" >> "$INSTALL_FILE"
    fi
    
    local releases
    if ! releases=$(helm list --all-namespaces -o json 2>/dev/null); then
        log_warning "未找到任何 Helm release"
        return 0
    fi
    
    if [[ "$(echo "$releases" | jq '. | length')" -eq 0 ]]; then
        log_warning "未找到任何 Helm release"
        return 0
    fi
    
    echo "$releases" | jq -r '.[] | "\(.name) \(.namespace)"' | while read -r release namespace; do
        export_single_helm_release "$release" "$namespace"
    done
    
    if [[ "$DRY_RUN" == false ]] && [[ -f "$INSTALL_FILE" ]]; then
        chmod +x "$INSTALL_FILE"
        log_success "创建 Helm 安装脚本: ${INSTALL_FILE##*/}"
    fi
}

# Export single Helm release
export_single_helm_release() {
    local release="$1"
    local namespace="$2"
    
    # Skip if matches exclude pattern
    if [[ -n "$HELM_EXCLUDE_REGEX" && "$release" =~ $HELM_EXCLUDE_REGEX ]]; then
        log_warning "跳过 Helm release: $release (匹配排除规则)"
        return
    fi
    
    local values_file="$HELM_DIR/${namespace}_${release}-values.yaml"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[试运行] 将导出 Helm values: $release ($namespace) -> ${values_file##*/}"
    else
        if helm get values "$release" -n "$namespace" > "$values_file" 2>/dev/null; then
            log_success "导出 Helm values: $release ($namespace) -> ${values_file##*/}"
            
            # Get chart info and add install command
            local manifest
            manifest=$(helm get manifest "$release" -n "$namespace" 2>/dev/null || echo "")
            
            local chart="<chart-name>"
            local chart_version="<version>"
            
            if [[ -n "$manifest" ]]; then
                # Try to extract chart info from labels
                chart=$(echo "$manifest" | grep -m1 "app.kubernetes.io/name:" | sed 's/.*app.kubernetes.io\/name: *//; s/"//g' || echo "<chart-name>")
                chart_version=$(echo "$manifest" | grep -m1 "app.kubernetes.io/version:" | sed 's/.*app.kubernetes.io\/version: *//; s/"//g' || echo "<version>")
            fi
            
            echo "helm upgrade --install $release charts/$chart --version $chart_version -f helm-values/${namespace}_${release}-values.yaml --namespace $namespace --create-namespace" >> "$INSTALL_FILE"
        else
            log_error "导出 Helm values 失败: $release ($namespace)"
        fi
    fi
}

# Export non-Helm resources
export_k8s_resources() {
    local ns="$1"
    
    if [[ "$ns" == "all-namespaces" ]]; then
        log_info "导出所有命名空间的非 Helm 管理资源"
        export_k8s_all_namespaces
        return $?
    fi
    
    log_info "导出命名空间 $ns 的非 Helm 管理资源"
    
    local resource_types="deployments statefulsets daemonsets services persistentvolumeclaims ingresses serviceaccounts roles rolebindings configmaps secrets"
    
    for resource_type in $resource_types; do
        export_k8s_resource_type "$resource_type" "$ns"
    done
}

# Export K8s resources from all namespaces
export_k8s_all_namespaces() {
    local resource_types="deployments statefulsets daemonsets services persistentvolumeclaims ingresses serviceaccounts roles rolebindings configmaps secrets"
    
    for resource_type in $resource_types; do
        log_info "处理所有命名空间的资源类型: $resource_type"
        
        local resources
        if ! resources=$(kubectl get "$resource_type" --all-namespaces -o json 2>/dev/null); then
            continue
        fi
        
        if [[ "$(echo "$resources" | jq '.items | length')" -eq 0 ]]; then
            continue
        fi
        
        echo "$resources" | jq -r '.items[] | "\(.metadata.name) \(.metadata.namespace)"' | while read -r resource_name resource_ns; do
            export_single_k8s_resource "$resource_type/$resource_name" "$resource_ns"
        done
    done
}

# Export single resource type from namespace
export_k8s_resource_type() {
    local resource_type="$1"
    local ns="$2"
    
    log_info "处理资源类型: $resource_type (命名空间: $ns)"
    
    local resources
    if ! resources=$(kubectl get "$resource_type" -n "$ns" -o name 2>/dev/null); then
        return
    fi
    
    if [[ -z "$resources" ]]; then
        return
    fi
    
    echo "$resources" | while read -r resource; do
        export_single_k8s_resource "$resource" "$ns"
    done
}

# Export single K8s resource
export_single_k8s_resource() {
    local resource="$1"
    local namespace="$2"
    
    # Skip if matches exclude pattern
    if [[ -n "$K8S_EXCLUDE_REGEX" && "$resource" =~ $K8S_EXCLUDE_REGEX ]]; then
        log_warning "跳过资源: $resource (匹配排除规则)"
        return
    fi
    
    # Check if resource is managed by Helm
    local is_helm_managed
    is_helm_managed=$(kubectl get "$resource" -n "$namespace" -o json 2>/dev/null | jq -r '.metadata.labels["app.kubernetes.io/managed-by"] // "none"')
    
    if [[ "$is_helm_managed" == "Helm" ]]; then
        log_info "跳过 Helm 管理的资源: $resource"
        return
    fi
    
    local filename="$RESOURCE_DIR/${namespace}_${resource//\//_}.yaml"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[试运行] 将导出资源: $resource ($namespace) -> ${filename##*/}"
    else
        if kubectl get "$resource" -n "$namespace" -o yaml 2>/dev/null | \
           yq eval 'del(
               .metadata.uid,
               .metadata.resourceVersion,
               .metadata.namespace,
               .metadata.annotations."kubectl.kubernetes.io/last-applied-configuration",
               .metadata.creationTimestamp,
               .status,
               .spec.clusterIP,
               .spec.clusterIPs,
               .spec.ports[].nodePort
           )' - > "$filename"; then
            log_success "导出资源: $resource ($namespace) -> ${filename##*/}"
        else
            log_error "导出资源失败: $resource ($namespace)"
        fi
    fi
}

# Main export function
do_export() {
    # Interactive mode
    if [[ "$NON_INTERACTIVE" == false ]]; then
        # Show cluster information and get confirmation
        show_cluster_info
        echo ""
        read -p "确认连接到正确的集群？[Y/n]: " cluster_confirm
        cluster_confirm=${cluster_confirm:-Y}
        if [[ ! "$cluster_confirm" =~ ^[Yy]$ ]]; then
            log_error "用户取消操作"
            return 1
        fi
        
        # Interactive namespace selection
        local selected_ns
        selected_ns=$(select_namespace)
        if [[ $? -ne 0 ]]; then
            return 1
        fi
        
        # Interactive directory selection
        select_export_directory
        
        # Confirm export settings
        if ! confirm_export_settings "$selected_ns"; then
            return 1
        fi
    else
        local selected_ns
        selected_ns=$(get_namespace)
    fi
    
    # Use selected namespace if in interactive mode
    local ns="${selected_ns:-$(get_namespace)}"
    
    if [[ "$ns" == "all-namespaces" ]]; then
        log_info "开始导出所有命名空间的 K8s 资源"
    else
        log_info "开始导出命名空间 $ns 的 K8s 资源"
    fi
    
    log_info "导出目录: $EXPORT_DIR"
    
    if [[ -n "$HELM_EXCLUDE_REGEX" ]]; then
        log_info "Helm 排除规则: $HELM_EXCLUDE_REGEX"
    fi
    
    if [[ -n "$K8S_EXCLUDE_REGEX" ]]; then
        log_info "K8s 排除规则: $K8S_EXCLUDE_REGEX"
    fi
    
    if ! confirm_export_dir; then
        return 1
    fi
    
    case "$COMMAND" in
        export)
            export_helm_resources "$ns"
            export_k8s_resources "$ns"
            ;;
        helm-only)
            export_helm_resources "$ns"
            ;;
        resources-only)
            export_k8s_resources "$ns"
            ;;
    esac
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[试运行] 导出模拟完成"
    else
        log_success "导出成功完成!"
        echo ""
        log_info "📂 导出目录: ${BLUE}$EXPORT_DIR${NC}"
        if [[ -f "$INSTALL_FILE" ]]; then
            log_info "🚀 Helm 安装脚本: ${BLUE}${INSTALL_FILE##*/}${NC}"
        fi
        if [[ "$ns" == "all-namespaces" ]]; then
            log_info "📋 导出了所有命名空间的资源"
        else
            log_info "📋 导出了命名空间 ${BLUE}$ns${NC} 的资源"
        fi
    fi
}

# Show configuration
show_config() {
    log_info "K8s Export Tool Configuration"
    echo "================================"
    echo "Current namespace: $(get_namespace)"
    echo "Export base directory: $EXPORT_BASE_DIR"
    echo "Export directory: $EXPORT_DIR"
    echo "Helm exclude pattern: ${HELM_EXCLUDE_REGEX:-<none>}"
    echo "K8s exclude pattern: ${K8S_EXCLUDE_REGEX:-<default>}"
    echo "================================"
}

# Main function
main() {
    parse_args "$@"
    
    case "$COMMAND" in
        check)
            show_config
            check_prerequisites
            ;;
        export|helm-only|resources-only)
            if ! check_prerequisites; then
                exit 1
            fi
            do_export
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi