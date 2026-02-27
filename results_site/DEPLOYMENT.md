# Vercel Deployment Guide

## Deployment Status

✅ **Successfully deployed to:** https://resultssite.vercel.app

## Environment Variables

Set these in the Vercel dashboard under **Settings → Environment Variables**, or via the CLI.

### Required

| Variable | Description |
|---|---|
| `WEBHOOK_SECRET` | Authentication secret for webhook requests. Must match the `WEBHOOK_SECRET` set in the main Race Timing system. |

### Optional

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL/MySQL connection string for persistent storage. If not set, SQLite in `/tmp` is used (data is ephemeral per cold start). |

#### Setting via CLI

```bash
cd results_site
vercel env add WEBHOOK_SECRET production
# Enter your secret when prompted

# Redeploy to apply
vercel --prod
```

> **SQLite on Vercel:** Vercel's filesystem is read-only except `/tmp`. Without `DATABASE_URL`, the site uses `/tmp/results_public.db` which is reset on every cold start. Results are re-populated automatically when the main timing system publishes via webhooks. For persistent storage, set `DATABASE_URL` to a hosted database (e.g. Supabase, Railway Postgres).

## Connecting the Main Timing System

Once deployed, configure the main Race Timing system to publish to this site:

1. Set `RESULTS_PUBLISH_URL=https://resultssite.vercel.app` in the main system's `.env`
2. Set `WEBHOOK_SECRET` to the same value as above
3. Use the **Publish Results** button in the Race Control UI, or trigger auto-publish

## Testing the Deployment

```bash
# Health check (should return {"status": "ok", ...})
curl https://resultssite.vercel.app/ping

# Home page
curl https://resultssite.vercel.app/

# Test webhook (replace YOUR_SECRET)
curl -X POST https://resultssite.vercel.app/webhook/publish-event \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: YOUR_SECRET" \
  -d '{"event_id": 1, "name": "Test Event", "date": "2025-01-01T00:00:00"}'
```

## Deployment URLs

- **Production:** https://resultssite.vercel.app
- **Vercel Dashboard:** https://vercel.com/danielcrows-projects/results_site

## Troubleshooting

### Webhook returns 401 Unauthorized
- `WEBHOOK_SECRET` in Vercel does not match the main system's `WEBHOOK_SECRET`
- Redeploy after changing environment variables

### Results disappear after a while
- Expected behaviour with SQLite on Vercel (ephemeral `/tmp`)
- Set `DATABASE_URL` to a persistent database, or re-publish from the main system

### CSS not loading
- Ensure `vercel.json` includes the static files build and route (already configured)
- Check browser DevTools Network tab for 404s on `/static/css/style.css`

### Changes not appearing after redeploy
- Clear browser cache or open in incognito mode
- Check Vercel deployment logs for build errors

## Local Development

```bash
cd results_site
pip install -r requirements.txt
export WEBHOOK_SECRET=dev-secret
python app.py
# Visit http://localhost:5002