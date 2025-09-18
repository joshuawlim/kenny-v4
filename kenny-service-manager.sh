#!/bin/bash

# Kenny V4 Service Manager
# Centralized service orchestration for the Kenny V4 ecosystem
# Usage: ./kenny-service-manager.sh [start|stop|status|restart|health|logs]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/kenny-config.json"
PID_DIR="$SCRIPT_DIR/.kenny-pids"
LOG_DIR="$SCRIPT_DIR/.kenny-logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create necessary directories
mkdir -p "$PID_DIR" "$LOG_DIR"

# Utility functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if jq is installed
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        error "jq is required but not installed. Please install jq first."
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        error "curl is required but not installed. Please install curl first."
        exit 1
    fi
}

# Parse configuration
get_services() {
    local service_type="$1"
    jq -r ".services.${service_type} | keys[]" "$CONFIG_FILE" 2>/dev/null || echo ""
}

get_service_config() {
    local service_type="$1"
    local service_name="$2"
    local field="$3"
    jq -r ".services.${service_type}.\"${service_name}\".${field}" "$CONFIG_FILE" 2>/dev/null
}

# Health check functions
check_http_health() {
    local url="$1"
    curl -s -f "$url" > /dev/null 2>&1
}

check_tcp_health() {
    local host_port="$1"
    # Remove tcp:// prefix and parse host:port
    local clean_url=$(echo "$host_port" | sed 's|tcp://||')
    local host=$(echo "$clean_url" | cut -d: -f1)
    local port=$(echo "$clean_url" | cut -d: -f2)
    nc -z "$host" "$port" > /dev/null 2>&1
}

health_check_service() {
    local service_type="$1"
    local service_name="$2"
    
    local health_check=$(get_service_config "$service_type" "$service_name" "health_check")
    
    if [[ -z "$health_check" || "$health_check" == "null" ]]; then
        return 1
    fi
    
    if [[ "$health_check" == http* ]]; then
        check_http_health "$health_check"
    elif [[ "$health_check" == tcp* ]]; then
        check_tcp_health "$health_check"
    else
        return 1
    fi
}

# Service management functions
start_manual_service() {
    local service_name="$1"
    local path=$(get_service_config "manual_services" "$service_name" "path")
    local start_command=$(get_service_config "manual_services" "$service_name" "start_command")
    local port=$(get_service_config "manual_services" "$service_name" "port")
    
    if [[ "$path" == "null" || "$start_command" == "null" ]]; then
        warn "Service $service_name missing path or start_command configuration"
        return 1
    fi
    
    # Check if already running
    local pid_file="$PID_DIR/${service_name}.pid"
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            warn "Service $service_name already running (PID: $pid)"
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    
    # Check if port is in use
    if [[ "$port" != "null" ]] && lsof -i ":$port" > /dev/null 2>&1; then
        error "Port $port is already in use for service $service_name"
        return 1
    fi
    
    log "Starting $service_name..."
    
    # Change to service directory and start
    (
        cd "$SCRIPT_DIR/$path" || exit 1
        nohup $start_command > "$LOG_DIR/${service_name}.log" 2>&1 &
        echo $! > "$pid_file"
    )
    
    # Wait a moment and check if it started successfully
    sleep 2
    local pid=$(cat "$pid_file" 2>/dev/null)
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        success "Started $service_name (PID: $pid)"
        
        # Wait for health check
        log "Waiting for $service_name to be healthy..."
        local attempts=0
        while [[ $attempts -lt 10 ]]; do
            if health_check_service "manual_services" "$service_name"; then
                success "$service_name is healthy"
                return 0
            fi
            sleep 1
            ((attempts++))
        done
        
        warn "$service_name started but health check failed"
        return 0
    else
        error "Failed to start $service_name"
        rm -f "$pid_file"
        return 1
    fi
}

stop_manual_service() {
    local service_name="$1"
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [[ ! -f "$pid_file" ]]; then
        warn "No PID file found for $service_name"
        return 1
    fi
    
    local pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        log "Stopping $service_name (PID: $pid)..."
        kill "$pid"
        
        # Wait for graceful shutdown
        local attempts=0
        while [[ $attempts -lt 10 ]] && kill -0 "$pid" 2>/dev/null; do
            sleep 1
            ((attempts++))
        done
        
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            warn "Force killing $service_name"
            kill -9 "$pid"
        fi
        
        success "Stopped $service_name"
    else
        warn "Process $pid for $service_name not found"
    fi
    
    rm -f "$pid_file"
}

