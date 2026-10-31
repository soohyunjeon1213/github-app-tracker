# GitHub App Finder

A static GitHub Pages discovery dashboard backed by GitHub Actions. No paid hosting, browser token, dependencies, or Mac app required.

## Install and deploy

1. Create a **public** GitHub repository named `github-app-tracker` on your GitHub account. (Public dashboard data is visible to everyone; do not put private review data in this repository.)
2. Upload the entire contents of this folder to its `main` branch, including `.github/workflows/` (GitHub web upload hides dotfiles on some machines; check they are committed).
3. In **Settings → Actions → General → Workflow permissions**, enable **Read and write permissions** for `GITHUB_TOKEN`. GitHub organization rules may disallow this; adjust accordingly.
4. In **Settings → Pages**, select **GitHub Actions** as the build/deployment source.
5. Under **Actions → Discover GitHub repositories**, choose **Run workflow** to initialize real discovery data. The workflow commits `data/repos.json` and `docs/data.json` back to `main`.
6. Under **Actions → Publish dashboard**, run the workflow or wait for the push. The dashboard will be at `https://YOUR_GITHUB_USERNAME.github.io/github-app-tracker/`.

If the scanner workflow is missing, check GitHub Actions is enabled and the workflow YAML file exists on the `main` branch.

## Schedules and what is detected

The GitHub Action uses six UTC cron slots with a New York local-time check to run at **09:00, 14:00, and 20:00 Eastern**, including daylight saving time. GitHub schedule triggers may run late or be skipped during heavy load, and the local-time guard can therefore skip delayed jobs. Use Actions → Run workflow for manual scanning. GitHub Pages **cannot directly dispatch a workflow** without an authenticated backend; the dashboard Scan Now button opens the GitHub Actions workflow page.

Each scan searches per topic sorted by **recently updated**, using the configured page limit (default: 3 × 100 repositories/topic). This is a *bounded sample*, not a guaranteed exhaustive topic inventory. `macos` and `swiftui` often exceed the sample, so the dashboard reports incomplete coverage. GitHub's search API caps accessible results at 1,000 per query; indexing can be delayed. A repo's `first_seen` means **first found by this tracker**, not the time its topic was added. The first scan establishes a baseline: all repos appear in New, but no outbound notifications are sent.

## Topic editing

Edit `config.json` on GitHub (`https://github.com/YOUR_GITHUB_USERNAME/github-app-tracker/edit/main/config.json`). Add, remove, rename, or set `enabled:false` for topic entries. GitHub Actions reads this file **every scan**, so edits take effect on the next scan. Dashboard-only edits cannot securely commit changes to GitHub without an authenticated backend. Default page limit is adjustable in `scan.pages_per_topic` (1–10). Increasing pages increases API consumption.

## Review history and cross-device use

Review actions stay in browser `localStorage` (same site and browser profile) across reloads. Safari on iPhone and on Mac do **not** sync these actions. Use Settings → Export/Import JSON to transfer backups between devices. Clearing browser data may delete history; back it up regularly. The discovery database remains in Git history and persists between scans.

## Filtering

The "Likely Mac apps" checkbox uses an intentionally simple keyword heuristic. It may hide genuine apps; turn it off to view every discovered repo. Unknown licenses, Apple Silicon compatibility, installed size, and Mac compatibility are **unverified**, never guessed. The releases link points to the repo releases page, not a verified latest release.

## Notifications

Optional daily summary and push/email notifications are **not implemented** in this baseline (the dashboard provides counts). Implementing reliable external notifications needs a destination and deduplicated send history. This tracker does not claim otherwise.

## Local tests

Run `python3 -m unittest discover -s tests -v`. To run the dashboard locally from project root: `python3 -m http.server 8000 -d docs` and open `http://localhost:8000`. The initial `docs/data.json` is intentionally empty until the first live scan.
