/**
 * Cloudflare Worker: LINE Webhook ハンドラー
 *
 * 処理フロー:
 *   1. X-Line-Signature ヘッダーで HMAC-SHA256 署名を検証
 *   2. events[].message.text から「👍N」「👎N」パターンをパース
 *   3. KV の last_articles から記事情報を照合
 *   4. KV の preferences にフィードバックを追記（最大 MAX_HISTORY 件）
 *   5. 200 OK を返す（LINE は 200 以外でリトライするため必須）
 *
 * KV バインディング名: KV
 * Cloudflare Secret: LINE_CHANNEL_SECRET
 */

const MAX_HISTORY = 100;
const FEEDBACK_RE = /^([👍👎])(\d+)$/u;

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
 * @param {Request} request
 * @param {{ KV: KVNamespace, LINE_CHANNEL_SECRET: string }} env
 */
export default {
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

      await handleFeedback(env.KV, feedback.action, feedback.index).catch((err) => {
        console.error("handleFeedback error:", err);
      });
    }

    return new Response("OK", { status: 200 });
  },
};

/**
 * フィードバックを KV に記録する。
 * @param {KVNamespace} kv
 * @param {"good" | "bad"} action
 * @param {number} articleIndex - 1-indexed
 */
async function handleFeedback(kv, action, articleIndex) {
  // last_articles から記事情報を取得
  const lastArticlesRaw = await kv.get("last_articles");
  if (!lastArticlesRaw) {
    console.warn("last_articles not found in KV");
    return;
  }
  const lastArticles = JSON.parse(lastArticlesRaw);
  const article = lastArticles[String(articleIndex)];
  if (!article) {
    console.warn(`Article index ${articleIndex} not found in last_articles`);
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