status_manual_service() {
    local service_name="$1"
    local pid_file="$PID_DIR/${service_name}.pid"
    local port=$(get_service_config "manual_services" "$service_name" "port")
    
    printf "%-25s" "$service_name:"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            if health_check_service "manual_services" "$service_name"; then
                echo -e "${GREEN}RUNNING${NC} (PID: $pid, Port: $port) ✅"
            else
                echo -e "${YELLOW}RUNNING${NC} (PID: $pid, Port: $port) ⚠️  Health check failed"
            fi
        else
            echo -e "${RED}STOPPED${NC} (Stale PID: $pid)"
            rm -f "$pid_file"
        fi
    else
        if [[ "$port" != "null" ]] && lsof -i ":$port" > /dev/null 2>&1; then
            echo -e "${YELLOW}UNKNOWN${NC} (Port $port in use by unknown process)"
        else
            echo -e "${RED}STOPPED${NC}"
        fi
    fi
}

status_docker_service() {
    local service_name="$1"
    local port=$(get_service_config "docker_managed" "$service_name" "port")
    local ports=$(get_service_config "docker_managed" "$service_name" "ports")
    
    printf "%-25s" "$service_name:"
    
    # Check if it's a multi-port service
    if [[ "$ports" != "null" ]]; then
        local first_port=$(echo "$ports" | jq -r '.[0]' 2>/dev/null)
        if [[ -n "$first_port" ]] && lsof -i ":$first_port" > /dev/null 2>&1; then
            if health_check_service "docker_managed" "$service_name"; then
                echo -e "${GREEN}RUNNING${NC} (Docker, Ports: $ports) ✅"
            else
                echo -e "${YELLOW}RUNNING${NC} (Docker, Ports: $ports) ⚠️  Health check failed"
            fi
        else
            echo -e "${RED}STOPPED${NC} (Docker)"
        fi
    elif [[ "$port" != "null" ]] && lsof -i ":$port" > /dev/null 2>&1; then
        if health_check_service "docker_managed" "$service_name"; then
            echo -e "${GREEN}RUNNING${NC} (Docker, Port: $port) ✅"
        else
            echo -e "${YELLOW}RUNNING${NC} (Docker, Port: $port) ⚠️  Health check failed"
        fi
    else
        echo -e "${RED}STOPPED${NC} (Docker)"
    fi
}

# Main commands
start_docker_services() {
    log "Starting Docker services..."

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running. Please start Docker Desktop first."
        return 1
    fi

    # Navigate to Docker directory
    if [[ ! -d "$SCRIPT_DIR/local-ai-packaged" ]]; then
        error "local-ai-packaged directory not found"
        return 1
    fi

    cd "$SCRIPT_DIR/local-ai-packaged"

    # Clean up any conflicting containers first
    log "Cleaning up existing containers..."
    docker-compose down --remove-orphans 2>/dev/null || true

    # Force remove specifically conflicting containers
    log "Removing conflicting containers..."
    docker rm -f redis searxng supabase-imgproxy 2>/dev/null || true
    docker container prune -f 2>/dev/null || true

    # Start Docker services
    log "Starting fresh Docker containers..."
    if docker-compose up -d; then
        success "Docker services started"
    else
        error "Failed to start Docker services"
        return 1
    fi
}

cmd_start() {
    log "Starting Kenny V4 services..."

    # Start Docker services first
    start_docker_services

    # Start manual services in dependency order
    local manual_services=($(get_services "manual_services"))
    
    # Start Go bridge first (no dependencies)
    if [[ " ${manual_services[@]} " =~ " whatsapp-go-bridge " ]]; then
        start_manual_service "whatsapp-go-bridge"
    fi
    
    # Start MCP bridge (depends on Go bridge)
    if [[ " ${manual_services[@]} " =~ " whatsapp-mcp-bridge " ]]; then
        start_manual_service "whatsapp-mcp-bridge"
    fi
    
    # Start Cloudflare tunnel (depends on Open-WebUI)
    if [[ " ${manual_services[@]} " =~ " cloudflare-tunnel " ]]; then
        start_manual_service "cloudflare-tunnel"
    fi
    
    success "Kenny V4 service startup completed"
}

