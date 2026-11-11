import { useEffect, useState } from "react";

import { type SearchSuggestionResult, visibleSearchSuggestions } from "./search-suggestion-state";

export function useSearchSuggestions<T>({ enabled, load, query, submittedQuery }: {
  enabled: boolean;
  load(search: string): Promise<T[]>;
  query: string;
  submittedQuery: string;
}): T[] {
  const [result, setResult] = useState<SearchSuggestionResult<T>>({ search: "", items: [] });

  useEffect(() => {
    const search = query.trim();
    if (!enabled || !search || search === submittedQuery) return;
    let active = true;
    const timer = setTimeout(() => {
      void load(search)
        .then((items) => { if (active) setResult({ search, items }); })
        .catch(() => { if (active) setResult({ search, items: [] }); });
    }, 180);
    return () => { active = false; clearTimeout(timer); };
  }, [enabled, load, query, submittedQuery]);

  return visibleSearchSuggestions(result, query, submittedQuery);
}
