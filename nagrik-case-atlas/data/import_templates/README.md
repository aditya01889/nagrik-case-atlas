# Normalized data import templates

These CSVs contain headers only by design. Do not add unverified claims or invented example politicians. `verification_status` should be `discovered`, `needs_review`, `verified`, or `rejected`. Only `verified` records appear in public candidate results.

Recommended import sequence: constituencies, parties, people, source_documents, candidacies, cases, case_events. The importer reads all files in one transaction; foreign-key IDs must match across files.

- `constituencies.csv`: `id,name,state_name,legislature,boundary_version_id,geometry_source_url,is_active`
- `parties.csv`: `id,name,abbreviation`
- `people.csv`: `id,full_name,identity_notes`
- `source_documents.csv`: `id,title,source_type,source_url,published_date,content_sha256,verification_status,reviewer,review_notes`
- `candidacies.csv`: `id,person_id,constituency_id,party_id,election_date,status,source_document_id,valid_from,valid_to,verification_status,verification_notes`
- `cases.csv`: `id,case_title,case_number,court_name,offence_summary,statutory_provisions,is_serious,seriousness_rank,seriousness_basis,source_document_id,source_url,declared_in_affidavit,filed_date,verification_status,person_id,role,identity_verification`

`seriousness_rank` is optional, reviewed, and uses `1` for the highest severity under a published classification framework. If no rank is set, the app does not invent a “most serious” case.
- `case_events.csv`: `id,case_id,event_type,event_date,status_after_event,summary,source_document_id,verification_status,verified_by,verified_at`

For `legislature`, use `lok_sabha`, `assembly`, or `rajya_sabha`. For source records, retain exact source URLs and dates. Never infer current status from an old affidavit alone.
