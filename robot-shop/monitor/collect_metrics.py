import socket
import json
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

SOCKET_PATH = "/var/run/docker.sock"
CSV_FILE = "/dataset/metrics/container_stats.csv"

def docker_get(path):
    """Sends HTTP GET request to Docker Unix Socket and parses JSON response."""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(SOCKET_PATH)
        req = f"GET {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode('utf-8'))
        
        response = b""
        while True:
            data = s.recv(8192)
            if not data:
                break
            response += data
        s.close()
        
        parts = response.split(b"\r\n\r\n", 1)
        if len(parts) < 2:
            return None
        
        header, body = parts
        
        # Unchunk HTTP payload if returned by Docker daemon
        if b"transfer-encoding: chunked" in header.lower():
            unchunked = b""
            while body:
                try:
                    lines = body.split(b"\r\n", 1)
                    size_str = lines[0].split(b";")[0].strip()
                    chunk_size = int(size_str, 16)
                    if chunk_size == 0:
                        break
                    rest = lines[1]
                    unchunked += rest[:chunk_size]
                    body = rest[chunk_size + 2:]
                except Exception:
                    break
            body = unchunked
            
        return json.loads(body.decode('utf-8', errors='ignore'))
    except Exception:
        return None

def calculate_cpu_percent(stats):
    """Calculates CPU usage percentage across allocated cores."""
    try:
        cpu_stats = stats.get("cpu_stats", {})
        precpu_stats = stats.get("precpu_stats", {})
        
        cpu_count = cpu_stats.get("online_cpus") or len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", [1]))
        cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get("system_cpu_usage", 0)
        
        if system_delta > 0.0 and cpu_delta > 0.0:
            return (cpu_delta / system_delta) * cpu_count * 100.0
    except Exception:
        pass
    return 0.0

def fetch_container_stats(container_info):
    """Fetches stats for a single container instance."""
    c_id = container_info.get("Id")
    c_name = container_info.get("Names", ["/unknown"])[0].lstrip("/")
    
    stats = docker_get(f"/containers/{c_id}/stats?stream=false")
    if not stats:
        return None
        
    cpu_pct = round(calculate_cpu_percent(stats), 2)
    
    mem_stats = stats.get("memory_stats", {})
    mem_usage = mem_stats.get("usage", 0) / (1024 * 1024)
    mem_limit = mem_stats.get("limit", 1) / (1024 * 1024)
    mem_pct = round((mem_usage / mem_limit) * 100, 2) if mem_limit > 0 else 0.0
    pids = stats.get("pids_stats", {}).get("current", 0)
    
    return (c_name, cpu_pct, mem_usage, mem_limit, mem_pct, pids)

def main():
    os.makedirs("/dataset/metrics", exist_ok=True)
    
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w") as f:
            f.write("timestamp,container_name,cpu_percent,mem_usage_mb,mem_limit_mb,mem_percent,pids\n")

    print("=== Host-side Resource Telemetry Collector Active ===")
    
    while True:
        try:
            containers = docker_get("/containers/json")
            if containers and isinstance(containers, list):
                timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                
                # Query all running containers concurrently in parallel
                with ThreadPoolExecutor(max_workers=20) as executor:
                    results = list(executor.map(fetch_container_stats, containers))
                
                with open(CSV_FILE, "a") as f:
                    for res in results:
                        if res:
                            c_name, cpu_pct, mem_usage, mem_limit, mem_pct, pids = res
                            f.write(f"{timestamp},{c_name},{cpu_pct},{mem_usage:.2f},{mem_limit:.2f},{mem_pct},{pids}\n")
                            
        except Exception as e:
            print(f"Metrics collection exception: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    main()