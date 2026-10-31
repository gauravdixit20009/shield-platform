# 🛡️ SHIELD Platform

**Secure Hub for Intelligence, Enforcement & Law Data**

Production-grade Law Enforcement Intelligence Platform for IPS/IAS/Police Officers

---

## 🚀 Quick Start (Development)

### Prerequisites
- Docker + Docker Compose
- Node.js 20+
- Python 3.12+

### 1. Clone & Setup
```bash
cp .env.template .env
# Fill all values in .env (generate keys with: openssl rand -hex 64)
```

### 2. Start Infrastructure
```bash
cd infra
docker compose up -d postgres redis minio ollama
```

### 3. Pull AI Model
```bash
docker exec shield_ollama ollama pull llama3.2:3b
```

### 4. Run Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. Run Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

---

## 🏗️ Architecture

| Service | Tech | Port |
|---------|------|------|
| API | FastAPI (Python) | 8000 |
| Web App | Next.js 15 | 3000 |
| Database | PostgreSQL 16 | 5432 (internal) |
| Cache | Redis 7 | 6379 (internal) |
| Evidence Vault | MinIO | 9000 (internal) |
| AI Engine | Ollama (local LLM) | 11434 (internal) |
| Reverse Proxy | Nginx + WAF | 80/443 |

---

## 🔒 Security Features

- ✅ **Zero-Trust Architecture** — Nothing trusted by default
- ✅ **MFA (TOTP)** — Google Authenticator compatible
- ✅ **Argon2id Password Hashing** — Best-in-class
- ✅ **JWT RS256** — Asymmetric signing
- ✅ **Device Fingerprinting** — Only registered devices
- ✅ **Row-Level Security (RLS)** — DB-enforced access control
- ✅ **Immutable Audit Log** — Append-only via DB rules
- ✅ **Field-Level Encryption** — AES-256 on sensitive data
- ✅ **WAF (ModSecurity)** — Web Application Firewall
- ✅ **No External AI APIs** — All AI runs locally (Ollama)
- ✅ **Evidence Hash Chain** — SHA-512 tamper detection
- ✅ **Two-Person Integrity** — Case transfers need 2 approvals

---

## 📁 Project Structure

```
shield/
├── backend/          # FastAPI Python API
├── frontend/         # Next.js Web App
├── mobile/           # React Native Mobile App
├── infra/            # Docker, Nginx, DB scripts
└── docs/             # API & Security docs
```

---

## ⚠️ Production Checklist

- [ ] Change ALL secrets in `.env`
- [ ] Configure SSL certificates
- [ ] Enable ModSecurity WAF rules
- [ ] Apply `infra/db_security.sql` PostgreSQL RLS
- [ ] Set up automated encrypted backups
- [ ] Configure Sentry for error monitoring
- [ ] Set up Prometheus + Grafana monitoring
- [ ] Restrict server firewall (only 80/443 public)
- [ ] Enable audit log archival to WORM storage

---

*Government of India — Ministry of Home Affairs*  
*Classification: RESTRICTED*
