# Fast AI Copilot for a live presentation

## What changed
- The AI provider request timeout defaults to **9 seconds**, instead of 90 seconds.
- A successful **exact same request** is cached in the running server for up to **1 hour** (max 128 entries), so a repeat is instant. The cache key includes the farm/field context, conversation, provider configuration and model. No cross-farm cached answers.
- If the primary provider fails or times out, the optional backup provider is attempted immediately. There is **no repeated wait on a failing provider**.
- Backend errors no longer display the entire provider URL or key.
- No fake AI answers are generated. If all providers fail, the UI reports an error rather than presenting invented content.

## Render environment
```text
AI_PRIMARY_PROVIDER=gemini
AI_PRIMARY_MODEL=<model ID confirmed by your Google AI Studio project>
AI_PRIMARY_API_KEY=<your secret key>
AI_REQUEST_TIMEOUT_SECONDS=9
```

Optional **backup**, if you have access to a second AI provider:
```text
AI_BACKUP_PROVIDER=openai
AI_BACKUP_MODEL=<supported model ID>
AI_BACKUP_API_KEY=<secret backup key>
```

Do not put keys in GitHub, screenshots, frontend files or chat.

## Recommended live-demo runbook
1. Before presenting, open the deployed site and verify Render reports **Live** for the latest commit.
2. Sign in and open a **test farm**. Open the exact field you will show.
3. Ask the 2–3 questions you intend to demonstrate **once before the presentation**. Their answers will be cached if the server process stays running and the request context is unchanged.
4. During the presentation, use the **same questions, same field and same conversation history** to receive cached answers. If history differs, it is a new request.
5. Keep the browser tab open. A Render Free instance may sleep/restart, losing the in-memory cache; this cannot be guaranteed by software alone.
6. Keep a screenshot of a previously verified answer as a **clearly labelled backup slide**. Do not present a screenshot as a live API response.
7. If the provider is overloaded, the app fails fast rather than waiting 90 seconds. A backup provider requires separately configured credentials.

## Caveat
The first-ever AI response still needs a network call; there is no guarantee of instant Gemini availability. For a no-wait live demonstration, use previously prepared screenshots or a controlled, explicitly labelled demo playback. A paid always-on Render service and a second AI provider reduce risk but cannot guarantee zero latency.
