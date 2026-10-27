# PC Price Watch

Beginner-friendly scheduled price monitor for gaming PCs and components. Uses SerpApi Google Shopping results, filters supported retailer channels, tracks alerts, and sends SMS through Twilio.

## Watches
- Prebuilt gaming PC under $2,200 with Ryzen 7 7800X3D or 9800X3D, a configured GPU equivalent, 32GB DDR5, and at least 1TB SSD/NVMe. The bot flags cooling/storage details that listings do not confirm; verify CPU and GPU liquid cooling on the retailer page.
- RTX 5070 Ti under $1,000.
- New 32GB DDR5 desktop memory kit under $350.

Search terms include clearance, sale, special offer, discounts, and coupons. Promotion labels are clues from listing text, not proof a coupon works. Used, open-box, and refurbished listings are excluded by default. Retailer channels: Amazon, Best Buy, Micro Center, Newegg, Costco, Sam's Club, Walmart, B&H Photo Video, Adorama, and direct PC manufacturers. Shopping aggregators do not guarantee every retailer or every deal appears.

## 1. Set up accounts
1. Get a SerpApi key: https://serpapi.com/
2. Set up an SMS-capable Twilio number: https://www.twilio.com/docs/messaging/quickstart
3. Install Python 3.11+: https://www.python.org/downloads/windows/

Never commit real credentials. Use GitHub Actions Secrets for cloud runs.

## 2. Test locally on Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
py price_watch.py --dry-run
```
Fill in `.env` with your real keys. `DRY_RUN=true` prints alerts without sending texts. A dry run still uses SerpApi searches. When ready, set `DRY_RUN=false` and run `py price_watch.py` to send actual alerts.

## 3. Configure GitHub Actions
In repository Settings → Secrets and variables → Actions, create these repository secrets:
- `SERPAPI_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`
- `ALERT_PHONE_NUMBER`

Then open Actions → PC price watch → Run workflow. The schedule runs daily at 9 AM and 7 PM Eastern time. GitHub Actions keeps running while your PC is off.

## Price limits and settings
Edit `config.json` to adjust thresholds, GPU equivalents, and search terms. The bot suppresses duplicate alerts unless the price drops by at least $25; it sends at most three alerts per category per run. Verify the final price, seller, condition, specifications, and coupon eligibility on the retailer checkout page.

## Costs and limitations
SerpApi and Twilio have usage/price limits that can change; check https://serpapi.com/pricing and https://www.twilio.com/en-us/sms/pricing/us. The default schedule makes three searches twice daily (about 180 searches per 30-day month). Manually running workflows also consumes searches. Search result text can be incomplete or stale; no deal is guaranteed.

## Troubleshooting
- Missing API key: check `.env` locally or repository Actions secrets.
- No alerts: results may not include a supported merchant or all required specs.
- SMS fails: verify Twilio number capability, credentials, and destination verification on trial accounts.
- No repeat alert: duplicate suppression only repeats for a $25+ drop or when a listing later falls back under the threshold.

References: https://serpapi.com/shopping-results · https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
