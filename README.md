# AI Content Creator for LinkedIn

Approval-based LinkedIn posting agent for AI and RPA updates.

It fetches recent news, picks one topic, drafts a post with OpenAI, emails it to you for approval, and publishes only after you approve.

## Flow

```text
RSS news -> topic selection -> LinkedIn draft -> approval email -> LinkedIn publish
```

This project is intentionally human-in-the-loop. It will never publish a fresh draft without your approval.

## Project Files

- `main.py` runs one workflow step.
- `config.py` loads settings and validates them.
- `rss_fetcher.py` collects recent news topics from RSS feeds.
- `topic_selector.py` chooses the best topic with OpenAI.
- `post_generator.py` writes or rewrites the LinkedIn post.
- `email_service.py` sends the approval email.
- `approval_checker.py` checks Gmail for `APPROVE` or `DENY`.
- `linkedin_service.py` publishes approved posts to LinkedIn.
- `storage_manager.py` manages persistent workflow state in `storage.json`.
- `check_setup.py` validates your local `.env`.

## Requirements

- Python `3.11` or `3.12`
- OpenAI API key
- Gmail account with 2-Step Verification and an App Password
- LinkedIn Developer app with a valid user access token

Python `3.14` may show OpenAI or Pydantic warnings. Use `3.11` or `3.12` for the cleanest setup.

## Local Setup

### 1. Install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Create `.env`

```powershell
Copy-Item .env.example .env
```

Then fill in your real values.

### 3. Gmail settings

Use a Gmail App Password, not your normal Gmail password.

Set these values:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_gmail_address@gmail.com
SMTP_PASSWORD=your_gmail_app_password
EMAIL_FROM=your_gmail_address@gmail.com
EMAIL_TO=approver_email@gmail.com

IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your_gmail_address@gmail.com
IMAP_PASSWORD=your_gmail_app_password
```

### 4. LinkedIn settings

In LinkedIn Developer Portal:

1. Open your app.
2. Enable `Share on LinkedIn`.
3. Enable `Sign In with LinkedIn using OpenID Connect`.
4. Generate a user access token with these scopes:

```text
openid
profile
w_member_social
```

Then put the token in `.env`:

```env
LINKEDIN_ACCESS_TOKEN=your_access_token
```

Get your LinkedIn person id:

```powershell
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://api.linkedin.com/v2/userinfo
```

Use the returned `sub` value:

```env
LINKEDIN_AUTHOR_URN=urn:li:person:YOUR_SUB_VALUE
LINKEDIN_API_VERSION=202604
```

Do not use your public LinkedIn profile URL id. Use the `sub` value from `/v2/userinfo`.

### 5. Check local setup

```powershell
python check_setup.py
```

Expected result:

```text
READY: .env has the required values and basic formats look valid.
```

## Manual Usage

Run:

```powershell
python main.py
```

Behavior:

1. If no draft is pending, the app creates one and emails it to you.
2. If a draft is already pending, the app checks Gmail for your reply.
3. If you approved it, the app publishes it to LinkedIn.
4. If you denied it, the app rewrites the draft and emails a new version.

Typical manual flow:

1. Run `python main.py`
2. Review the draft in email
3. Approve or deny
4. Run `python main.py` again

## GitHub Actions

The repo now uses two workflows:

```text
.github/workflows/linkedin-weekly-draft.yml
.github/workflows/linkedin-approval-check.yml
```

This keeps drafting and approval checks separate.

Flow:

1. Sunday morning the draft workflow runs once.
2. It creates a draft only if nothing is already pending.
3. The approval-check workflow runs every 15 minutes.
4. If you approve, it publishes the post.
5. If you deny, it regenerates the draft and emails a new version.

### Schedule

- Draft workflow: Sunday `03:30 UTC` / Sunday `09:00 AM IST`
- Approval check workflow: Sunday only, every 15 minutes from `09:15 AM IST` onward

### Required GitHub secrets

Add these repository secrets:

```text
OPENAI_API_KEY
SMTP_USERNAME
SMTP_PASSWORD
EMAIL_TO
LINKEDIN_ACCESS_TOKEN
LINKEDIN_AUTHOR_URN
```

Optional overrides:

```text
OPENAI_MODEL
SMTP_HOST
SMTP_PORT
EMAIL_FROM
IMAP_HOST
IMAP_PORT
IMAP_USERNAME
IMAP_PASSWORD
LINKEDIN_API_VERSION
MAX_REGEN_ATTEMPTS
LOG_LEVEL
LOG_MAX_BYTES
LOG_BACKUP_COUNT
```

Workflow defaults:

- `EMAIL_FROM` falls back to `SMTP_USERNAME`
- `IMAP_USERNAME` falls back to `SMTP_USERNAME`
- `IMAP_PASSWORD` falls back to `SMTP_PASSWORD`
- Gmail host and port defaults are already set

### Important notes

- Keep the repository private because `storage.json` is committed back to the repo to preserve pending state.
- In GitHub repository settings, set Actions workflow permissions to `Read and write`.
- The workflow uses repo secrets directly, not your local `.env`.
- `python main.py` still works locally with the original behavior.
- If you approve or deny outside the Sunday check window, the workflow will not process it automatically until the next Sunday unless you run it manually.

## Logs and State

Logs are written to:

```text
logs/agent.log
```

State is stored in:

```text
storage.json
```

`storage.json` tracks:

- used topics
- approved posts
- current pending approval
- regeneration count

To reset state:

```json
{
  "used_topics": [],
  "approved_posts": [],
  "pending_approval": null,
  "regeneration_count": 0
}
```

## Common Fixes

### LinkedIn API version issue

Set:

```env
LINKEDIN_API_VERSION=202604
```

### `Not enough permissions to access: userinfo`

Generate a new LinkedIn token with:

```text
openid profile w_member_social
```

### LinkedIn author validation failed

Your `LINKEDIN_AUTHOR_URN` does not match the authenticated token user.

Check with:

```powershell
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://api.linkedin.com/v2/userinfo
```

Then set:

```env
LINKEDIN_AUTHOR_URN=urn:li:person:SUB_VALUE
```

### Email approval check times out

The IMAP checker uses a 30-second timeout. If it hangs repeatedly, check your Gmail app password, IMAP access, and network connection.

## Security

- Never commit `.env`
- Never share your LinkedIn token
- Use Gmail App Passwords
- Regenerate the LinkedIn token when it expires
