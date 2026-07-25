# Onelap2Strava WebApp 🚴‍♂️➡️🏃‍♂️

[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https.docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[**中文文档 (Chinese Version)**](./README_CN.md)

**Onelap2Strava** is a modern, multi-user Web Application designed to automatically synchronize indoor cycling activities from **Onelap (顽鹿竞技)** to **Strava**. 

It features a dual-mode Strava engine that supports both **Cookie-based Web Uploads** (for free/non-API Strava accounts) and the **Official Strava OAuth API v3**.

---

## ✨ Features

- 👥 **Multi-User Isolation**: Supports multiple users with isolated credentials, sync histories, and settings.
- 🍪 **Strava Cookie Upload Engine (No API Key Required)**: Bypasses API subscription restrictions for free Strava accounts by automatically handling `_strava4_session` web sessions and CSRF token uploads.
- 🔑 **Official Strava OAuth API Mode**: Provides native support for official Strava API credentials (`Client ID`, `Client Secret`, `Refresh Token`).
- 🪄 **Web Token Generator Assistant**: Built-in OAuth Token Assistant to exchange `Refresh Token` directly in the UI without using terminal commands.
- 🔐 **Zero-Trust AES-256 Encryption**: All sensitive data (passwords, cookies, API secrets) are encrypted with **AES-256-GCM** before being saved to the database.
- ⏰ **Automated Background Sync**: Background scheduler (every 3h, 6h, 12h, or 24h) with incremental activity deduplication.
- 📊 **Modern SPA Dashboard**: Sleek dark-mode interface built with Tailwind CSS, metric cards, visual tutorials, and live log console.

---

## 🚀 Quick Deployment (Docker Compose on VPS)

### Prerequisites
- VPS (Linux / Ubuntu / Debian / CentOS)
- Docker & Docker Compose installed

### Step 1: Clone Repository
```bash
git clone https://github.com/TrojanFish/onelap2strava.git
cd onelap2strava
```

### Step 2: Configure Environment Variables
Copy the environment variables template file (you can keep the defaults unless you have specific needs):
```bash
cp .env.example .env
```

Edit the `.env` file or `docker-compose.yml` to customize your secret keys (Optional):
```yaml
environment:
  - SECRET_KEY=your_random_secret_jwt_key
  - ENCRYPTION_KEY=u234567890123456789012345678901234567890123=
  - DATABASE_URL=sqlite:///./data/onelap2strava.db
```

### Step 3: Launch Container
```bash
docker-compose up -d
```
Access the Web Dashboard by visiting `http://<your-vps-ip>:8766` in your browser!

---

## 🔑 How to Configure Strava Credentials

### Mode A: Strava Cookie Mode (For Free/Non-API Users)
1. Open [Strava.com](https://www.strava.com) in Chrome/Edge on your PC and log in.
2. Press `F12` to open Developer Tools, go to the **Application** tab.
3. Expand **Storage -> Cookies -> https://www.strava.com**.
4. Double-click and copy the value of `_strava4_session`.
5. Paste it into the Web App under **Account & Cookie/API Config** and save.

---

### Mode B: Official Strava API Mode (For Developers)

#### 1. Obtain Authorization Code
Visit [Strava API Settings](https://www.strava.com/settings/api) to get your **Client ID** and **Client Secret**. Then open the following URL in your browser:
```text
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=read,activity:write,activity:read_all
```
Click **Authorize**. You will be redirected to `http://localhost/?code=...`. Copy the code parameter (e.g. `7754cccfa08317e4acd55f612dcc01f5465b4d11`).

#### 2. Exchange for Refresh Token
- **Option 1 (Web Assistant)**: Paste your `Client ID`, `Client Secret`, and `Code` directly into the Web App's **One-Click Token Assistant** and click **Generate Refresh Token**.
- **Option 2 (Terminal curl)**:
```bash
curl -X POST https://www.strava.com/oauth/token   -F client_id=YOUR_CLIENT_ID   -F client_secret=YOUR_CLIENT_SECRET   -F code=YOUR_CODE_FROM_STEP_1   -F grant_type=authorization_code
```
Copy the `refresh_token` from the JSON response and save it in the Web App.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, SQLite, Cryptography (AES-256), Httpx, APScheduler.
- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Tailwind CSS, FontAwesome 6.
- **Deployment**: Docker, Docker Compose, Uvicorn.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
