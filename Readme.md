Absolutely! Here's a cleaner, updated `README.md` with clear **Docker**, **Flask**, and **Next.js frontend** usage — organized and developer-friendly.

---

### ✅ **Updated `README.md`**

```md
# 🔗 DOP Blockchain

A custom-built blockchain platform with Flask (Python) for backend and Next.js (React) for frontend. It includes wallet management, transaction handling, mining, and real-time pub-sub via WebSockets.

---

## 📁 Project Structure

```
project-root/
│
├── backend/              # Flask-based blockchain API
│   ├── blockchain/       
│   ├── wallet/           
│   ├── pubsub/           
│   ├── app.py
│   └── ...
│
├── blockchain-frontend/             # Next.js frontend (React)
│
├── Dockerfile            # Docker config for backend
├── docker-compose.yml    # (Optional) Compose for fullstack
├── requirements.txt
└── README.md
```

---

## 🔧 Local Development Setup

### ✅ Backend (Flask)

1. **Activate virtual environment:**

```bash
# Windows
.\blockchain\Scripts\activate

# Linux/macOS
source blockchain/bin/activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Run tests (optional):**

```bash
python -m pytest backend/test
```

4. **Run with seed data (optional):**

```powershell
$env:SEED_DATA = 'True'
python -m backend.app
```

---

### ✅ Frontend (Next.js)

1. **Navigate to the frontend directory:**

```bash
cd frontend
```

2. **Install dependencies:**

```bash
npm install
```

3. **Run the development server:**

```bash
npm run dev
```

Frontend runs on: `http://localhost:3000`

---

## 🐳 Docker Setup (Backend Only)

### ✅ Dockerfile (for Flask backend)

Make sure your Dockerfile looks like this:

```dockerfile
# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables (optional)
ENV FLASK_APP=backend.app
ENV PYTHONUNBUFFERED=1

# Expose Flask port
EXPOSE 5000

# Start the app
CMD ["python", "-m", "backend.app"]
```

---

### ✅ Build and Run

1. **Build Docker image:**

```bash
docker build -t dop-blockchain-backend .
```

2. **Run container:**

```bash
docker run -d -p 5000:5000 --name dop-backend dop-blockchain-backend
```

---

## 📝 Environment Variables

- `SEED_DATA` → Generate test blockchain data
- `PEER=True` → Run a peer node on a different port

---

## 📬 API Endpoints (Backend)

- `/blockchain` → Full blockchain
- `/blockchain/mine` → Mine a block
- `/wallet/info` → Wallet address, balance, and private key
- `/wallet/transact` → Send transaction
- `/transactions/:address` → All transactions for an address
- `/wallet/import` → Import wallet with private key

---

## 💡 Future Improvements

- 🔐 Wallet encryption with passphrases
- 🌍 Peer-to-peer sync via WebSockets
- 📉 Block explorer interface (frontend)
- 📦 IPFS support for decentralized storage
- 📱 Mobile wallet support

---

## 🧑‍💻 Contributors

> Add your name here 💙

---

```

Let me know if you'd like a separate `docker-compose.yml` to run **both frontend and backend** together!