# Hassas (حساس)

> _Hassas — the sensor for your sensitivities._

A multi-agent system that people experience as a single chat companion in the messaging apps they already use (Telegram first, WhatsApp next), helping them find the hidden food triggers behind their reactions.

The name is Arabic and means both **"sensitive"** and **"sensor"**: Hassas is sensitive to every detail, so you don't have to be.

---

## 1. The problem

People react to something they ate (hives, swelling, gut symptoms) but can't find the cause.

**User problems**

1. **Unexplained reactions.** Recurring symptoms after eating, with no identified trigger.
2. **Most people never get diagnosed.** About half of adults with convincing food allergies have never seen a doctor about them. They guess and avoid foods, often the wrong ones.
3. **Food diaries are too tedious.** Allergists ask for a detailed food and symptom diary, but almost no one keeps it complete.
4. **Doctors get vague histories.** "I think it happens after seafood sometimes" is hard to act on.
   **Why it's hard**
5. **Hidden ingredients.** People log dishes ("a burger," "pad thai"), not ingredients. The trigger may be a component they don't know is there: anchovies in Caesar dressing, peanuts in a satay sauce, pine nuts in pesto, milk in a burger bun, shared frying oil.
6. **Delayed reactions.** Symptoms can appear hours later (e.g. alpha-gal syndrome, 2–6+ hours after red meat), so the last meal is often the wrong suspect.
7. **Everyday foods mislead.** Bread and coffee appear before every reaction without being the cause; simple counting blames them.
8. **Cofactors.** Some reactions only happen with exercise, alcohol, painkillers or illness.
9. **Small, noisy personal data.** Each person has few reactions and imperfect logs.

**Context** 10. **Existing tools only know part of what people eat.** Most apps are built around English-language food databases and Western packaged products, leaving out home cooking, local restaurants and international dishes — exactly where hidden ingredients are hardest to know.

**Scale:** at least 10.8% of US adults have a convincing food allergy, ~19% believe they do, only ~47.5% are physician-diagnosed, and ~48% developed at least one allergy as adults (Gupta et al., JAMA Network Open, 2019).

---

## 2. What Hassas does

- **Natural chat logging** in a messaging app — text or voice notes, in whatever words the user would use with a friend.
  e.g. _"Had a cheeseburger and fries from Joe's, then a latte"_
- **Speaks the user's language** — English, Arabic (any dialect), or a mix.
- **Ingredient research & verification** — turns each dish into its likely ingredients (see below).
- **Targeted follow-up questions** — only when the answer would change the analysis.
  e.g. _"Was that the house dressing or the vinaigrette?"_
- **"Ask the restaurant"** — when an ingredient is uncertain, Hassas drafts a short message the user can send to the restaurant to ask.
- **Lag-aware pattern analysis** (case-crossover design): compares exposures in the 0–8 hours before each reaction against the user's own symptom-free periods, adjusting for everyday foods and cofactors.
- **Uncertainty-aware pattern scoring** — every pattern comes with how strong it is _and_ how sure Hassas is about it (see below).
- **Pattern Summary** — a web page linked from the chat that the user can keep or share with their doctor:
  - reaction timeline with shaded lookback windows
  - ranked table of recurring ingredients, each with its pattern score, uncertainty range and status
  - uncertainty highlights: which patterns depend on unconfirmed ingredients, and which single confirmation would change the picture most
  - evidence trail for the top patterns: which meals contained them, their confidence levels, and where that information came from
  - boundary statement: _"Patterns in your own log, for discussion with a clinician — not a diagnosis."_

### Ingredient research & verification

Hassas doesn't rely on what the model "remembers" about a dish. For every logged meal it:

1. **Searches the web** for the dish, prioritizing the most specific source available:
   1. the restaurant's or brand's own published menu, ingredient or allergen information
   2. packaging and product databases (for packaged foods)
   3. standard recipes for the dish, from several independent sources
