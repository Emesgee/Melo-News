# Melo-News — User Guide

Welcome to **Melo-News**, a real-time, map-based platform for **citizen journalism**. This guide is for *people using the app* — no technical knowledge required. It explains what you see on screen, how to read whether a report can be trusted, and how to contribute your own reports safely.

> Looking to install or self-host the app instead? See the [Installation Guide](../INSTALLATION.md) and [Documentation Index](README.md).

---

## Table of Contents

1. [What is Melo-News?](#1-what-is-melo-news)
2. [Getting Started](#2-getting-started)
3. [A Tour of the Screen](#3-a-tour-of-the-screen)
4. [Exploring the Map](#4-exploring-the-map)
5. [The Events Feed](#5-the-events-feed)
6. [Understanding Trust: Events, Corroboration & Reporters](#6-understanding-trust-events-corroboration--reporters)
7. [Reading a Report](#7-reading-a-report)
8. [Searching & Filtering](#8-searching--filtering)
9. [Submitting a Report](#9-submitting-a-report)
10. [Your Account & Reporter Standing](#10-your-account--reporter-standing)
11. [For Moderators](#11-for-moderators)
12. [Privacy & Safety](#12-privacy--safety)
13. [Troubleshooting](#13-troubleshooting)
14. [Need More Help?](#14-need-more-help)

---

## 1. What is Melo-News?

Melo-News collects **first-hand reports from citizen reporters** and plots them on an interactive map, so you can see **what is happening and where**. Unlike a feed of headlines, Melo-News is built around one question: **can you trust this report enough to act on it?**

To answer that honestly, the app groups related reports into **Events** (incidents) and shows you the *basis* of trust — never a simple "verified ✓". You can see:

- How many **distinct reporters** independently described the same event (corroboration).
- Each reporter's **track record** and standing.
- Whether accounts of an event **conflict** (disputed).
- An automated **confidence estimate**, clearly labelled as secondary to human corroboration.

You can explore everything **without an account**. An account is only needed to submit reports under a persistent identity and to build a track record — though you can also submit **anonymously**.

---

## 2. Getting Started

### Opening the app

Open Melo-News in your web browser (desktop or mobile), or use the Android reporter app. The layout adapts to your screen. When it loads, you'll see the **map** (the Home page).

### Do I need an account?

| Action | Account needed? |
|---|---|
| View the map and the Events feed | ❌ No |
| Read reports and see trust details | ❌ No |
| Search & filter | ❌ No |
| **Submit a report anonymously** | ❌ No |
| **Submit under a persistent identity (build a track record)** | ✅ Yes |
| **View "My Stories"** | ✅ Yes |

Anonymous reports are welcome, but they are **marked as unverifiable** and don't count toward corroboration the way an identified reporter's report does — see [Understanding Trust](#6-understanding-trust-events-corroboration--reporters).

---

## 3. A Tour of the Screen

At the top of the app is a **fixed top bar**:

| Button | Icon | What it does |
|---|---|---|
| **Menu** | ☰ | Opens navigation (Home, Events, Upload, My Stories, Login/Logout). |
| **Search** | 🔍 | Shows or hides the search bar. See [Searching & Filtering](#8-searching--filtering). |
| **Events** | — | Opens the [Events feed](#5-the-events-feed) — the reader's view of corroborated incidents. |
| **Upload** | ⬆ | Start a report. Sends you to login first only if you want to submit under your account. |
| **My Stories** | 📄 | *(Logged in)* Your submitted reports. |
| **Moderation** | ✓ | *(Moderators only)* The review queue. |
| **Dark / Light mode** | ☀ / 🌙 | Switches theme (remembered between visits). |
| **Login / Logout** | ⤵ / ⤴ | Signs you in or out. |

---

## 4. Exploring the Map

Each **marker** is a report placed at the location it describes.

- **Drag** to pan, **scroll / pinch** to zoom.
- **Clusters:** nearby reports group into a numbered circle; click to zoom in and split them.
- **Click a marker** to open the report, including its **trust details** (see [Reading a Report](#7-reading-a-report)).

### Privacy zoom limit

For the safety of people on the ground, the map **limits how far you can zoom in** — you can see the town or neighborhood, not a precise street pinpoint. This is intentional; see [Privacy & Safety](#12-privacy--safety).

---

## 5. The Events Feed

Open **Events** from the top bar to see reports grouped into **incidents**, ordered so the most trustworthy lead:

- **Corroborated events first**, then developing ones.
- **Disputed events are shown prominently**, with a clear warning, so conflicting accounts are never buried.

Each card shows:

- A **status badge** — Corroborated / Developing / Disputed / Closed.
- **Corroboration**, shown concretely: *"✓ 3 corroborating"* means three **distinct** reporters independently described it. Anonymous supporting reports are shown **separately** (e.g. *"+1 anonymous"*) and don't count toward that number.
- A **confidence band** (Low / Medium / High) — an automated estimate, clearly secondary to the human corroboration above.
- Location, number of reports, and severity.

Click **Show reports** to expand the individual reports behind an event, each with its reporter's standing.

---

## 6. Understanding Trust: Events, Corroboration & Reporters

This is the heart of Melo-News. Trust is shown as evidence you can judge — never a binary stamp.

### Events and corroboration

A single report is just one account. When **multiple distinct reporters** independently describe the **same event** (close in place and time), Melo-News groups their reports into one **Event** and counts the corroboration.

- **Corroboration counts distinct people, not reports.** If one person posts five times, that's still one source. Corroboration only rises when *different* reporters confirm the same thing.
- An event becomes **Corroborated** when enough distinct, established reporters line up — not just because a number got large. A flood of brand-new accounts **cannot** make something look corroborated on its own.

### Event status

| Badge | Meaning |
|---|---|
| **Developing** | Reported, but not yet corroborated by enough distinct established reporters. |
| **Corroborated** | Independently confirmed by multiple distinct reporters — the strongest signal. |
| **Disputed** | Accounts conflict. Treat with caution until it's resolved. |
| **Closed** | The event is concluded or archived. |

### Reporter standing

Every report shows who is behind it, as a **reporter chip**:

- A **pseudonymous handle** (not a real name) with a **track record** — for example *"rung 2 · 11/14 reports corroborated"*. Reporters earn standing ("rungs") over time by filing reports that get corroborated.
- **"new reporter"** — a fresh identity with no track record yet, shown muted. Treated cautiously, like an anonymous report.
- **"anonymous · unverifiable"** — no account attached. Welcome, but it can't be vouched for.
- A **🔏 signed** badge means the report was cryptographically signed on the reporter's device — tamper-evident. Reports submitted from the web are unsigned (a lower-assurance lane).

### Confidence band

You may also see a **Low / Medium / High** confidence band. This is an **automated estimate only**. We deliberately never show a precise percentage — that would imply false precision. Always weigh **human corroboration** above the band.

---

## 7. Reading a Report

1. **Click a marker** on the map (or **Show reports** on an event).
2. A panel shows the report's **text, media, time, and location**.
3. A **trust strip** shows the report's event status, corroboration, the reporter's standing, the 🔏 signed badge if present, and the confidence band.

Use the trust strip to judge how much weight to give the report — a lone, unverified report from a new reporter is very different from one inside a corroborated event.

---

## 8. Searching & Filtering

Click the **🔍 search icon** to open the search bar.

- **Keyword:** type into the search box and press Enter. An empty search returns the most recent reports.
- **Topic chips:** one-click buttons for common subjects; they adapt to your results.
- **Date range:** click the date button to set a **From**/**To** window. ⚠ The range cannot exceed **24 hours**, which keeps results focused. Click **Apply**, or **Clear** to reset.
- The bar shows a **result count**; **Clear** resets keyword, dates, and chips at once.

---

## 9. Submitting a Report

You can contribute a report from the web or the Android app. You may submit **under your account** (to build a track record) or **anonymously**.

**How to submit:**

1. Click **Upload** (⬆).
2. Add the report details:
   - **What happened** — a clear title and description / witness statement.
   - **Where** — the city, or a map location. Use the place the event happened, not where you are now if that would put you at risk.
   - **Severity** and any **media** (photo/video).
3. Submit. You'll get a confirmation; your report is processed in the background and grouped into the right event.

**What happens next:**

- Your report is **clustered** with any other reports of the same event.
- **New, anonymous, and lower-standing reports are reviewed by a moderator before they appear publicly.** Established reporters' reports may publish immediately — but anything **high-severity, sensitive, or carrying the first photo/video of a new event is always reviewed first**, for safety.
- Once public, your report contributes to its event's corroboration.

**Supported media:** images (JPG, PNG, GIF, WebP), video (MP4, AVI, MOV, WebM), plus documents and audio where relevant.

> **Safety:** location metadata (GPS/EXIF) is **stripped from your media** before it's stored, so a photo can't silently reveal exactly where you stood. See [Privacy & Safety](#12-privacy--safety).

---

## 10. Your Account & Reporter Standing

### Creating an account

Register from the login screen, then log in. On the Android app you can register in-app and you're logged in automatically.

### Your identity is a pseudonym

Melo-News is **pseudonymous-first**: you report under a persistent **handle**, not your real name. Over time your handle accrues a visible **track record** ("X reports, Y corroborated") and can climb the **trust ladder** (rungs) as your reports are corroborated. Higher standing means your reports are trusted — and reviewed — more lightly.

### My Stories

When signed in, open **My Stories** (📄) to see everything you've submitted and its status.

> **Session expiry:** for security you may be logged out after inactivity — just log in again.

---

## 11. For Moderators

If your account has the **moderator** (or **steward**) role, a **Moderation** button (✓) appears.

- The **review queue** is ordered by **priority, not arrival time** — dangerous, sensitive, and about-to-be-corroborated reports surface first, and nothing is left to starve.
- For each report you can **Approve** (it becomes public and counts toward corroboration) or **Reject** (with a reason shown to the reporter).
- Watch for **duplicate signals** — several near-identical reports from one author are a sign of a single person using multiple accounts; reject the extras rather than letting them inflate a count.
- **Stewards** additionally bootstrap the community: they can set a user's **role** and **vouch** trusted reporters up the trust ladder, which can immediately promote a corroborated event.

Regular users never see these tools.

---

## 12. Privacy & Safety

Melo-News is built for reporters who may be at risk:

- **No real name required.** Identities are pseudonymous; you can also report fully anonymously.
- **Media is scrubbed of location metadata (GPS/EXIF)** before storage — a photo won't silently reveal your exact position.
- **The map zoom is limited**, so locations can't be pinpointed to a precise spot.
- **Your identity is never exposed in the app's data** — reports show a handle or "anonymous", never an account ID.
- **Signed reports** from the Android app are tamper-evident, even if relayed through other devices.
- Unverified content is **reviewed before it appears publicly**, and disputed accounts are flagged rather than hidden.

If you see harmful or inaccurate content, use the reporting option so a moderator can review it.

---

## 13. Troubleshooting

| Problem | What to try |
|---|---|
| **No reports on the map / empty Events feed** | There may simply be no recent corroborated reports in view. Clear filters or pan to another area. |
| **My report isn't public yet** | New, anonymous, or sensitive reports are reviewed by a moderator first. It will appear once approved. |
| **An event shows "Disputed"** | Accounts of it conflict — treat it with caution until corroborating evidence resolves it. |
| **Search shows a date error** | Your date range is longer than 24 hours — narrow it. |
| **Can't submit under my account** | Make sure you're logged in and the media type is supported. You can also submit anonymously. |
| **Logged out unexpectedly** | Your session expired for security — log in again. |
| **Something looks broken** | Refresh the page. If it persists, report it (see below). |

---

## 14. Need More Help?

- **Installation / self-hosting:** [Installation Guide](../INSTALLATION.md)
- **All documentation:** [Documentation Index](README.md)
- **Report a problem or request a feature:** open an issue on the project's GitHub page, or contact the Melo-News team.

---

*Melo-News is an open-source, community-controlled platform for citizen journalism. Built with care for reporter safety, transparency, and earned trust.*
