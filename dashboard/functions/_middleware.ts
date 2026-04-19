interface Env {
  DASHBOARD_SECRET?: string;
}

const REALM = "Tech Article Dashboard";

function unauthorized(): Response {
  return new Response("Unauthorized", {
    status: 401,
    headers: { "WWW-Authenticate": `Basic realm="${REALM}"` },
  });
}

export const onRequest: PagesFunction<Env> = async ({ request, env, next }) => {
  const secret = env.DASHBOARD_SECRET;
  if (!secret) {
    return next();
  }

  const authHeader = request.headers.get("Authorization");
  if (!authHeader?.startsWith("Basic ")) {
    return unauthorized();
  }

  const encoded = authHeader.slice(6);
  const decoded = atob(encoded);
  const colonIdx = decoded.indexOf(":");
  const password = colonIdx >= 0 ? decoded.slice(colonIdx + 1) : decoded;

  if (password !== secret) {
    return unauthorized();
  }

  return next();
};