2. **Verifies the findings** before they enter the analysis:
   - **Cross-checking** — an ingredient found in several independent sources is trusted more than one found in a single recipe.
   - **Source ranking** — official restaurant or brand information outranks generic recipes.
   - **Confidence level per ingredient** — each ingredient is marked _confirmed_ (official source or user/restaurant confirmation), _likely_ (most sources agree), or _possible_ (some recipes include it).
   - **Conflict flagging** — when sources disagree, the ingredient is flagged instead of silently picked.
   - **Human confirmation** — uncertain ingredients that matter become a follow-up question to the user or an "ask the restaurant" message.
   - **Citations** — every ingredient keeps the source it came from, shown in the Pattern Summary's evidence trail.
3. **Weights the analysis by confidence** — a _possible_ ingredient counts less than a _confirmed_ one, so a guess can never dominate the result.
4. **Remembers verified dishes** — once a dish from a specific place is verified, Hassas reuses it the next time it's logged.
   Research runs in the background: Hassas acknowledges a log instantly and verifies the ingredients afterwards, so logging stays fast.

### Pattern scoring & uncertainty

Ingredient uncertainty isn't hidden or averaged away — it's built into the scoring itself. Hassas separates two kinds of uncertainty and reports both:

- **Data uncertainty** — _were the ingredients really in those meals?_
- **Statistical uncertainty** — _is there enough history to tell a pattern from coincidence?_
  **How an ingredient is scored**

1. **Probabilistic exposure.** Each meal contributes an exposure probability for each ingredient, from its verification level (e.g. _confirmed_ ≈ 1.0, _likely_ ≈ 0.7, _possible_ ≈ 0.3; tunable).
2. **Time-weighted windows.** Exposure before a reaction is weighted by a delay curve across the 0–8 h window, instead of a hard cut-off.
3. **Case vs. control comparison.** Expected exposure in the windows before reactions is compared with matched control windows from the same user's symptom-free periods (e.g. the same time of day on other days). This is what neutralizes everyday foods: if bread is everywhere, it's equally present in both.
4. **Small-data shrinkage.** Scores are pulled toward "no pattern" until the evidence is strong enough to overcome it (a Bayesian prior), so two coincidences can't produce a top result.
5. **Simulating the unknowns.** The analysis is re-run many times, each time randomly deciding whether each uncertain ingredient was present according to its probability (Monte Carlo). This gives every score a **range**, not just a number: a pattern that holds across all simulations is robust; one that appears only when guesses go a certain way is fragile.
6. **Cofactor check.** Each top pattern is also scored with and without cofactors (exercise, alcohol, painkillers), to show when an ingredient only seems to matter in combination.
   **Uncertainty drives the next question.** For the top patterns, Hassas calculates which single unconfirmed ingredient, if confirmed or ruled out, would change the ranking the most — and that becomes its next follow-up question or "ask the restaurant" message. Verification effort goes where it matters most.

**Pattern status** — every ingredient gets one of these labels, in plain language:

| Status                | Meaning                                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------- |
| **Collecting**        | Not enough reactions or symptom-free days yet; no patterns are shown.                    |
| **Emerging pattern**  | A signal is appearing, but the range is wide or it depends on unconfirmed ingredients.   |
| **Strong pattern**    | Consistently present before reactions, robust across simulations, mostly confirmed data. |
| **Can't be assessed** | Present in nearly every window (or almost never), so there's no contrast to learn from.  |
| **Unlikely**          | Eaten often during symptom-free periods without reactions following.                     |

A minimum-evidence threshold (a set number of reactions and symptom-free days) must be met before any pattern above **Collecting** is shown.

---

## 3. How Hassas works

Hassas is a multi-agent system, but users only ever meet **one Hassas** in their chat. Behind it, a small team of components does the work:

| Component                       | Type                            | Role                                                                                                                                                                                                                              |
| ------------------------------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Channel adapters**            | Code                            | Translate each messaging app (Telegram now, WhatsApp later) to and from neutral messages, so nothing else depends on which app the user is in.                                                                                    |
| **Hassas (conversation agent)** | LLM agent                       | The only component the user talks to. Understands meals, symptoms and cofactors from text or voice, holds the personality, asks follow-up questions, drafts "ask the restaurant" messages, and handles severe-symptom escalation. |
| **Research agent**              | LLM agent with web search       | Finds ingredient information for each logged dish, following the source-priority order.                                                                                                                                           |
| **Verification agent**          | LLM agent                       | Independently checks the research agent's findings: cross-checks sources, assigns confidence levels, flags conflicts, and attaches citations.                                                                                     |
| **Analysis engine**             | Deterministic code              | Pattern scoring: case-crossover comparison, delay weighting, shrinkage, Monte Carlo ranges, cofactor checks, statuses, and choosing the most informative next question.                                                           |
| **Summary builder**             | Code (LLM optional for wording) | Generates the Pattern Summary page from the analysis results.                                                                                                                                                                     |

