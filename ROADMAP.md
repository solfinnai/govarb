# GovArb Roadmap — From MVP to Revenue

## Phase 1: Make the Scanner Actually Useful (Days 1-3)
*Goal: Someone could look at the output and make a real business decision*

### 1.1 Fix Price Matching (CRITICAL)
- [ ] Current: only matches ~10% of contracts (lookup table too small)
- [ ] Add DigiKey API integration (free developer key, 1000 req/day) — search by keyword, get real pricing
- [ ] Add Mouser API integration (free, search by part number / keyword)
- [ ] Add Octopart API as fallback (aggregates 100+ distributors)
- [ ] Parse NSN (National Stock Number) from descriptions to get exact part matches
- [ ] Parse part numbers from descriptions (regex: MS*, MIL-*, JANTX*, etc.)
- [ ] **Test:** Run scanner on 100 contracts, target >60% price match rate

### 1.2 Fix Data Quality
- [ ] Filter out mega-contracts (>$50M) — those aren't arbitrageable by small vendors
- [ ] Filter out classified/restricted contracts
- [ ] Better PSC code coverage — add: 5905 (Resistors), 5910 (Capacitors), 5920 (Fuses), 6210 (Indoor Lighting), 6240 (Electrical Lamps)
- [ ] Handle multi-line-item contracts (right now we only see total obligation, not per-item)
- [ ] Deduplicate contracts that appear under multiple award modifications
- [ ] **Test:** Manual review of top 20 opportunities — are they real?

### 1.3 Improve Scoring
- [ ] Weight by contract size (sweet spot: $5K-$500K — small enough to win, big enough to matter)
- [ ] Factor in incumbent advantage (how long has current vendor held this contract?)
- [ ] Factor in recompete timeline (when does this contract renew?)
- [ ] Add "ease of entry" score based on set-aside type, NAICS, and small business status
- [ ] **Test:** Score 50 contracts, have Henry manually rank them, compare to algorithm

---

## Phase 2: Make the Product Real (Days 4-7)
*Goal: Someone could sign up, pay, and get genuine value*

### 2.1 Automated Reports
- [ ] Build email report generator (HTML email with top 20 weekly opportunities)
- [ ] Add NAICS code filtering (users pick their industry)
- [ ] Add PSC code filtering (users pick their product categories)
- [ ] Schedule: daily scan at 6 AM ET, weekly digest every Monday
- [ ] Store scan results in SQLite database for history/trends

### 2.2 Landing Page → Real Checkout
- [ ] Buy domain (govarb.com / govarb.io / govarbscanner.com)
- [ ] Wire Stripe checkout to pricing tiers
- [ ] Build simple user dashboard (login → see your filtered opportunities)
- [ ] Add email signup to Mailchimp/ConvertKit for nurture sequence

### 2.3 Proposal Template Generator
- [ ] Auto-generate bid response skeleton from contract data
- [ ] Include: cover letter, technical approach, pricing template, past performance section
- [ ] CMMC 2.0 compliance checklist
- [ ] Export as Word doc (.docx)

### 2.4 Validate with Real Humans
- [ ] Find 5-10 existing government contractors (LinkedIn, SAM.gov search)
- [ ] Offer free 30-day trial in exchange for feedback
- [ ] Ask: "Would you pay $499/mo for this? What's missing?"
- [ ] **Kill criterion:** If 0/10 say yes → pivot or kill
- [ ] **Go criterion:** If 3+/10 say yes → double down

---

## Phase 3: Scale & Monetize (Weeks 2-4)
*Goal: First paying customers*

### 3.1 Cold Outreach
- [ ] Scrape SAM.gov for vendors in our target PSC codes
- [ ] Build email list of procurement managers / business development leads
- [ ] Write 3-email sequence: problem → solution → demo offer
- [ ] Send via Instantly.ai (already configured)
- [ ] Target: 100 emails/day, 3% reply rate = 3 conversations/day

### 3.2 Content Marketing
- [ ] Write "How Government Contractors Are Leaving Money on the Table" blog post
- [ ] Create LinkedIn content showing real (anonymized) markup examples
- [ ] Post in r/govcon, r/smallbusiness, government contracting forums
- [ ] Create YouTube video: "I Built an AI That Finds Overpriced Government Contracts"

### 3.3 Product Improvements
- [ ] Real-time alerting (new high-score opportunity → email/SMS within 1 hour)
- [ ] SAM.gov vendor enrichment (show which vendors are in each NAICS code)
- [ ] Competition dashboard (who else is bidding on similar contracts?)
- [ ] Price trend charts (is this item getting more or less overpriced over time?)

---

## Phase 4: Compound & Expand (Month 2-3)
*Goal: $10K+ MRR*

### 4.1 Expand Data Sources
- [ ] Add state/local procurement (not just federal)
- [ ] Add NATO/allied country procurement databases
- [ ] Add GSA Schedule pricing for comparison
- [ ] Add historical win rates by vendor/NAICS

### 4.2 Advanced Features
- [ ] AI-powered "opportunity matching" — learn user preferences from clicks/saves
- [ ] Automated bid submission (for micro-purchases <$10K)
- [ ] Teaming partner finder (match small businesses with large primes)
- [ ] Subcontracting opportunity tracker

### 4.3 Revenue Optimization
- [ ] Usage-based pricing (per-opportunity or per-scan)
- [ ] White-label for government consulting firms
- [ ] Affiliate program for SAM.gov registration services
- [ ] Annual contract discounts for enterprise

---

## Key Metrics to Track

| Metric | Phase 1 Target | Phase 2 Target | Phase 3 Target |
|--------|---------------|---------------|---------------|
| Price match rate | >60% | >80% | >90% |
| Opportunities per scan | >50 | >200 | >500 |
| Manual accuracy check | >70% real | >85% real | >95% real |
| Email signups | — | 50 | 500 |
| Paying customers | — | 1-5 | 20-50 |
| MRR | $0 | $500-2,500 | $10,000+ |

---

## Current Status (March 15, 2026)

**✅ Done:**
- USAspending API integration — confirmed working with live data
- Scanner CLI with dry-run mode (12 sample contracts)
- First live scan: found BAE Systems $218M microcircuit contract
- Landing page deployed to govarb-site.vercel.app
- Scoring algorithm (markup × competition × COTS designation)

**🔧 Needs Work:**
- Price matching only covers ~10% of contracts (lookup table too small)
- No real-time DigiKey/Mouser API integration yet
- No user accounts or payment processing
- No automated report delivery
- No domain purchased

**🚀 First Priority:** Phase 1.1 — Fix price matching. Everything downstream depends on this.

---

*Updated: March 15, 2026 | Sol Finn ☀️*
