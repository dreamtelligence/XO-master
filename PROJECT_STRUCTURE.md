# 📂 Project Structure

Clean, production-ready file organization for the AI Music Studio Platform.

---

## Directory Tree

```
ai-music-studio/
├── 📄 Core Files
│   ├── index.html                          # Main SPA (360KB)
│   ├── sw.js                               # Service Worker (PWA)
│   ├── package.json                        # Node.js dependencies
│   ├── vercel.json                         # Vercel deployment config
│   ├── .gitignore                          # Git ignore rules
│   ├── .env.example                        # Environment variables template
│   └── supabase_credit_schema.sql          # Database schema
│
├── 📄 Documentation
│   ├── README.md                           # Main project README
│   ├── LICENSE                             # MIT License
│   ├── CONTRIBUTING.md                     # Contribution guidelines
│   ├── CLAUDE.md                           # AI assistant context
│   └── PROJECT_STRUCTURE.md                # This file
│
├── 📁 docs/
│   ├── ARCHITECTURE.md                     # System architecture (70KB)
│   └── SETUP.md                            # Development setup guide (60KB)
│
├── 📁 api/                                 # Vercel Edge Functions
│   ├── credits.js                          # Credit management (294 lines)
│   ├── webhook.js                          # Stripe webhook handler
│   ├── create-checkout-session.js          # Payment session creation
│   └── paywall.js                          # Credit verification
│
├── 📁 Modal AI Services (Python)
│   ├── modal_app_zfturbo_complete.py       # SCNet XL IHF + Mel-Band RoFormer separation (26KB)
│   ├── modal_app_enhancement.py            # MossFormer2 + Whisper turbo + AST (27KB)
│   ├── modal_app_matchering.py             # pedalboard mastering chain (41KB)
│   ├── modal_app_transcription.py          # MuScriptor + beat_this + essentia (47KB)
│   └── modal_app_audio_generation.py       # Stable Audio Open 1.0 (12KB)
│
├── 📁 public/
│   ├── header.webp                         # Hero image (85KB)
│   ├── header.jpg                          # Hero image fallback (365KB)
│   └── favicons/                           # App icons
│       ├── favicon.ico
│       ├── apple-touch-icon.png
│       ├── favicon-16x16.png
│       ├── favicon-32x32.png
│       ├── android-chrome-192x192.png
│       └── android-chrome-512x512.png
│
├── 📁 Legal Pages (German)
│   ├── impressum.html                      # Imprint
│   ├── datenschutz.html                    # Privacy policy
│   └── agb.html                            # Terms & conditions
│
└── 📁 .github/
    ├── workflows/
    │   ├── ci.yml                          # Continuous Integration
    │   └── deploy.yml                      # Automated deployment
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md                   # Bug report template
    │   └── feature_request.md              # Feature request template
    ├── pull_request_template.md            # PR template
    └── REPOSITORY_SETUP.md                 # GitHub setup guide
```

---

## File Categories

### 🎯 Core Application Files (Must Keep)

**Frontend:**
- `index.html` - Single Page Application with all services
- `sw.js` - Service Worker for PWA functionality
- `public/` - Static assets (images, icons)

**Backend API:**
- `api/*.js` - Vercel serverless functions (4 files)

**AI Services:**
- `modal_app_*.py` - Modal GPU services (5 files)

**Configuration:**
- `package.json` - Dependencies and scripts
- `vercel.json` - Deployment configuration
- `.gitignore` - Git ignore patterns
- `.env.example` - Environment variables template

**Database:**
- `supabase_credit_schema.sql` - PostgreSQL schema with RLS

### 📚 Documentation Files (Portfolio Essential)

**Main Docs:**
- `README.md` - Project overview and showcase
- `LICENSE` - MIT License
- `CONTRIBUTING.md` - Contribution guidelines
- `CLAUDE.md` - AI assistant context
- `PROJECT_STRUCTURE.md` - This file

**Detailed Guides:**
- `docs/ARCHITECTURE.md` - Technical deep-dive
- `docs/SETUP.md` - Development setup

**GitHub:**
- `.github/` - Issue templates, PR template, workflows

### 🌍 Legal Pages (Required for Production)

German legal requirements:
- `impressum.html` - Imprint (Impressumspflicht)
- `datenschutz.html` - Privacy policy (DSGVO)
- `agb.html` - Terms & conditions

---

## File Sizes

| Category | Files | Total Size |
|----------|-------|------------|
| **Frontend** | 4 | ~360KB |
| **Documentation** | 7 | ~150KB |
| **API Functions** | 4 | ~30KB |
| **Modal Services** | 5 | ~176KB |
| **Images** | 8 | ~450KB |
| **Legal Pages** | 3 | ~40KB |
| **Config Files** | 4 | ~5KB |
| **Total** | ~35 files | ~1.2MB |

