# koperasi-kyn

Aplikasi web Sistem Koperasi Simpan Pinjam — **Koperasi Karma Yadnya Nadhi**.  
Backend Python (FastAPI) + Frontend Vue 3 (Vite) + Database SQLite.

## Stack

| Layer      | Teknologi                                        |
|------------|--------------------------------------------------|
| Backend    | Python 3.11, FastAPI, SQLAlchemy, SQLite         |
| Frontend   | Vue 3, Vite, Pinia, Vue Router                   |
| Deployment | Docker / PM2 + Nginx (VPS Ubuntu/Debian)         |

---

## Development (lokal)

**Prasyarat:** Python 3.10+, Node.js 18+

```bash
# Backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend build
cd frontend && npm install && npm run build && cd ..

# Jalankan (satu server, port 8002)
uvicorn backend.main:app --reload --port 8002
```

Buka **http://127.0.0.1:8002**

### Mode dev (hot-reload, dua terminal)

```bash
# Terminal 1
uvicorn backend.main:app --reload --port 8002

# Terminal 2
cd frontend && npm run dev
```

Buka **http://127.0.0.1:5173**

---

## Deploy ke VPS — Docker (Rekomendasi)

```bash
git clone https://github.com/nyoman-pradipta/koperasi-kyn.git
cd koperasi-kyn

# Buat folder persistent untuk database & uploads
mkdir -p data/uploads

docker compose up -d --build
docker compose logs -f
```

Aplikasi berjalan di port **8002**. Pasang Nginx sebagai reverse proxy:

```bash
sudo cp nginx.conf /etc/nginx/sites-available/koperasi-kyn
sudo ln -s /etc/nginx/sites-available/koperasi-kyn /etc/nginx/sites-enabled/
# Edit server_name di nginx.conf sesuai domain/IP VPS
sudo nginx -t && sudo systemctl reload nginx
```

---

## Deploy ke VPS — PM2 (tanpa Docker)

```bash
cd /var/www/koperasi-kyn

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cd frontend && npm ci && npm run build && cd ..

pm2 start ecosystem.config.js
pm2 save && pm2 startup
```

---

## Struktur Folder

```
koperasi-kyn/
├── backend/            # FastAPI — API + sajikan frontend/dist
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/        # members, loans, payments, collaterals, reminders…
│   └── services/
├── frontend/           # Vue 3 + Vite
│   └── src/
│       ├── views/
│       ├── stores/     # Pinia
│       └── api/        # axios client (Bearer token)
├── Dockerfile          # Multi-stage build
├── docker-compose.yml
├── ecosystem.config.js # PM2
├── nginx.conf          # Reverse proxy
└── requirements.txt
```

## Login Default

| Username | Password | Role  |
|----------|----------|-------|
| admin    | admin    | Admin |
