import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const source = fs.readFileSync(
  path.join(process.cwd(), "src/components/ui/typography.tsx"),
  "utf8",
);

test("section headings place supporting labels below the title", () => {
  const styles = source.slice(source.indexOf("sectionHeading:"));
  const sectionHeading = styles.slice(0, styles.indexOf("sectionIdentity:"));

  assert.match(sectionHeading, /alignItems: "stretch"/);
  assert.match(sectionHeading, /gap: tokens\.spacing\.xs/);
  assert.doesNotMatch(sectionHeading, /flexDirection: "row"/);
  assert.doesNotMatch(sectionHeading, /justifyContent: "space-between"/);
  assert.match(source, /sectionDetail: \{[^}]*textAlign: "left"/);
});
