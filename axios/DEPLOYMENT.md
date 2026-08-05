# Deploying Axios for Free — MongoDB Atlas + Render

This gets your app running on a real public URL, live 24/7, with no
credit card and no cost.

---

## Part 1 — MongoDB Atlas (free cloud database)

1. Go to https://www.mongodb.com/cloud/atlas/register and sign up (free).
2. Create a new **free M0 cluster** (choose any cloud provider/region —
   pick one close to you, doesn't matter much for a project).
3. **Create a database user:**
   - Left sidebar → *Database Access* → *Add New Database User*
   - Set a username and password (use a simple password with no
     special characters like `@` or `/` — they cause connection
     string issues). Save these somewhere.
4. **Allow network access:**
   - Left sidebar → *Network Access* → *Add IP Address*
   - Click **"Allow Access from Anywhere"** (`0.0.0.0/0`) — needed
     since Render's servers don't have a fixed IP on the free tier.
5. **Get your connection string:**
   - Go to *Database* → click **Connect** on your cluster → **Drivers**
   - Copy the connection string, looks like:
     ```
     mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
     ```
   - Replace `<username>` and `<password>` with what you created in step 3.
   - Add your database name before the `?`, so it becomes:
     ```
     mongodb+srv://myuser:mypassword@cluster0.xxxxx.mongodb.net/axios_db?retryWrites=true&w=majority
     ```

Keep this full string handy — you'll paste it into Render as an
environment variable in Part 2.

---

## Part 2 — Render (free app hosting)

1. Push this project to a **GitHub repository** (Render deploys from
   GitHub). If you don't have one yet:
   - Create a new repo on github.com
   - Upload/push this whole `axios` folder to it
2. Go to https://render.com and sign up (free, no card required).
3. Click **New +** → **Web Service** → connect your GitHub repo.
4. Configure the service:
   - **Name:** axios (or whatever you like)
   - **Region:** any
   - **Branch:** main
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app` (already set via the
     included `Procfile`, but Render sometimes asks you to confirm it)
5. **Add environment variables** (Render dashboard → *Environment*):
   | Key | Value |
   |---|---|
   | `MONGO_URI` | your full Atlas connection string from Part 1 |
   | `SECRET_KEY` | any long random string, e.g. `axios-super-secret-key-2026` |
6. Click **Create Web Service**. Render will build and deploy —
   takes a few minutes on first deploy.
7. Once live, Render gives you a public URL like:
   ```
   https://axios.onrender.com
   ```
   This is permanent (unlike ngrok) and stays online as long as the
   service is running.

---

## Important notes for the free tier

- **Cold starts:** Render's free tier spins your app down after 15
  minutes of no traffic. The next visit takes ~30-50 seconds to wake
  back up. Totally fine for a college demo — just don't panic if the
  first load is slow.
- **Uploaded resumes are not permanent:** Render's free tier
  filesystem resets on redeploy/restart, so files in `uploads/` can
  disappear. Candidate *data* (name, skills, score, etc.) stays safe
  in MongoDB Atlas regardless — only the actual resume file itself
  could be lost. Fine for a demo; let me know if you want persistent
  file storage added (e.g. free Cloudinary tier) for anything beyond
  that.
- **Email notifications:** still work the same way — set `SMTP_HOST`,
  `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` as additional Render
  environment variables if you want real emails sent; otherwise they
  log to `notifications.log` same as local (though that log also
  resets on redeploy, for the same filesystem reason above).

---

## Local development still works as before

Locally, if you don't set `MONGO_URI`, the app automatically falls
back to `mongodb://localhost:27017` — so nothing changes for your
local VS Code + local MongoDB workflow. The environment variable is
only needed for the deployed version.
