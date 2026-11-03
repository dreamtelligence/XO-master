# 🛠️ Development Setup Guide

Complete step-by-step guide to set up the AI Music Studio Platform for local development.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Configuration](#configuration)
5. [Running Locally](#running-locally)
6. [Deployment](#deployment)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts

Before you begin, create accounts on these platforms:

- [ ] **GitHub** - [github.com](https://github.com)
- [ ] **Modal Labs** - [modal.com](https://modal.com) (Serverless GPU)
- [ ] **Hugging Face** - [huggingface.co](https://huggingface.co) (token for the gated MuScriptor and Stable Audio Open weights)
- [ ] **Vercel** - [vercel.com](https://vercel.com) (Frontend hosting)
- [ ] **Supabase** - [supabase.com](https://supabase.com) (Database)
- [ ] **Stripe** - [stripe.com](https://stripe.com) (Payments)

### Required Software

Install the following on your development machine:

```bash
# Node.js 18+ (includes npm)
node --version  # Should be v18.0.0 or higher
npm --version   # Should be 9.0.0 or higher

# Python 3.11+ (for the Modal CLI; each service pins its own Python inside its image)
python3 --version  # Should be 3.11.0 or higher
pip3 --version

# Git
git --version

# Optional but recommended
brew install --cask visual-studio-code  # Or your preferred editor
```

### Install Development Tools

```bash
# Install Vercel CLI globally
npm install -g vercel

# Install Modal CLI
pip3 install modal

# Install PostgreSQL client (for database setup)
brew install postgresql  # macOS
# sudo apt-get install postgresql-client  # Linux
```

---

## Quick Start

**For experienced developers who want to get up and running quickly:**

```bash
# 1. Clone repository
git clone https://github.com/dreamtelligence/XO-master.git
cd XO-master

# 2. Install dependencies
npm install

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 4. Run database migrations
psql -h [SUPABASE_HOST] -U postgres -d postgres -f supabase_credit_schema.sql

# 5. Deploy Modal services (needs the `huggingface` secret, see Step 5)
modal token new
modal secret create huggingface HF_TOKEN=hf_...
for f in modal_app_*.py; do modal deploy "$f"; done

# 6. Start dev server
npm run dev
# Open http://localhost:3000
```

---

## Detailed Setup

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/dreamtelligence/XO-master.git

# Navigate to project directory
cd XO-master

# Verify files
ls -la
```

Expected files:
```
XO-master/
├── index.html
├── package.json
├── vercel.json
├── supabase_credit_schema.sql
├── modal_app_*.py (5 files)
├── api/ (4 API functions)
└── docs/
```

### Step 2: Install Node.js Dependencies

```bash
# Install npm packages
npm install

# Verify installation
npm list --depth=0
```

Expected output:
```
music-ai-separator@1.0.0
├── stripe@14.25.0
└── serve@14.0.0
```

### Step 3: Set Up Supabase Database

#### Create Supabase Project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. Click "New Project"
3. Fill in:
   - **Project name**: `music-ai-studio`
   - **Database password**: (save this securely)
   - **Region**: Choose closest to your users
4. Wait for project creation (~2 minutes)

#### Get Database Credentials

From your Supabase project dashboard:

1. Click "Settings" → "Database"
2. Note these values:
   - **Host**: `db.xxx.supabase.co`
   - **Database name**: `postgres`
   - **Port**: `5432`
   - **User**: `postgres`

#### Run Database Schema

```bash
# Navigate to project directory
cd XO-master

# Run schema SQL file
psql -h db.xxx.supabase.co -U postgres -d postgres -f supabase_credit_schema.sql

# When prompted, enter your database password
Password for user postgres: [your_password]
```

Expected output:
```
CREATE EXTENSION
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE INDEX
...
CREATE FUNCTION
COMMENT
```

#### Get API Keys

From Supabase dashboard:

1. Click "Settings" → "API"
2. Copy these values:
   - **Project URL**: `https://xxx.supabase.co`
   - **anon public key**: `eyJhbGc...` (for frontend)
   - **service_role secret**: `eyJhbGc...` (for backend only, keep secure!)

### Step 4: Set Up Stripe

#### Create Stripe Account

1. Sign up at [stripe.com](https://stripe.com)
2. Complete business verification (can start in test mode)

#### Create Products & Prices

In Stripe Dashboard:

1. Go to "Products" → "Add Product"
2. Create 4 products:

**Product 1: Test Package (1 Credit)**
- Name: `AI Studio - Test Package`
- Price: `€3.49` (one-time)
- Copy the **Price ID** (e.g., `price_1Rx...`)

**Product 2: Starter Package (10 Credits)**
- Name: `AI Studio - Starter Package`
- Price: `€24.99` (one-time)
- Copy the **Price ID**

**Product 3: Pro Package (25 Credits)**
- Name: `AI Studio - Pro Package`
- Price: `€49.99` (one-time)
- Copy the **Price ID**

**Product 4: Studio Package (50 Credits)**
- Name: `AI Studio - Studio Package`
- Price: `€79.99` (one-time)
- Copy the **Price ID**

#### Configure Webhooks

1. Go to "Developers" → "Webhooks"
2. Click "Add endpoint"
3. Enter URL: `https://your-domain.vercel.app/api/webhook`
   - Use your Vercel domain (deploy first, update later if needed)
4. Select events to listen to:
   - ✅ `checkout.session.completed`
5. Copy the **Webhook signing secret** (starts with `whsec_`)

#### Register Allowed Domains

1. Go to "Settings" → "Branding"
2. Add these domains:
   - `studio.kleindigitalsolutions.de` (your production domain)
   - `localhost:3000` (for testing)
   - `*.vercel.app` (for preview deployments)

#### Get API Keys

From Stripe Dashboard → "Developers" → "API keys":

1. Copy **Secret key** (starts with `sk_test_` or `sk_live_`)
2. Copy **Publishable key** (starts with `pk_test_` or `pk_live_`)

### Step 5: Set Up Modal Labs

#### Create Modal Account

1. Sign up at [modal.com](https://modal.com)
2. Verify email and phone number

#### Authenticate Modal CLI

```bash
# Login to Modal
modal token new

# Follow the browser authentication flow
# This will open a browser window for you to authenticate

# Verify authentication
modal profile current
```

Expected output:
```
Workspace: your-workspace
Token: active
```

#### Hugging Face Token (gated models)

MuScriptor (transcription) and Stable Audio Open (generation) are gated on Hugging Face:

1. Create a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. With the same account, accept the licenses of
   [MuScriptor large](https://huggingface.co/MuScriptor/muscriptor-large) (CC BY-NC 4.0, non-commercial) and
   [Stable Audio Open 1.0](https://huggingface.co/stabilityai/stable-audio-open-1.0) (Stability AI Community License)
3. Store it as a Modal secret:

```bash
modal secret create huggingface HF_TOKEN=hf_...
```

#### Deploy the AI Services

```bash
modal deploy modal_app_zfturbo_complete.py      # Separation: SCNet XL IHF + Mel-Band RoFormer
modal deploy modal_app_enhancement.py           # Speech: MossFormer2 + Whisper large-v3-turbo + AST
modal deploy modal_app_matchering.py            # Mastering: pedalboard chain
modal deploy modal_app_transcription.py         # Transcription: MuScriptor + beat_this + essentia
modal deploy modal_app_audio_generation.py      # Generation: Stable Audio Open 1.0
```

The first build of each image takes several minutes: model weights are downloaded at build time and
baked into the image (separation checkpoints are pinned and checked against SHA-256). Only MuScriptor
is fetched on first use and then cached in the `muscriptor-hf-cache` volume.

Each deploy prints a web endpoint like:
```
https://<workspace>--music-ai-separator-zfturbo-complete-fastapi-app.<region>.modal.run
```

**Copy the endpoint URLs** - you'll need them for the frontend configuration (Step 7).

### Step 6: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Create .env file
touch .env

# Open in editor
code .env  # or nano .env
```

Add the following variables:

```bash
# Stripe Keys
STRIPE_SECRET_KEY=sk_test_xxx  # or sk_live_xxx for production
STRIPE_PUBLISHABLE_KEY=pk_test_xxx  # or pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Stripe Price IDs (from Step 4)
STRIPE_PRICE_SINGLE=price_xxx
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_STUDIO=price_xxx

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...  # Public anon key
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Secret service role key

# Security
CREDIT_WEBHOOK_SECRET=your_random_secret_here_32_chars_min
```

The Modal endpoints are not environment variables: they are set directly in `index.html` (Step 7).

**Generate a secure webhook secret:**
```bash
# macOS/Linux
openssl rand -hex 32

# Or use this Node.js command
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### Step 7: Update Frontend Configuration

Replace the Modal URLs in `index.html` with the ones printed by `modal deploy`:

| Constant in `index.html` | Modal app |
|--------------------------|-----------|
| `API_BASE`, `HEALTH_URL`, `MODELS_URL`, `MODAL_API_BASE` | `music-ai-separator-zfturbo-complete` (`fastapi-app`) |
| `MATCHERING_API_BASE`, `MATCHERING_HEALTH_URL` | `matchering-ai-mastering` (`matchering-app`) |
| `TRANSCRIPTION_API_BASE` | `music-ai-transcription-complete` (`transcription-app`) |
| `ENHANCEMENT_API_BASE` | `audio-enhancement-complete` (`fastapi-app`) |

The audio generation service (`audio-generation-stable-audio-open`) has no UI in `index.html` yet and
is used through its API directly.

---

## Configuration

### Vercel Configuration

The `vercel.json` file is pre-configured:

```json
{
  "version": 2,
  "builds": [
    { "src": "index.html", "use": "@vercel/static" },
    { "src": "api/**/*.js", "use": "@vercel/node" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/$1" },
    { "src": "/(.*)", "dest": "/index.html" }
  ]
}
```

### Modal Configuration

Each Modal app defines its image, GPU and models at the top of the file:

```python
# Example: modal_app_zfturbo_complete.py

ZFTURBO_COMMIT = "6fdad13..."      # ZFTurbo repo pinned to a known commit

SEPARATION_MODELS = {
    "stems":  {"name": "SCNet XL IHF", "model_type": "scnet", ...},              # vocals/drums/bass/other
    "vocals": {"name": "Mel-Band RoFormer (KimberleyJensen)",
               "model_type": "mel_band_roformer", ...},                            # cleaner vocals
}   # each entry has a pinned download URL and a SHA-256 checksum

@app.function(image=zfturbo_image, gpu="a10g", timeout=1800, memory=20480, ...)
def bs_roformer_separate_audio(...):   # name kept for compatibility with existing deployments
    ...
```

To swap a model, change its entry (URL, config, checksum) and redeploy.

### Package.json Scripts

Available npm scripts:

```json
{
  "scripts": {
    "dev": "vercel dev",           // Start Vercel dev server
    "build": "echo 'Static build'", // No build needed for static files
    "start": "npx serve .",        // Serve static files locally
    "deploy": "vercel --prod"      // Deploy to production
  }
}
```

---

## Running Locally

### Option 1: Vercel Dev Server (Recommended)

```bash
# Start Vercel development server
npm run dev

# This starts:
# - Frontend on http://localhost:3000
# - API functions on http://localhost:3000/api/*
# - Simulates Vercel edge functions locally
```

**Advantages:**
- Simulates production environment
- API routes work exactly as in production
- Automatic reloading on file changes

### Option 2: Simple HTTP Server

```bash
# Start basic HTTP server
npm start
# or
python3 -m http.server 8080

# Open browser to http://localhost:8080
```

**Note:** API routes won't work with this method. Use for frontend development only.

### Testing Modal Functions Locally

```bash
# Serve a service with hot reload on a temporary dev URL (without deploying)
modal serve modal_app_zfturbo_complete.py

# Or open a shell inside the service image
modal shell modal_app_zfturbo_complete.py
```

### Testing Stripe Webhooks Locally

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:3000/api/webhook

# Trigger test webhook
stripe trigger checkout.session.completed
```

---

## Deployment

### Deploy to Vercel

#### First-Time Deployment

```bash
# Login to Vercel
vercel login

# Link project to Vercel
vercel link

# Deploy to production
vercel --prod
```

Follow the prompts:
- **Set up and deploy?** Yes
- **Which scope?** Your username/organization
- **Link to existing project?** No
- **Project name?** music-ai-studio
- **Directory?** ./
- **Override settings?** No

#### Add Environment Variables to Vercel

```bash
# Add each environment variable
vercel env add STRIPE_SECRET_KEY
# Paste the value when prompted
# Select: Production, Preview, Development

# Repeat for all variables:
vercel env add STRIPE_WEBHOOK_SECRET
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add SUPABASE_SERVICE_ROLE_KEY
vercel env add CREDIT_WEBHOOK_SECRET
```

**Or use Vercel Dashboard:**
1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Select your project
3. Go to "Settings" → "Environment Variables"
4. Add all variables from your `.env` file

#### Subsequent Deployments

```bash
# Deploy to production
vercel --prod

# Or just push to git (auto-deploys)
git push origin main
```

### Deploy Modal Services

```bash
# Deploy all Modal services
modal deploy modal_app_zfturbo_complete.py
modal deploy modal_app_enhancement.py
modal deploy modal_app_matchering.py
modal deploy modal_app_transcription.py
modal deploy modal_app_audio_generation.py

# Verify deployments
modal app list
```

### Update Stripe Webhook URL

After deploying to Vercel:

1. Go to Stripe Dashboard → "Developers" → "Webhooks"
2. Edit your webhook endpoint
3. Update URL to: `https://your-vercel-domain.vercel.app/api/webhook`
4. Save changes

### Configure Custom Domain (Optional)

In Vercel Dashboard:

1. Go to your project → "Settings" → "Domains"
2. Add your custom domain (e.g., `studio.kleindigitalsolutions.de`)
3. Follow DNS configuration instructions
4. Update Stripe webhook URL to use custom domain

---

## Troubleshooting

### Common Issues

#### 1. Modal Deployment Fails

**Error:** `401 Client Error` / `Access to model ... is restricted` while building or on first use

**Solution:** The `huggingface` secret is missing, or its token belongs to an account that has not
accepted the MuScriptor / Stable Audio Open licenses (see Step 5).

```bash
modal secret list   # must contain "huggingface"
```

**Error:** `sha256sum: WARNING: 1 computed checksum did NOT match`

**Solution:** A pinned separation checkpoint changed upstream. Check the URL and checksum in
`SEPARATION_MODELS` in `modal_app_zfturbo_complete.py` before updating them.

#### 2. Database Connection Fails

**Error:** `could not connect to server`

**Solution:**
```bash
# Check Supabase credentials
echo $NEXT_PUBLIC_SUPABASE_URL

# Test connection
psql -h db.xxx.supabase.co -U postgres -d postgres

# Verify environment variables in Vercel
vercel env ls
```

#### 3. Stripe Webhook Not Working

**Error:** `No signatures found matching the expected signature`

**Solution:**
```bash
# Verify webhook secret matches
echo $STRIPE_WEBHOOK_SECRET

# Test webhook locally
stripe listen --forward-to localhost:3000/api/webhook

# Check Stripe Dashboard → Webhooks → Events
```

#### 4. Credits Not Deducted

**Error:** User credits not decreasing after service use

**Solution:**
```sql
-- Check database function exists
SELECT * FROM pg_proc WHERE proname = 'deduct_user_credits';

-- Test function manually
SELECT * FROM deduct_user_credits('user_id', 1, 'separation', 'job_123');

-- Check API logs in Vercel
vercel logs
```

#### 5. Modal GPU Out of Memory

**Error:** `RuntimeError: CUDA out of memory`

**Solution:**
- Disable TTA for very long tracks (it doubles the work per segment)
- Or move the function to a larger GPU, e.g. `gpu="l40s"` or `gpu="a100"` in `@app.function`,
  and redeploy
- Check the logs: `modal app logs music-ai-separator-zfturbo-complete`

### Getting Help

If you encounter issues not covered here:

1. Check [GitHub Issues](https://github.com/dreamtelligence/XO-master/issues)
2. Review Modal Logs: `modal app logs <app-name>`
3. Review Vercel Logs: `vercel logs`
4. Check Supabase Logs in dashboard
5. Create a new issue with:
   - Error message
   - Steps to reproduce
   - Environment (local/staging/production)
   - Relevant logs

---

## Next Steps

After completing setup:

1. ✅ Test each AI service locally
2. ✅ Make a test credit purchase
3. ✅ Verify webhook credit allocation
4. ✅ Test full user flow (signup → purchase → use service)
5. ✅ Deploy to production
6. ✅ Monitor logs for errors
7. ✅ Set up custom domain
8. ✅ Enable production mode in Stripe

---

**Congratulations! Your AI Music Studio Platform is ready for development.**

For architecture details, see [ARCHITECTURE.md](./ARCHITECTURE.md)

For contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md)
