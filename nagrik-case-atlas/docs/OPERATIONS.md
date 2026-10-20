# Operations checklist

## Before first local run
- [ ] Install Docker Desktop / Docker Engine and Compose.
- [ ] Copy `.env.example` to `.env`.
- [ ] Replace both example secrets.
- [ ] Keep the service local until source coverage and review policy are ready.

## Before publishing any case record
- [ ] Original affidavit or court order stored/linked.
- [ ] Person identity match verified.
- [ ] Case identifier checked; related proceedings deduplicated/linked.
- [ ] Allegation and legal status represented separately.
- [ ] Event date and recorded date set.
- [ ] Source document verification status is `verified`.
- [ ] Seriousness flag/rank reviewed and rationale recorded if shown.
- [ ] Corrections route and review history available.

## Before public deployment
- [ ] Current Lok Sabha and all Assembly boundary versions validated against official sources.
- [ ] Rajya Sabha representation handled separately from geographic constituencies.
- [ ] National candidate roster reconciled to official membership/nominations.
- [ ] Historical snapshots tested across elections, by-elections and delimitation.
- [ ] Security review of admin APIs, source URL allowlist and backups completed.
- [ ] Source freshness and coverage metrics visible on the public site.
- [ ] Public terms, privacy notice and corrections policy published.
