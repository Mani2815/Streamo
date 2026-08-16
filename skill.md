# Streamo UI Engineering Skill

## Purpose

Design and implement a production-quality UI/UX for Streamo, a real-time data engineering and analytics platform.

The goal is to transform Streamo from a functional prototype dashboard into a polished, professional data platform interface suitable for:

- University project demonstrations
- Technical presentations
- Portfolio/GitHub showcase
- Data engineering interviews
- Live demonstrations

The UI must communicate that Streamo is a serious real-time data engineering platform, not a generic CRUD dashboard.

---

# 1. Core Principle

Treat Streamo as a product.

Do NOT make isolated visual changes page-by-page.

Create one coherent visual system shared across:

- Overview
- Sources
- Analytics
- Data Quality

All pages must feel like the same application.

---

# 2. Existing Architecture Must Be Preserved

Before modifying anything, inspect the repository.

Important existing technologies:

- FastAPI
- Python
- Apache Kafka
- Apache Spark Structured Streaming
- PostgreSQL
- MinIO
- Apache Airflow
- Grafana
- Docker Compose
- Vanilla HTML
- CSS
- JavaScript

Do NOT replace the frontend with React/Vue/etc. unless explicitly requested.

Do NOT rewrite backend APIs merely to improve UI.

The frontend must consume the existing APIs.

---

# 3. First Audit the Existing Frontend

Inspect:

- frontend HTML files
- CSS
- JavaScript
- API calls
- chart implementation
- navigation
- source selector
- loading states
- empty states
- error handling
- responsive behavior

Identify:

- duplicated styles
- hardcoded values
- inconsistent spacing
- inconsistent typography
- weak hierarchy
- unnecessary whitespace
- poor responsive behavior
- stale state
- confusing navigation
- misleading metrics
- fake/static data

Create a short UI audit before implementation.

---

# 4. Visual Direction

Use a modern data-platform aesthetic.

Reference the visual language of professional products such as:

- Datadog
- Grafana
- Vercel
- Linear
- Stripe
- modern cloud monitoring dashboards

Do NOT copy any product directly.

Streamo should have its own identity.

---

# 5. Design System

Create a centralized design system using CSS variables.

Example:

