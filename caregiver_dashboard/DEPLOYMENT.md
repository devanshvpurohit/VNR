# Deployment Guide - SURDAS Caregiver Dashboard v2.0

Production deployment guide for the SURDAS Caregiver Dashboard.

## 📋 Prerequisites

- Node.js 18+ and npm
- Python 3.8+ with SURDAS backend
- Web server (nginx, Apache, or similar) for production
- SSL certificate (recommended for HTTPS)
- Network configuration for WebSocket connections

## 🏗️ Build Options

### Option 1: Development Mode (Local Network)

**Best for**: Testing, local caregivers on same network

```bash
cd caregiver_dashboard
npm install
npm run dev -- --host
```

Access from any device on network:
```
http://[server-ip]:5173
```

**Pros**: 
- Quick setup
- Hot reload for development
- No build step needed

**Cons**:
- Not optimized
- Not suitable for production
- Requires dev server running

---

### Option 2: Production Build (Recommended)

**Best for**: Production deployments, better performance

```bash
cd caregiver_dashboard
npm run build
```

This creates optimized files in `dist/` directory.

#### Serve with Preview

```bash
npm run preview -- --host --port 3000
```

#### Serve with Simple HTTP Server

```bash
cd dist
python3 -m http.server 3000
```

#### Serve with nginx

```nginx
server {
    listen 80;
    server_name surdas-dashboard.local;
    
    root /path/to/suradas/caregiver_dashboard/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # WebSocket proxy
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    # API proxy
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### Option 3: Docker Deployment

**Best for**: Containerized deployments, cloud hosting

#### Create Dockerfile

```dockerfile
# caregiver_dashboard/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Build and Run

```bash
# Build image
docker build -t surdas-dashboard:v2 .

# Run container
docker run -d \
  -p 3000:80 \
  --name surdas-dashboard \
  surdas-dashboard:v2
```

---

## 🔧 Configuration

### Environment-Specific Settings

Create different config files for each environment:

#### `src/config.ts`

```typescript
export const config = {
  development: {
    API: 'http://localhost:8000',
    WS: 'ws://localhost:8000/ws',
    CONTROLLER_IP: '192.168.4.2',
    VIDEO_FEED: 'http://localhost:8888/video_feed'
  },
  production: {
    API: 'https://api.surdas.example.com',
    WS: 'wss://api.surdas.example.com/ws',
    CONTROLLER_IP: '192.168.4.2',
    VIDEO_FEED: 'https://video.surdas.example.com/feed'
  }
};

const env = import.meta.env.MODE || 'development';
export default config[env as keyof typeof config];
```

#### Update `src/App.tsx`

```typescript
import config from './config';

const API = config.API;
const WS = config.WS;
const CONTROLLER_IP = config.CONTROLLER_IP;
const VIDEO_FEED = config.VIDEO_FEED;
```

---

## 🔒 Security Considerations

### 1. Enable HTTPS (Recommended)

```nginx
server {
    listen 443 ssl http2;
    server_name surdas-dashboard.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name surdas-dashboard.example.com;
    return 301 https://$server_name$request_uri;
}
```

### 2. Add Authentication (Optional but Recommended)

#### Basic Auth with nginx

```nginx
location / {
    auth_basic "SURDAS Dashboard";
    auth_basic_user_file /etc/nginx/.htpasswd;
    try_files $uri $uri/ /index.html;
}
```

Generate password file:
```bash
htpasswd -c /etc/nginx/.htpasswd caregiver
```

#### Custom Authentication

Implement in backend (`telemetry.py`):

```python
from fastapi import WebSocket, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != "caregiver" or credentials.password != "secure_password":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.username

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, username: str = Depends(verify_credentials)):
    # ... existing code
```

### 3. Firewall Rules

```bash
# Allow only specific IPs (example)
sudo ufw allow from 192.168.1.0/24 to any port 3000
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

### 4. Rate Limiting

```nginx
limit_req_zone $binary_remote_addr zone=dashboard:10m rate=10r/s;

location / {
    limit_req zone=dashboard burst=20;
    # ... rest of config
}
```

---

## 🌐 Network Configuration

### Local Network Access

1. **Find server IP**:
   ```bash
   # macOS/Linux
   ifconfig | grep "inet "
   
   # Or
   hostname -I
   ```

2. **Configure firewall**:
   ```bash
   # Allow dashboard port
   sudo ufw allow 3000/tcp
   
   # Allow backend port
   sudo ufw allow 8000/tcp
   
   # Allow video feed port
   sudo ufw allow 8888/tcp
   ```

3. **Access from devices**:
   ```
   http://[server-ip]:3000
   ```

### Remote Access (VPN Recommended)

For remote caregiver access:

1. **Set up WireGuard VPN**:
   ```bash
   sudo apt install wireguard
   # Configure VPN server
   ```

2. **Access through VPN**:
   - Caregivers connect to VPN
   - Access dashboard via private IP
   - More secure than port forwarding

### Port Forwarding (Not Recommended)

If you must expose directly to internet:

1. Forward ports on router: 80, 443
2. Use HTTPS only
3. Implement strong authentication
4. Enable fail2ban for security
5. Monitor access logs

---

## 📊 Performance Optimization

### 1. Build Optimizations

```bash
# Production build with optimizations
npm run build

