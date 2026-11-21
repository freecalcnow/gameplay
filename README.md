# Arcadia Global 100 — static browser arcade

## What is included
- 100 dedicated game pages (10 retained concepts + 90 added entries).
- 100 original, procedurally drawn SVG cover illustrations.
- Shared HTML5 Canvas game engine with original gameplay modes and per-game variations.
- Responsive homepage, search, category filtering, daily featured game, favourites, personal best scores and recent-play tracking.
- Local-only high scores and visit streaks using browser localStorage.
- 100 game URLs, category landing pages, About, Help, Contact, Privacy and Terms pages.
- Metadata, canonical URLs, VideoGame/BreadcrumbList structured data, sitemap.xml and robots.txt.
- Basic PWA manifest and service worker for static-file caching.
- Ad placement placeholders only; no ads or ad network code is activated.

## Run locally
Open `index.html` or run a local server from this folder, for example `python -m http.server 8000`. For the service worker / install support, use localhost or HTTPS.

## Publish to GitHub Pages
1. Create a public repository and upload the contents of this folder to its root.
2. Enable GitHub Pages from the repository's main branch and root folder.
3. For a custom domain, connect it in GitHub Pages and enable HTTPS.
4. Replace every `https://freecalcnow.github.io/gameplay` placeholder in canonical URLs, JSON-LD, `sitemap.xml`, `robots.txt`, Open Graph URLs and social image references with the final HTTPS domain.
5. Replace `REPLACE_WITH_SEARCH_CONSOLE_TOKEN` in the homepage meta tag with the verification token from Google Search Console. Verify the property, then submit `/sitemap.xml`. This package prepares the sitemap; it does not submit or verify a property on the owner's behalf.
6. Replace `malikarslan032154@gmail.com` on the Contact page with a real support address. Review Privacy and Terms before publishing.

## Ads and monetization
There are reserved ad placeholders, but no publisher IDs or ad scripts. Apply for approval first and add only the exact approved ad code. Keep ads clearly separate from play/navigation controls; Google's gameplay-page guidance recommends at least 150px separation from the actual game. Do not use forced clicks, fake close buttons, floating ads, auto-refresh tricks or ads that block gameplay. Review current policies before launch.

AdSense account holders must be 18 or older. A publisher under 18 needs a parent/guardian to apply with their own Google Account; payments are made to that adult if approved.

## Current limits (important)
- This is a static front-end build. Scores, favourites, and streaks remain on one browser/device. There is no real user account system, cross-device sync, cloud save, anti-cheat or global leaderboard.
- There is no real-time multiplayer or server matchmaking. Titles described as arena/board challenges are single-player or against simple local CPU logic.
- The 100 catalog entries are distinct themed play experiences built from a set of reusable original game mechanics; this is not 100 fully bespoke commercial-scale games with separate art teams. Each has its own URL, SEO description, cover art and game parameters.
- A service worker caches the app shell and files as they are visited. The first visit requires internet access and browser support.
- The game collection has been syntax/static checked in this package, but it still needs real device/browser playtesting before a public launch.

## Before a serious launch
Connect a real domain, configure Search Console, run mobile/browser QA, add accessibility checks, create a proper support address, review privacy/consent duties for target countries, measure Core Web Vitals, and add a secure backend before promising accounts, global leaderboards, multiplayer or cloud saves.
