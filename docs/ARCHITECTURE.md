# 🏗️ System Architecture

This document provides a comprehensive overview of the AI Music Studio Platform architecture, including system design decisions, data flow, and technical implementation details.

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Frontend Architecture](#frontend-architecture)
3. [Backend Services](#backend-services)
4. [Database Design](#database-design)
5. [Payment System](#payment-system)
6. [AI/ML Pipeline](#aiml-pipeline)
7. [Security Architecture](#security-architecture)
8. [Deployment Strategy](#deployment-strategy)
9. [Monitoring & Observability](#monitoring--observability)

---

## High-Level Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Browser (Desktop/Mobile)                                        │
│  ├─ Single Page Application (Vanilla JS)                        │
│  ├─ WaveSurfer.js (Audio Visualization)                         │
│  ├─ Web Audio API (Real-time Processing)                        │
│  └─ Service Worker (PWA, Offline Support)                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                      EDGE LAYER (Vercel)                         │
├─────────────────────────────────────────────────────────────────┤
│  Vercel CDN (Global Edge Network)                               │
│  ├─ Static Assets (HTML, CSS, JS, Images)                       │
│  └─ Edge Functions (Serverless API)                             │
│      ├─ /api/credits          (Credit Management)               │
│      ├─ /api/webhook          (Stripe Events)                   │
│      ├─ /api/create-checkout  (Payment Sessions)                │
│      └─ /api/paywall          (Access Control)                  │
└─────────────────────────────────────────────────────────────────┘
           ↓                    ↓                    ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Stripe API      │  │  Supabase        │  │  Modal Labs      │
│  (Payments)      │  │  (PostgreSQL)    │  │  (GPU Compute)   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
                                                      ↓
                                          ┌──────────────────────┐
                                          │  NVIDIA A10G GPU     │
                                          │  (24GB VRAM)         │
                                          │  ├─ SCNet XL IHF     │
                                          │  ├─ Mel-Band RoFormer│
                                          │  ├─ MossFormer2      │
                                          │  ├─ Whisper turbo    │
                                          │  ├─ AST (AudioSet)   │
                                          │  ├─ Stable Audio Open│
                                          │  ├─ MuScriptor       │
                                          │  └─ beat_this        │
                                          └──────────────────────┘
```

### Design Principles

1. **Serverless-First**: No server management, auto-scaling, pay-per-use
2. **Security by Design**: RLS policies, webhook verification, service role isolation
3. **Performance Optimization**: Edge CDN, GPU acceleration, lazy loading
4. **Cost Efficiency**: Pay-per-second GPU billing, optimized model parameters
5. **Developer Experience**: Infrastructure as Code, version-controlled schemas

---

## Frontend Architecture

### Single Page Application (SPA)

**Technology Stack:**
- **Vanilla JavaScript (ES6+)**: No framework overhead, faster load times
- **Bootstrap 5.3**: Responsive design system
- **WaveSurfer.js**: Audio waveform visualization
- **Web Audio API**: Client-side audio processing

**File Structure:**
```
index.html (360KB)
├─ HTML Structure
│  ├─ Navigation & Hero
│  ├─ Service Tabs (5 AI Services)
│  ├─ Pricing Section
│  ├─ User Menu & Credit Balance
│  └─ Paywall Modal
│
├─ CSS Styles
│  ├─ Bootstrap 5.3
│  ├─ Custom Styles
│  └─ Animations
│
└─ JavaScript Modules
   ├─ Audio Service Manager
   ├─ Credit System Manager
   ├─ Stripe Integration
   ├─ WaveSurfer Controller
   ├─ Modal Dialogs
   └─ API Client
```

### Key Components

#### 1. Audio Service Manager
```javascript
class AudioServiceManager {
  constructor() {
    this.modalEndpoints = {
      separation: 'https://bucci369--music-ai-separator.modal.run',
      enhancement: 'https://bucci369--speech-enhancement.modal.run',
      mastering: 'https://bucci369--audio-mastering.modal.run',
      transcription: 'https://bucci369--music-transcription.modal.run',
      generation: 'https://bucci369--audio-generation.modal.run'
    }
  }

  async processAudio(service, file, options) {
    // 1. Check credits
    await this.checkCredits(service)

    // 2. Upload to Modal
    const jobId = await this.uploadToModal(service, file, options)

    // 3. Poll for results
    const result = await this.pollJobStatus(jobId)

    // 4. Deduct credits
    await this.deductCredits(service, jobId)

    // 5. Download results
    return result
  }
}
```

#### 2. Credit System Manager
```javascript
class CreditManager {
  async getBalance(userId) {
    const response = await fetch(`/api/credits?userId=${userId}`)
    return response.json()
  }

  async deductCredits(userId, service, jobId) {
    const response = await fetch('/api/credits', {
      method: 'PUT',
      body: JSON.stringify({ userId, service, jobId, credits: 1 })
    })
    return response.json()
  }
}
```

#### 3. Paywall System
```javascript
class PaywallManager {
  async checkAccess(userId, service) {
    const response = await fetch('/api/paywall', {
      method: 'POST',
      body: JSON.stringify({ userId, service })
    })

    if (response.status === 402) {
      // Insufficient credits - show paywall
      this.showPaywallModal()
      return false
    }

    return true
  }

  async createCheckoutSession(packageType) {
    const response = await fetch('/api/create-checkout-session', {
      method: 'POST',
      body: JSON.stringify({ packageType })
    })
    const { url } = await response.json()
    window.location.href = url // Redirect to Stripe
  }
}
```

### Progressive Web App (PWA)

**Service Worker Features:**
- Offline fallback page
- Static asset caching
- Background sync for failed requests
- Push notifications (future)

```javascript
// sw.js
const CACHE_NAME = 'ai-music-studio-v1'
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/header.webp',
  '/favicons/favicon.ico'
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
  )
})
```

---

## Backend Services

### Vercel Edge Functions

**Architecture Benefits:**
- Global edge network (low latency)
- Auto-scaling (0 to ∞)
- Pay-per-execution
- Native Stripe integration

#### API Endpoints

**1. Credit Management (`/api/credits`)**
```javascript
// GET /api/credits?userId=xxx
// Returns: { userId, email, credits, purchases, usage }

// POST /api/credits (secured by webhook secret)
// Body: { userId, credits, packageType, sessionId, webhookSecret }
// Returns: { userId, credits, transactionId }

// PUT /api/credits
// Body: { userId, service, jobId, credits: 1 }
// Returns: { userId, credits, usageId }
```

**2. Stripe Webhook (`/api/webhook`)**
```javascript
// POST /api/webhook
// Stripe sends: checkout.session.completed
// Flow:
//   1. Verify webhook signature
//   2. Extract session data
//   3. Call /api/credits with webhook secret
//   4. Atomically add credits to user
//   5. Log purchase in database
```

**3. Payment Session (`/api/create-checkout-session`)**
```javascript
// POST /api/create-checkout-session
// Body: { packageType: 'starter' | 'pro' | 'studio' }
// Returns: { url: 'https://checkout.stripe.com/...' }
```

**4. Paywall Check (`/api/paywall`)**
```javascript
// POST /api/paywall
// Body: { userId, service }
// Returns:
//   200 OK - User has credits
//   402 Payment Required - { currentBalance, required }
```

### Modal AI Services

**Serverless GPU Functions:**

Each Modal app is a standalone FastAPI service with:
- Custom Docker image with ML dependencies
- NVIDIA A10G GPU allocation
- Volume storage for model weights
- Auto-scaling based on demand

**Example: Music Separation Service** (simplified from `modal_app_zfturbo_complete.py`)

```python
import modal

app = modal.App("music-ai-separator-zfturbo-complete")

# Volume for uploads, job status and result files
volume = modal.Volume.from_name("music-files-storage", create_if_missing=True)
storage_path = "/vol/music_files"

# ZFTurbo repo pinned to a fixed commit; SCNet XL IHF and Mel-Band RoFormer weights are
# downloaded at build time and verified against SHA-256 checksums
zfturbo_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(["ffmpeg", "libsndfile1", "git", "curl", "build-essential"])
    .run_commands([f"git clone {ZFTURBO_REPO} {ZFTURBO_DIR}",
                   f"cd {ZFTURBO_DIR} && git checkout {ZFTURBO_COMMIT}",
                   "pip install -r /tmp/requirements.txt"])
    .pip_install(["fastapi[standard]", "python-multipart", "requests"])
    .run_commands(_download_commands())  # wget + sha256sum -c per checkpoint
)

@app.function(
    image=zfturbo_image,
    gpu="a10g",                    # NVIDIA A10G (24GB VRAM)
    timeout=1800,                  # 30 minute max
    memory=20480,                  # 20GB RAM
    volumes={storage_path: volume},
    scaledown_window=120,
)
def bs_roformer_separate_audio(audio_data: bytes, filename: str, job_id: str,
                               selected_stems: str = "all", use_tta: bool = False,
                               extract_instrumental: bool = False) -> dict:
    """
    SCNet XL IHF -> vocals, drums, bass, other
    Mel-Band RoFormer (KimberleyJensen) -> cleaner vocals / instrumental
    (function name kept for compatibility with existing deployments)
    """
    # 1. Convert the upload to 44.1kHz stereo WAV with ffmpeg
    # 2. run_zfturbo_inference("stems", ...)  -> ZFTurbo inference.py --model_type scnet
    # 3. run_zfturbo_inference("vocals", ...) -> ZFTurbo inference.py --model_type mel_band_roformer
    # 4. Write stems, 30s previews and all.zip to the volume, update job status
    ...

@app.function(image=zfturbo_image, volumes={storage_path: volume})
@modal.asgi_app()
def fastapi_app():
    return create_fastapi_app()  # upload, status, download and health routes
```

**Modal Services Overview:**

| Service | GPU Memory | Avg Processing Time | Cost per Track |
|---------|------------|---------------------|----------------|
| SCNet + Mel-Band RoFormer Separation | 8-12GB | 45-120s | €0.014-€0.037 |
| Speech Enhancement | 4-6GB | 15-30s | €0.005-€0.010 |
| AI Mastering | 2-4GB | 30-60s | €0.010-€0.020 |
| Music Transcription | 6-8GB | 20-45s | €0.006-€0.017 |
| Audio Generation | 10-14GB | 10-20s | €0.003-€0.007 |

---

## Database Design

### Supabase PostgreSQL Schema

**Entity-Relationship Diagram:**

```
┌─────────────────┐
│  credit_users   │
├─────────────────┤
│ id (PK)         │──┐
│ email           │  │
│ credits         │  │
│ stripe_cust_id  │  │
│ created_at      │  │
│ updated_at      │  │
└─────────────────┘  │
                     │
        ┌────────────┴────────────┐
        │                         │
        ↓                         ↓
┌─────────────────┐     ┌─────────────────┐
│credit_purchases │     │  credit_usage   │
├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │
│ user_id (FK)    │     │ user_id (FK)    │
│ credits         │     │ credits         │
│ package_type    │     │ service         │
│ session_id      │     │ job_id          │
│ payment_amount  │     │ processing_time │
│ created_at      │     │ file_size       │
└─────────────────┘     │ created_at      │
                        └─────────────────┘
```

**Key Tables:**

**1. credit_users**
```sql
CREATE TABLE credit_users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    credits INTEGER DEFAULT 0 CHECK (credits >= 0),
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index on email for fast lookups
CREATE INDEX idx_credit_users_email ON credit_users(email);
```

**2. credit_purchases**
```sql
CREATE TABLE credit_purchases (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT REFERENCES credit_users(id) ON DELETE CASCADE,
    credits INTEGER NOT NULL CHECK (credits > 0),
    package_type TEXT NOT NULL,
    stripe_session_id TEXT UNIQUE,
    payment_amount DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for analytics
CREATE INDEX idx_credit_purchases_user_id ON credit_purchases(user_id);
CREATE INDEX idx_credit_purchases_session_id ON credit_purchases(stripe_session_id);
```

**3. credit_usage**
```sql
CREATE TABLE credit_usage (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT REFERENCES credit_users(id) ON DELETE CASCADE,
    credits INTEGER NOT NULL CHECK (credits > 0),
    service TEXT NOT NULL,
    job_id TEXT,
    modal_endpoint TEXT,
    processing_time INTEGER,
    file_size INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for analytics and user history
CREATE INDEX idx_credit_usage_user_id ON credit_usage(user_id);
CREATE INDEX idx_credit_usage_service ON credit_usage(service);
CREATE INDEX idx_credit_usage_created_at ON credit_usage(created_at DESC);
```

### Stored Procedures

**Atomic Credit Operations:**

**1. add_user_credits()**
```sql
CREATE OR REPLACE FUNCTION add_user_credits(
    p_user_id TEXT,
    p_credits INTEGER,
    p_package_type TEXT,
    p_session_id TEXT,
    p_payment_amount DECIMAL
)
RETURNS TABLE(new_balance INTEGER, transaction_id UUID) AS $$
DECLARE
    v_transaction_id UUID;
    v_new_balance INTEGER;
BEGIN
    -- Insert purchase record
    INSERT INTO credit_purchases (user_id, credits, package_type, stripe_session_id, payment_amount)
    VALUES (p_user_id, p_credits, p_package_type, p_session_id, p_payment_amount)
    RETURNING id INTO v_transaction_id;

    -- Update user credits (atomic)
    UPDATE credit_users
    SET credits = credits + p_credits, updated_at = NOW()
    WHERE id = p_user_id
    RETURNING credits INTO v_new_balance;

    RETURN QUERY SELECT v_new_balance, v_transaction_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**2. deduct_user_credits()**
```sql
CREATE OR REPLACE FUNCTION deduct_user_credits(
    p_user_id TEXT,
    p_credits INTEGER,
    p_service TEXT,
    p_job_id TEXT DEFAULT NULL
)
RETURNS TABLE(new_balance INTEGER, usage_id UUID) AS $$
DECLARE
    v_usage_id UUID;
    v_current_balance INTEGER;
    v_new_balance INTEGER;
BEGIN
    -- Check current balance
    SELECT credits INTO v_current_balance
    FROM credit_users
    WHERE id = p_user_id;

    -- Validate sufficient credits
    IF v_current_balance < p_credits THEN
        RAISE EXCEPTION 'Insufficient credits. Current: %, Required: %',
            v_current_balance, p_credits;
    END IF;

    -- Insert usage record
    INSERT INTO credit_usage (user_id, credits, service, job_id)
    VALUES (p_user_id, p_credits, p_service, p_job_id)
    RETURNING id INTO v_usage_id;

    -- Update user credits (atomic)
    UPDATE credit_users
    SET credits = credits - p_credits, updated_at = NOW()
    WHERE id = p_user_id
    RETURNING credits INTO v_new_balance;

    RETURN QUERY SELECT v_new_balance, v_usage_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## Payment System

### Stripe Integration Flow

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ 1. Click "Buy Credits"
       ↓
┌─────────────────────────────────────────┐
│  Frontend                                │
│  paywall.showPurchaseModal()            │
└──────┬──────────────────────────────────┘
       │ 2. POST /api/create-checkout-session
       ↓
┌─────────────────────────────────────────┐
│  Vercel Edge Function                   │
│  stripe.checkout.sessions.create({      │
│    line_items: [{ price: priceId }],    │
│    metadata: { userId, packageType }    │
│  })                                      │
└──────┬──────────────────────────────────┘
       │ 3. Return checkout URL
       ↓
┌─────────────────────────────────────────┐
│  Stripe Checkout                        │
│  User enters payment info               │
│  (Supports: Card, Klarna, PayPal, etc.) │
└──────┬──────────────────────────────────┘
       │ 4. Payment successful
       ↓
┌─────────────────────────────────────────┐
│  Stripe Webhook Event                   │
│  checkout.session.completed             │
└──────┬──────────────────────────────────┘
       │ 5. POST /api/webhook (signed)
       ↓
┌─────────────────────────────────────────┐
│  Webhook Handler                        │
│  1. Verify signature                    │
│  2. Extract metadata                    │
│  3. Call add_user_credits()             │
│  4. Return 200 OK                       │
└──────┬──────────────────────────────────┘
       │ 6. Credits added to Supabase
       ↓
┌─────────────────────────────────────────┐
│  Supabase Database                      │
│  - Insert credit_purchases              │
│  - Update credit_users.credits          │
│  (All atomic via stored procedure)      │
└─────────────────────────────────────────┘
```

### Security Measures

1. **Webhook Signature Verification**
```javascript
const signature = req.headers['stripe-signature']
const event = stripe.webhooks.constructEvent(
  req.body,
  signature,
  process.env.STRIPE_WEBHOOK_SECRET
)
// Only proceed if signature valid
```

2. **Idempotent Credit Allocation**
```sql
-- stripe_session_id is UNIQUE
-- Prevents duplicate credit allocation on webhook retries
INSERT INTO credit_purchases (stripe_session_id, ...)
VALUES ('cs_xxx', ...)
ON CONFLICT (stripe_session_id) DO NOTHING
```

3. **Credit Addition Requires Webhook Secret**
```javascript
// Only webhook can add credits
if (req.body.webhookSecret !== process.env.CREDIT_WEBHOOK_SECRET) {
  return res.status(403).json({ error: 'Unauthorized' })
}
```

---

## AI/ML Pipeline

### Model Deployment Strategy

**1. Model Storage:**
- Weights are downloaded at image build time and baked into the container images
  (separation checkpoints pinned to fixed URLs/commits and verified with SHA-256)
- Exception: the gated MuScriptor weights are cached in the `muscriptor-hf-cache` volume on first use
- Gated Hugging Face models (MuScriptor, Stable Audio Open) need a Modal secret `huggingface` with `HF_TOKEN`
- Modal volumes hold uploads, job status and result files, not model weights

**2. Models per service:**

| Service | File | Models |
|---------|------|--------|
| Separation | `modal_app_zfturbo_complete.py` | SCNet XL IHF (4 stems), Mel-Band RoFormer (vocals/instrumental) |
| Speech Enhancement | `modal_app_enhancement.py` | MossFormer2_SE_48K, Whisper large-v3-turbo, AST (AudioSet) |
| Transcription | `modal_app_transcription.py` | MuScriptor large, beat_this, essentia (chords, key) |
| Generation | `modal_app_audio_generation.py` | Stable Audio Open 1.0 |
| Mastering | `modal_app_matchering.py` | pedalboard DSP chain (no neural model) |

**3. Inference (separation):**
```python
# The separation service calls ZFTurbo's inference.py once per model
cmd = [
    "python", f"{ZFTURBO_DIR}/inference.py",
    "--model_type", model["model_type"],          # "scnet" or "mel_band_roformer"
    "--config_path", f"{MODEL_DIR}/{model['config_file']}",
    "--start_check_point", f"{MODEL_DIR}/{model['model_file']}",
    "--input_folder", str(input_dir),
    "--store_dir", str(store_dir),
    "--device_ids", "0",
]
if use_tta:
    cmd.append("--use_tta")                       # test-time augmentation: better quality, ~2x time
if extract_instrumental:
    cmd.append("--extract_instrumental")

env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"  # reduce GPU memory fragmentation
subprocess.run(cmd, capture_output=True, text=True, timeout=1500, env=env, cwd=ZFTURBO_DIR)
```

**4. Error Handling:**
- Each job writes its status (progress, phase, error) to the volume; the frontend polls it
- A failed inference run sets the job status to `error` with the last part of stderr, instead of hanging

---

## Security Architecture

### Multi-Layer Security

**1. Row-Level Security (RLS)**
```sql
-- Users can only see their own data
ALTER TABLE credit_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own data" ON credit_users
    FOR SELECT USING (auth.uid()::text = id);

-- Service role bypasses RLS (for API operations)
CREATE POLICY "Service role full access" ON credit_users
    FOR ALL USING (auth.role() = 'service_role');
```

**2. API Authentication**
```javascript
// Supabase service role key (server-side only)
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY  // Never exposed to client
)
```

**3. CORS Policy**
```javascript
// Only allow specific origins
const allowedOrigins = [
  'https://studio.kleindigitalsolutions.de',
  'http://localhost:3000'
]

if (allowedOrigins.includes(req.headers.origin)) {
  res.setHeader('Access-Control-Allow-Origin', req.headers.origin)
}
```

**4. Rate Limiting (Future)**
```javascript
// Vercel Edge Config + Upstash Redis
const rateLimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(10, "1 m"),
})

const { success } = await rateLimit.limit(userId)
if (!success) return res.status(429).json({ error: 'Too many requests' })
```

---

## Deployment Strategy

### CI/CD Pipeline

**Vercel (Frontend + API):**
```yaml
# Auto-deploy on git push
git push origin main
→ Vercel builds and deploys
→ Edge functions deployed globally
→ Automatic HTTPS certificate
```

**Modal (AI Services):**
```bash
# Manual deployment with CLI
modal deploy modal_app_zfturbo_complete.py
→ Image built and cached
→ Function deployed to Modal cloud
→ GPU auto-scaling enabled
```

### Environment Management

**Development:**
```bash
# Local frontend
python3 -m http.server 8080

# Test Modal functions locally
modal run modal_app_zfturbo_complete.py
```

**Staging:**
```bash
# Vercel preview deployment
vercel  # Creates preview URL

# Modal staging app
modal deploy modal_app_zfturbo_complete.py --name staging
```

**Production:**
```bash
# Vercel production
vercel --prod

# Modal production
modal deploy modal_app_zfturbo_complete.py
```

---

## Monitoring & Observability

### Metrics & Logging

**Vercel Analytics:**
- Edge function execution time
- Error rates
- Geographic distribution
- Cache hit rates

**Modal Logs:**
```python
import logging

logger = logging.getLogger(__name__)

@app.function()
def process_audio(file):
    logger.info(f"Processing started: {file.name}")
    # ... processing ...
    logger.info(f"Processing completed in {duration}s")
```

**Supabase Analytics:**
```sql
-- Daily credit usage
SELECT
    DATE(created_at) as date,
    service,
    COUNT(*) as usage_count,
    SUM(credits) as total_credits
FROM credit_usage
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at), service;

-- Revenue analytics
SELECT
    package_type,
    SUM(payment_amount) as revenue,
    COUNT(*) as purchases
FROM credit_purchases
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY package_type;
```

### Error Tracking

**Stripe Webhook Events:**
- Logged in Stripe dashboard
- Failed webhooks auto-retry
- Email alerts on repeated failures

**Modal GPU Errors:**
- Auto-retry on transient failures
- Logs stored in Modal dashboard
- Alerts on sustained error rates

---

## Performance Optimizations

### Frontend
- **Lazy Loading**: Service tabs load on demand
- **Image Optimization**: WebP format, optimized sizes
- **Code Splitting**: Separate bundles for each service
- **Service Worker**: Cache static assets

### Backend
- **Edge Functions**: Global distribution, low latency
- **Connection Pooling**: Supabase connection pool
- **Query Optimization**: Indexed columns, efficient joins

### GPU Compute
- **Model Caching**: Persistent volumes for model weights
- **Warm Instances**: Keep instances warm during peak hours
- **Batch Processing**: Process multiple segments in parallel
- **Half Precision**: FP16 for faster inference (where applicable)

---

## Scalability Considerations

**Current Limits:**
- Vercel Edge Functions: 10s timeout, 4.5MB response limit
- Modal A10G: 10 minute timeout, 24GB VRAM
- Supabase: 500GB database, unlimited API requests

**Scaling Strategies:**
- **Horizontal**: Modal auto-scales to 100+ GPUs
- **Vertical**: Upgrade to A100 GPUs for larger models
- **Geographic**: Deploy Modal functions in multiple regions
- **Caching**: Redis cache for frequent queries

---

This architecture supports **production-grade AI services** with enterprise-level security, scalability, and performance.
