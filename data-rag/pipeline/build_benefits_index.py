"""Index the shared medical-benefits DB without calling public collection APIs.

Run from data-rag: python -m pipeline.build_benefits_index
Use --dry-run to validate and snapshot documents without loading the model.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from health_benefits.recommendation.search_benefits import load_database
from pipeline.clean import join_sections
from pipeline.chunk import chunk_document


def normalize(row):
    source = {'central': 'welfare_central', 'local': 'welfare_local'}[row['source']]
    service_id = str(row.get('source_service_id') or '').strip()
    title = str(row.get('name') or '').strip()
    if not service_id or not title:
        raise ValueError('Missing service ID or title')
    region = ' '.join(str(row[k]) for k in ('provider_province', 'provider_municipality') if row.get(k))
    sections = {'서비스명': title, '서비스 개요': row.get('summary_text'),
                '지원 대상': row.get('target_text'), '선정 기준': row.get('criteria_text'),
                '서비스 내용': row.get('benefit_text'), '신청 방법': row.get('application_method'),
                '신청 기간 원문': row.get('application_period_text')}
    meta = {'지역': region, '지역설명': '제공기관 지역이며 신청자 거주 요건과 다를 수 있음',
            'url': row.get('source_url'), 'source_url': row.get('source_url'),
            '생애주기': row.get('life_cycle_names'), '대상특성': row.get('target_group_names'),
            '관심주제': row.get('theme_codes'), 'origin_table': 'public.healty_benefit',
            'source_service_id': service_id}
    return dict(id=service_id, source=source, title=title,
                text=join_sections(sections), metadata=meta)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    rows = load_database()  # Existing loader uses a READ ONLY transaction.
    if not rows:
        raise ValueError('Empty DB result: refusing to change index')
    documents = [normalize(r) for r in rows]
    keys = [(d['source'], d['id']) for d in documents]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate source/service IDs')
    chunks = [c for d in documents for c in chunk_document(d)]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'health_benefits' / 'data' / 'rag_builds' / stamp
    output.mkdir(parents=True)
    (output / 'documents.json').write_text(json.dumps(documents, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Documents: {len(documents)}; chunks: {len(chunks)}; sources: {dict(Counter(d["source"] for d in documents))}', flush=True)
    print(f'Snapshot: {output}', flush=True)
    if args.dry_run:
        return
    from pipeline.vectorstore import PERSIST_DIR, get_collection, add_chunks
    from pipeline.embed import embed_texts
    # Stop the backend during this operation. Preserve a restorable local copy.
    db_path = Path(PERSIST_DIR)
    if db_path.exists():
        shutil.copytree(db_path, output / 'chroma_backup')
    collection = get_collection()
    old_ids = set(collection.get(where={'source': {'$in': ['welfare_central', 'welfare_local']}}, include=[])['ids'])
    for start in range(0, len(chunks), 32):
        batch = chunks[start:start + 32]
        add_chunks(batch, embed_texts([c['text'] for c in batch]))
        print(f'Indexed {min(start + 32, len(chunks))}/{len(chunks)}', flush=True)
    expected = {c['chunk_id'] for c in chunks}
    present = set(collection.get(where={'source': {'$in': ['welfare_central', 'welfare_local']}}, include=[])['ids'])
    if not expected.issubset(present):
        raise RuntimeError('Verification failed; stale chunks have not been deleted')
    stale = sorted(old_ids - expected)
    for start in range(0, len(stale), 500):
        collection.delete(ids=stale[start:start + 500])
    actual = set(collection.get(where={'source': {'$in': ['welfare_central', 'welfare_local']}}, include=[])['ids'])
    if actual != expected:
        raise RuntimeError('Final chunk IDs do not match the DB snapshot')
    print(f'Complete: {len(actual)} welfare chunks; removed {len(stale)} stale chunks. Restart backend to refresh BM25.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Build failed: {type(exc).__name__}', file=sys.stderr)
        sys.exit(1)
