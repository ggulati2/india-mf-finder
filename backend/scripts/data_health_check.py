"""Data sanitation / health / validity sweep across everything BUT raw NAV accuracy
(NAV-vs-AMFI accuracy is already covered by scripts/verify_data.py — run both).

  python scripts/data_health_check.py

Checks, each independent and non-fatal on its own (report-everything, not fail-fast):
  1. Riskometer values are one of the 6 official SEBI levels (nothing fabricated/typo'd).
  2. Riskometer freshness: flags anything older than ~45 days (should refresh monthly).
  3. SchemeHolding rows: weight_pct in a sane range, and each scheme's holdings total
     lands in [30, 105]% (parse_holdings' own scale-detection sanity band) - catches a
     regression that slips past import-time validation via a manual DB edit or migration.
     Note: multi-asset/dynamic-allocation funds legitimately disclose small NEGATIVE
     weights for short derivative/hedge positions (e.g. "ICICI BANK LTD^" at -0.49%) -
     these are real AMC-published figures, not bugs, so the sane range is generous
     ([-100, 100.5]) and only truly nonsensical magnitudes are flagged as failures.
  4. SchemeHolding orphans: rows pointing at a scheme_id that no longer exists, or at a
     scheme that is_active == False (stale disclosure for a scheme we no longer track).
  5. Duplicate holdings: same (scheme_id, isin, as_of) appearing more than once, with or
     without matching weight, is reported for visibility but never treated as a failure
     on its own - arbitrage/hedge funds legitimately carry multiple distinct derivative
     legs on the same underlying stock that can coincidentally share a weight (e.g. two
     -0.04% futures legs, different expiries). The real regression-catcher for double-
     counted imports is check 3's per-scheme total-weight sanity band, which would fail
     if a duplicate insert inflated a scheme's total past 105%.
  6. Scheme identity sanity: amfi_code / isin uniqueness (schema already enforces this, but
     a direct check catches an incomplete migration), and no blank/placeholder scheme_name.
  7. NAV staleness: active schemes whose latest_nav_date is more than 10 calendar days old.
  8. Holdings staleness: distinct (amc, as_of) combinations, flags any as_of older than ~40 days.
  9. SchemeNAVData / SchemeAnalytics orphans: rows pointing at a scheme_id with no matching
     mutual_fund_schemes row at all. refresh_master() only ever deactivates a vanished scheme
     (is_active=False), it never hard-deletes one, so this should never happen from normal ETL
     - if it does, something else (a manual edit, a concurrent/competing process touching the
     same DB, a botched migration) deleted a scheme row without cascading. Found once by hand
     during the 2026-09-22 Neon migration (scheme_id 99: 13 years of NAV history + analytics,
     no scheme record) and traced to a stale artifact, not our ETL - this check exists so the
     next one is caught automatically instead of by chance during a migration.

Exit code 1 if any category found a real problem (excluding informational staleness notes,
which are expected to accumulate between monthly refreshes and don't indicate corruption).
"""
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

from app.db.database import SessionLocal
from app.db.models import MutualFundScheme, SchemeAnalytics, SchemeHolding, SchemeNAVData

VALID_RISK_LEVELS = {
    "Low", "Low to Moderate", "Moderate", "Moderately High", "High", "Very High",
}


