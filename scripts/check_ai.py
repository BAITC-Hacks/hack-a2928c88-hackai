"""One real AI call on a labelled synthetic sample; never prints credentials."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
from app.llm import Extractor


def main():
    load_dotenv(ROOT / '.env')
    if not os.getenv('OPENAI_API_KEY'):
        raise SystemExit('OPENAI_API_KEY is not configured')
    os.environ['MOCK'] = '0'
    sample = json.loads((ROOT / 'data/samples/ai-sana-synthetic.json').read_text(encoding='utf-8'))['drafts'][0]
    result, mode, provider, failures = Extractor().extract({'draft':sample['text']}, {})
    print(json.dumps({'synthetic':True,'mode':mode,'provider':provider,
        'questions':len(result.questions),'evidence_fields':[e.field for e in result.evidence],
        'quote_validation':'passed','failures':failures},ensure_ascii=True))
    if mode != 'live' or provider != 'openai':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
