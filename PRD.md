# Product Requirements Document (PRD)
## YouTube SEO Metadata Generator & Auto-Updater

**Document Version:** 1.0  
**Date:** November 2, 2025  
**Author:** Product Team

---

## 1. Product Overview

### 1.1 Working Title
**YouTube SEO Metadata Generator & Auto-Updater**

### 1.2 Goal
Given a YouTube video URL, the system:
- Pulls the video's transcript
- Generates SEO-optimized metadata using AI:
  - **Title**: ≤100 characters
  - **Description**: ≤5000 characters
  - **Keywords/Tags**: ≤500 total characters, comma-separated, NO hashtags
- Automatically updates the video metadata on YouTube
- Implements safeguards, rollbacks, and optional approval flows

### 1.3 Primary Users
- Channel owners with permission to update videos
- Video editors with YouTube channel access
- Content marketers managing multiple videos

### 1.4 Success Metrics (KPIs)
- **+CTR** on impressions (YouTube Analytics) vs. 7-day pre-baseline
- **+Average View Duration (AVD)** and % viewed
- **+Search-driven views** (Browse/Shorts when applicable)
- **+Suggested traffic share** from relevant queries
- **Reduced time to publish** optimized metadata (< 2 minutes median)
- **Automation success rate**: 99% on eligible videos

---

## 2. Key Requirements (TL;DR)

| Requirement | Description |
|-------------|-------------|
| **Input** | YouTube URL (single or batch), optional: target language, brand keywords, tone, negative keywords |
| **Transcript** | Fetch via Captions API (owned videos) or fallback to extraction library/ASR |
| **AI Generation** | Title, description, tags within platform limits. NO hashtags. Tags are comma-separated |
| **Character Limits** | Hard enforcement with graceful truncation preserving semantic integrity |
| **Auto-Update** | Via YouTube Data API v3 with OAuth2 (user-granted) |
| **Automations** | Schedule re-optimization, bulk jobs, performance guardrails, auto-rollback, notifications |
| **Audit Trail** | Versioning for all metadata changes per video |
| **Modes** | Dry-run/approve mode AND instant publish mode |
| **i18n** | Multi-language transcripts with optional localized metadata |

---

## 3. Detailed Functional Requirements

### 3.1 Input & Validation

#### Required Inputs:
- YouTube video URL (format: `https://www.youtube.com/watch?v=VIDEO_ID`)

#### Optional Inputs:
- Primary/secondary target keywords
- Brand terms and style guide
- Tone/style preferences (educational, punchy, professional)
- Target language(s)
- Default CTA snippets
- Product names/USPs
- Prohibited terms list

#### Batch Upload:
- CSV/JSON format with columns:
  - `video_url` (required)
  - `lang` (optional)
  - `notes` (optional)
  - `priority` (optional)
  - `custom_keywords` (optional)

#### Validation Steps:
1. Verify URL format and extract `videoId`
2. Resolve & validate `videoId` via YouTube API
3. Ensure authenticated user has rights to update video
4. Check API quotas before proceeding

---

### 3.2 Transcript Retrieval

#### Preferred Method:
- **YouTube Captions API** for owned videos
  - `captions.list(videoId)` → `captions.download(id)`
  - Requires OAuth scope for caption read

#### Fallback Methods:
1. **youtube_transcript_api** library
   - Fetch community/auto captions when permitted
   - `YouTubeTranscriptApi.get_transcript(video_id, languages=[...])`

2. **ASR (Automatic Speech Recognition)**
   - Download audio via `pytube` or `yt-dlp` (only if user owns rights)
   - Run speech-to-text locally or via vendor API

#### Edge Cases:
- Multi-track captions → select best-confidence, desired language
- Timestamps only → parse and use available data
- Partial segments → handle gracefully
- Language detection → auto-detect or use user preference
- No transcript available → trigger ASR or show actionable error

---

### 3.3 SEO Generation Logic (AI-Assisted)

#### Guidelines Enforced:

##### Title (≤100 chars)
- Lead with primary query/keyword
- Compelling value proposition
- Avoid clickbait
- Include brand when useful
- Readable capitalization
- No emojis (unless explicitly allowed by user)
- Avoid bracket abuse

