"""
Notification dispatcher for CI pipeline results.

Reads configuration from environment variables so every target is opt-in
via repository secrets:

  SLACK_WEBHOOK_URL  → Slack notification
  EMAIL_TO           → email notification (requires EMAIL_FROM + EMAIL_PASSWORD)
  PR_NUMBER          → GitHub PR comment (requires GITHUB_TOKEN + REPOSITORY)
"""

import os
import smtplib
import sys
from email.mime.text import MIMEText

import requests

# ---------------------------------------------------------------------------
# Shared context
# ---------------------------------------------------------------------------
STATUS = os.environ.get("NOTIFY_STATUS", "unknown")
WORKFLOW = os.environ.get("NOTIFY_WORKFLOW", "CI")
RUN_URL = os.environ.get("NOTIFY_RUN_URL", "")

ICON = "✅" if STATUS == "success" else "❌"
SUMMARY = f"{ICON} *{WORKFLOW}* — {STATUS.upper()}"
errors = []


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------
def notify_slack():
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        print("[notify] Slack: skipped (no SLACK_WEBHOOK_URL)")
        return

    payload = {
        "text": SUMMARY,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{SUMMARY}\n<{RUN_URL}|View run>",
                },
            }
        ],
    }
    resp = requests.post(webhook, json=payload, timeout=10)
    if resp.status_code == 200:
        print("[notify] Slack: sent")
    else:
        errors.append(f"Slack HTTP {resp.status_code}: {resp.text}")
        print(f"[notify] Slack: FAILED — {resp.status_code}")


# ---------------------------------------------------------------------------
# Email (Gmail App Password / SMTP TLS)
# ---------------------------------------------------------------------------
def notify_email():
    to_addr = os.environ.get("EMAIL_TO", "").strip()
    from_addr = os.environ.get("EMAIL_FROM", "").strip()
    password = os.environ.get("EMAIL_PASSWORD", "").strip()

    if not to_addr:
        print("[notify] Email: skipped (no EMAIL_TO)")
        return
    if not from_addr or not password:
        errors.append("Email: EMAIL_FROM or EMAIL_PASSWORD not set")
        print("[notify] Email: FAILED — missing credentials")
        return

    subject = f"CI {STATUS.upper()}: {WORKFLOW}"
    body = f"{SUMMARY}\n\nRun URL: {RUN_URL}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(from_addr, password)
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
        print("[notify] Email: sent")
    except Exception as exc:
        errors.append(f"Email: {exc}")
        print(f"[notify] Email: FAILED — {exc}")


# ---------------------------------------------------------------------------
# GitHub PR comment
# ---------------------------------------------------------------------------
def notify_github_pr():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    repo = os.environ.get("REPOSITORY", "").strip()

    if not pr_number or pr_number == "":
        print("[notify] GitHub PR comment: skipped (not a PR)")
        return
    if not token or not repo:
        errors.append("GitHub PR: GITHUB_TOKEN or REPOSITORY not set")
        print("[notify] GitHub PR comment: FAILED — missing config")
        return

    body = f"{SUMMARY}\n\n[View run]({RUN_URL})"
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.post(url, json={"body": body}, headers=headers, timeout=10)
    if resp.status_code == 201:
        print("[notify] GitHub PR comment: posted")
    else:
        errors.append(f"GitHub PR HTTP {resp.status_code}: {resp.text}")
        print(f"[notify] GitHub PR comment: FAILED — {resp.status_code}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"[notify] status={STATUS} workflow={WORKFLOW}")
    notify_slack()
    notify_email()
    notify_github_pr()

    if errors:
        print("\n[notify] Some notifications failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("[notify] All notifications dispatched successfully.")
