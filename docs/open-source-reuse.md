# Open-Source Reuse Assessment

## Objective

Reuse mature community-calendar and event-ingestion methods instead of rebuilding solved problems. Evaluate both code and architecture. Borrowing an idea is not the same as copying source code; every copied component requires license and dependency review.

## Primary references

### 1. judell/community-calendar
Repository: https://github.com/judell/community-calendar

**Why it matters:** Closest overall reference for community event aggregation. Its documented pipeline includes ICS feeds, reusable scrapers, source registration, source attribution, normalization, deduplication, event classification, and database loading.

**Study and adapt:**
- Feed registry and source onboarding workflow.
- DB-driven source inventory rather than hard-coded workflow steps.
- Reusable scraper/adaptor patterns.
- Attribution propagation from source through event output.
- Pipeline staging and operational build reports.
- Duplicate handling and event ordering lessons.

**Do not copy blindly:**
- Its exact hosting/database/workflow choices.
- Any destructive deduplication behavior without CivicCal review safeguards.
- LLM classification as a required dependency.
- Its geographic or product-specific assumptions.

**License:** Repository identifies Apache License 2.0; verify the current LICENSE file and dependency licenses before code reuse.

### 2. tophe112-source/mapsee-aggregator
Repository: https://github.com/tophe112-source/mapsee-aggregator

**Why it matters:** Strong ingestion-adapter reference with multiple public event source types and a broad catalog of site/API patterns.

**Study and adapt:**
- ICS conditional fetching with ETag and Last-Modified.
- JSON-LD Event extraction.
- Localist and other reusable calendar API adapters.
- Socrata, CKAN, and OpenDataSoft open-data adapters.
- Source configuration/catalog patterns.
- Source health and catalog validation workflows.
- Geographic and category enrichment where supported by source facts.

**Do not copy blindly:**
- Broad global event discovery when CivicCal's initial scope is local.
- Keyed commercial API integrations as core dependencies.
- Source-specific assumptions that don't match local publishers.
- Any behavior that invents missing details or discards source provenance.

**License:** Repository identifies MIT; verify current LICENSE and dependency licenses before code reuse.

### 3. not-the-singer/keeper
Repository: https://github.com/not-the-singer/keeper

**Why it matters:** Reference for ICS aggregation and downstream calendar synchronization, including stable source/destination mapping concepts.

**Study and adapt:**
- Calendar aggregation and sync boundaries.
- Stable identity/mapping concepts.
- Self-hosting and operational separation.
- Read-only integration patterns.

**Do not copy blindly:**
- Deleting destination events merely because they disappear from a source.
- Its timeslot-focused model, which does not preserve CivicCal's full event details.
- Redis/other infrastructure unless a measured need exists.

**License:** AGPL-3.0 per repository README. Code incorporation or modification may create source-disclosure and distribution obligations. Prefer design study unless AGPL compatibility is explicitly accepted after review.

### 4. survos/ccal
Repository: https://github.com/survos/ccal

**Why it matters:** Reference for organization, calendar, feed, user subscription, and moderation relationships.

**Study and adapt:**
- Organization-to-calendar/feed data model.
- Feed moderation workflow.
- Individual calendar subscription model.
- Existing iCalendar parsing and generation library choices.

**Do not copy blindly:**
- Full Symfony/PHP application stack.
- Account-oriented product assumptions if CivicCal's public feeds can remain open.
- Its specific booking abstraction where source observations are needed.

**License:** Repository identifies MIT; verify current LICENSE and dependency licenses before code reuse.

### 5. mhagander/icalaggregator
Repository: https://github.com/mhagander/icalaggregator

**Why it matters:** Small Python example for merging iCalendar feeds.

**Study and adapt:** Minimal aggregation concepts and test cases.

**Limitations:** Too small to serve as CivicCal's overall architecture.

## Reuse decision

CivicCal remains a modular Python application with a portable SQLite-first core. Do not fork a complete reference application as the foundation.

Priority:
1. Use judell/community-calendar as the overall pipeline and source-management reference.
2. Use mapsee-aggregator as the adapter and conditional-fetching reference.
3. Use Keeper for downstream ICS aggregation/synchronization lessons only.
4. Use ccal for organization/feed/subscription modeling.
5. Use icalaggregator for small implementation examples.

## Required code-reuse checklist

Before copying any code:
- Inspect the current repository and exact file being considered.
- Verify project license and copyright notices.
- Review dependency licenses and maintenance status.
- Check tests and edge cases against CivicCal requirements.
- Identify infrastructure and runtime dependencies.
- Compare data models and destructive behavior.
- Record copied/adapted files and upstream attribution.
- Add CivicCal-specific tests before integrating.
- Prefer a small adapter or isolated library over importing an entire application.

## Important boundary

This is an engineering reference assessment, not a claim that any of these projects' code has been copied, installed, executed, or fully audited. The next reuse task is a targeted code-level comparison of source registry, fetcher, ICS parser/generator, deduplication, and API/feed modules.
