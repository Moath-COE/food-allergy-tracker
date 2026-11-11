# 3. Use plain httpx for the Telegram adapter

Date: 2026-11-10
Status: Accepted

## Context

What forces are at play: the problem, constraints, requirements (CH-1, CH-10)...

## Decision

We will call the Telegram Bot API directly with httpx instead of using aiogram or python-telegram-bot.

## Consequences

- Adapter stays thin; no framework routing competing with the neutral core.
  − We hand-write Pydantic models for the updates we use.
  − Retries and rate limiting are our job.
