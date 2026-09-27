157-          type: string
158-          description: Full title of the event.
159:        collateral_return_type:
160-          type: string
161-          description: >
162-            Collateral-return netting type for this event: `MECNET` for mutually
163-            exclusive markets, `DIRECNET` for directional netting, or an empty
164-            string for no collateral-return netting.
165-
166-            Netting applies within this event, not across all events in its
167-            series, and also requires netting to be enabled for the trading
168-            account or subtrader.
169-
170-            Use `with_nested_markets=true` to retrieve the markets associated
171-            with each event.
172:        mutually_exclusive:
173-          type: boolean
174-          description: >
175-            True when `collateral_return_type` is `MECNET`: at most one market
176-            in this event can resolve to 'yes'.
177-
178-            False for both `DIRECNET` and an empty collateral-return type. A
179-            false value does not mean collateral-return netting is unavailable.
180-            Use `collateral_return_type` to distinguish these cases.
181-        category:
182-          type: string