stop_docker_services() {
    log "Stopping Docker services..."

    if [[ -d "$SCRIPT_DIR/local-ai-packaged" ]]; then
        cd "$SCRIPT_DIR/local-ai-packaged"
        docker-compose down
        success "Docker services stopped"
    else
        warn "local-ai-packaged directory not found"
    fi
}

cmd_stop() {
    log "Stopping Kenny V4 services..."

    # Stop manual services first
    local manual_services=($(get_services "manual_services"))
    for service in "${manual_services[@]}"; do
        stop_manual_service "$service"
    done

    # Stop Docker services
    stop_docker_services

    success "Kenny V4 services stopped"
}

cmd_status() {
    echo -e "\n${BLUE}=== Kenny V4 Service Status ===${NC}\n"
    
    echo -e "${YELLOW}Docker Managed Services:${NC}"
    local docker_services=($(get_services "docker_managed"))
    for service in "${docker_services[@]}"; do
        status_docker_service "$service"
    done
    
    echo ""
    echo -e "${YELLOW}Manual Services:${NC}"
    local manual_services=($(get_services "manual_services"))
    for service in "${manual_services[@]}"; do
        status_manual_service "$service"
    done
    
    echo ""
    echo -e "${BLUE}Quick URLs:${NC}"
    echo "  Open-WebUI: http://localhost:3000"
    echo "  n8n: http://localhost:5678"
    echo "  WhatsApp Bridge: http://localhost:3004"
    echo "  Public URL: https://ai.youroldmatekenny.com"
}

cmd_restart() {
    log "Restarting Kenny V4 services..."
    cmd_stop
    sleep 2
    cmd_start
}

cmd_health() {
    echo -e "\n${BLUE}=== Kenny V4 Health Check ===${NC}\n"
    
    local all_healthy=true
    
    # Check manual services
    local manual_services=($(get_services "manual_services"))
    for service in "${manual_services[@]}"; do
        printf "%-30s" "$service:"
        if health_check_service "manual_services" "$service"; then
            echo -e "${GREEN}HEALTHY${NC} ✅"
        else
            echo -e "${RED}UNHEALTHY${NC} ❌"
            all_healthy=false
        fi
    done
    
    echo ""
    
    # Check docker services
    local docker_services=($(get_services "docker_managed"))
    for service in "${docker_services[@]}"; do
        printf "%-30s" "$service:"
        if health_check_service "docker_managed" "$service"; then
            echo -e "${GREEN}HEALTHY${NC} ✅"
        else
            echo -e "${RED}UNHEALTHY${NC} ❌"
            all_healthy=false
        fi
    done
    
    echo ""
    if $all_healthy; then
        success "All services are healthy"
    else
        error "Some services are unhealthy"
        exit 1
    fi
}

cmd_logs() {
    local service_name="$1"
    
    if [[ -z "$service_name" ]]; then
        echo "Available log files:"
        ls -la "$LOG_DIR"
        return
    fi
    
    local log_file="$LOG_DIR/${service_name}.log"
    if [[ -f "$log_file" ]]; then
        tail -f "$log_file"
    else
        error "Log file not found for service: $service_name"
        echo "Available services: $(get_services "manual_services" | tr '\n' ' ')"
    fi
}

# Main script
main() {
    check_dependencies
    
    case "${1:-status}" in
        start)
            if [[ "$2" == "docker" ]]; then
                start_docker_services
            else
                cmd_start
            fi
            ;;
        stop)
            cmd_stop
            ;;
        status)
            cmd_status
            ;;
        restart)
            cmd_restart
            ;;
        health)
            cmd_health
            ;;
        logs)
            cmd_logs "$2"
            ;;
        *)
            echo "Kenny V4 Service Manager"
            echo "Usage: $0 [start|stop|status|restart|health|logs [service_name]]"
            echo ""
            echo "Commands:"
            echo "  start   - Start all manual services"
            echo "  stop    - Stop all manual services"
            echo "  status  - Show service status"
            echo "  restart - Restart all services"
            echo "  health  - Run health checks"
            echo "  logs    - Show logs (optionally for specific service)"
            ;;
    esac
}

main "$@"