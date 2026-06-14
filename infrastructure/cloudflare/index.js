/**
 * Cloudflare Worker: LINE Webhook ハンドラー + 日次フェッチ Cron Trigger
 *
 * 処理フロー（fetch ハンドラー）:
 *   1. X-Line-Signature ヘッダーで HMAC-SHA256 署名を検証
 *   2. events[].message.text から「👍N」「👎N」パターンをパース
 *   3. KV の last_articles から記事情報を照合
 *   4. KV の preferences にフィードバックを追記（最大 MAX_HISTORY 件）
 *   5. LINE Reply API で確認メッセージを返信
 *   6. 200 OK を返す（LINE は 200 以外でリトライするため必須）
 *
 * 処理フロー（scheduled ハンドラー）:
 *   Cron Trigger（23:15 UTC = JST 8:15）で発火し、GitHub workflow_dispatch API を呼び出して
 *   daily-fetch.yml を起動する。GitHub Actions の schedule 遅延（40〜70分）を回避するための仕組み。
 *
 * KV バインディング名: KV
 * Cloudflare Secret: LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, GITHUB_TOKEN
 */

// These values must match src/core/constants.py (MAX_HISTORY) and src/core/kv_keys.py (key names).
const MAX_HISTORY = 100;
const FEEDBACK_RE = /^([👍👎])(\d+)$/u;
const LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply";

const GH_DISPATCH_URL =
  "https://api.github.com/repos/ht311/tech-article-fetcher/actions/workflows/daily-fetch.yml/dispatches";

/**
 * HMAC-SHA256 で LINE の署名を検証する。
 * @param {string} channelSecret
 * @param {string} body - リクエストボディ（生テキスト）
 * @param {string} signature - X-Line-Signature ヘッダー値（Base64）
 * @returns {Promise<boolean>}
 */
async function verifySignature(channelSecret, body, signature) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(channelSecret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signed = await crypto.subtle.sign("HMAC", key, encoder.encode(body));
  const expected = btoa(String.fromCharCode(...new Uint8Array(signed)));
  return expected === signature;
}

/**
 * フィードバックテキスト（例: 「👍1」「👎3」）をパースする。
 * @param {string} text
 * @returns {{ action: "good" | "bad", index: number } | null}
 */
function parseFeedback(text) {
  const trimmed = text.trim();
  const match = trimmed.match(FEEDBACK_RE);
  if (!match) return null;
  const emoji = match[1];
  const index = parseInt(match[2], 10);
  if (isNaN(index) || index < 1) return null;
  return { action: emoji === "👍" ? "good" : "bad", index };
}

/**
 * LINE Reply API でメッセージを返信する。
 * @param {string} channelAccessToken
 * @param {string} replyToken
 * @param {string} text
 */
async function replyMessage(channelAccessToken, replyToken, text) {
  const res = await fetch(LINE_REPLY_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${channelAccessToken}`,
    },
    body: JSON.stringify({
      replyToken,
      messages: [{ type: "text", text }],
    }),
  });
  if (!res.ok) {
    const body = await res.text();
    console.error(`LINE Reply API error: ${res.status} ${body}`);
  }
}

/**
 * GitHub Actions の workflow_dispatch API を呼び出して daily-fetch.yml を起動する。
 * GitHub Actions の schedule 遅延（毎日 40〜70 分）を回避するために Cron Trigger から使用する。
 * @param {string} token - GitHub Fine-grained PAT（Actions: Read and write）
 */
async function dispatchWorkflow(token) {
  const res = await fetch(GH_DISPATCH_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "tech-article-fetcher-cron",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref: "main" }),
  });
  if (!res.ok) {
    console.error(`workflow_dispatch failed: ${res.status} ${await res.text()}`);
  } else {
    console.log("workflow_dispatch: daily-fetch.yml triggered successfully");
  }
}

/**
 * @param {Request} request
 * @param {{ KV: KVNamespace, LINE_CHANNEL_SECRET: string, LINE_CHANNEL_ACCESS_TOKEN: string, GITHUB_TOKEN: string }} env
 */
export default {
  /**
   * Cron Trigger（23:15 UTC = JST 8:15）で発火し、daily-fetch.yml を workflow_dispatch で起動する。
   * @param {ScheduledEvent} event
   * @param {object} env
   * @param {ExecutionContext} ctx
   */
  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatchWorkflow(env.GITHUB_TOKEN));
  },

  async fetch(request, env) {
    // LINE は GET でヘルスチェックすることがある
    if (request.method !== "POST") {
      return new Response("OK", { status: 200 });
    }

    const body = await request.text();
    const signature = request.headers.get("X-Line-Signature") ?? "";

    // 署名検証
    const isValid = await verifySignature(env.LINE_CHANNEL_SECRET, body, signature);
    if (!isValid) {
      return new Response("Unauthorized", { status: 401 });
    }

    let payload;
    try {
      payload = JSON.parse(body);
    } catch {
      return new Response("Bad Request", { status: 400 });
    }

    // 各イベントを処理（エラーが出ても 200 を返す）
    for (const event of payload.events ?? []) {
      if (event.type !== "message" || event.message?.type !== "text") continue;
      const text = event.message.text ?? "";
      const feedback = parseFeedback(text);
      if (!feedback) continue;

      const replyToken = event.replyToken;

      await handleFeedback(env.KV, feedback.action, feedback.index, replyToken, env.LINE_CHANNEL_ACCESS_TOKEN).catch((err) => {
        console.error("handleFeedback error:", err);
      });
    }

    return new Response("OK", { status: 200 });
  },
};

/**
 * フィードバックを KV に記録し、ユーザーに返信する。
 * @param {KVNamespace} kv
 * @param {"good" | "bad"} action
 * @param {number} articleIndex - 1-indexed
 * @param {string} replyToken
 * @param {string} channelAccessToken
 */
async function handleFeedback(kv, action, articleIndex, replyToken, channelAccessToken) {
  // last_articles から記事情報を取得
  const lastArticlesRaw = await kv.get("last_articles");
  if (!lastArticlesRaw) {
    console.warn("last_articles not found in KV");
    if (replyToken) {
      await replyMessage(channelAccessToken, replyToken, "フィードバックを受け取りましたが、記事情報が見つかりませんでした。");
    }
    return;
  }
  const lastArticles = JSON.parse(lastArticlesRaw);
  const article = lastArticles[String(articleIndex)];
  if (!article) {
    console.warn(`Article index ${articleIndex} not found in last_articles`);
    if (replyToken) {
      await replyMessage(channelAccessToken, replyToken, "フィードバックを受け取りましたが、記事情報が見つかりませんでした。");
    }
    return;
  }

  // preferences を読み込んで履歴に追記
  const prefsRaw = await kv.get("preferences");
  const prefs = prefsRaw ? JSON.parse(prefsRaw) : { history: [] };
  if (!Array.isArray(prefs.history)) prefs.history = [];

  prefs.history.push({
    action,
    title: article.title,
    source: article.source,
    url: article.url,
    timestamp: new Date().toISOString(),
  });

  // 最大件数を超えた場合は古いものを削除
  if (prefs.history.length > MAX_HISTORY) {
    prefs.history = prefs.history.slice(-MAX_HISTORY);
  }

  await kv.put("preferences", JSON.stringify(prefs));
  console.log(`Recorded ${action} for article ${articleIndex}: ${article.title}`);
}
