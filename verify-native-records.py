from pathlib import Path
import json,collections,datetime,sys
p=Path('/var/local/meteohub-live-test')
rows=[json.loads(x) for x in (p/'state/provenance.jsonl').read_text().splitlines()]
raw=(p/'weather/202611/raw').read_text().splitlines()
from normalize_native import normalize_record as norm
last=datetime.datetime.strptime(raw[-1].split()[0],'%Y%m%d%H%M%S').replace(tzinfo=datetime.timezone.utc).timestamp() if raw else 0
final='--final' in sys.argv
expected=collections.Counter(norm(x['plugin']) for x in rows if 'plugin' in x and (final or int(x['received_at'])<=last))
actual=collections.Counter(norm(x,True) for x in raw)
report={'last_flushed_epoch':last,'expected_records_through_last_flush':sum(expected.values()),'actual_records':len(raw),'missing':list((expected-actual).items()),'unexpected':list((actual-expected).items()),'accepted_total':sum('plugin' in x for x in rows),'rejected_temperature':sum(x.get('reason','').startswith('source temperature') for x in rows)}
start=int((p/'temperature-order-start').read_text())
baseline=json.loads((p/'before-temperature-order.json').read_text())['actual_records']
new_expected=collections.Counter(norm(x['plugin']) for x in rows if 'plugin' in x and x['received_at']>=start and (final or int(x['received_at'])<=last))
new_actual=collections.Counter(norm(x,True) for x in raw[baseline:])
report.update(post_fix_expected=sum(new_expected.values()),post_fix_archived=sum(new_actual.values()),post_fix_missing=list((new_expected-new_actual).items()),post_fix_unexpected=list((new_actual-new_expected).items()),final=final)
print(json.dumps(report));(p/'record-check.json').write_text(json.dumps(report,indent=2))
