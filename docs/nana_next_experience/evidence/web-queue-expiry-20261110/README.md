# Unsent queue deadlines during an active request

Parent75382db original production app failed the new desktop case: after virtual20 minutes the unsent body still appeared while the first HTTP request remained pending. Raw baseline `/tmp/nana-expiry-baseline.log`.

The existing queue now schedules its nearest deadline, removes only expired unsent entries and their rendered body, and schedules remaining deadlines. It preserves the active request/receipt and original timeout. Unmount cleans up the timer.

Production TypeScript/Vite build passed(2.63s),67 units(3.43s),12 browser queue scenarios at desktop/360/390/412(19.1s). Final log `/tmp/nana-expiry-verified.log`, outputs `/tmp/nana-expiry-verified`, app `/tmp/nana-expiry-dist`, config `/tmp/nana-expiry-playwright.config.ts`. Two queued bodies entered5s apart disappear at their own deadlines; only the first request was posted and its VERIFIED reply still arrives. Virtual20m05s does not prove actual20-minute residence.

First failures retained: `/tmp/nana-expiry-fixed.log` used a strict multi-element locator(8pass4fail); `/tmp/nana-expiry-final.log` advanced21m across original1230000ms HTTP timeout(8pass4fail). Final test stays below that original timeout and preserves behavioral assertions. First TS Set UUID typing error corrected to Set<string>.

Root overlay ran out of space saving evidence. The known npm cache was copied intact from `/workspace/scratch/npm-cache` to `/tmp/nana-preserved-npm-cache`, all560 file/link fingerprints matched before source cache removal and original-path symlink. Manifest `/tmp/nana-npm-cache-preservation.json`. No test DB/source/Git/old release was removed. Build/test outputs stay in /tmp.

Core source unchanged; original acddab6 full CI2153/12 evidence reused. No APK/CURRENT/model/account/phone/production update. All original A–H remaining scope continues.