**Flow:** the user logs a meal → Hassas acknowledges instantly → the research and verification agents work in the background → verified ingredients are stored → the analysis engine updates the scores → if an unconfirmed ingredient matters, Hassas asks about it → the Pattern Summary is updated.

**Design decisions**

- **Research and verification are separate agents.** An agent checking its own findings tends to approve them. An independent verifier with its own instructions — prove each ingredient, check every source — is what makes the verification trustworthy.
- **The analysis is code, not an agent.** Scoring must be reproducible: the same log must always produce the same summary, and the benchmark is only meaningful if the engine is deterministic. LLMs handle language and research; code handles statistics.
- **One persona, many components.** Internal agents are never exposed to the user, so the experience stays a conversation with a friend, not a support system.
- **Channel-neutral core.** The conversation is designed around what every supported messaging app can do; app-specific extras (editing a message, mini apps) improve the experience but are never required.

---

## 4. Personality

Hassas is the friend who notices everything — and is a little dramatic about it.

- **Notices what you skip:** _"And the sauce on that burger? Don't hide it from me 👀"_
- **Playfully suspicious of clues:** _"Pesto again? That's the third time before a reaction… I'm getting suspicious."_
- **Brief:** one or two lines per reply. Logging takes seconds.
- **Matches your language and tone.**
  **Where the personality switches off**
- **Never jokes about symptoms.** Reaction reports get a calm, clear response: record details, ask about timing.
- **Serious mode for severe symptoms** (throat swelling, trouble breathing, fainting): all humor stops, and Hassas directs the user to emergency care immediately.
- **Patterns, never diagnosis.** "Pine nuts keep showing up — worth mentioning to your doctor" ✅ / "You're allergic to pine nuts" ❌

---

## 5. Safety principles

These are core design decisions for Hassas, not add-ons:

- **Hassas never diagnoses.** It never says what someone is allergic to.
- **Hassas never gives dietary instructions.** No "avoid X," no diets, no nutrition advice — no calories, macros or diet tips.
- **The output is the user's own data, organized.** Patterns in their log, plus a summary they can take to a clinician, who makes the decisions.
- **Severe symptoms come first.** Anything that sounds like a serious reaction gets an immediate emergency-care referral, before any logging.
- **Honest uncertainty.** Every ingredient carries a confidence level and a source, every pattern carries an uncertainty range and status, and no pattern is shown before the minimum-evidence threshold is met. Hassas never presents a guess as a fact.
- **Careful language.** Hassas talks about "your log," "patterns," and "worth discussing with your doctor" — never "diagnosis," "allergy test," or "safe to eat."
- **Health data is treated as sensitive.** Encrypted storage, minimal access, consent before anything is stored, and clear documentation of how data is handled.

---

## 6. How Hassas is different

Food-and-symptom diary apps already exist. Most of them are standalone apps with forms, barcode scanners and photo logging, use simple correlation or counting, and are built around English and Western packaged food. Hassas takes a different approach:

|                      | **Typical existing apps**                              | **Hassas**                                                                                           |
| -------------------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Where it lives       | A separate app to remember to open                     | Inside a messaging app people already use (Telegram; WhatsApp as premium)                            |
| Logging              | Forms, food databases, barcodes, photos                | Natural conversation, text or voice                                                                  |
| Ingredient knowledge | User entry, a fixed database, or unverified AI guesses | A dedicated research agent + an independent verification agent, with confidence levels and citations |
| Hidden ingredients   | Only what the user knows to enter                      | Actively looks for likely hidden components and cross-reactions                                      |
| Pattern analysis     | Simple correlation or "what you ate before symptoms"   | Case-crossover method: lag-aware, frequency-adjusted, accounts for cofactors                         |
| Uncertainty          | A single score, or none                                | Every pattern has a score, a range and a status; data and statistical uncertainty shown separately   |
| Everyday-food bias   | Usually not addressed                                  | Explicitly corrected                                                                                 |
| Missing information  | Records whatever it's given                            | Asks targeted follow-ups, or helps the user ask the restaurant                                       |
| Languages            | Mostly English                                         | English, Arabic (any dialect), and mixed                                                             |

