# Phase 1 Data Model: Cultural Event Calendar Agent

Derived from the spec's Key Entities section and functional requirements. All models are Python `pydantic` models (`src/models/`); fields marked *unknown-able* must accept an explicit `"unknown"` sentinel rather than being omitted or null, per FR-008.

## UserPreferenceSet

Inputs for a single calendar-generation request (FR-001).

| Field | Type | Required | Notes |
|---|---|---|---|
| `location` | `str` | yes | Free-text area/location (city, neighborhood, postal code) |
| `max_cost` | `Decimal \| None` | no | `None`/absent = no cost ceiling; `0` = free only |
| `event_types` | `list[str]` | no | Empty/absent = all types (US1 Acceptance Scenario 2) |
| `genres` | `list[str]` | no | Applies only when `"music"` is in `event_types`; ignored otherwise |
| `calendar_length_days` | `int` | yes | Span from today; must be > 0 |
| `start_time_window` | `tuple[time, time] \| None` | no | `None` = no start-time restriction |

**Validation rules**:
- `calendar_length_days` must be a positive integer.
- `genres` set while `event_types` excludes `"music"` is accepted but has no effect (documented, not an error) — matches US3 scenario 2 semantics.
- `max_cost` must be `>= 0` when present.

## TrustedSource

An entry in the user-maintained trusted local source list (FR-002a).

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | `str` | yes | Human-readable label (e.g. "The Blue Note") |
| `url` | `HttpUrl` | yes | Venue/org/arts-council event page |
| `added_at` | `date` | yes (system-set) | Set on `sources add` |

**Storage**: list of these, serialized to `trusted_sources.yaml`. Uniqueness key: `url`.

**State transitions**: none (create/list/delete only — no in-place mutation required by FR-002a).

## CulturalEvent

A discovered event candidate, pre- and post-filtering (Key Entities).

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | `str` | yes | |
| `date` | `date` | yes | One occurrence; multi-day/recurring events expand to one `CulturalEvent` per distinct date/showtime within the window (Edge Cases) |
| `start_time` | `time \| Literal["unknown"]` | yes | *unknown-able* |
| `venue` | `str` | yes | |
| `cost` | `Decimal \| Literal["unknown"] \| Literal["free"]` | yes | *unknown-able*; `"free"` distinct from `0` cost cases already covered by `Decimal(0)` — kept as literal for display clarity |
| `event_type` | `str` | yes | e.g. "music", "theater", "festival", "comedy", "art" |
| `genre` | `str \| Literal["unknown"] \| None` | no | Only meaningful when `event_type == "music"`; `None` for non-music types |
| `source_ref` | `SourceRef` | yes | Where this candidate came from |

### SourceRef

| Field | Type | Notes |
|---|---|---|
| `kind` | `Literal["trusted_source", "web_search"]` | |
| `identifier` | `str` | `TrustedSource.url` or search result URL |

**Deduplication key** (FR-007): `(normalize(name), date, normalize(venue))` — two `CulturalEvent` records that collide on this key from different `source_ref`s are merged into one entry; when fields disagree between duplicates, prefer the trusted-source value over the web-search value, and prefer a known value over `"unknown"`.

**Filtering rules** (FR-003, applied to produce the output set from all discovered candidates):
1. `date` within `[today, today + calendar_length_days]`
2. `event_type` in `preferences.event_types` (skip filter if `event_types` empty)
3. if `event_type == "music"` and `preferences.genres` non-empty: `genre` in `preferences.genres`
4. `cost` satisfies `preferences.max_cost` — events with `cost == "unknown"` are **included** and flagged, not silently dropped (US2 Acceptance Scenario 2)
5. `start_time` within `preferences.start_time_window`, if set — events with `start_time == "unknown"` are excluded from a start-time-windowed request (cannot verify the constraint is satisfied)

## MarkdownCalendar

The generated output document (Key Entities).

| Field | Type | Notes |
|---|---|---|
| `preferences` | `UserPreferenceSet` | echoed for traceability at the top of the document |
| `generated_at` | `datetime` | |
| `events` | `list[CulturalEvent]` | post-filter, post-dedup, sorted by `(date, start_time)` |
| `is_empty` | `bool` | derived: `len(events) == 0` |
| `most_restrictive_filter` | `str \| None` | best-effort note when `is_empty`, per Edge Cases guidance |

**Rendering rule**: one H2 section per date, one bullet per event with name, start time, venue, cost, type (+genre if music). If `is_empty`, the document body is a single clear statement instead of empty sections (FR-009), optionally naming `most_restrictive_filter`.
