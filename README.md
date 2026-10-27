# PC Price Watch

Scheduled gaming-PC and component price monitor. Uses SerpApi Google Shopping results and sends a single email digest for new qualifying deals to an Outlook/Hotmail inbox using the Resend email API.

## Watches
- Prebuilt gaming PC under $2,200 with Ryzen 7 7800X3D or 9800X3D, a configured GPU equivalent, 32GB DDR5, and at least 1TB SSD/NVMe. The bot flags cooling/storage details that listings do not confirm; verify CPU and GPU liquid cooling on the retailer page.
- RTX 5070 Ti under $1,000.
- New 32GB DDR5 desktop memory kit under $350.

Used, open-box, and refurbished listings are excluded by default. Promotion labels are clues from listing text, not proof a coupon works. Retailer channels include Amazon, Best Buy, Micro Center, Newegg, Costco, Sam's Club, Walmart, B&H Photo Video, Adorama, and direct PC manufacturers. Shopping aggregators do not guarantee every retailer or deal appears.

## 1. Set up the email sender
1. Create a Resend account at https://resend.com/ using the same Outlook/Hotmail address you want to receive alerts at.
2. Create a Resend API key in the Resend dashboard.
3. This configuration uses Resend's testing sender `onboarding@resend.dev`. With that sender, the recipient generally must be the email address associated with your Resend account. To send to a different recipient or use your own From address, verify a domain in Resend and update the sender in `price_watch.py`.
4. Get a SerpApi key at https://serpapi.com/.

Emails will arrive in your Outlook/Hotmail inbox, but Resend—not Outlook SMTP—sends them. No phone app or phone number is required.

## 2. Configure GitHub Actions Secrets
Open repository **Settings → Secrets and variables → Actions → New repository secret** and add:

- `SERPAPI_API_KEY` — your SerpApi key
- `RESEND_API_KEY` — your Resend API key
- `ALERT_EMAIL` — the Outlook/Hotmail address that should receive alerts

Never commit real credentials. If a SerpApi key was previously pasted into a chat or committed to a repository, revoke it and create a replacement before using it.

## 3. Run and verify
1. Open **Actions → PC price watch** and select **Run workflow**.
2. For a delivery test, set **Send a test email only (skip shopping searches)** to **true**. This sends a test email without using SerpApi searches or changing alert history.
3. After the test arrives, run it again with that option set to **false** to perform the real price check.
4. Normal runs send an email only when new qualifying deals are found. If no new deals qualify, no email is sent. Check the Actions logs and Resend dashboard if the test fails.

The workflow runs at 13:00 and 23:00 UTC. That is 09:00 and 19:00 Eastern during daylight time, and 08:00 and 18:00 Eastern during standard time. GitHub cron uses UTC, so the local wall-clock times shift seasonally.

## 4. Test locally on Windows PowerShell
Install Python 3.11+ from https://www.python.org/downloads/windows/, then:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
py price_watch.py --dry-run
```
Fill in your real keys in the local `.env` file. A dry run still uses SerpApi searches but does not send email or save alert history. Never commit `.env`.

## Price limits and behavior
Edit `config.json` to adjust thresholds, GPU equivalents, and search terms. Duplicate alerts are suppressed unless the same listing drops by at least $25; the bot sends at most three alerts per category per run. Alerts include links and any uncertain specs for manual verification.

## Costs and limitations
SerpApi has usage limits and pricing: https://serpapi.com/pricing. Resend has its own free and paid sending limits, which can change: https://resend.com/pricing. The default schedule makes three shopping searches twice daily (about 180 searches per 30-day month); manual runs also use searches. Search results may be incomplete or stale, and deal labels are not guaranteed discounts.

## Troubleshooting
- Missing API key: check repository Actions secrets for exact names.
- No email: there may be no new qualifying deals; inspect the Actions log and Resend dashboard.
- Resend rejects the recipient: use the same address associated with your Resend account with the testing sender, or verify a domain in Resend.
- No repeat alert: a listing repeats only after a $25+ price drop or if it later becomes qualifying again.

References: https://serpapi.com/shopping-results · https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
