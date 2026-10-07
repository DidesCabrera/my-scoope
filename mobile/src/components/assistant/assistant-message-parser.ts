export type AssistantTextBlock =
  | { kind: "heading"; level: number; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "quote"; text: string }
  | { kind: "unordered-item"; text: string }
  | { kind: "ordered-item"; number: string; text: string };

const HEADING = /^ {0,3}(#{1,3})\s+(.+?)\s*#*$/;
const UNORDERED_ITEM = /^\s*[-+*]\s+(.+)$/;
const ORDERED_ITEM = /^\s*(\d+)[.)]\s+(.+)$/;
const QUOTE = /^\s*>\s?(.*)$/;

export function parseAssistantText(source: string): AssistantTextBlock[] {
  const blocks: AssistantTextBlock[] = [];
  const paragraph: string[] = [];
  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push({ kind: "paragraph", text: paragraph.join("\n") });
    paragraph.length = 0;
  };

  for (const line of source.replace(/\r\n?/g, "\n").split("\n")) {
    if (!line.trim()) {
      flushParagraph();
      continue;
    }
    const heading = line.match(HEADING);
    const unordered = line.match(UNORDERED_ITEM);
    const ordered = line.match(ORDERED_ITEM);
    const quote = line.match(QUOTE);
    if (heading) {
      flushParagraph();
      blocks.push({ kind: "heading", level: heading[1].length, text: heading[2] });
    } else if (unordered) {
      flushParagraph();
      blocks.push({ kind: "unordered-item", text: unordered[1] });
    } else if (ordered) {
      flushParagraph();
      blocks.push({ kind: "ordered-item", number: ordered[1], text: ordered[2] });
    } else if (quote) {
      flushParagraph();
      blocks.push({ kind: "quote", text: quote[1] });
    } else {
      paragraph.push(line);
    }
  }
  flushParagraph();
  return blocks;
}