##### Description (≤5000 chars)
- **First 1-2 sentences** (150-200 chars):
  - Front-load hook/primary keywords
  - These appear in search snippets
- Include:
  - Concise summary
  - Key takeaways
  - Timestamps/chapters (if available)
  - CTAs (Call-to-Action)
  - Links to related videos/playlists
  - Credits and gear list
  - Disclosure text (as configured)
- Keep keyword density natural (avoid stuffing)

##### Tags (≤500 chars total, comma-separated)
- Primary/secondary keywords
- Long-tail variations
- Entities and topics
- Misspellings/aliases (where appropriate)
- High relevance only
- **NO hashtags (#)**

#### NLP Pipeline:

1. **Clean & Normalize Transcript**
   - Fix punctuation and casing
   - Remove filler words
   - Remove sponsor reads (if configured)

2. **Topic/Keyphrase Extraction**
   - TextRank/KeyBERT for keywords
   - Named Entity Recognition (NER)

3. **Query Intent Mapping**
   - Classify: informational vs. how-to vs. review vs. news
   - Identify target audience

4. **Draft Generation via LLM**
   - Style guardrails and brand voice
   - Constrained decoding to hit character limits
   - Multi-pass refinement

5. **Policy Filters**
   - Profanity list
   - Legal/compliance exclusions
   - Brand do/don't lists

6. **Final Pass**
   - Rewriter for fluency and limit compliance
   - Dedupe near-synonyms in tags
   - Ensure NO hashtags anywhere
   - Validate character counts

---

### 3.4 Automations & Workflows

#### Operation Modes:

##### 1. Instant Update
- Generate → Update metadata immediately
- No human approval required
- Best for: High-volume channels with trust in automation

##### 2. Approve & Publish
- Generate → Await human approval → Update
- Preview and edit before publishing
- Best for: High-stakes videos, compliance-sensitive content

##### 3. Scheduled Re-Optimization
- Re-run generation weekly or on performance triggers
- Example trigger: CTR < baseline − X% for N days
- Suggest or push updates based on configuration

#### Performance Guardrails:

1. **Post-Change Monitoring**
   - Track metrics (CTR, impressions, AVD) daily for 14 days
   - Compare to 7-day pre-change baseline

2. **Auto-Rollback Triggers**
   - If median CTR over last 3 days drops > Y% vs. baseline
   - AND impressions are stable (±Z%)
   - → Automatically revert to previous metadata
   - → Send notification

3. **Notification Events**
   - Generation finished
   - Publish succeeded/failed
   - Guardrail triggered
   - Rollback executed
   - Weekly performance report

#### Batch Jobs:
- CSV import to generate/publish for many videos
- Concurrency controls with rate-limit awareness
- Progress tracking and error handling
- Partial failure recovery

---

### 3.5 Publishing to YouTube

#### APIs Used:
- **YouTube Data API v3**
  - `videos.update(part=snippet)`
  - Update: `title`, `description`, `tags`

#### OAuth Scopes Required:
```
https://www.googleapis.com/auth/youtube
https://www.googleapis.com/auth/youtube.force-ssl
https://www.googleapis.com/auth/yt-analytics.readonly
https://www.googleapis.com/auth/youtube.readonly (for captions)
```

#### Quota & Error Handling:
| Error Code | Description | Action |
|------------|-------------|--------|
| 403 | `rateLimitExceeded` | Exponential backoff with jitter |
| 403 | `quotaExceeded` | Queue for next day, notify admin |
| 400 | `invalidValue` | Validate and sanitize inputs |
| 401/403 | `insufficientPermissions` | Re-authenticate or skip |

#### Safety Measures:
- Only update fields we own (preserve visibility, category, etc.)
- Option to **append** vs. **replace** sections of descriptions
- Keep affiliate disclosures and legal text
- Version control for rollback

---

### 3.6 Compliance & Brand Controls

#### Policy Controls:
- **Prohibited terms list**: Words/phrases to never include
- **Required legal disclosures**: Auto-insert or preserve
- **COPPA flag**: Respect and maintain
- **No misrepresentation**: Accuracy checks

#### Brand Configuration:
- Configurable brand voice/tone
- Do/don't lists for language
- Required brand mentions
- CTA templates

#### Chapter Generation:
- Option to keep existing chapters
- Auto-generate from transcript timestamps (if policy allows)
- Format: `0:00 Intro | 1:23 Topic 1 | 5:45 Conclusion`

---

### 3.7 Telemetry & Reporting

#### Data Stored Per Version:
- Metadata snapshot (title, description, tags)
- Timestamp of change
- Actor (human username or "automation")
- Diff from previous version
- Performance baseline at time of change
- Reason for change (scheduled, manual, performance-triggered)

#### Dashboard Features:
- Per-video metrics pre/post change
- Cohort analysis (all videos changed in timeframe)
- Win/loss rate (% of changes improving CTR)
- Export to CSV for audit

#### Alerts:
- Slack/Email notifications
- Custom thresholds
- Weekly digest reports

---

## 4. Non-Functional Requirements (NFRs)

| NFR | Requirement | Target |
|-----|-------------|--------|
| **Language Support** | Unicode, RTL, multi-language | English + configurable languages |
| **Performance** | Single video end-to-end | < 30s avg (excluding ASR) |
| **Performance** | Batch throughput | 20+ videos/min (subject to quotas) |
| **Reliability** | Success rate on eligible videos | 99% |
| **Resilience** | Handle transient API errors | Retry with exponential backoff |
| **Security** | OAuth 2.0 | PKCE for installed apps |
| **Security** | Secrets | Encrypted at rest |
| **Security** | Logs | PII-safe, no token leakage |
| **Security** | Permissions | Principle of least privilege |
| **Observability** | Logging | Structured logs (JSON) |
| **Observability** | Error tracking | Sentry-style capture |
| **Observability** | Metrics | p50/p95 latency tracking |

---

## 5. User Stories & Acceptance Criteria

### Story 1: Quick Update
**As a** channel owner  
**I want to** paste a YouTube URL and click "Generate & Update"  
**So that** my video metadata is optimized in one step

**Acceptance Criteria:**
- ✅ Title ≤ 100 chars
- ✅ Description ≤ 5000 chars
- ✅ Tags ≤ 500 chars, comma-separated
- ✅ NO hashtags in any field
- ✅ YouTube reflects changes within 2 minutes
- ✅ Success notification shown

---

### Story 2: Preview & Edit
**As an** editor  
**I want to** preview AI outputs and edit before publishing  
**So that** I can ensure brand consistency

**Acceptance Criteria:**
- ✅ Inline editor with character counters
- ✅ Real-time limit enforcement
- ✅ Publish updates only chosen fields
- ✅ Can save draft without publishing

---

### Story 3: Scheduled Re-Optimization
**As a** marketer  
**I want** weekly re-optimization with impact reports  
**So that** my content stays current with SEO best practices

**Acceptance Criteria:**
- ✅ System re-runs on schedule
- ✅ Proposes changes with rationale
- ✅ Applies or queues based on config
- ✅ Report emailed/Slacked with metrics

---

### Story 4: Compliance
**As a** compliance owner  
**I need** certain disclaimers always included  
**So that** we meet legal requirements

**Acceptance Criteria:**
- ✅ Configured boilerplate preserved/inserted
- ✅ Prohibited terms blocked
- ✅ Audit trail for all changes

---

### Story 5: Rollback
**As an** analyst  
**I need** audit trail and rollback if performance drops  
**So that** we can quickly recover from bad changes

**Acceptance Criteria:**
- ✅ Version history stored per video
- ✅ One-click rollback restores previous metadata
- ✅ Auto-rollback on guardrail trigger
- ✅ Notification sent on rollback

---

## 6. System Design & Architecture

### 6.1 Components

```
┌─────────────────┐
│   CLI / Web UI  │  (FastAPI/Flask)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Orchestrator   │  (Celery/RQ for jobs & schedules)
└────────┬────────┘
         │
         ├──────► Transcript Service (Captions API + fallbacks/ASR)
         │
         ├──────► NLP/AI Service (LLM prompts, constraints, filters)
         │
         ├──────► Publisher (YouTube Data API v3 client)
         │
         ├──────► Analytics Poller (YouTube Analytics API)
         │
         ├──────► Datastore (PostgreSQL/SQLite)
         │
         └──────► Notifier (Slack/Email webhooks)
```

### 6.2 Data Model (Simplified)

#### Table: `videos`
```sql
CREATE TABLE videos (
    video_id VARCHAR(20) PRIMARY KEY,
    channel_id VARCHAR(30),
    title_current VARCHAR(100),
    description_current TEXT,
    tags_current VARCHAR(500),
    lang VARCHAR(10),
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Table: `metadata_versions`
```sql
CREATE TABLE metadata_versions (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(20) REFERENCES videos(video_id),
    title VARCHAR(100),
    description TEXT,
    tags VARCHAR(500),
    created_at TIMESTAMP,
    created_by VARCHAR(100),  -- user or 'automation'
    reason VARCHAR(255),       -- 'manual', 'scheduled', 'performance_trigger'
    performance_baseline_json TEXT,
    INDEX(video_id, created_at)
);
```

#### Table: `jobs`
```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50),          -- 'generate', 'publish', 'reoptimize'
    status VARCHAR(20),        -- 'pending', 'running', 'completed', 'failed'
    input_json TEXT,
    output_json TEXT,
    error_message TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

