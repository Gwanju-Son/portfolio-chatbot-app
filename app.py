from flask import Flask, render_template, request, jsonify
import os
from rag_service import RAGService

# Initialize Flask app
app = Flask(__name__)

# --- Data for RAG ---
# You can add more structured data here.
# For example, load from JSON files or write directly.
portfolio_data = [
    {
        "id": "pm-philosophy",
        "title": "PM으로서의 철학",
        "content": "저는 교육의 본질을 이해하고, 데이터를 통해 그것을 구현하는 PM입니다. 학습자 중심 설계, 데이터 기반 의사결정, 그리고 지속적인 개선 사이클을 통해 측정 가능한 성과를 만드는 것을 목표로 합니다. 좋은 교육은 '무엇을 가르치느냐'가 아니라 '어떻게 배우게 하느냐'의 문제이며, 명확한 목표, 적절한 난이도, 즉각적인 피드백, 반복 가능한 프로세스라는 구조를 설계하는 것이 PM의 핵심 역량이라고 믿습니다."
    },
    {
        "id": "edupm-copilot",
        "title": "EduPM Copilot 프로젝트",
        "content": "B2B 기업교육 PM의 반복적이고 산재된 업무(Discovery, 설계, 운영, 회고)를 효율화하기 위해 EduPM Copilot을 개발했습니다. 대화형 챗봇을 통해 고객의 니즈를 파악하고, 맞춤형 커리큘럼을 추천하며, 관련 문서를 자동으로 생성하고, 성과 회고까지 통합하는 것을 목표로 했습니다. 이 프로젝트를 통해 요구사항 정의부터 커리큘럼 초안 생성까지의 시간을 단축하고, 문서 자동화로 산출물 작성 시간을 줄이는 성과를 거두었습니다. Streamlit, Python, LLM 기술을 활용했습니다."
    },
    {
        "id": "data-skills",
        "title": "데이터 분석 및 AI 역량",
        "content": "K-Digital Training 과정을 통해 데이터 분석과 AI 역량을 심화했습니다. Python을 활용한 데이터 처리, 시각화, 통계 분석이 가능합니다. 특히 TF-IDF 같은 자연어 처리 기술을 이용해 텍스트 데이터에서 핵심 정보를 추출하고, 이를 바탕으로 RAG(Retrieval-Augmented Generation) 시스템을 구축하는 경험을 했습니다. Google Gemini API와 같은 LLM을 활용하여 사용자의 질문에 자연스럽게 답변하는 챗봇을 개발할 수 있습니다."
    },
    {
        "id": "career-journey",
        "title": "주요 경력 및 경험",
        "content": "철학과 교육학을 전공하며 학습의 본질을 탐구했습니다. 한국외대X동원재단 교육 조교, AI 기반 교육 벤처 창업, ReadingStar Institute, '손샘의리딩클래스' 1인 교육사업 등 다양한 현장에서 교육 기획, 운영, 학습 지원 경험을 쌓았습니다. 이러한 경험을 통해 학습자의 니즈를 파악하고 교육의 임팩트를 측정하기 위해 데이터와 AI의 필요성을 절감하게 되었습니다. 최근에는 2024 용인특례시 오픈미디어포럼 운영총괄 PM, 2024 청년일경험 사업(ESG형) 제안 및 기획 PM 역할을 수행하며 프로젝트 관리 역량을 강화했습니다."
    }
]

# --- RAG Service Initialization ---
# Initialize the RAG service with the portfolio data
rag_service_instance = RAGService(docs_paths=[]) # Start with no file-based docs
rag_service_instance = rag_service_instance.copy_with_extra_docs(portfolio_data)

# --- API Routes ---
@app.route('/')
def index():
    """Render the main chatbot interface."""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle the chat request from the user."""
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "Message not provided"}), 400

    try:
        # Use the RAG service to get an answer
        # The answer method combines retrieval and generation
        answer_data = rag_service_instance.answer(user_message)
        
        response_text = answer_data.get("answer", "죄송합니다, 답변을 생성하는 데 문제가 발생했습니다.")
        
        return jsonify({"reply": response_text})

    except Exception as e:
        print(f"Error during chat processing: {e}")
        return jsonify({"error": "An internal error occurred."}), 500

if __name__ == '__main__':
    # Use Gunicorn for production. For local dev, this is fine.
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
