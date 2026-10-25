# Journey spec: Produce-led onboarding (first 28 days)

Written in the structure CleverTap and WebEngage use for journeys (entry trigger → audience → steps → exit → goal), so it can be built in either tool. Events and properties match `data/mixpanel_events.csv`.

## Setup

| Field | Value |
|---|---|
| Journey name | `ONB_produce_led_v1` |
| Entry trigger | `Order Placed` where `order_number = 1` |
| Audience | First-time buyers, Bengaluru + Hyderabad, all channels |
| Split | 45% treatment (this journey) · 45% control (current gift-led onboarding) · 10% global holdout (no onboarding messages) |
| Primary goal (conversion event) | `Order Placed` where `order_number = 3` within 28 days of entry |
| Guardrails | Avg order value, gift + credit cost per buyer, unsubscribe rate, CX tickets per 100 orders |
| Exit criteria | Goal reached · 28 days passed · user unsubscribes · open CX complaint (route to service recovery instead) |
| Frequency cap | Max 1 push + 1 WhatsApp per 48 h; quiet hours 21:00–08:00 |

## What changes vs today

| | Control: gift-led (today) | Treatment: produce-led |
|---|---|---|
| Order 1 | Free gift | Free gift (unchanged: the "aha" moment stays) |
| Order 2 | Free gift | ₹60 credit on a basket with fresh produce + quality guarantee message |
| Order 3 | Free gift | No incentive; habit message ("your weekly fruit & veg") |
| Messaging | Generic offers | Freshness proof: what was screened, sweetness checks, lab tests |

## Steps

| # | When | Condition | Channel | Message (draft) | Why |
|---|---|---|---|---|---|
| 1 | Order 1 delivered + 2 h | Always | In-app card | "Tasted the difference? Every mango we sell is sweetness-checked. Here's what we tested this week." | Reinforce the quality promise right after the first experience |
| 2 | Day 3 | No 2nd order yet | Push | "Your fruit & veg, picked this morning. ₹60 off your next basket with fresh produce." | Pull the 2nd order forward with the category that builds habit |
| 3 | Day 3 | 2nd order placed | Skip to step 5 | — | Don't message people who already converted |
| 4 | Day 7 | Still no 2nd order | WhatsApp | "Weekend fruit box? Your ₹60 produce credit expires in 3 days." | Deadline on the only incentive |
| 5 | Day 10 after order 2 | No 3rd order yet | Push | "Make it weekly: add your staples to Sunday's fruit & veg order." | Basket width + routine, no discount |
| 6 | Day 21 | Still < 3 orders | In-app + email | "Not quite right last time? Reply and we'll fix it." | Catch quality issues before they become churn |
| 7 | Any time | `CX complaint` event | Exit → service recovery journey | — | A trust problem needs a person, not a promo |

## Readout plan

- **Sample size:** ~2,450 buyers per arm to detect a +4 pt change in the 3rd-order rate (80% power, 5% significance). With 90% of FirstClub's ~3,270 new households a week in the two test arms, that's ~1.7 weeks of enrolment plus the 28-day window, so about 6 weeks.
- **Decision rule:** ship if the lift's 95% interval stays above the break-even line and guardrails hold. The break-even line is below zero (produce-led is cheaper), so a flat result can still be a win on cost.
- **Query:** `sql/05_experiment_readout.sql`.
