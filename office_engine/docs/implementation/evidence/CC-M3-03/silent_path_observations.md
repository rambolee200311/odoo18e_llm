# Silent Retrieval Transport Observations — CC-M3-03

The evidence below separates a real UI transport observation from the final export HVR. Threads 290 and 312 were real non-streaming OpenAI UI attempts whose overall export plans later failed or were rejected; these observations are used only to verify message visibility timing, not to claim successful HVR data delivery.

## Real Bus and SSE boundary

Excerpt from `/tmp/cc_m3_03_server_debug.log`, thread 312:

```text
2026-11-16 08:48:43,707 ... suppress Bus notify thread=312 message=463318
2026-11-16 08:48:43,713 ... SSE event thread=312 type=message_create id=463318 silent=True hidden=True
2026-11-16 08:48:43,722 ... suppress Bus notify thread=312 message=463319
2026-11-16 08:48:43,725 ... SSE event thread=312 type=message_create id=463319 silent=True hidden=True
2026-11-16 08:48:43,727 ... SSE event thread=312 type=message_update id=463319 silent=True hidden=True
2026-11-16 08:48:53,055 ... SSE event thread=312 type=message_create id=463326 silent=False hidden=False
```

Thread 290 recorded the same pre-notify Bus suppression and hidden SSE `message_create` / `message_update` sequence. The final successful thread 677 has six retained messages tagged silent in Odoo ORM, while its UI showed Office activity and final response without the discovery messages. Its complete trace is in `hvr_actual_trace_thread_677.json`.

## Automated path boundaries

The 38-test M3 run includes:

- Discuss history excludes the silent message while retaining the underlying message and success result in context.
- SSE filtering removes only marked `message_create` / `message_update`; it preserves tool events and the generator return value.
- Retriever errors and their matching assistant tool-call message become visible.
- Mixed Retriever + Office tool-call assistant messages are not marked silent.
- The streaming route is not classified as the non-streaming Office route and stays visible.
- `_notify_thread` returns no Bus messages for both default notification and explicit `msg_vals.partner_ids` input.

The real HVR used the default live notification path. A separate live explicit-subscriber event and an actual Provider-produced mixed tool-call message were not captured; both remain clearly tracked in the ATR.
