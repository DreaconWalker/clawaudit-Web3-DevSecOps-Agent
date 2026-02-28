# Testing the GitHub webhook flow

**The program does not create PRs.** It **reacts** when **you** open or update a Pull Request: GitHub sends a webhook to the app, then the app audits the PR diff and posts the result as a comment on that PR.

**Ready-made test repo:** Use the folder **`clawaudit-auto-git-pr-test-repo/`** in this project. It contains a vulnerable Solidity contract and **SETUP.md** with step-by-step instructions to push it to GitHub as `clawaudit-auto-git-pr-test-repo` and open a PR to trigger the webhook.

Follow these steps to test end-to-end.

---

## 1. Make your backend reachable from the internet

GitHub can only call your webhook if it can reach your server.

- **Option A — Deployed backend**  
  If your API is already on a public URL (e.g. `https://your-app.fly.dev`), use that as the base URL below.

- **Option B — Local testing with ngrok**  
  1. Install [ngrok](https://ngrok.com/download).
  2. Start your FastAPI backend: `uvicorn main:app --host 0.0.0.0 --port 8000`
  3. In another terminal: `ngrok http 8000`
  4. Copy the HTTPS URL ngrok shows (e.g. `https://abc123.ngrok.io`). That is your **webhook base URL** for the next steps.

- **Option C — Local testing with Pinggy**  
  1. Start your FastAPI backend: `uvicorn main:app --host 0.0.0.0 --port 8000`
  2. In another terminal: **`pinggy http 8000`** (must be port **8000**, not 8501). Streamlit runs on 8501 and does not have the webhook endpoint — a tunnel to 8501 will return **405 Method Not Allowed** for `POST /webhook/github`.
  3. Copy the HTTPS URL Pinggy shows (e.g. `https://xxxxx.free.pinggy.link`). Use `https://YOUR_PINGGY_URL/webhook/github` as the Payload URL in GitHub.

---

## 2. Add the webhook to your GitHub repo

1. Open the repo you want to test (create a new one or use an existing).
2. Go to **Settings → Webhooks → Add webhook**.
3. **Payload URL:**  
   `https://YOUR_HOST/webhook/github`  
   - With ngrok: `https://abc123.ngrok.io/webhook/github`  
   - With a deployed app: `https://your-app.fly.dev/webhook/github`
4. **Content type:** `application/json`
5. **Which events:** choose **Let me select individual events** → enable **Pull requests** only.
6. Leave **Secret** empty (this app doesn’t verify it yet).
7. Click **Add webhook**. You should see a green checkmark after GitHub sends a “ping” (we don’t handle the ping; that’s OK).

---

## 3. Ensure `.env` has `GITHUB_TOKEN`

In your project `.env`:

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

- Create a token: GitHub → **Settings → Developer settings → Personal access tokens** (or Fine-grained tokens).
- Scopes: **repo** (full) so the app can post comments, create branches, and open the **remediation PR** (suggested fix). For fine-grained tokens: Contents (read/write), Pull requests (read/write).
- For a **private** repo, the token must belong to an account that has access to that repo.

Restart the backend after changing `.env`.

---

## 4. Create a PR that triggers the webhook

**You** create the repo and the PR; the app only runs when GitHub notifies it.

1. **Create a repo** (or use an existing one). Example: `my-audit-test`.

2. **Add a base branch** (e.g. `main`):
   - Add a simple file (e.g. `README.md`), commit, push.

3. **Create a branch with contract code**:
   ```bash
   git checkout -b add-contract
   ```
   Add a Solidity file, e.g. `contracts/Vulnerable.sol`:
   ```solidity
   // SPDX-License-Identifier: MIT
   pragma solidity ^0.8.0;
   contract VulnerableBank {
       mapping(address => uint) public balances;
       function withdraw() external {
           uint amount = balances[msg.sender];
           require(amount > 0);
           (bool ok,) = msg.sender.call{value: amount}("");
           require(ok);
           balances[msg.sender] = 0;  // reentrancy: state updated after external call
       }
   }
   ```
   Commit and push:
   ```bash
   git add contracts/Vulnerable.sol
   git commit -m "Add vulnerable contract"
   git push -u origin add-contract
   ```

4. **Open a Pull Request** on GitHub:
   - In the repo, click **Compare & pull request** for `add-contract`, or go to **Pull requests → New pull request**.
   - Base: `main`, compare: `add-contract`.
   - Click **Create pull request**.

5. **What happens next**:
   - GitHub sends a `pull_request` event (action `opened`) to your **Payload URL**.
   - Your backend receives it, fetches the PR diff, runs the OpenClaw agent on the diff, and posts the audit as a **comment on that PR**.
   - If the audit finds vulnerabilities and the report includes a **## Patched code** section with a Solidity block, and the PR changes **exactly one** `.sol` file, the app will **create a remediation PR** (branch `clawaudit-fix-pr-<number>`) with the patched code and post a second comment linking to it. The developer can review and merge that PR to apply the fix.
   - A short PR update is also posted to your Moltbook submolt.

6. **Check the PR**:
   - Refresh the PR page; you should see a new comment from the bot with the security report (may take 1–2 minutes).
   - If a fix was suggested, you should also see a second comment with a link to the **ClawAudit: suggested fix** PR. Open that PR to review and merge the patched code.
   - If nothing appears, check **Recent Deliveries** in **Settings → Webhooks → your webhook** for the request and response (e.g. 200 vs 5xx).

---

## 5. Test “synchronize” (optional)

When you **push new commits** to the same PR branch, GitHub sends a `synchronize` event. Your app will run again and post a **new** comment with the updated diff audit.

```bash
# Edit contracts/Vulnerable.sol, then:
git add contracts/Vulnerable.sol
git commit -m "Fix typo"
git push
```

Refresh the PR; you should see another audit comment.

---

## Quick checklist

| Step | You do | App does |
|------|--------|----------|
| 1 | Expose backend (deploy or ngrok) | — |
| 2 | Add webhook in repo Settings | — |
| 3 | Set `GITHUB_TOKEN` in `.env`, restart backend | — |
| 4 | Create repo, add branch with contract code, **open a PR** | Receives webhook → audits diff → **posts comment on the PR** |
| 5 | (Optional) Push more commits to the PR branch | Receives `synchronize` → audits new diff → posts another comment |

So: **you create the repo and the PR; the program only runs when GitHub sends the webhook and then posts the audit as a comment on that PR.**