#### Table: `configs`
```sql
CREATE TABLE configs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    policy_json TEXT,          -- prohibited terms, required disclosures
    brand_json TEXT,           -- tone, style, CTAs
    notification_json TEXT,    -- Slack webhook, email addresses
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 6.3 Secrets Management
- Store in OS keyring or HashiCorp Vault
- OAuth tokens encrypted at rest
- Environment variables for non-sensitive config

---

## 7. API & Integration Details

### 7.1 YouTube Data API v3

#### Update Video Metadata:
```python
videos.update(
    part="snippet",
    body={
        "id": video_id,
        "snippet": {
            "title": new_title,
            "description": new_description,
            "tags": new_tags_list,
            "categoryId": existing_category  # preserve
        }
    }
)
```

**Scopes:**
- `https://www.googleapis.com/auth/youtube`
- `https://www.googleapis.com/auth/youtube.force-ssl`

### 7.2 Captions/Transcript

#### Owned Videos:
```python
# List captions
captions_list = youtube.captions().list(
    part="snippet",
    videoId=video_id
).execute()

# Download caption
caption_download = youtube.captions().download(
    id=caption_id
).execute()
```

#### Fallback (youtube_transcript_api):
```python
from youtube_transcript_api import YouTubeTranscriptApi

transcript = YouTubeTranscriptApi.get_transcript(
    video_id,
    languages=['en', 'auto']
)
```

