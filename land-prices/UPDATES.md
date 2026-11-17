# Iraq land-price recurring update

The owner approved this public feed, including published advertiser coordinates, on 2026-11-17. Only land-prices/ belongs to this task. Never change other download files or applications.

Every run downloads latest.json and the three scripts in this folder into a fresh temporary directory, with a fresh raw/ directory. Use a local Python environment with lxml. Run python refresh_feed.py --output latest-candidate.json. Never reuse cached source HTML from an earlier run. The collectors obey robots.txt, read public pages only, and keep advertiser contacts, images and prose out of the feed.

The script merges by source ID, updates observed prices, preserves up to 12 previous price observations, and discovers regions from new records. Missing records are retained, not declared sold. Original publication dates and currencies remain unchanged. Unreachable sources keep their previous data. If both listing sources fail, the script exits 2: do not publish a candidate as a successful refresh. Explain partial failures.

Government tax references remain historical. The official archive is checked for changes, but a changed PDF archive is flagged for review rather than blindly extracting uncertain new values or treating them as current market prices.

After a successful refresh, fetch the current GitHub content SHA of land-prices/latest.json, replace only that file through the GitHub connector update_file operation using that SHA and the exact candidate UTF-8 text, then download the raw URL again. Validate the gzip SHA-256, decompression and row count. Preserve a failed source's records. Never use a fabricated successful timestamp. The APK downloads the feed on opening with internet and saves the last valid version atomically.

Feed URL: https://raw.githubusercontent.com/nydgrdp-del/random-voice-downloads/main/land-prices/latest.json

If a script's SHA-256 differs from the values recorded in the automation prompt, stop execution and report the changed script for review. Do not silently run modified code. No credentials belong in the feed or scripts.
