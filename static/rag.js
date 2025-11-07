document.addEventListener('DOMContentLoaded', () => {
    const askBtn = document.getElementById('askBtn');
    const qInput = document.getElementById('questionInput');
    const answerArea = document.getElementById('answerArea');
    const sourcesArea = document.getElementById('sourcesArea');
    const kSelect = document.getElementById('kSelect');

    askBtn.addEventListener('click', async () => {
        const question = qInput.value.trim();
        if (!question) return;
        answerArea.textContent = '생성 중...';
        sourcesArea.textContent = '';

        try {
            const resp = await fetch('/api/rag', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, k: parseInt(kSelect.value || '3', 10) })
            });
            const data = await resp.json();
            if (data.success) {
                answerArea.textContent = data.answer;
                if (data.sources && data.sources.length) {
                    sourcesArea.textContent = '참고 문서: ' + data.sources.join(', ');
                }
            } else {
                answerArea.textContent = '오류: ' + (data.error || 'unknown');
            }
        } catch (e) {
            answerArea.textContent = '서버 연결 오류: ' + e.message;
        }
    });
});
