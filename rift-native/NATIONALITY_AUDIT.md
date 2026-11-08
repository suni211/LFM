# LFM nationality verification gate

Original people catalog: `rift-native/assets/people.json` (1,088 entries as of 2026-11-08).
- Entries with ISO nationality code: **5 / 1,088**.
- Entries still lacking ISO code: **1,083**.
- Records marked as real people: **1,072**; real people lacking ISO code: **1,067**.
- 16 LCK CL/LDL source placeholders are marked `real_person=false`; do not assign them a nationality by inferring a competitive region.
- No 1,000-person verified-country mapping exists on this branch. Do not claim that bulk identity checks have been completed.
- The league operator dashboard includes `/operator/nationality-audit` to report the true number after each import.

LCK CL and LDL are standalone **competitions**, not club names `LCK 2군` or `LDL 2군`. Those 16 source placeholder team values have been corrected to `소속 미확인`. The LCK CL game directory has ten development club identities and links existing parent academy players as a **read-only club profile** without duplicating their IDs; the LDL game directory has development-organisation clubs but lacks verified 2026 individual rosters. These must not be presented as official 2026 LDL season participants or as fully verified playable squads.

Run from the repo root:

```sh
python3 rift-native/tools/audit_nationalities.py
python3 rift-native/tools/audit_nationalities.py --mapping verified-nationalities.csv
python3 rift-native/tools/audit_nationalities.py --mapping verified-nationalities.csv --apply
```

The audit generates `rift-native/nationality-audit.json` and `rift-native/nationality-review.csv`. Review queue contains missing **nationality codes**, not necessarily missing Korean display text.

CSV header: `id,nickname,real_name,code,source`. Example: provide the exact ID and unchanged names from the catalog, the ISO 3166-1 alpha-2 code, and an HTTPS source confirming that specific person's identity and nationality. Do not automatically use league/region/team or Korean-looking names. Common nicknames can collide. If a record cannot be independently verified, leave it in the review queue.

The tool rejects mismatched identities, duplicate IDs, missing source links, unsupported country codes and conflicts with existing codes. **A source URL's content is not fetched or checked by this script; a human/source verification step is still required before importing CSV rows.** This script cannot truthfully establish that all 1,088 have been verified by itself.

The web player profile should show nationality only when a specific person has a country code or existing nationality label. A game's region is a competitive region, not citizenship.

Deployment target: `LOL.lcktcg.com`. Do not reuse the existing `berrple.com/rift` Caddy deploy script. Use a dedicated site block, TLS and reverse proxy, and keep the backend bound to localhost. Publish only after nationality review and application/API tests.
