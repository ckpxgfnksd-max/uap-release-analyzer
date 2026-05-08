# war.gov/UFO/ ("PURSUE") page quirks

Notes from the May 2026 release scrape. Read this before writing fresh
scraper code — it will save you an hour.

## Page architecture

- `https://www.war.gov/UFO/` is a single-page DNN/jQuery app. The records
  table is rendered server-side into a paginated list of buttons:
  `<button class="record-row" data-record-trigger data-record-id="record-NNN">`.
- Pagination is **DOM-only** — there is no JSON API. Records 1–10 are in
  the DOM; clicking a numbered page button or `Prev`/`Next` swaps the
  buttons in place. There is no infinite scroll and no XHR for the data.
- Each row has child `.record-meta` spans for agency, release date,
  incident date, location, and document type. Sometimes the meta is jammed
  into `.record-title` instead (DOW UAP "PR" rows do this) — don't assume
  one structure.
- Pagination shows up to ~7 numbered buttons at a time around the current
  page (sliding window). To enumerate all records, click `Next` repeatedly
  until `.pagination-next` becomes `disabled`.

## How to get download URLs

Records do not link directly. Clicking a row opens `#record-modal` with a
`<button data-record-modal-download>`. That button's click handler builds
a URL via `<a download>` (in the page's same origin) and dispatches a
synthetic `MouseEvent('click')`. So the URL is only realized when you
trigger the download.

The pattern that works: hook `HTMLAnchorElement.prototype.click` to
capture `this.href`, also hook `window.open`, then iterate every
`record-row`, click it, click the download button, capture
`window.__lastDl`, click `[data-record-modal-close]`, repeat.

Captured URLs follow `https://www.war.gov/medialink/ufo/release_1/<lower(filename)>.<ext>`.

## Footguns

- ~17% of the records (in the May 2026 tranche, the DOW-UAP-PR* "Unresolved
  Report" series) open in an inline viewer instead of triggering a real
  download. The captured URL is a `blob:` URL into the user's session, not
  a media URL. There is **no clean way** to derive the real medialink URL
  for those files in the current page implementation — you have to either
  scroll the iframe and download from inside the viewer, or skip them.
- `window.open` in some flows passes feature strings that get concatenated
  into your captured URL (you'll see `<filename>+M5+M11`). Filter those
  out and re-attempt with the canonical filename.
- Filenames with spaces and em-dashes appear unencoded; `fetch()` from the
  page handles this fine, but `curl` on the host needs `urlencode`.
- The page is a US-government `*.war.gov` host that is typically *not* on
  workspace egress allowlists. If you need shell `curl`/`wget`, ask the
  user to allowlist `www.war.gov`. Otherwise drive everything through
  the browser MCP and save via `<a download>`.

## Robust scrape pseudocode

```js
window.__urls = {};
HTMLAnchorElement.prototype.click = function(){ window.__lastDl = this.href };
window.open = function(u){ window.__lastDl = u };

async function harvest(){
  // Page 1 first
  const p1 = [...document.querySelectorAll('.pagination-button')].find(b => b.innerText.trim() === '1');
  if (p1 && !p1.classList.contains('is-active')) { p1.click(); await raf(); }
  for (let pg = 1; pg <= 30; pg++){
    for (const row of document.querySelectorAll('button.record-row')){
      const title = row.querySelector('.record-title').innerText.trim();
      if (window.__urls[title]?.startsWith('https://www.war.gov/medialink/')) continue;
      window.__lastDl = null;
      row.click();           await raf();
      document.querySelector('[data-record-modal-download]').click(); await raf();
      if (window.__lastDl?.startsWith('https://www.war.gov/medialink/')) {
        window.__urls[title] = window.__lastDl;
      }
      document.querySelector('[data-record-modal-close]').click(); await raf();
    }
    const nx = document.querySelector('.pagination-next');
    if (!nx || nx.disabled) break;
    nx.click(); await raf();
  }
}
function raf(){ return new Promise(r => requestAnimationFrame(()=>requestAnimationFrame(r))); }
```

## Future tranches

The page promised "rolling tranches every few weeks". When release_02 lands
the DOM should be the same shape; the only thing that needs updating is
the medialink path (`/release_1/` → `/release_2/`). Re-run the scrape,
diff against the prior `inventory.csv` to see what's new.