---

## What Was Removed

### ❌ Deleted Files (Cleanup)

**Duplicate Documentation:**
- ❌ `CREDIT_SYSTEM_IMPLEMENTATION.md` → Moved to `docs/ARCHITECTURE.md`
- ❌ `FINAL_STRUCTURE.md` → Outdated
- ❌ `modal_deployment.md` → Moved to `docs/SETUP.md`

**Duplicate Modal Apps:**
- ❌ `modal_app_enhanced_simple.py` → Duplicate of `modal_app_enhancement.py`
- ❌ `modal_app_zfturbo_enhanced.py` → Duplicate of `modal_app_zfturbo_complete.py`
- ❌ `modal_apps/` directory → All duplicates

**Backup Files:**
- ❌ `vercel-backup.json` → Not needed (Git history exists)
- ❌ `vercel-public.json` → Unused

**Old Scripts:**
- ❌ `deploy_enhanced.sh` → Replaced by GitHub Actions
- ❌ `deploy_modal.sh` → Replaced by GitHub Actions

**Unused Code:**
- ❌ `performance-optimizations.js` → Not included in index.html

**Total Removed:** 11 files (~150KB)

---

## Production Deployment Files

### Required for Vercel Deployment

```
✅ index.html
✅ api/
✅ public/
✅ vercel.json
✅ package.json
✅ sw.js
✅ Legal pages (impressum.html, datenschutz.html, agb.html)
```

### Required for Modal Deployment

```
✅ modal_app_zfturbo_complete.py
✅ modal_app_enhancement.py
✅ modal_app_matchering.py
✅ modal_app_transcription.py
✅ modal_app_audio_generation.py
```

### Required for Database Setup

```
✅ supabase_credit_schema.sql
```

---

## Development Files

### For Local Development

```
✅ .env.example              → Copy to .env and fill in
✅ package.json              → npm install
✅ docs/SETUP.md             → Follow setup guide
```

### For Contributors

```
✅ CONTRIBUTING.md           → Contribution guidelines
✅ .github/                  → Issue/PR templates
✅ docs/ARCHITECTURE.md      → Technical details
```

---

## File Ownership & Purpose

### Frontend Team
- `index.html` - Main application
- `sw.js` - Service Worker
- `public/` - Assets
- Legal pages

### Backend Team
- `api/` - Vercel functions
- `modal_app_*.py` - AI services
- `supabase_credit_schema.sql` - Database

### DevOps Team
- `vercel.json` - Deployment config
- `.github/workflows/` - CI/CD
- `.gitignore` - Git rules

### Documentation Team
- `README.md` - Main docs
- `docs/` - Technical docs
- `.github/` templates

---

## Recommended Next Steps

### 1. Environment Setup
```bash
cp .env.example .env
# Fill in your API keys
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Database Setup
```bash
psql -h [SUPABASE_HOST] -U postgres -f supabase_credit_schema.sql
```

### 4. Deploy Modal Services
```bash
modal deploy modal_app_zfturbo_complete.py
modal deploy modal_app_enhancement.py
modal deploy modal_app_matchering.py
modal deploy modal_app_transcription.py
modal deploy modal_app_audio_generation.py
```

### 5. Deploy Frontend
```bash
vercel --prod
```

---

## File Maintenance

### When Adding New Features

**New AI Service:**
1. Create `modal_app_[service].py`
2. Add to deployment workflow in `.github/workflows/deploy.yml`
3. Update `index.html` with new service tab
4. Document in `docs/ARCHITECTURE.md`

**New API Endpoint:**
1. Create `api/[endpoint].js`
2. Test locally with `vercel dev`
3. Add tests to `.github/workflows/ci.yml`
4. Document in `docs/ARCHITECTURE.md`

**New Documentation:**
1. Add to `docs/` directory
2. Link from `README.md`
3. Update this `PROJECT_STRUCTURE.md`

---

## Archive Policy

**Keep:**
- All production code
- All documentation
- All configuration files
- Git history (don't force push)

**Don't Keep:**
- Temporary files (.tmp, .log)
- Build artifacts (dist/, build/)
- Environment files (.env)
- node_modules/
- __pycache__/

**Use .gitignore for automatic exclusion**

---

## Backup Strategy

**Git:**
- All code is version controlled
- No need for `.backup` files

**Database:**
- Supabase provides automatic backups
- Export schema with: `pg_dump -s`

**Deployment:**
- Vercel keeps deployment history
- Modal keeps function versions

---

**Project Structure Last Updated:** 2024-10-10
**Total Files:** 35
**Total Size:** ~1.2MB (excluding node_modules)
