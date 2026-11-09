# 📺 BharatBeacon — Automated Hourly News Broadcast Engine
> **"India's Window to the World"**

Automated end-to-end broadcast pipeline that ingests top trending news, generates AI-powered retention storyboards, produces professional Full HD **YouTube Shorts (9:16)** and **Long-Form Bulletins (16:9)**, and publishes directly to YouTube every hour.

---

## 🚀 GitHub Actions Cloud Automation (Every Hour at :00 IST)

The repository includes a ready-to-use GitHub Actions workflow:
📁 [`.github/workflows/hourly_broadcast.yml`](.github/workflows/hourly_broadcast.yml)

### 1. Push to GitHub
```bash
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
git push -u origin main
```

### 2. Configure GitHub Secrets
In your GitHub repository, navigate to:
**Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions** $\rightarrow$ **New repository secret**:

| Secret Name | Value | Description |
| :--- | :--- | :--- |
| `YOUTUBE_CLIENT_SECRETS` | Contents of `client_secrets.json` | Google Cloud OAuth Client ID configuration |
| `YOUTUBE_TOKEN_JSON` | Contents of `token.json` | Perpetual OAuth refresh token for YouTube uploads |

### 3. Automated Schedule
* **Cadence:** Every hour at `:00` IST (`18:30 UTC = 00:00 IST`).
* **Trigger:** Fully autonomous cron schedule + manual **Run workflow** button.