---

## 7. Validation

A Python simulator generates a few hundred synthetic users, each with:

- a known hidden trigger (often inside a dish)
- realistic reaction delays (0–8 h)
- cofactors (exercise, painkillers, alcohol)
- everyday staples (bread, coffee, milk)
- noisy, incomplete logging
  Hassas's method is compared against **naive counting** (what most existing apps do), measuring how often each finds the true trigger.

Headline result format: _"Naive counting finds the true trigger X% of the time; Hassas finds it Y%."_

Real-world use (people logging their own meals) shows usability; the simulated benchmark shows correctness. Both are needed.

---

## 8. Channels

- **Telegram is the first channel.** Its Bot API is free, has no 24-hour messaging window or per-message fees, and needs no business verification — ideal for development and an open beta, and it lets Hassas send reminders and follow-ups when they're useful.
- **WhatsApp is planned as a premium channel.** It's where most of the target audience already chats, but it charges per message and limits messages a business starts, so it fits a paid tier.
- **The core is channel-neutral.** Conversation logic speaks in neutral messages (text, a short choice, a summary link, a nudge) and works within the stricter limits of both apps: at most three options per question, typed answers always accepted, no reliance on editing messages or sending unprompted. Each app gets a thin adapter; Telegram-only features (inline keyboards, message editing, Mini Apps, a commands menu) are extras on top.
- **One user, many channels.** Users have an internal identity, with each messaging account linked to it, so a user can later move to or add WhatsApp without losing their history.
- **The Pattern Summary is a web page**, so it works on any device and can be shared with a doctor by link. In Telegram it can also open as a Mini App — the same page, not a separate feature set.

---

## 9. Hassas Version 1 Specs

**Architecture**

- Channel adapters (Telegram now, WhatsApp later) around a channel-neutral core
- Conversation agent (the Hassas persona) as the single user-facing component
- Separate research and verification agents, running in the background
- Deterministic analysis engine and summary builder
- Database of verified dishes, reused across logs
  **Onboarding**
- Short in-chat onboarding: language, timezone, consent, optional known triggers
  **Logging**
- Meal and symptom logging through chat (Telegram; WhatsApp later), by text or voice note
- English and Arabic (any dialect), including mixed messages
- Logging of cofactors: exercise, alcohol, painkillers, illness
- Optional logging reminders
  **Ingredients**
- Web research for every logged dish, prioritizing restaurant/brand sources
- Multi-source verification with per-ingredient confidence levels (confirmed / likely / possible)
- Conflict flagging and source citations
- Memory of verified dishes per restaurant
- Targeted follow-up questions for uncertain ingredients that matter
- "Ask the restaurant" message drafting
  **Analysis**
- Case-crossover pattern analysis with delay-weighted 0–8 h lookback windows and matched control windows
- Probabilistic, confidence-weighted ingredient exposures
- Bayesian shrinkage for small data
- Monte Carlo simulation of uncertain ingredients → score ranges
- Cofactor comparison for top patterns
- Pattern statuses (Collecting / Emerging / Strong / Can't be assessed / Unlikely) with a minimum-evidence threshold
- "Most informative next question" selection for follow-ups
  **Output**
- Pattern Summary web page: timeline, ranked ingredients with scores, ranges and statuses, uncertainty highlights, evidence trail with sources and confidence levels, boundary statement
  **Safety**
- Severe-symptom detection with immediate emergency-care referral
- No diagnosis, no dietary instructions
- Consent before storing health data; encrypted storage
  **Validation**
- Synthetic benchmark comparing Hassas against naive counting