```css
:root {
  --bg-primary: ...;
  --bg-secondary: ...;
  --surface: ...;
  --surface-elevated: ...;
  --border: ...;
  --text-primary: ...;
  --text-secondary: ...;
  --text-muted: ...;
  --accent: ...;
  --success: ...;
  --warning: ...;
  --danger: ...;
}

6. Color Direction

Move away from the current overwhelming solid-blue sidebar.

Use:

dark navy / midnight as the primary brand color
warm off-white or very light neutral backgrounds
subtle borders
restrained accent colors
green for healthy states
amber for warnings
red for failures
blue/indigo for primary actions

The interface should feel calm and professional.

Avoid excessive saturated blue.

7. Typography

Create clear hierarchy:

Product name
Page title
Page description
Section heading
Metric value
Metric label
Supporting metadata

Use a modern sans-serif font.

Avoid excessive bold text.

Metric values should be visually dominant.

Labels should be smaller and quieter.

8. Layout

Use a consistent application shell:

┌──────────────────────────────────────────────┐
│ Streamo                         Source ▾     │
├──────────────┬───────────────────────────────┤
│              │                               │
│ Overview     │ Page heading                  │
│ Sources      │ Description                   │
│ Analytics    │                               │
│ Data Quality │ Content                       │
│              │                               │
│              │                               │
└──────────────┴───────────────────────────────┘

Sidebar:

compact
clean
clear active state
icons where useful
no giant empty blue area

Main content:

max-width container
consistent spacing
responsive grid
meaningful information density
9. Application Header

Create a proper header.

Include:

Streamo branding
current page title
selected data source
system/pipeline status
optional refresh control

The source selector should look like a professional application control, not a basic HTML dropdown.

10. Overview Page

The Overview page should answer:

"What is happening in my data platform right now?"

Recommended structure:

Header
Overview
Real-time health and activity across your data pipelines
KPI row

Show:

Active Sources
Total Records
Average Quality
Pipeline Health

Each KPI should include:

value
label
small supporting context
trend/status where available
Pipeline health

Show source-level status using:

healthy
warning
error
inactive
Activity section

Show:

recent ingestion activity
record volume
latest ingestion time
source status
Insight section

Surface meaningful system observations.

Do not fill empty areas with decorative elements.

11. Sources Page

The Sources page should feel like a data-source management console.

Show:

source name
source type
endpoint
status
last ingestion
records
quality
actions

Provide a clear:

+ Add Data Source

button.

The add-source flow should use a modal/drawer rather than an awkward page transition if compatible with the current architecture.

Clearly separate:

source configuration
validation
connection status
12. Analytics Page

Analytics is one of Streamo's most important pages.

It should feel like a real analytics workspace.

Structure:

Analytics
Source / Dataset
Time range


┌────────┬────────┬────────┬────────┐
│Records │Metrics │Quality │Freshness│
└────────┴────────┴────────┴────────┘


┌─────────────────────────────────────┐
│ Main trend chart                    │
└─────────────────────────────────────┘


┌──────────────────┬──────────────────┐
│ Metric analysis  │ Dimensions       │
└──────────────────┴──────────────────┘


┌─────────────────────────────────────┐
│ Generated insights                  │
└─────────────────────────────────────┘

Charts must be readable.

Use proper:

axes
labels
tooltips
legends
empty states

Avoid decorative charts that do not communicate data.

13. Data Quality Page

The current Data Quality page is too empty.

Redesign it as a real quality-monitoring workspace.

Top KPI cards:

Quality Rate
Valid Records
Invalid Records
Total Records

Then:

Quality Breakdown
────────────────────────────────


Null violations
Range violations
Format violations

Use a visual breakdown.

For example:

progress bars
compact bar chart
donut chart where appropriate

Then include:

Quality issues

Show the actual violations when available.

Example:

Range violation
humidity
Expected: 0–100
Observed: 150
Records: 1

For zero records:

Quality Rate
—
No records available for this source

Never display 100% for an empty source.

14. Real-Time State

The UI must clearly distinguish:

loading
live
stale
empty
error

Use small status indicators.

Example:

● Live
● Updating
● Stale

Do not pretend data is real-time if it isn't.

15. Source Switching

Source selection is global state.

When the user changes source:

immediately clear old metrics
show loading state
fetch new source data
update all relevant components
remove stale values

Never allow:

Sales selected
↓
Weather selected
↓
Sales metrics remain visible

This is a critical correctness requirement.

16. Empty States

Empty states must be intentional.

Bad:

blank page

Good:

No records yet


This source has not produced any records.


[Refresh]

For no sources:

No data sources configured


Connect your first API to start streaming data.


[Add Data Source]
17. Error States

Errors should be visible and understandable.

Example:

Unable to load analytics


The selected source could not be reached.


[Retry]

Do not expose raw stack traces to users.

Log technical details to the console/backend logs.

18. Loading States

Use skeleton loaders instead of jumping from:

0

to:

154,203

Use:

skeleton cards
chart placeholders
table placeholders

Avoid excessive spinners.

19. Responsive Design

The application must work on:

desktop
laptop
tablet

The dashboard should not depend on a fixed 1600px layout.

Use:

grid-template-columns
minmax()
clamp()
flex

where appropriate.

20. Accessibility

Ensure:

sufficient contrast
keyboard navigation
visible focus states
semantic HTML
labels for form controls
accessible buttons
chart descriptions where practical
21. Performance

Do not repeatedly fetch the same endpoint unnecessarily.

Use:

controlled polling
request cancellation
debouncing where appropriate
efficient DOM updates

Do not introduce a large frontend framework merely for state management.

22. Data Integrity

Never invent metrics.

Every displayed value must originate from:

existing API response
calculated frontend value based on actual API data
clearly identified derived metric

Do not hardcode:

100%
50,000 records
99.8%

unless they are actual test/demo data.

23. Do Not Overdesign

Avoid:

excessive gradients
giant cards
huge empty spaces
unnecessary animations
excessive shadows
decorative illustrations
excessive rounded corners
excessive neon colors
dashboard clutter

The visual goal is:

Dense enough for a professional data platform, but calm enough to understand immediately.

24. Implementation Process

Follow this order:

Phase A

Audit existing frontend.

Phase B

Create design tokens.

Phase C

Redesign application shell/navigation.

Phase D

Redesign Overview.

Phase E

Redesign Sources.

Phase F

Redesign Analytics.

Phase G

Redesign Data Quality.

Phase H

Fix loading/empty/error states.

Phase I

Fix responsive behavior.

Phase J

Regression-test all existing API functionality.

25. Regression Requirements

After UI changes verify:

/
source loading
source creation
source validation
source switching
analytics
data quality
records
charts
refresh
API errors
empty sources

Do not consider the redesign complete if only the visual appearance works.

26. Final Quality Standard

Before declaring completion, ask:

Does this look like a professional data platform?
Is the current source obvious?
Can a user understand pipeline health in 5 seconds?
Can a user understand data quality in 5 seconds?
Are charts useful rather than decorative?
Are empty/loading/error states clear?
Does every page feel visually related?
Does the UI remain functional with real API data?
Is stale state impossible?
Does the UI look good without requiring a screenshot-specific layout?

The final result should feel like:

Streamo — a professional real-time data engineering control and analytics platform.