# Analyze bundle size
npm install --save-dev rollup-plugin-visualizer
```

### 2. nginx Optimizations

```nginx
# Enable gzip compression
gzip on;
gzip_vary on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

# Enable caching
location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 3. WebSocket Optimizations

```nginx
# Increase timeouts for WebSocket
proxy_read_timeout 86400;
proxy_send_timeout 86400;
keepalive_timeout 86400;
```

---

## 🔍 Monitoring & Logging

### Application Logs

#### Browser Console
- Check for errors: F12 → Console
- Monitor WebSocket status
- Track event flow

#### Backend Logs

```python
# In telemetry.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler()
    ]
)
```

### nginx Access Logs

```nginx
access_log /var/log/nginx/surdas-access.log;
error_log /var/log/nginx/surdas-error.log;
```

### Health Checks

```bash
# Check API
curl http://localhost:8000/health

# Check dashboard
curl -I http://localhost:3000

# Check WebSocket (with websocat)
websocat ws://localhost:8000/ws
```

---

## 🚀 Automated Deployment

### Systemd Service (Linux)

#### Dashboard Service

```ini
# /etc/systemd/system/surdas-dashboard.service
[Unit]
Description=SURDAS Caregiver Dashboard
After=network.target

[Service]
Type=simple
User=surdas
WorkingDirectory=/home/surdas/suradas/caregiver_dashboard
ExecStart=/usr/bin/npm run preview -- --host --port 3000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Backend Service

```ini
# /etc/systemd/system/surdas-backend.service
[Unit]
Description=SURDAS Backend
After=network.target

[Service]
Type=simple
User=surdas
WorkingDirectory=/home/surdas/suradas
ExecStart=/usr/bin/python3 surdas_brain.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable surdas-dashboard
sudo systemctl enable surdas-backend
sudo systemctl start surdas-dashboard
sudo systemctl start surdas-backend

# Check status
sudo systemctl status surdas-dashboard
sudo systemctl status surdas-backend
```

---

## 🔄 Updates & Maintenance

### Update Dashboard

```bash
cd caregiver_dashboard
git pull origin main
npm install
npm run build
sudo systemctl restart surdas-dashboard
```

### Backup Configuration

```bash
# Backup important files
tar -czf surdas-backup-$(date +%Y%m%d).tar.gz \
  caregiver_dashboard/src/config.ts \
  /etc/nginx/sites-available/surdas \
  /etc/systemd/system/surdas-*.service
```

---

## 🆘 Troubleshooting Production Issues

### Dashboard Won't Start

```bash
# Check build errors
npm run build

# Check port availability
sudo lsof -i :3000

# Check file permissions
ls -la dist/
```

### WebSocket Connection Fails

```bash
# Check backend is running
curl http://localhost:8000/health

# Check WebSocket port
sudo lsof -i :8000

# Test WebSocket manually
websocat ws://localhost:8000/ws
```

### High CPU/Memory Usage

```bash
# Monitor resources
htop

# Check dashboard process
ps aux | grep node

# Check backend process
ps aux | grep python
```

---

## 📈 Scaling

### Multiple Caregivers

The dashboard supports multiple concurrent connections:

```python
# In telemetry.py - already implemented
connected_clients: set = set()
# Each caregiver gets their own WebSocket connection
```

### Load Balancing (Advanced)

For high availability:

```nginx
upstream surdas_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;  # Secondary instance
}

server {
    location /ws {
        proxy_pass http://surdas_backend;
        # ... WebSocket config
    }
}
```

---

## ✅ Production Checklist

Before going live:

- [ ] Build production version (`npm run build`)
- [ ] Configure HTTPS with valid certificate
- [ ] Set up authentication
- [ ] Configure firewall rules
- [ ] Enable monitoring and logging
- [ ] Set up automatic backups
- [ ] Create systemd services for auto-start
- [ ] Test from multiple devices
- [ ] Verify WebSocket reconnection
- [ ] Test fall detection alerts
- [ ] Document access credentials
- [ ] Set up VPN for remote access (if needed)
- [ ] Create deployment documentation
- [ ] Train caregivers on dashboard use

---

## 📞 Support

For deployment issues:
1. Check logs: Browser console, nginx logs, backend logs
2. Verify network connectivity
3. Test each component individually
4. Review security settings
5. Check firewall rules

---

**Happy deploying! 🚀**