### 7.3 YouTube Analytics API

#### Get Baseline Metrics:
```python
analytics.reports().query(
    ids="channel==MINE",
    startDate="7daysAgo",
    endDate="today",
    metrics="views,estimatedMinutesWatched,averageViewDuration,impressions,impressionCtr",
    filters=f"video=={video_id}",
    dimensions="day"
).execute()
```

**Scope:**
- `https://www.googleapis.com/auth/yt-analytics.readonly`

---

## 8. UX Flow (Web UI)

```
1. Paste video URL
   ↓
2. Validate ownership/permissions
   ↓
3. Fetch transcript
   ↓
4. Show detected language & length
   ↓
5. Click "Generate"
   ↓
6. Display AI-generated metadata:
   - Title (with 100-char counter)
   - Description (with 5000-char counter)
   - Tags (with 500-char counter)
   ↓
7. Optional: Edit inline
   ↓
8. Click "Publish" or "Schedule"
   ↓
9. Confirmation + link to video
   ↓
10. Analytics monitoring starts
    ↓
11. (If enabled) Scheduled re-optimization
    ↓
12. Notifications on success/issues
```

---

## 9. Constraints & Edge Cases

| Scenario | Handling |
|----------|----------|
| **No transcript available** | Show actionable error, offer manual paste or ASR |
| **Transcript too short/low quality** | Use title/description heuristics, related videos, channel context |
| **Non-owner URL** | Read-only preview, disable publish |
| **Multi-language** | If `lang=xx` set, translate metadata (keep original in versions) |
| **Character limit enforcement** | Truncate smartly, avoid mid-word cuts, ellipsize gracefully |
| **Tags deduplication** | Combine unique tokens, remove duplicates, strip # characters |
| **API quota exceeded** | Queue for retry, notify admin, resume next day |
| **OAuth token expired** | Refresh token automatically, re-authenticate if needed |

