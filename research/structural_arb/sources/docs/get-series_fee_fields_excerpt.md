178-          nullable: true
179-          x-omitempty: true
180-          description: Internal product metadata of the series.
181:        fee_type:
182-          allOf:
183-            - $ref: '#/components/schemas/FeeType'
184-          description: >-
185-            FeeType is a string representing the series' fee structure. Fee
186-            structures can be found at
187-            https://kalshi.com/docs/kalshi-fee-schedule.pdf. 'quadratic' is
188-            described by the General Trading Fees Table,
189-            'quadratic_with_maker_fees' is described by the General Trading Fees
190-            Table with maker fees described in the Maker Fees section,
191-            'quadratic_with_combo_maker_fees' is the same maker-fee structure
192-            with a 0.5 maker multiplier instead of 0.25, 'flat' is described by
193-            the Specific Trading Fees Table.
194:        fee_multiplier:
195-          type: number
196-          format: double
197-          description: >-
198-            FeeMultiplier is a floating point multiplier applied to the fee
199-            calculations.
200-        additional_prohibitions:
201-          type: array
202-          nullable: true
203-          items:
204-            type: string
205-          description: >-
206-            AdditionalProhibitions is a list of additional trading prohibitions
