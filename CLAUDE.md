# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Klein Digital Solutions AI Music Studio - Professional AI-powered music service platform offering stem separation, mastering, speech enhancement, transcription, and audio generation. The platform uses a credit-based payment system with Stripe integration and runs AI workloads on Modal's serverless GPU infrastructure.

**Tech Stack:**
- Frontend: Vanilla JavaScript + Bootstrap 5.3 (SPA hosted on Vercel)
- Backend: Modal Labs serverless functions (Python 3.11 + FastAPI)
- GPU: NVIDIA A10G (24GB VRAM)
- Payment: Stripe with credit system
- Database: Supabase (PostgreSQL with RLS)
- Deployment: Vercel (frontend + API routes), Modal (AI services)

## Development Commands

### Local Development
```bash
# Start local dev server
npm run dev          # Uses vercel dev server
# OR
python3 -m http.server 8080

# Install dependencies
npm install
```

### Modal AI Services Deployment
```bash
# Install Modal CLI
pip install modal

# Login to Modal
modal token new

# Deploy individual AI services
modal deploy modal_app_zfturbo_complete.py      # Music Separation (SCNet XL IHF + Mel-Band RoFormer)
modal deploy modal_app_enhancement.py           # Speech Enhancement (MossFormer2 + Whisper turbo + AST)
modal deploy modal_app_matchering.py            # AI Mastering
modal deploy modal_app_transcription.py         # Music Transcription (MIDI)
modal deploy modal_app_audio_generation.py      # Audio Generation (Stable Audio Open 1.0)

# List deployed apps
modal app list
```

### Vercel Deployment
```bash
# Deploy to production
vercel --prod

# Deploy to preview
vercel
```

## Architecture

### Credit System Flow
1. **User Management**: Users stored in Supabase `credit_users` table with credit balance
2. **Purchase Flow**: Stripe checkout → webhook → credit allocation via `api/webhook.js`
3. **Service Access**: Paywall check (`api/paywall.js`) → deduct credits (`api/credits.js`) → Modal AI service
4. **Security**: All credit operations use Supabase service role with RLS policies, webhook secret verification

### API Endpoints (Vercel Edge Functions)
- `GET/POST/PUT /api/credits` - Credit management (balance, add, deduct)
- `POST /api/create-checkout-session` - Stripe checkout session for credit packages
- `POST /api/webhook` - Stripe webhook for payment events
- `POST /api/paywall` - Credit verification before service access

### Modal AI Services
Each Modal app is a standalone FastAPI service with GPU access:
- **modal_app_zfturbo_complete.py**: SCNet XL IHF (4 stems) + Mel-Band RoFormer KJ (vocals/instrumental), weights baked into the image
- **modal_app_enhancement.py**: MossFormer2_SE_48K + Whisper large-v3-turbo + AST for speech enhancement (no TensorFlow: TF + torch in one process segfaulted)
- **modal_app_matchering.py**: Professional audio mastering chain
- **modal_app_transcription.py**: MuScriptor large (melody + drums) + beat_this + essentia (chords, key) for MIDI transcription
- **modal_app_audio_generation.py**: Stable Audio Open 1.0 for text-to-audio generation (no frontend UI yet)

### Frontend Structure
- **index.html**: Single-page application with all services
- Service tabs: Separation, Mastering, Transcription, Enhancement, Generation
- Credit balance displayed in user menu
- Paywall modal triggers when credits insufficient
- WaveSurfer.js for audio visualization

## Key Implementation Details

### Supabase Database Schema
Located in `supabase_credit_schema.sql`:
- **credit_users**: User accounts with credit balance
- **credit_purchases**: Purchase history with Stripe session tracking
- **credit_usage**: Service usage tracking with job details
- Stored procedures: `add_user_credits()`, `deduct_user_credits()` (atomic transactions)
- Views: Daily analytics, monthly revenue, user activity summary