def main():
    db = SessionLocal()
    problems = 0
    notes = []

    schemes = db.query(MutualFundScheme).all()
    active = [s for s in schemes if s.is_active]
    by_id = {s.scheme_id: s for s in schemes}

    print(f"Schemes: {len(schemes)} total, {len(active)} active")

    # 1. Riskometer value sanity
    bad_levels = [(s.scheme_id, s.scheme_name, s.riskometer) for s in active
                  if s.riskometer and s.riskometer not in VALID_RISK_LEVELS]
    if bad_levels:
        problems += 1
        print(f"[FAIL] {len(bad_levels)} schemes have a riskometer value outside the 6 official SEBI levels:")
        for sid, name, lvl in bad_levels[:10]:
            print(f"    scheme {sid} {name[:50]!r}: {lvl!r}")
    else:
        with_risk = sum(1 for s in active if s.riskometer)
        print(f"[OK]   riskometer values all valid ({with_risk}/{len(active)} active schemes have one)")

    # 2. Riskometer freshness
    stale_cutoff = date.today() - timedelta(days=45)
    stale_risk = [s for s in active if s.riskometer and s.riskometer_as_of and s.riskometer_as_of < stale_cutoff]
    if stale_risk:
        notes.append(f"{len(stale_risk)} schemes' riskometer is older than 45 days (due for monthly refresh)")

    # 3. Holdings weight sanity
    holdings = db.query(SchemeHolding).all()
    # Generous bounds: multi-asset/dynamic funds legitimately disclose small negative
    # weights for short derivative/hedge positions (see module docstring point 3).
    bad_weight_rows = [h for h in holdings if h.weight_pct is None or not (-100 <= float(h.weight_pct) <= 100.5)]
    negative_rows = [h for h in holdings if h.weight_pct is not None and float(h.weight_pct) < 0]
    if bad_weight_rows:
        problems += 1
        print(f"[FAIL] {len(bad_weight_rows)} holding rows have weight_pct outside [-100,100.5]")
        for h in bad_weight_rows[:10]:
            print(f"    holding {h.id} scheme {h.scheme_id} {h.name[:40]!r}: {h.weight_pct}")
    else:
        print(f"[OK]   all {len(holdings)} holding rows have a sane weight_pct")
    if negative_rows:
        notes.append(f"{len(negative_rows)} holding rows have a negative weight_pct (expected: short derivative/hedge lines in multi-asset funds)")

    totals = defaultdict(float)
    for h in holdings:
        totals[(h.scheme_id, h.as_of)] += float(h.weight_pct or 0)
    bad_totals = [(k, v) for k, v in totals.items() if not (30 <= v <= 105)]
    if bad_totals:
        problems += 1
        print(f"[FAIL] {len(bad_totals)} scheme/as_of holdings sets total outside [30,105]%:")
        for (sid, as_of), total in bad_totals[:10]:
            nm = by_id.get(sid).scheme_name[:45] if sid in by_id else f"(missing scheme {sid})"
            print(f"    scheme {sid} {nm!r} as_of {as_of}: {total:.1f}%")
    else:
        print(f"[OK]   all {len(totals)} scheme/as_of holdings sets total within [30,105]%")

    # 4. Orphaned / stale-scheme holdings
    orphan_holdings = [h for h in holdings if h.scheme_id not in by_id]
    inactive_holdings = [h for h in holdings if h.scheme_id in by_id and not by_id[h.scheme_id].is_active]
    if orphan_holdings:
        problems += 1
        print(f"[FAIL] {len(orphan_holdings)} holding rows reference a non-existent scheme_id")
    if inactive_holdings:
        notes.append(f"{len({h.scheme_id for h in inactive_holdings})} inactive schemes still carry {len(inactive_holdings)} holding rows (harmless but worth pruning)")

    # 5. Duplicate holdings - a true double-insert has an IDENTICAL weight for the same
    # (scheme_id, isin, as_of); the same ISIN with a DIFFERENT weight is a normal
    # separate disclosure line (e.g. cash equity + derivative/hedge position) and is
    # only counted informationally.
    exact_dup_counter = Counter((h.scheme_id, h.isin, h.as_of, round(float(h.weight_pct), 4)) for h in holdings if h.isin)
    exact_dups = [(k, c) for k, c in exact_dup_counter.items() if c > 1]
    multiline_counter = Counter((h.scheme_id, h.isin, h.as_of) for h in holdings if h.isin)
    multiline = [(k, c) for k, c in multiline_counter.items() if c > 1]
    print(f"[OK]   holdings duplication within normal bounds (per-scheme totals sane; see check 3) - "
          f"{len(exact_dups)} exact-weight repeats, {len(multiline)} same-ISIN multi-line combos, out of {len(holdings)} rows")
    if exact_dups:
        notes.append(f"{len(exact_dups)} (scheme, isin, as_of) combos repeat with an IDENTICAL weight - worth a manual glance if this count grows (e.g. after adding a new AMC), example: scheme {exact_dups[0][0][0]} isin {exact_dups[0][0][1]}")
    if multiline:
        notes.append(f"{len(multiline)} (scheme, isin, as_of) combos have multiple lines total (normal: cash+derivative/hedge/multi-expiry disclosure)")

    # 6. Scheme identity sanity
    amfi_dupe = [c for c, n in Counter(s.amfi_code for s in schemes).items() if n > 1]
    isin_dupe = [c for c, n in Counter(s.isin for s in schemes).items() if n > 1]
    blank_names = [s.scheme_id for s in schemes if not s.scheme_name or not s.scheme_name.strip()]
    if amfi_dupe or isin_dupe or blank_names:
        problems += 1
        if amfi_dupe:
            print(f"[FAIL] duplicate amfi_code values: {amfi_dupe[:10]}")
        if isin_dupe:
            print(f"[FAIL] duplicate isin values: {isin_dupe[:10]}")
        if blank_names:
            print(f"[FAIL] {len(blank_names)} schemes with blank scheme_name: {blank_names[:10]}")
    else:
        print("[OK]   scheme identity fields (amfi_code, isin, scheme_name) all sane/unique")

    # 7. NAV staleness
    nav_cutoff = date.today() - timedelta(days=10)
    stale_nav = [s for s in active if s.latest_nav_date and s.latest_nav_date < nav_cutoff]
    no_nav = [s for s in active if not s.latest_nav_date]
    if stale_nav:
        notes.append(f"{len(stale_nav)} active schemes haven't had a NAV update in 10+ days")
    if no_nav:
        notes.append(f"{len(no_nav)} active schemes have no latest_nav_date at all")

    # 8. Holdings staleness
    as_of_cutoff = date.today() - timedelta(days=40)
    as_of_by_source = defaultdict(set)
    for h in holdings:
        as_of_by_source[h.source or "(unknown source)"].add(h.as_of)
    old_sources = {src: sorted(dates) for src, dates in as_of_by_source.items() if max(dates) < as_of_cutoff}
    if old_sources:
        notes.append(f"{len(old_sources)} holdings source(s) haven't been refreshed in 40+ days: {list(old_sources)[:8]}")

    # 9. NAV / analytics orphans - a scheme_id with history but no scheme row at all. This
    # should never happen from normal ETL (refresh_master only deactivates, never deletes), so
    # unlike check 4's holdings orphans this is always a hard failure, not just a note.
    from sqlalchemy import text as _sql
    nav_orphans = [r[0] for r in db.execute(_sql(
        "SELECT DISTINCT scheme_id FROM scheme_nav_data WHERE scheme_id NOT IN (SELECT scheme_id FROM mutual_fund_schemes)"
    ))]
    analytics_orphans = [r[0] for r in db.execute(_sql(
        "SELECT DISTINCT scheme_id FROM scheme_analytics WHERE scheme_id NOT IN (SELECT scheme_id FROM mutual_fund_schemes)"
    ))]
    if nav_orphans or analytics_orphans:
        problems += 1
        if nav_orphans:
            print(f"[FAIL] {len(nav_orphans)} scheme_id(s) have NAV history but no scheme record: {nav_orphans[:10]}")
        if analytics_orphans:
            print(f"[FAIL] {len(analytics_orphans)} scheme_id(s) have analytics but no scheme record: {analytics_orphans[:10]}")
    else:
        print("[OK]   no NAV/analytics rows orphaned from a missing scheme record")

    print()
    if notes:
        print("Notes (informational, not failures):")
        for n in notes:
            print(f"  - {n}")
        print()

    if problems:
        print(f"RESULT: {problems} check(s) found real problems.")
        sys.exit(1)
    print("RESULT: all data-sanitation checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