---

## 10. AI Prompts & Constraints

### System Prompt Template (LLM)

```
You are a senior YouTube SEO strategist specializing in video optimization.

CONSTRAINTS:
- Title: Maximum 100 characters
- Description: Maximum 5000 characters
- Tags: Maximum 500 characters total, comma-separated
- NO hashtags (#) anywhere in any field
- Use natural language, avoid keyword stuffing
- Include primary keyword in the first sentence of description
- Be compelling but not clickbait

INPUTS PROVIDED:
- Primary keyword: "{primary_keyword}"
- Brand voice: "{brand_voice}"
- Target audience: "{target_audience}"
- Transcript (cleaned): "{transcript_text}"
- Channel context: "{channel_description}"

TASK:
Generate optimized metadata that:
1. Front-loads key phrases in first 150 chars of description
2. Includes concise summary and key takeaways
3. Uses primary + secondary keywords naturally
4. Adds clear CTA (Call-to-Action)
5. Maintains brand voice throughout

OUTPUT FORMAT (JSON):
{
  "title": "...",
  "description": "...",
  "tags": "keyword one, keyword two, keyword three, ..."
}

VALIDATION:
- Enforce character limits strictly
- Run toxicity/safety filter
- Strip any hashtags
- Ensure no forbidden terms
```

### Post-Processing Validation:
1. **Character Count Check**: Enforce hard limits
2. **Hashtag Removal**: Strip all `#` characters
3. **Toxicity Filter**: Run content moderation API
4. **Compliance Check**: Verify no prohibited terms
5. **Keyword Density**: Ensure natural distribution (1-2% target)

---

## 11. Example CLI Usage

### Single Video:
```bash
python main.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --mode auto \
  --lang en
```

### Batch Processing:
```bash
python main.py \
  --batch videos.csv \
  --mode approve \
  --notify slack
```

### Scheduled Re-optimization:
```bash
python main.py \
  --reoptimize \
  --video-ids "VIDEO_ID_1,VIDEO_ID_2" \
  --schedule weekly
```

---

## 12. High-Level Pseudo-Code

```python
def process_video(url, mode='auto', lang='en'):
    # 1. Extract and validate
    video_id = extract_video_id(url)
    assert has_permission(video_id), "Insufficient permissions"
    
    # 2. Get transcript
    transcript = get_transcript(video_id, lang)
    if not transcript:
        transcript = run_asr(video_id)  # fallback if allowed
    
    # 3. Extract keyphrases
    keyphrases = extract_keyphrases(transcript)
    
    # 4. Generate SEO metadata via LLM
    config = load_user_config()
    seo_json = llm_generate(
        transcript=transcript,
        keyphrases=keyphrases,
        config=config
    )
    
    # 5. Validate and clean
    seo_json = enforce_limits_and_clean(seo_json)
    
    # 6. Publish or save draft
    if mode == "approve":
        save_draft(video_id, seo_json)
        notify_user("Draft ready for review")
    else:
        # Get baseline metrics
        baseline = fetch_analytics_baseline(video_id)
        
        # Save previous version
        prev_metadata = get_current_metadata(video_id)
        
        # Update YouTube
        update_youtube(video_id, seo_json)
        
        # Save version history
        save_version(video_id, prev_metadata, seo_json, baseline)
        
        # Schedule guardrail checks
        schedule_guardrail_checks(video_id, baseline)
        
        notify_user("Video updated successfully")
```

---

## 13. Rollout Plan

### Phase 1: MVP (Weeks 1-4)
- ✅ CLI + single-video processing
- ✅ Approve/publish modes
- ✅ Transcript via Captions API + fallback
- ✅ Basic LLM integration
- ✅ Manual guardrails (no auto-rollback)

### Phase 2: Automation (Weeks 5-8)
- ✅ Web UI (FastAPI)
- ✅ Batch processing
- ✅ Scheduled re-optimization
- ✅ Auto-rollback on performance drop
- ✅ Slack/Email notifications

