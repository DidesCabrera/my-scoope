// This file is generated from design/ui-contract.json. Do not edit by hand.
export const tokens = {
  "contract": "myscoope.visual-grammar.v2",
  "mode": "dark",
  "color": {
    "surfaceApp": "#000000",
    "surfacePage": "#121212",
    "surfaceCard": "#121212",
    "surfaceMuted": "#202020",
    "surfaceElevated": "#242424",
    "textMain": "#F5F5F5",
    "textMuted": "#B5B5B5",
    "textSoft": "#8F8F8F",
    "textSubtle": "#737373",
    "entityIconForeground": "#FFFFFF",
    "structuralIndicatorForeground": "#FFFFFF",
    "borderSoft": "#2A2A2A",
    "borderDefault": "#343434",
    "borderStrong": "#4A4A4A",
    "interactivePrimary": "#8AB4FF",
    "interactivePressed": "#A9C8FF",
    "danger": "#FF6B6B",
    "success": "#01E888",
    "warning": "#FFD16E",
    "kcalSurface": "#26211D",
    "kcalBorder": "#5A4031",
    "allocationBarTrack": "#313131",
    "allocationPanelTrack": "#313131",
    "protein": "#00D0F5",
    "carbs": "#01E888",
    "fat": "#BBFF00",
    "quantity": "#FFFB82",
    "ppk": "#FFD16E",
    "ppkMuted": "#FFB69F",
    "food": "#FF8800",
    "meal": "#CF34B0",
    "dailyPlan": "#7C4DDB",
    "dpm": "#0084A2",
    "program": "#3A86FF",
    "proposal": "#121212",
    "inbox": "#121212",
    "comparator": "#3057FF",
    "home": "#121212",
    "profile": "#121212"
  },
  "spacing": {
    "xs": 4,
    "compact": 6,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 22,
    "xxl": 28,
    "screen": 18
  },
  "radius": {
    "sm": 8,
    "md": 12,
    "lg": 16,
    "card": 22,
    "pill": 999
  },
  "type": {
    "hero": 34,
    "title": 26,
    "section": 20,
    "body": 16,
    "caption": 13,
    "label": 12
  },
  "weight": {
    "regular": "400",
    "medium": "500",
    "semibold": "600",
    "bold": "700",
    "extraBold": "800",
    "black": "900"
  },
  "card": {
    "outerPadding": 18,
    "innerPadding": 14,
    "gap": 12
  }
} as const;

export const font = {
  "regular": "System",
  "medium": "System",
  "semibold": "System",
  "bold": "System"
} as const;

export type VisualTokens = typeof tokens;
