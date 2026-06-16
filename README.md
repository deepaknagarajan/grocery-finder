# Grocery Finder

A Streamlit web app that uses Claude Vision to scan a grocery store aisle photo and find any product by name. Scan the shelf once — then search as many times as you want with no additional API calls.

---

## How It Works

1. **Upload** a grocery store aisle photo (JPG, PNG, or WebP)
2. **Scan Shelf** — Claude reads every product label on the shelf (one API call)
3. **Search** any product name — results appear instantly with no further API calls
4. **Download** the annotated image with circles drawn around matches

---

## Features

- One Claude API call per photo — all searches after that are free and instant
- Draws colored circles around every matching product
- Shows a full list of all products found on the shelf
- Single-column layout that works on desktop and mobile
- Download annotated image as JPEG

---

## Requirements

- Python 3.10+
- An Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com)

---

## Local Setup

### 1. Install dependencies

```bash
cd C:\Users\sai35\sai_source\grocery_finder
pip install -r requirements.txt
```

### 2. Set your API key (optional but recommended)

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Or you can paste it into the sidebar when the app opens.

### 3. Run the app

```bash
streamlit run app.py
```

Opens at `http://localhost:8501` in your browser.

---

## Run on Your Phone (Local Network)

Make sure your phone and computer are on the same WiFi network, then run:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Open `http://10.0.0.128:8501` on your phone.

> Replace `10.0.0.128` with your computer's local IP address.  
> Find it by running `ipconfig` in a terminal and looking for **IPv4 Address**.

---

## Deploy to Streamlit Community Cloud (Free, Public URL)

Deploying gives you a permanent public link that works from any phone or browser, anywhere.

### Step 1 — Push to GitHub

Create a new repo on [github.com](https://github.com), then:

```bash
cd C:\Users\sai35\sai_source\grocery_finder

git init
git add app.py requirements.txt README.md
git commit -m "Initial grocery finder app"
git remote add origin https://github.com/YOUR_USERNAME/grocery-finder.git
git push -u origin main
```

### Step 2 — Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account
2. Click **New app**
3. Select your `grocery-finder` repo, branch `main`, file `app.py`
4. Click **Advanced settings** and add your API key as a secret:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

5. Click **Deploy**

Your app will be live at a URL like:
```
https://yourname-grocery-finder-app-xxxx.streamlit.app
```

> The app reads `ANTHROPIC_API_KEY` from the secret automatically — the sidebar key field will be hidden.

### Step 3 — Update the app

Any time you push a change to GitHub, Streamlit Cloud redeploys automatically:

```bash
git add app.py
git commit -m "Update app"
git push
```

---

## API Key

- Get your key at [console.anthropic.com](https://console.anthropic.com) → API Keys → Create Key
- Add a payment method at console.anthropic.com → Billing before your free credit runs out
- Each shelf scan costs roughly **$0.02–0.05** depending on image size (uses `claude-opus-4-8`)
- Searches after the scan are free

---

## Project Structure

```
grocery_finder/
├── app.py            # Streamlit app
├── requirements.txt  # anthropic, streamlit, Pillow
└── README.md
```

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Circles appear in the wrong location | The image is resized to max 1568px before scanning — this is normal and coordinates are calculated against the resized dimensions |
| "Could not find" a product | Try a shorter search term, e.g. just the brand name (`McCormick` instead of `McCormick Organic Ground Ginger`) |
| Scan takes a long time | Normal for large images with many products — Claude is reading every label |
| App not reachable on phone | Make sure both devices are on the same WiFi and you used `--server.address 0.0.0.0` |
| Invalid API key error | Check that your key starts with `sk-ant-` and hasn't expired |