### Credit Package Pricing (Launch Special)
```javascript
{
  'single': { credits: 1, price: '€3.49', stripe_price_id: 'price_SINGLE_CREDIT_ID' },
  'starter': { credits: 10, price: '€24.99', stripe_price_id: 'price_1RnxJsAmspxoSxsTWG1nkwdL' },
  'pro': { credits: 25, price: '€49.99', stripe_price_id: 'price_1RnxMNAmspxoSxsT13PcPtQW' },
  'studio': { credits: 50, price: '€79.99', stripe_price_id: 'price_1RnxO0AmspxoSxsTVTuTSQSe' }
}
```

### Environment Variables Required
```bash
# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...

# Security
CREDIT_WEBHOOK_SECRET=...  # For secure credit addition via webhook
```

### Modal GPU Configuration
A10G optimized settings for quality:
- **Segment Size**: 25-30 (vs 7-10 local) - larger segments = better quality
- **Shifts**: 2 shifts for improved separation
- **Processing Cost**: €0.014-€0.037 per track (99%+ profit margin)
- **Cold Start**: <10 seconds
- **Auto-scaling**: Unlimited concurrent users

### Security Measures
1. **Credit Management**: Server-side only, Supabase RLS policies
2. **Payment Webhook**: Stripe signature verification
3. **Credit Addition**: Requires `CREDIT_WEBHOOK_SECRET` (only via webhook)
4. **User Authentication**: Supabase auth integration
5. **Service Role**: Admin operations use `SUPABASE_SERVICE_ROLE_KEY`

## Important File Locations

- **Main Frontend**: `index.html` (360KB - comprehensive SPA)
- **API Functions**: `api/*.js` (webhook.js, credits.js, create-checkout-session.js, paywall.js)
- **Modal Services**: `modal_app_*.py` in root directory
- **Database Schema**: `supabase_credit_schema.sql`
- **Documentation**: `CREDIT_SYSTEM_IMPLEMENTATION.md`, `modal_deployment.md`, `FINAL_STRUCTURE.md`
- **Assets**: `public/header.webp`, `public/favicons/`

## Common Development Patterns

### Adding New Modal AI Service
1. Create `modal_app_<service>.py` with FastAPI endpoints
2. Use Modal image with required ML dependencies
3. Deploy with `modal deploy modal_app_<service>.py`
4. Update frontend with new service tab and API endpoint
5. Add service type to credit deduction logic

### Testing Credit Flow End-to-End
1. Enable admin mode in browser console: `enableAdminMode()`
2. Test purchase flow with Stripe test cards
3. Verify webhook credit allocation in Supabase dashboard
4. Test service usage and credit deduction
5. Check balance persistence: `disableAdminMode()`

### Modifying AI Model Parameters
Modal services have configuration at top of each file:
- Segment size, overlap, shifts (quality vs speed tradeoff)
- GPU memory settings (A10G has 24GB VRAM)
- Timeout and retry logic
- Output format and quality settings

## Domain and Deployment Info

- **Production Domain**: `studio.kleindigitalsolutions.de`
- **Vercel Deployment**: Auto-deploys from git push
- **Modal Endpoints**: `https://aliundmaggy--<app-name>-<function>.us-east.modal.run` (workspace `aliundmaggy`)
- **Gated models**: Modal secret `huggingface` (HF account Bucci369) must have accepted MuScriptor large + Stable Audio Open
- **Licenses**: MuScriptor weights are CC BY-NC 4.0 -> private/non-commercial use only
- **Stripe Allowed Domains**: Configured in Stripe Dashboard

## Performance Characteristics

- **Separation**: ~60s for a 30s track when warm
- **Speech Enhancement**: 15-30s processing
- **AI Mastering**: 30-60s processing
- **Music Transcription**: 20-45s processing
- **Audio Generation**: 10-20s processing
- **Profit Margin**: 99%+ on all services (Modal GPU costs vs credit pricing)

## Known Issues & Solutions

- **Modal Cold Starts**: First request after idle takes ~10s (warm instances are instant)
- **Large Files**: 100MB limit on file uploads (enforced client-side)
- **Webhook Retries**: Stripe retries failed webhooks - ensure idempotent credit allocation
- **CORS**: Configured for `studio.kleindigitalsolutions.de` and localhost