### Phase 3: Advanced Features (Weeks 9-12)
- ✅ Multi-language support
- ✅ ASR integration (Whisper/vendor API)
- ✅ Fine-tuned LLM prompts
- ✅ Advanced analytics dashboards
- ✅ Chapter auto-generation
- ✅ A/B testing framework

---

## 14. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **API quota limits** | High | Medium | Implement caching, backoff, job queuing; monitor usage |
| **Incorrect optimization hurting CTR** | High | Medium | Guardrails + auto-rollback + versioning |
| **Transcript unavailable/poor quality** | Medium | Medium | ASR fallback, manual paste option, flag low-confidence |
| **Policy/compliance violations** | High | Low | Required disclaimers, do/don't lists, human-in-loop option |
| **Model drift/prompt degradation** | Medium | Low | Keep prompt tests, periodic evaluation, manual overrides |
| **OAuth token expiration** | Low | Medium | Automatic refresh, graceful re-auth prompts |
| **Rate limiting during batch jobs** | Medium | High | Exponential backoff, queue management, spread over time |

---

## 15. Acceptance Test Checklist (Go/No-Go)

### Pre-Launch Checklist:

#### Functionality:
- [ ] Single video URL generates valid metadata
- [ ] Title ≤ 100 chars in all test cases
- [ ] Description ≤ 5000 chars in all test cases
- [ ] Tags ≤ 500 chars, comma-separated, NO hashtags
- [ ] Transcript retrieval works (Captions API + fallback)
- [ ] OAuth flow completes successfully
- [ ] Video metadata updates on YouTube
- [ ] Batch processing handles 50+ videos
- [ ] Scheduled re-optimization triggers correctly
- [ ] Auto-rollback works when CTR drops

#### Non-Functional:
- [ ] End-to-end processing < 30s per video
- [ ] 99% success rate on test set (N=100 videos)
- [ ] No secrets in logs
- [ ] Encrypted OAuth tokens
- [ ] Error notifications sent correctly
- [ ] Version history saved for all changes

#### Compliance:
- [ ] Prohibited terms blocked
- [ ] Required disclaimers preserved
- [ ] No policy violations in 100 test videos
- [ ] Audit trail complete and exportable

---

## 16. Open Questions (Stakeholder Sign-Off Required)

1. **Tone & Style**
   - What's the default tone? (educational, punchy, brand-specific)
   - Are emojis allowed in titles/descriptions?

2. **Chapters**
   - Should we auto-generate chapters from transcript timestamps?
   - Format preference for chapter markers?

3. **Thresholds**
   - Minimum metric thresholds for auto-rollback?
   - Default: CTR drop > 15%, impressions stable ±10%, N=3 days?

4. **Notifications**
   - Which channels? (Slack, Email, SMS)
   - Which recipients? (channel owner, team lead, analyst)
   - Frequency? (real-time, daily digest, weekly)

5. **Languages**
   - Priority languages beyond English?
   - Should we translate metadata or keep original language?

6. **ASR**
   - Which ASR vendor? (Whisper, Google, AWS)
   - Cost threshold for ASR usage?

---

## 17. Minimal Tech Stack

### Core:
- **Python**: 3.11+
- **Web Framework**: FastAPI or Flask
- **Google APIs**: `google-api-python-client`, `google-auth`, `google-auth-oauthlib`

### NLP & AI:
- **NLP**: `spacy`, `keybert`, `nltk`
- **LLM**: Pluggable (OpenAI API, Anthropic, Vertex AI, local)
- **Text Processing**: `regex`, `beautifulsoup4`

### Task Queue:
- **Queue**: Celery + Redis (or RQ for simpler setup)
- **Scheduler**: Celery Beat

### Database:
- **Development**: SQLite
- **Production**: PostgreSQL

### UI (Optional):
- **Frontend**: FastAPI templates (Jinja2) or React
- **Styling**: TailwindCSS or Bootstrap

### Notifications:
- **Slack**: Webhook integration
- **Email**: SMTP (SendGrid, AWS SES)

### DevOps:
- **Containerization**: Docker + docker-compose
- **Environment**: `.env` files, `python-dotenv`
- **Logging**: `structlog` or Python `logging` with JSON formatter
- **Monitoring**: Sentry for error tracking

