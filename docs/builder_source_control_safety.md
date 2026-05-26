# Builder Source-Control Safety

This note captures the source-control state that must be fixed before broad
Builder implementation continues.

## Current State

| Path | State | Risk |
|---|---|---|
| `/home/charles2/sailly-browser-demo` | Git repo on `master`, no remote configured | Backend work can be committed locally but is not backed up off-host. |
| `/home/charles2/sailly/apps/dashboard` | Live dashboard source, not inside a git repo | Builder UI work can be lost or overwritten by deploy/build operations. |
| `/home/charles2/sailly-mvp-complete` | Git repo with CodeCommit remote | Stale relative to live dashboard; not safe as automatic push target. |

## Immediate Backup

The current dashboard Builder source has been archived to:

`/home/charles2_hotmail_de/backups/`

The archive contains:

- `/home/charles2/sailly/apps/dashboard/app/builder`
- `/home/charles2/sailly/apps/dashboard/next.config.mjs`
- `/home/charles2/sailly/apps/dashboard/package.json`

## Required Before Production Builder Work

1. Choose the source of truth for the dashboard:
   - restore/connect `/home/charles2/sailly` to its intended git remote, or
   - create a clean repository/branch for the current live dashboard tree.
2. Add a remote for `/home/charles2/sailly-browser-demo` or document why it remains local-only.
3. Exclude runtime/generated artifacts before committing:
   - `.env*`
   - `.next/`
   - `node_modules/`
   - `.state/`
   - `.cursor/`
   - `logs/`
   - `reports/`
   - `call_reports/`
4. Do not push `/home/charles2/sailly-mvp-complete` as-is; it is stale and has large unrelated drift.

## Builder Lab Rule

Until dashboard source control is fixed, Builder Lab work may add backend
scaffolding and docs, but production-facing dashboard changes should be backed
up before each build/deploy and treated as at-risk.
