# Suplementos

Status: local implementation, pending staging integration

Suplementos are a Pro-only personal library. They are informational and never
contribute to nutritional totals. A DailyPlan can contain ordered supplement
intakes alongside meals; each intake has an optional time and one or more
supplements with planned quantities. Intake labels are derived from order.

Users can also save named intake compositions inside the Supplements area.
These presets contain ordered supplement doses but no time. After selecting a
preset while editing a DailyPlan, the user configures the time for that plan
instance and the system copies the composition into a new plan intake. Later
edits or deletion of the preset do not modify DailyPlans that already used it.

An intake's detail lists its supplements. Each supplement opens its own detail
with optional components, description, user-provided information and label
nutrition per default dose. Label nutrition is stored only on the library
supplement: it is not copied into intake snapshots and never contributes to
meal or DailyPlan nutritional totals. A plan containing only supplement
intakes is complete.

Completion is recorded per intake and lived day, using the same whole-item
criterion as meals. Meal and supplement panels and completion summaries are
mutually exclusive in the UI. Non-Pro users retain their data, but supplement
buttons open the Pro upsell and do not expose the stored content.

Rollout is controlled by `SUPPLEMENTS_FEATURE_ENABLED`, disabled by default.
Enabling it exposes the capability only to Pro users. Turning it off again
closes API and mobile access without changing stored records. Both migrations
can be applied and reversed on a disposable database, but reversing the model
migration after real users create supplements would delete their data. For a
deployed rollback, turn off the switch and keep the tables.

Supported use units: capsule, tablet, softgel, gummy, sachet, scoop, drop, ml,
g, mg, mcg, IU, and teaspoon. Components are optional informational lines in g,
mg, mcg, ml, or IU.
The separate form field uses capsule, tablet, softgel, gummy, sachet, powder,
liquid, or drop; it never determines nutrition or converts a dose automatically.
The same physical product may be entered separately as Food and Supplement;
this version does not link or synchronize those entries.

Unit choices are based on common oral supplement forms and label conventions
described by the [FDA](https://www.fda.gov/consumers/consumer-updates/fda-101-dietary-supplements)
and [NIH ODS](https://ods.od.nih.gov/HealthInformation/ODS_Frequently_Asked_Questions.aspx).
No conversion between units or medical benefit claim is inferred by the app.
