#!/usr/bin/fish

# Fish shell configuration and utilities
# Fish-specific syntax and features

# Set environment variables
set -gx EDITOR vim
set -gx BROWSER firefox
set -gx TERM xterm-256color

# Custom variables
set -g fish_greeting "Welcome to the development environment!"
set -g project_root $HOME/projects

# Function: Setup development environment
function setup_dev_env --description "Setup development environment with all tools"
    echo "Setting up development environment..."
    
    # Create project directories
    for dir in $project_root/{frontend,backend,scripts,docs}
        mkdir -p $dir
        echo "Created directory: $dir"
    end
    
    # Install development tools
    if command -q npm
        echo "Installing Node.js packages..."
        npm install -g typescript eslint prettier
    end
    
    if command -q pip
        echo "Installing Python packages..."
        pip install --user black flake8 pytest
    end
    
    echo "Development environment setup complete!"
end

# Function: Project management
function project --description "Manage development projects"
    set -l action $argv[1]
    set -l name $argv[2]
    
    switch $action
        case create
            if test -z "$name"
                echo "Error: Project name required"
                return 1
            end
            
            set -l project_dir $project_root/$name
            mkdir -p $project_dir/{src,tests,docs,scripts}
            
            # Initialize Git repository
            cd $project_dir
            git init
            
            # Create basic files
            echo "# $name" > README.md
            echo "node_modules/\n*.pyc\n__pycache__/" > .gitignore
            
            echo "Project '$name' created at $project_dir"
            
        case list
            echo "Available projects:"
            for project in $project_root/*
                if test -d $project
                    set -l project_name (basename $project)
                    set -l git_status ""
                    
                    if test -d $project/.git
                        set git_status " (git)"
                    end
                    
                    echo "  $project_name$git_status"
                end
            end
            
        case switch
            if test -z "$name"
                echo "Error: Project name required"
                return 1
            end
            
            set -l project_dir $project_root/$name
            if test -d $project_dir
                cd $project_dir
                echo "Switched to project: $name"
            else
                echo "Error: Project '$name' not found"
                return 1
            end
            
        case remove
            if test -z "$name"
                echo "Error: Project name required"
                return 1
            end
            
            set -l project_dir $project_root/$name
            if test -d $project_dir
                echo "Are you sure you want to remove project '$name'? (y/N)"
                read -l confirm
                
                if test "$confirm" = "y" -o "$confirm" = "Y"
                    rm -rf $project_dir
                    echo "Project '$name' removed"
                else
                    echo "Operation cancelled"
                end
            else
                echo "Error: Project '$name' not found"
                return 1
            end
            
        case '*'
            echo "Usage: project {create|list|switch|remove} [name]"
            return 1
    end
end

# Function: Git helpers
function git_status_all --description "Show git status for all projects"
    echo "Git status for all projects:"
    
    for project in $project_root/*
        if test -d $project/.git
            set -l project_name (basename $project)
            echo ""
            echo "=== $project_name ==="
            
            cd $project
            
            set -l status (git status --porcelain)
            if test -n "$status"
                git status --short
            else
                echo "Clean working directory"
            end
            
            # Check for unpushed commits
            set -l unpushed (git log --oneline @{u}.. 2>/dev/null)
            if test -n "$unpushed"
                echo "Unpushed commits: "(echo $unpushed | wc -l)
            end
        end
    end
end

# Function: Docker management
function docker_cleanup --description "Clean up Docker resources"
    echo "Cleaning up Docker resources..."
    
    # Remove stopped containers
    set -l stopped_containers (docker ps -aq --filter status=exited)
    if test -n "$stopped_containers"
        docker rm $stopped_containers
        echo "Removed stopped containers"
    end
    
    # Remove dangling images
    set -l dangling_images (docker images -qf dangling=true)
    if test -n "$dangling_images"
        docker rmi $dangling_images
        echo "Removed dangling images"
    end
    
    # Remove unused volumes
    docker volume prune -f
    echo "Removed unused volumes"
    
    # Remove unused networks
    docker network prune -f
    echo "Removed unused networks"
    
    echo "Docker cleanup complete!"
end

# Function: System monitoring
function monitor_system --description "Monitor system resources"
    set -l duration 60
    if test -n "$argv[1]"
        set duration $argv[1]
    end
    
    echo "Monitoring system for $duration seconds..."
    
    set -l start_time (date +%s)
    set -l end_time (math $start_time + $duration)
    
    while test (date +%s) -lt $end_time
        clear
        echo "=== System Monitor ==="
        echo "Time: "(date)
        echo ""
        
        # CPU usage
        echo "CPU Usage:"
        top -bn1 | grep "Cpu(s)" | awk '{print $2}' | tr -d '%us,'
        
        # Memory usage
        echo "Memory Usage:"
        free -h | grep "Mem:"
        
        # Disk usage
        echo "Disk Usage:"
        df -h | grep -E '^/dev/'
        
        # Network activity
        echo "Network Activity:"
        cat /proc/net/dev | grep -E "(eth|wlan|enp)" | head -3
        
        sleep 5
    end
end

# Function: Log analysis
function analyze_logs --description "Analyze system logs"
    set -l log_type $argv[1]
    set -l lines 50
    
    if test -n "$argv[2]"
        set lines $argv[2]
    end
    
    switch $log_type
        case system
            echo "=== System Logs (last $lines lines) ==="
            journalctl -n $lines --no-pager
            
        case auth
            echo "=== Authentication Logs ==="
            tail -n $lines /var/log/auth.log | grep -E "(Failed|Invalid|Error)"
            
        case nginx
            echo "=== Nginx Error Logs ==="
            if test -f /var/log/nginx/error.log
                tail -n $lines /var/log/nginx/error.log
            else
                echo "Nginx error log not found"
            end
            
        case apache
            echo "=== Apache Error Logs ==="
            if test -f /var/log/apache2/error.log
                tail -n $lines /var/log/apache2/error.log
            else
                echo "Apache error log not found"
            end
            
        case '*'
            echo "Usage: analyze_logs {system|auth|nginx|apache} [lines]"
            return 1
    end
end

# Function: Network utilities
function net_utils --description "Network utility functions"
    set -l action $argv[1]
    
    switch $action
        case scan
            set -l target $argv[2]
            if test -z "$target"
                set target "192.168.1.0/24"
            end
            
            echo "Scanning network: $target"
            if command -q nmap
                nmap -sn $target
            else
                echo "nmap not installed"
                return 1
            end
            
        case ports
            set -l host $argv[2]
            if test -z "$host"
                set host "localhost"
            end
            
            echo "Checking open ports on $host"
            if command -q nmap
                nmap -F $host
            else
                echo "nmap not installed"
                return 1
            end
            
        case connections
            echo "Active network connections:"
            netstat -tuln | grep LISTEN
            
        case speed
            echo "Testing internet speed..."
            if command -q speedtest-cli
                speedtest-cli
            else
                echo "speedtest-cli not installed"
                return 1
            end
            
        case '*'
            echo "Usage: net_utils {scan|ports|connections|speed} [target]"
            return 1
    end
end

# Function: File utilities
function file_utils --description "File and directory utilities"
    set -l action $argv[1]
    
    switch $action
        case find_large
            set -l size $argv[2]
            if test -z "$size"
                set size "100M"
            end
            
            echo "Finding files larger than $size"
            find . -type f -size +$size -exec ls -lh {} \; | sort -k5 -hr
            
        case find_duplicates
            echo "Finding duplicate files (by MD5)..."
            find . -type f -exec md5sum {} \; | sort | uniq -d -w32
            
        case cleanup_temp
            echo "Cleaning up temporary files..."
            find /tmp -type f -atime +7 -delete 2>/dev/null
            find $HOME/.cache -type f -atime +30 -delete 2>/dev/null
            echo "Temporary files cleaned"
            
        case backup_config
            set -l backup_dir $HOME/config_backup_(date +%Y%m%d)
            mkdir -p $backup_dir
            
            # Backup important config files
            for config in $HOME/.bashrc $HOME/.zshrc $HOME/.vimrc $HOME/.gitconfig
                if test -f $config
                    cp $config $backup_dir/
                end
            end
            
            echo "Configuration files backed up to $backup_dir"
            
        case '*'
            echo "Usage: file_utils {find_large|find_duplicates|cleanup_temp|backup_config} [args]"
            return 1
    end
end

# Aliases for common operations
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'
alias grep='grep --color=auto'
alias df='df -h'
alias du='du -h'
alias free='free -h'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline'
alias gd='git diff'

# Docker aliases
alias dc='docker-compose'
alias dcup='docker-compose up -d'
alias dcdown='docker-compose down'
alias dcps='docker-compose ps'

# Custom prompt
function fish_prompt
    set -l last_status $status
    
    # Show current directory
    echo -n (set_color blue)(prompt_pwd)(set_color normal)
    
    # Show git branch if in git repo
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1
        set -l branch (git branch --show-current 2>/dev/null)
        if test -n "$branch"
            echo -n (set_color yellow)" ($branch)"(set_color normal)
        end
    end
    
    # Show status
    if test $last_status -ne 0
        echo -n (set_color red)" [$last_status]"(set_color normal)
    end
    
    echo -n ' $ '
end

# Initialize environment on shell start
if status is-interactive
    echo $fish_greeting
    
    # Check for updates
    if test -f $HOME/.config/fish/last_update
        set -l last_update (cat $HOME/.config/fish/last_update)
        set -l current_time (date +%s)
        set -l time_diff (math $current_time - $last_update)
        
        # Check once per day (86400 seconds)
        if test $time_diff -gt 86400
            echo "Checking for system updates..."
            echo $current_time > $HOME/.config/fish/last_update
        end
    else
        echo (date +%s) > $HOME/.config/fish/last_update
    end
end