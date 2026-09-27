142-          type: string
143:        market_type:
144-          type: string
145-          enum:
146-            - binary
147-            - scalar
148-          description: Identifies the type of market
149-        title:
150-          type: string
151-          deprecated: true
--
236-          description: String representation of the 24h market volume in contracts
237:        result:
238-          type: string
239-          enum:
240-            - 'yes'
241-            - 'no'
242-            - scalar
243-            - ''
244-        can_close_early:
245-          type: boolean
--
268-            dollars
269:        settlement_value_dollars:
270-          $ref: '#/components/schemas/FixedPointDollars'
271-          nullable: true
272-          x-omitempty: true
273-          description: >-
274-            The settlement value of the YES/LONG side of the contract in
275-            dollars. Only filled after determination
276-        settlement_ts:
277-          type: string
--
305-          x-go-type-skip-optional-pointer: true
306:        strike_type:
307-          type: string
308-          enum:
309-            - greater
310-            - greater_or_equal
311-            - less
312-            - less_or_equal
313-            - between
314-            - functional
--
319-          x-go-type-skip-optional-pointer: true
320:        floor_strike:
321-          type: number
322-          format: double
323-          nullable: true
324-          x-omitempty: true
325-          description: Minimum expiration value that leads to a YES settlement
326:        cap_strike:
327-          type: number
328-          format: double
329-          nullable: true
330-          x-omitempty: true
331-          description: Maximum expiration value that leads to a YES settlement
332-        functional_strike:
333-          type: string
334-          nullable: true
--
416-          x-go-type-skip-optional-pointer: true
417:        yes_settlement_value_dollars:
418-          $ref: '#/components/schemas/FixedPointDollars'
419-          nullable: true
420-          x-omitempty: true
421-          description: >-
422-            The settlement value of the YES/LONG side of the contract in
423-            dollars. Only filled after determination
424-    PriceRange:
425-      type: object
