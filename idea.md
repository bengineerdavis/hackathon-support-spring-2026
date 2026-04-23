# hackathon idea: use llm/agents to read sentry attachments to events/error type events

## problem
We have raw event logs as attachments within events sent to Sentry SaaS from a given SDK client, these are not human-readable, and therefore context can become lost or muddled.

## background 
we have a raw backup of whatever we collected per event 

## Solution

Create a visual interface that pulls and organize these logs per event, and then translates the raw logs into an approachable user-friendly summary so all stackholders can understand the problem being reported.

## Approach

- Synthesize attachments data via a pre-configured mcp to an agent that creates fake events to said project, which are captured via the SDK client

- Pull attachment data from my python test sentry project via the attachments API.

- Use a local model to digest this data and produce the summaries. 
  - save these summaries on-disk and use the local filesystem to organize the relationships of the summaries

- provide summaries to select and view on simple gui
