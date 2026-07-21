# AlienTAI single-task ownership guard

This repository is under active development in Jeff Pearson's established primary AlienTAI Codex task.

## Mandatory roadmap read for every task

After reading this file and before proposing, planning, or performing any AlienTAI work, read `ALIENTAI_MASTER_PLAN.md` in full. It is the authoritative dynamic roadmap for work order, current direction, dependencies, blockers, and phase status.

Also read `CODEX_CONTINUATION_INSTRUCTIONS.md` for operational handoff details. If the roadmap and continuation file disagree, remain read-only, inspect current evidence, and ask Jeff to reconcile the direction before proceeding.

For every authorized task that changes scope, priority, direction, dependencies, or phase status:

1. update `ALIENTAI_MASTER_PLAN.md` in the same task;
2. preserve reordered, deferred, or cancelled work in its direction-change log;
3. record evidence before marking any phase complete;
4. update its immediate next actions before ending the work session.

Do not rely on chat memory as the source of truth for the AlienTAI roadmap.

## Default state for every new AI task or chat

Treat this repository as **read-only**. You may inspect files, Git history, logs, and running processes, but you must not change project state.

Before doing any of the following, stop and ask Jeff to type the exact sentence `AUTHORIZE ALIENTAI WRITE ACCESS` in the current task:

- edit, create, delete, rename, or copy files;
- apply or reconstruct patches;
- restore code from Downloads, prior Codex work folders, old chats, archives, or previous versions;
- run trainers, collectors, servers, scheduled jobs, or other processes that write data;
- change `.env`, settings, databases, Supabase, OneDrive, Git, GitHub, or deployment state;
- commit, push, merge, rebase, reset, revert, or switch branches.

Generic replies such as "yes," "ok," "next," "continue," or broad computer permission do not unlock the repository. Authorization given in another task does not transfer to a new task.

## Authorized primary task

The long-running Codex task in which Jeff requested this ownership guard on 2026-07-20 is the authorized primary task and may continue normal AlienTAI work. The authorization applies only while that same task is being continued.

## Mandatory safety rules

1. The canonical project is `C:\Users\jeffp\alientai_start_over_8010` on branch `main`.
2. Never replay past work or assume an old patch is missing. Inspect the current repository and recent Git history first.
3. Never overwrite current files with copies from `Downloads`, `Documents\Codex`, archives, or another checkout unless Jeff explicitly names the source and destination after unlocking the task.
4. Preserve user/runtime changes, especially `.env` files, `data_v2\v2_settings.json`, model artifacts, archives, and training results.
5. Only one task may modify the repository or control training/collection jobs at a time.
6. Before an authorized write, report `git status`, the latest commits, relevant running processes, and the exact files or services that will change.
7. Do not disclose secrets or commit `.env` files, API keys, tokens, credentials, or private datasets.
8. Do not claim that an experiment, training run, download, backup, commit, or push succeeded without verifying it.

If there is any doubt about whether this is the established primary task, remain read-only and direct Jeff back to the pinned task named `PRIMARY - AlienTAI Development (Use This Task)`.