---

## 18. Example LLM Prompt (Full)

```
SYSTEM: You are a senior YouTube SEO strategist with 10+ years of experience optimizing video content for maximum discoverability and engagement.

CONSTRAINTS:
- Title: EXACTLY ≤100 characters (strict limit)
- Description: EXACTLY ≤5000 characters (strict limit)
- Tags: EXACTLY ≤500 characters total, comma-separated list (strict limit)
- CRITICAL: NO hashtags (#) anywhere in title, description, or tags
- Use natural, conversational language
- Avoid keyword stuffing (keep density ~1-2%)
- Front-load primary keyword in first 10 words of description
- Be compelling but accurate (no misleading clickbait)

INPUTS:
- Primary Keyword: "{primary_keyword}"
- Secondary Keywords: "{secondary_keywords}"
- Brand Voice: "{brand_voice}"
- Target Audience: "{target_audience}"
- Video Transcript (cleaned, 500 words): 
"""
{transcript_excerpt}
"""
- Channel Description: "{channel_description}"
- Required CTA: "{cta_text}"
- Required Disclosure: "{disclosure_text}"

TASK:
Generate YouTube metadata that maximizes:
1. Click-through rate (CTR) from search and suggested videos
2. Watch time and audience retention
3. Discoverability via YouTube and Google search

DESCRIPTION STRUCTURE:
1. Hook (first 150 chars): Include primary keyword, value prop
2. Summary: 2-3 sentences about video content
3. Key Takeaways: Bullet points or numbered list
4. Timestamps: (if applicable) "0:00 Intro | 2:15 Topic 1 | ..."
5. CTA: "{cta_text}"
6. Links: Related videos, playlist, social media
7. Disclosure: "{disclosure_text}"

TAGS STRATEGY:
- Include 10-15 highly relevant tags
- Mix of: broad category, specific topics, long-tail phrases
- Include common misspellings if applicable
- NO brand name spam
- NO hashtags

OUTPUT FORMAT (valid JSON only):
{
  "title": "Your optimized title here",
  "description": "Your optimized description here...",
  "tags": "tag one, tag two, tag three, tag four"
}

VALIDATION CHECKLIST:
✓ Title has primary keyword in first 5 words
✓ Description hook is compelling and includes primary keyword
✓ All character limits respected
✓ No hashtags anywhere
✓ Natural language (not robotic)
✓ CTA and disclosure included
✓ Tags are relevant and specific

Now generate the metadata:
```

---

## 19. Success Criteria Summary

| Metric | Baseline | Target (30 days) | Measurement |
|--------|----------|------------------|-------------|
| CTR | Current avg | +15-25% | YouTube Analytics |
| AVD | Current avg | +10-15% | YouTube Analytics |
| Search traffic | Current % | +20-30% | Traffic source report |
| Time to optimize | 30+ min | < 2 min | Internal tracking |
| Automation success | N/A | 99% | System logs |
| User satisfaction | N/A | 4.5/5 | Post-use survey |

---

## 20. Appendix: API Rate Limits & Quotas

### YouTube Data API v3 Quotas:
- **Default daily quota**: 10,000 units
- **Cost per operation**:
  - `videos.list`: 1 unit
  - `videos.update`: 50 units
  - `captions.list`: 50 units
  - `captions.download`: 200 units

### Rate Limiting Strategy:
- **Cost per video update**: ~300 units (list + download + update)
- **Max videos per day**: ~30 videos (with default quota)
- **Request quota increase**: For > 50 videos/day
- **Caching**: Cache video metadata for 1 hour to reduce list calls
- **Batch prioritization**: High-value videos first

### YouTube Analytics API:
- **Quota**: Separate from Data API
- **Calls per video**: 1 per baseline fetch, 1 per daily check
- **Cache**: 24 hours for analytics data

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-02 | Product Team | Initial PRD creation |

---

## Approval Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | _____________ | _____________ | _______ |
| Engineering Lead | _____________ | _____________ | _______ |
| Compliance Lead | _____________ | _____________ | _______ |
| Marketing Lead | _____________ | _____________ | _______ |

---

**END OF DOCUMENT**
