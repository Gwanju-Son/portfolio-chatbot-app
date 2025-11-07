import os
import json
from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import openai
except Exception:
    openai = None
try:
    import yaml
    import google.generativeai as genai
except Exception:
    genai = None


class RAGService:
    """Simple RAG service using TF-IDF retriever + OpenAI (optional).

    - Loads `tarot_cards.json` and `edupm_app/assets/matrices.json` (if present)
    - Builds TF-IDF index in memory
    - retrieve(query, k) -> top k docs
    - answer(query) -> uses OpenAI if OPENAI_API_KEY present else a fallback summary
    """

    def __init__(self, docs_paths: List[str] = None, domain_preference: str = 'edupm'):
        self.docs: List[Dict[str, Any]] = []
        self.vectorizer = None
        self.doc_matrix = None
        self.domain_preference = domain_preference

        if docs_paths is None:
            docs_paths = [
                "tarot_cards.json",
                os.path.join("edupm_app", "assets", "matrices.json"),
            ]

        for p in docs_paths:
            if os.path.exists(p):
                try:
                    self._load_docs_from_file(p)
                except Exception:
                    pass

        if len(self.docs) == 0:
            # fallback small sample
            self.docs = [{"id": "local-fallback", "title": "fallback", "content": "No documents found."}]

        self._build_index()

    def _load_docs_from_file(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            obj = json.load(f)

        # handle tarot_cards.json (major_arcana)
        if isinstance(obj, dict) and 'major_arcana' in obj:
            for card in obj['major_arcana']:
                text = ' '.join(filter(None, [card.get('description', ''), card.get('upright_meaning', ''), card.get('reversed_meaning', '')]))
                self.docs.append({
                    'id': f"tarot-{card.get('number')}",
                    'title': card.get('name'),
                    'content': text,
                    'source': 'tarot'
                })

        # handle simple assets like matrices.json
        elif isinstance(obj, dict):
            # try to stringify useful entries
            for k, v in obj.items():
                # if value is small, include as doc
                if isinstance(v, str):
                    self.docs.append({'id': f"assets-{k}", 'title': k, 'content': v, 'source': 'assets'})
                elif isinstance(v, dict):
                    content = json.dumps(v, ensure_ascii=False)
                    self.docs.append({'id': f"assets-{k}", 'title': k, 'content': content, 'source': 'assets'})
                elif isinstance(v, list):
                    content = ' '.join([str(i) for i in v])
                    self.docs.append({'id': f"assets-{k}", 'title': k, 'content': content, 'source': 'assets'})

    def _build_index(self):
        texts = [d['content'] for d in self.docs]
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.doc_matrix = self.vectorizer.fit_transform(texts)

    def copy_with_extra_docs(self, extra_docs: List[Dict[str, Any]]):
        """Return a new RAGService instance that includes extra_docs appended to current docs."""
        new = RAGService(docs_paths=[] , domain_preference=self.domain_preference)
        # avoid loading files in constructor when docs_paths is empty
        new.docs = [d.copy() for d in self.docs]
        # normalize extra docs and assign ids
        base_idx = len(new.docs)
        for i, ed in enumerate(extra_docs):
            eid = ed.get('id') or f'web-{base_idx + i}'
            new.docs.append({'id': eid, 'title': ed.get('title', eid), 'content': ed.get('content', ''), 'source': 'web'})
        new._build_index()
        return new

    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        if not query or self.doc_matrix is None:
            return []

        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.doc_matrix)[0]
        # apply domain preference boost or filter if configured
        if self.domain_preference == 'edupm':
            for i, d in enumerate(self.docs):
                src = d.get('source', '')
                # prefer 'assets' docs
                if src == 'assets':
                    sims[i] = min(1.0, sims[i] + 0.25)
                # deprioritize or hide tarot docs unless query explicitly mentions tarot
                if src == 'tarot':
                    q_lower = query.lower()
                    if 'tarot' not in q_lower and '타로' not in q_lower:
                        sims[i] = -1.0

        # prefer non-negative sims (filtered), fall back if not enough docs
        valid_idx = [i for i, s in enumerate(sims) if s >= 0]
        if len(valid_idx) == 0:
            top_idx = np.argsort(sims)[::-1][:k]
        else:
            # sort only valid indices by their sims
            valid_sims = np.array([sims[i] for i in valid_idx])
            order = np.argsort(valid_sims)[::-1]
            top_idx = [valid_idx[i] for i in order][:k]
        results = []
        for i in top_idx:
            results.append({'score': float(sims[i]), **self.docs[i]})
        return results

    def _build_prompt(self, question: str, docs: List[Dict[str, Any]]) -> str:
        docs_text = '\n\n'.join([f"[{d['id']}] {d['title']}: {d['content']}" for d in docs])
        prompt = f"""
You are an assistant that answers user questions using only the provided documents below. If the answer is not contained in the documents, say you don't know and provide best-effort general guidance.

Documents:
{docs_text}

Question: {question}

Answer in Korean, be concise and include a short list of sources (document ids) you used.
"""
        return prompt

    def answer(self, question: str, k: int = 3) -> Dict[str, Any]:
        docs = self.retrieve(question, k=k)
        prompt = self._build_prompt(question, docs)
        # Prefer Google Gemini if config.yaml includes a gemini api_key and genai is available
        try:
            config_path = os.path.join(os.getcwd(), 'config.yaml')
            if genai is not None and os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = yaml.safe_load(f)
                gem_key = cfg.get('gemini', {}).get('api_key')
                gem_model = cfg.get('gemini', {}).get('model', None)
                if gem_key:
                    try:
                        genai.configure(api_key=gem_key)
                        model_name = gem_model or 'gemini-1.5-small'
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(
                            prompt,
                            generation_config=genai.types.GenerationConfig(
                                temperature=0.2,
                                max_output_tokens=512
                            )
                        )
                        # model.generate_content may return different shapes; try .text first
                        text = getattr(response, 'text', None) or (response.get('candidates')[0].get('content') if isinstance(response, dict) and response.get('candidates') else None)
                        if not text:
                            # try str(response)
                            text = str(response)
                        return {'success': True, 'answer': text, 'sources': [d['id'] for d in docs]}
                    except Exception as e:
                        # fall through to try OpenAI or fallback
                        pass
        except Exception:
            pass

        # If openai available and key set, call it
        api_key = os.getenv('OPENAI_API_KEY')
        if openai is not None and api_key:
            try:
                openai.api_key = api_key
                resp = openai.ChatCompletion.create(
                    model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                    messages=[{"role": "system", "content": "You are an assistant that must answer using only the provided documents. If the documents do not contain the answer, respond that the information is not available."},
                              {"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.2,
                )
                text = resp['choices'][0]['message']['content']
                return {
                    'success': True,
                    'answer': text,
                    'sources': [d['id'] for d in docs]
                }
            except Exception as e:
                return {'success': False, 'error': f'OpenAI error: {str(e)}'}

        # fallback: return concatenated doc snippets + naive answer
        combined = '\n\n'.join([f"- {d['title']}: {d['content'][:300]}..." for d in docs])
        answer = f"문서 기반 요약:\n{combined}\n\n질문에 대한 간단한 안내: 해당 도메인 자료를 참고하여 일반적인 조언을 드립니다."
        return {'success': True, 'answer': answer, 'sources': [d['id'] for d in docs]}


# create a module-level instance for convenience
rag_service = RAGService()

if __name__ == '__main__':
    print('RAGService loaded with', len(rag_service.docs), 'documents')
