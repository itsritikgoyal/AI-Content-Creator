# AI Content Creator for LinkedIn

An approval-based LinkedIn posting agent.

It finds recent AI/RPA news, writes a LinkedIn post with OpenAI, emails you for approval, and publishes only after you approve.

## How It Works

```text
RSS news -> OpenAI topic selection -> OpenAI post draft -> approval email -> LinkedIn post
```

The app is intentionally human-in-the-loop. It will not publish a new draft until you approve it by email.

## Project Files

- `main.py` - runs one workflow step.
- `config.py` - loads `.env` settings and validates them.
- `rss_fetcher.py` - collects recent news topics from RSS feeds.
- `topic_selector.py` - asks OpenAI to choose the best topic.
- `post_generator.py` - asks OpenAI to write or rewrite the post.
- `email_service.py` - sends the approval email.
- `approval_checker.py` - checks your mailbox for `APPROVE` or `DENY`.
- `linkedin_service.py` - publishes approved posts to LinkedIn.
- `storage_manager.py` - stores pending/approved state in `storage.json`.
- `check_setup.py` - checks whether `.env` looks ready.

## Requirements

- Python 3.11 or 3.12 recommended.
- OpenAI API key.
- Gmail account with 2-Step Verification and an App Password.
- LinkedIn Developer app with a 3-legged OAuth access token.

Python 3.14 may show OpenAI/Pydantic compatibility warnings. Use 3.11 or 3.12 for the cleanest setup.

## 1. Install

Open PowerShell in this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Create `.env`

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and fill in your real values.

## 3. Gmail Setup

Use Gmail App Passwords, not your normal Gmail password.

1. Enable 2-Step Verification on your Google account.
2. Create an App Password for Mail.
3. Put that app password in:

```env
SMTP_PASSWORD=your_gmail_app_password
IMAP_PASSWORD=your_gmail_app_password
```

For Gmail, these defaults are normally correct:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
```

## 4. LinkedIn Setup

In LinkedIn Developer Portal:

1. Create or open your app.
2. Enable **Share on LinkedIn**.
3. Enable **Sign In with LinkedIn using OpenID Connect**.
4. Generate a new 3-legged access token with these scopes:

```text
openid
profile
w_member_social
```

`email` is optional.

Put the new token in `.env`:

```env
LINKEDIN_ACCESS_TOKEN=your_new_access_token
```

Now get your LinkedIn API person id:

```powershell
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://api.linkedin.com/v2/userinfo
```

The response contains `sub`:

```json
{
  "name": "Your Name",
  "sub": "7H_JpJb6pN"
}
```

Use that value like this:

```env
LINKEDIN_AUTHOR_URN=urn:li:person:7H_JpJb6pN
LINKEDIN_API_VERSION=202604
```

Do not use your public LinkedIn profile URL id. Use the `sub` value returned by `/v2/userinfo`.

## 5. Check Setup

Run:

```powershell
python check_setup.py
```

Expected result:

```text
READY: .env has the required values and basic formats look valid.
```

If it says `NOT READY`, fix the listed `.env` values first.

## 6. Run Manually

First run:

```powershell
python main.py
```

If no post is waiting for approval, this creates a new draft and emails it to you.

Approve the email by clicking the `Approve` link.

Second run:

```powershell
python main.py
```

This checks your inbox, finds the approval, and publishes the post to LinkedIn.

If you click `Deny`, the next run rewrites the draft and emails a new version.

## 7. Current Usage

Right now this project is set up for local/manual runs.

Run `python main.py` whenever you want the agent to take the next workflow step.

Typical posting rhythm:

1. Run `python main.py` to generate and email a draft.
2. Approve or deny from email.
3. Run `python main.py` again to publish or regenerate.

For future automation, run the same command from a scheduler or cloud job. The machine running it must have internet access and a valid `.env`.

## 8. Logs and State

Logs are written here:

```text
logs/agent.log
```

State is stored here:

```text
storage.json
```

`storage.json` tracks:

- topics already used
- approved posts
- the current pending approval
- regeneration count

To reset the app to a fresh state, replace `storage.json` with:

```json
{
  "used_topics": [],
  "approved_posts": [],
  "pending_approval": null,
  "regeneration_count": 0
}
```

## Common Fixes

### `NONEXISTENT_VERSION`

Set:

```env
LINKEDIN_API_VERSION=202604
```

### `Not enough permissions to access: userinfo`

Generate a new LinkedIn token with:

```text
openid profile w_member_social
```

### LinkedIn `/author` Validation Failed

Your `LINKEDIN_AUTHOR_URN` does not match the authenticated token user.

Call:

```powershell
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://api.linkedin.com/v2/userinfo
```

Then set:

```env
LINKEDIN_AUTHOR_URN=urn:li:person:SUB_VALUE
```

### App Hangs While Checking Email

The checker uses a 30-second IMAP timeout. If it repeatedly times out, check your Gmail app password, IMAP access, and internet connection.

## Security

- Never commit `.env`.
- Never share your LinkedIn access token.
- Use app passwords for Gmail.
- Regenerate the LinkedIn token when it expires.

## Clean Runtime Files

These are generated automatically and can be deleted safely:

- `__pycache__/`
- `logs/agent.log`
- old `.pyc` files

Do not delete `.env` unless you want to reconfigure credentials.
