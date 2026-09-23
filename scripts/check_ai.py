"""One real AI call on a labelled synthetic sample; never prints credentials."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
from app.llm import Extractor
from app.ai_config import model_for
from app.review import CardReviewer
from app.specification import SpecGenerator
from app.schemas import CardContent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['openai','nvidia'], default='openai')
    parser.add_argument('--workflow', choices=['extract','review','specification'], default='extract')
    args = parser.parse_args()
    load_dotenv(ROOT / '.env')
    key = 'OPENAI_API_KEY' if args.provider == 'openai' else 'NVIDIA_API_KEY'
    if not os.getenv(key):
        raise SystemExit(key + ' is not configured; no request sent')
    # Isolate the requested provider for this diagnostic process; never change .env.
    os.environ.pop('NVIDIA_API_KEY' if args.provider == 'openai' else 'OPENAI_API_KEY', None)
    os.environ['MOCK'] = '0'
    os.environ['FALLBACK_TO_MOCK'] = '0'
    fixtures = json.loads((ROOT / 'data/samples/ai-sana-synthetic.json').read_text(encoding='utf-8'))
    ai = Extractor()
    details = {}
    if args.workflow == 'extract':
        result, mode, provider, failures = ai.extract({'draft':fixtures['drafts'][0]['text']}, {})
        details = {'questions':len(result.questions),'evidence_fields':[e.field for e in result.evidence],
                   'quote_validation':'passed'}
    else:
        fields = {f:fixtures['cards'][0].get(f,'') for f in CardContent.model_fields}
        if args.workflow == 'review':
            reviewer = CardReviewer(ai)
            result = reviewer.review_nvidia(fields) if args.provider == 'nvidia' else reviewer.review(fields)
            mode, provider, failures = result['mode'],result['provider'],[]
            details = {'issues':len(result['issues']),'quote_validation':'passed'}
        else:
            source = {**fields,'industry':fixtures['cards'][0]['industry']}
            result, mode, provider, failures = SpecGenerator(ai.reserve).generate(source)
            details = {'ideas':len(result.ideas),'schema_validation':'passed','human_review_required':True}
    print(json.dumps({'synthetic':True,'mode':mode,'provider':provider,'model':model_for(provider),
        'workflow':args.workflow, **details, 'failures':failures},ensure_ascii=True))
    if mode != 'live' or provider != args.provider:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
