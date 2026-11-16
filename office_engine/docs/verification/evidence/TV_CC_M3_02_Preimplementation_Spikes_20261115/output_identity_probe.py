import hashlib
import json
from io import BytesIO
from openpyxl import Workbook, load_workbook
from office_verify import VerificationPolicy, VerificationBudget, verify_created_output_with_metrics

def main():
    ids = ['M3-IDENTITY-A', 'M3-IDENTITY-B', 'M3-IDENTITY-C']
    wb = Workbook()
    ws = wb.active
    ws.title = 'Export'
    ws.append(['Record ID', 'Label'])
    for n, value in enumerate(ids, start=1):
        ws.append([value, f'Synthetic {n}'])
    payload = BytesIO()
    wb.save(payload)
    content = payload.getvalue()
    report, metrics = verify_created_output_with_metrics(
        content,
        'synthetic-export.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        policy=VerificationPolicy(enabled_formats=('xlsx',)),
        budget=VerificationBudget(),
    )
    readback = load_workbook(BytesIO(content), read_only=True, data_only=True)
    actual = [row[0] for row in readback['Export'].iter_rows(min_row=2, max_col=1, values_only=True)]
    readback.close()
    result = {
        'fixture': 'synthetic_only', 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
        'office_verify_result': report.validation_result,
        'package_integrity_supported': any(x.get('feature') == 'xlsx_package_integrity' and x.get('capability') == 'SUPPORTED' for x in report.feature_results),
        'worksheet_structure_supported': any(x.get('feature') == 'worksheet_structure_readability' and x.get('capability') == 'SUPPORTED' for x in report.feature_results),
        'expected_identity_count': len(ids), 'actual_identity_count': len(actual),
        'identity_set_matches': set(actual) == set(ids), 'identity_unique': len(actual) == len(set(actual)),
        'elapsed_seconds': round(metrics['elapsed_seconds'], 3), 'max_observed_rss_bytes': metrics['max_observed_rss_bytes'],
        'worker_exited': metrics['worker_exited'], 'business_semantics_claimed': False,
    }
    print(json.dumps(result, sort_keys=True))
    assert result['office_verify_result'] == 'PARTIALLY_VERIFIED'
    assert result['package_integrity_supported'] and result['worksheet_structure_supported']
    assert result['identity_set_matches'] and result['identity_unique']

if __name__ == '__main__':
    main()
