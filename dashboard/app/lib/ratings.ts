const LS_KEY = "article_ratings";

export function getRatings(): Record<string, "good" | "bad"> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function setRating(url: string, action: "good" | "bad" | null): void {
  if (typeof window === "undefined") return;
  const ratings = getRatings();
  if (action === null) {
    delete ratings[url];
  } else {
    ratings[url] = action;
  }
  window.localStorage.setItem(LS_KEY, JSON.stringify(ratings));
}
