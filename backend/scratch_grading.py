# backend/scratch_grading.py
import asyncio
from app.langchain_.correction import grade_answer
from app.services.correction_logic import judgment_to_output

K = ('Ich haette gern einen Kaffee.', 'I would like a coffee.', 'subjunctive_II')
C = ('Ich gehe heute ins Kino.', "I'm going to the cinema today.", None)

CASES = [
    ('almost (case) #1',   *C, 'Ich gehe heute im Kino.'),
    ('almost (case) #2',   *C, 'Ich gehe heute im Kino.'),
    ('almost (case) #3',   *C, 'Ich gehe heute im Kino.'),
    ('correct, different', *C, 'Heute gehe ich in das Kino.'),
    ('wrong meaning #1',   *C, 'Ich mag Pizza.'),
    ('wrong meaning #2',   *C, 'Ich mag Pizza.'),
    ('rule avoided #1',    *K, 'Ich nehme einen Kaffee.'),
    ('rule avoided #2',    *K, 'Ich nehme einen Kaffee.'),
    ('rule avoided #3',    *K, 'Ich nehme einen Kaffee.'),
    ('rule avoided #4',    *K, 'Ich nehme einen Kaffee.'),
    ('rule avoided #5',    *K, 'Ich nehme einen Kaffee.'),
    ('rule used',          *K, 'Ich haette gern einen Kaffee.'),
    ('wrong noun (tea)',   *K, 'Ich haette gern einen Tee.'),
    ('near-miss + rule',   *K, 'Ich haette gern eine Kaffee.'),
]


async def main():
    for label, de, en, tag, ans in CASES:
        try:
            j = await grade_answer(target_de=de, target_en=en, user_answer=ans, grammar_tag=tag)
        except Exception as e:
            print(f'{label:20} | {ans!r}\n     ERROR {type(e).__name__}: {str(e)[:150]}')
            continue
        out = judgment_to_output(j)
        print(f'{label:20} | {ans!r}')
        print('    ', out.tier.value, '| very_close', out.very_close,
              '| rule', out.rule_practiced,
              '|', out.corrected_sentence or '-')
        print('     analysis:', j.analysis[:160])

asyncio.run(main())