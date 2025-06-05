#!/usr/bin/zsh

# System administration utilities
# ZSH-specific features and syntax

# ZSH options
setopt EXTENDED_GLOB
setopt NULL_GLOB
setopt INTERACTIVE_COMMENTS

# Global variables
typeset -A SYSTEM_SERVICES=(
    nginx /etc/nginx/nginx.conf
    apache2 /etc/apache2/apache2.conf
    mysql /etc/mysql/my.cnf
    postgresql /etc/postgresql/*/main/postgresql.conf
)

typeset -a LOG_DIRS=(
    /var/log/nginx
    /var/log/apache2
    /var/log/mysql
    /var/log/postgresql
)

# Function: Check system resources
function check_system_resources() {
    echo "=== System Resource Check ==="
    
    # Memory usage
    local mem_usage=$(free | awk 'NR==2{printf "%.2f%%", $3*100/$2}')
    echo "Memory Usage: $mem_usage"
    
    # Disk usage
    echo "Disk Usage:"
    df -h | grep -E '^/dev/' | while read -r line; do
        echo "  $line"
    done
    
    # CPU load
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | tr -d ' ')
    echo "Load Average: $load_avg"
    
    # Network connections
    local conn_count=$(netstat -nt | grep ESTABLISHED | wc -l)
    echo "Active Connections: $conn_count"
}

# Function: Service management
function manage_service() {
    local action="$1"
    local service="$2"
    
    if [[ -z "$service" ]]; then
        echo "Available services: ${(k)SYSTEM_SERVICES[@]}"
        return 1
    fi
    
    case "$action" in
        start|stop|restart|status)
            systemctl "$action" "$service"
            ;;
        config)
            local config_file="${SYSTEM_SERVICES[$service]}"
            if [[ -n "$config_file" && -f "$config_file" ]]; then
                $EDITOR "$config_file"
            else
                echo "Config file not found for $service"
            fi
            ;;
        logs)
            journalctl -u "$service" -f
            ;;
        *)
            echo "Unknown action: $action"
            echo "Available actions: start, stop, restart, status, config, logs"
            ;;
    esac
}

# Function: Log analysis
function analyze_logs() {
    local service="$1"
    local lines="${2:-100}"
    
    case "$service" in
        nginx)
            echo "=== Nginx Error Analysis ==="
            tail -n "$lines" /var/log/nginx/error.log | \
                grep -E "(error|warn)" | \
                sort | uniq -c | sort -nr
            ;;
        apache2)
            echo "=== Apache Error Analysis ==="
            tail -n "$lines" /var/log/apache2/error.log | \
                grep -E "(error|warn)" | \
                sort | uniq -c | sort -nr
            ;;
        all)
            for dir in "${LOG_DIRS[@]}"; do
                if [[ -d "$dir" ]]; then
                    echo "=== Analyzing $dir ==="
                    find "$dir" -name "*.log" -mtime -1 | \
                        xargs grep -l "error\|Error\|ERROR" 2>/dev/null | \
                        head -5
                fi
            done
            ;;
    esac
}

# Function: Security audit
function security_audit() {
    echo "=== Security Audit ==="
    
    # Check for failed login attempts
    echo "Recent failed login attempts:"
    grep "Failed password" /var/log/auth.log | tail -10
    
    # Check for suspicious processes
    echo "Processes with unusual network activity:"
    netstat -tulnp | grep -E ":80|:443|:22|:3389" | grep -v "127.0.0.1"
    
    # Check file permissions on sensitive files
    echo "Checking critical file permissions:"
    local critical_files=(
        /etc/passwd
        /etc/shadow
        /etc/sudoers
        /root/.ssh/authorized_keys
    )
    
    for file in "${critical_files[@]}"; do
        if [[ -f "$file" ]]; then
            ls -la "$file"
        fi
    done
    
    # Check for SUID files
    echo "SUID files (potential security risk):"
    find /usr -perm -4000 -type f 2>/dev/null | head -10
}

# Function: Backup management
function backup_manager() {
    local action="$1"
    local target="$2"
    
    local backup_dir="/backup"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    
    case "$action" in
        create)
            if [[ -z "$target" ]]; then
                echo "Please specify backup target"
                return 1
            fi
            
            local backup_file="${backup_dir}/backup_${target##*/}_${timestamp}.tar.gz"
            mkdir -p "$backup_dir"
            
            echo "Creating backup of $target..."
            tar -czf "$backup_file" -C "$(dirname "$target")" "$(basename "$target")"
            
            if [[ $? -eq 0 ]]; then
                echo "Backup created: $backup_file"
                # Calculate and store checksum
                sha256sum "$backup_file" > "${backup_file}.sha256"
            else
                echo "Backup failed!"
                return 1
            fi
            ;;
        list)
            echo "Available backups:"
            find "$backup_dir" -name "*.tar.gz" -printf "%TY-%Tm-%Td %TH:%TM %s %p\n" | sort -r
            ;;
        restore)
            if [[ -z "$target" ]]; then
                echo "Please specify backup file to restore"
                return 1
            fi
            
            local restore_dir="/restore_${timestamp}"
            mkdir -p "$restore_dir"
            
            echo "Restoring backup $target to $restore_dir..."
            tar -xzf "$target" -C "$restore_dir"
            
            if [[ $? -eq 0 ]]; then
                echo "Backup restored to: $restore_dir"
            else
                echo "Restore failed!"
                return 1
            fi
            ;;
        cleanup)
            local days_old="${target:-30}"
            echo "Cleaning up backups older than $days_old days..."
            find "$backup_dir" -name "*.tar.gz" -mtime +$days_old -delete
            find "$backup_dir" -name "*.sha256" -mtime +$days_old -delete
            ;;
    esac
}

