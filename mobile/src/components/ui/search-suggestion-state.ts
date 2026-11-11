export type SearchSuggestionResult<T> = { search: string; items: T[] };

export function visibleSearchSuggestions<T>(
  result: SearchSuggestionResult<T>,
  query: string,
  submittedQuery: string,
): T[] {
  const search = query.trim();
  return search && search !== submittedQuery && result.search === search ? result.items : [];
}
