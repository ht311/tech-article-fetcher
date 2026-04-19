"use client";

import { useEffect, useState } from "react";

export interface CategoryMeta {
  id: string;
  name: string;
}

export function useCategories(): CategoryMeta[] {
  const [categories, setCategories] = useState<CategoryMeta[]>([]);

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json() as Promise<{ category_defs?: CategoryMeta[] }>)
      .then((data) => {
        if (data.category_defs && data.category_defs.length > 0) {
          setCategories(data.category_defs);
        }
      })
      .catch(() => {});
  }, []);

  return categories;
}

export function categoryLabel(categories: CategoryMeta[], id: string | null): string {
  if (!id) return "その他";
  return categories.find((c) => c.id === id)?.name ?? id;
}