# Function: Performance monitoring
function performance_monitor() {
    local duration="${1:-60}"
    local interval="${2:-5}"
    
    echo "Monitoring system performance for ${duration}s (interval: ${interval}s)"
    
    local end_time=$((SECONDS + duration))
    
    while [[ $SECONDS -lt $end_time ]]; do
        local timestamp=$(date '+%H:%M:%S')
        local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | tr -d '%us,')
        local mem_usage=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
        local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
        
        printf "%s | CPU: %5.1f%% | Memory: %5.1f%% | Load: %s\n" \
               "$timestamp" "$cpu_usage" "$mem_usage" "$load_avg"
        
        sleep "$interval"
    done
}

# Function: Network diagnostics
function network_diagnostics() {
    local target_host="$1"
    
    if [[ -z "$target_host" ]]; then
        target_host="8.8.8.8"
    fi
    
    echo "=== Network Diagnostics for $target_host ==="
    
    # Ping test
    echo "Ping test:"
    ping -c 4 "$target_host"
    
    # Traceroute
    echo "Traceroute:"
    traceroute "$target_host" 2>/dev/null || echo "Traceroute not available"
    
    # DNS resolution
    echo "DNS resolution:"
    nslookup "$target_host"
    
    # Port scan (if nmap is available)
    if command -v nmap &> /dev/null; then
        echo "Port scan (common ports):"
        nmap -F "$target_host" 2>/dev/null
    fi
}

# ZSH completion function
function _sysadmin_complete() {
    local commands=(
        "resources:Check system resources"
        "service:Manage system services"
        "logs:Analyze log files"
        "security:Run security audit"
        "backup:Backup management"
        "monitor:Performance monitoring"
        "network:Network diagnostics"
    )
    
    _describe 'commands' commands
}

compdef _sysadmin_complete sysadmin

# Main function
function main() {
    local command="$1"
    shift
    
    case "$command" in
        resources|res)
            check_system_resources
            ;;
        service|svc)
            manage_service "$@"
            ;;
        logs|log)
            analyze_logs "$@"
            ;;
        security|sec)
            security_audit
            ;;
        backup|bak)
            backup_manager "$@"
            ;;
        monitor|mon)
            performance_monitor "$@"
            ;;
        network|net)
            network_diagnostics "$@"
            ;;
        *)
            cat <<EOF
System Administration Utilities

Usage: $0 COMMAND [OPTIONS]

Commands:
    resources (res)     - Check system resources
    service (svc)       - Manage system services
    logs (log)          - Analyze log files
    security (sec)      - Run security audit
    backup (bak)        - Backup management
    monitor (mon)       - Performance monitoring
    network (net)       - Network diagnostics

Examples:
    $0 resources
    $0 service restart nginx
    $0 logs nginx 200
    $0 backup create /etc
    $0 monitor 120 10
    $0 network google.com
EOF
            ;;
    esac
}

# ZSH-specific error handling
set -o errexit
set -o nounset

# Run main function if script is executed directly
if [[ "${ZSH_EVAL_CONTEXT:-}" == "toplevel" ]]; then
    main "$@"
fi