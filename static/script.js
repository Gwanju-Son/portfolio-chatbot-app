class TarotChatApp {
    constructor() {
        this.isWaitingForResponse = false;

        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.cardsContainer = document.getElementById('cardsContainer');
        this.numCardsSelect = document.getElementById('numCards');
        this.connectionStatus = document.getElementById('connectionStatus');
    }

    bindEvents() {
        this.sendButton.addEventListener('click', () => this.sendMessage());

        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.messageInput.addEventListener('input', () => {
            this.updateSendButton();
        });
    }


    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isWaitingForResponse) {
            return;
        }

        const numCards = parseInt(this.numCardsSelect.value);

        // 사용자 메시지 추가
        this.addUserMessage(message);
        this.messageInput.value = '';
        this.isWaitingForResponse = true;
        this.updateSendButton();

        // 대기 메시지 추가
        this.addThinkingMessage(`🔮 ${numCards}장의 카드를 뽑고 있습니다...`);

        try {
            const response = await fetch('/api/tarot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: message,
                    num_cards: numCards
                })
            });

            const data = await response.json();

            // 대기 메시지 제거
            this.removeThinkingMessage();

            if (data.success) {
                if (data.is_help) {
                    this.addBotMessage(data.message);
                } else {
                    this.addBotMessage(data.reading);
                    if (data.cards && data.cards.length > 0) {
                        this.displayCards(data.cards);
                    }
                }
            } else {
                this.addBotMessage(`❌ ${data.error}`);
            }

        } catch (error) {
            this.removeThinkingMessage();
            this.addBotMessage(`❌ 서버 연결 오류: ${error.message}`);
            console.error('Error:', error);
        }

        this.isWaitingForResponse = false;
        this.updateSendButton();
    }

    addUserMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user-message';
        messageDiv.textContent = message;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addBotMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';

        // 마크다운 형식의 메시지를 간단히 HTML로 변환
        const formattedMessage = this.formatMessage(message);
        messageDiv.innerHTML = formattedMessage;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addSystemMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system-message';
        messageDiv.innerHTML = this.formatMessage(message);

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addThinkingMessage(message) {
        this.removeThinkingMessage(); // 기존 thinking 메시지 제거

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message thinking-message';
        messageDiv.id = 'thinking-message';
        messageDiv.innerHTML = `
            <span class="loading-spinner"></span>
            ${message}
            <span class="typing-indicator"></span>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    removeThinkingMessage() {
        const thinkingMessage = document.getElementById('thinking-message');
        if (thinkingMessage) {
            thinkingMessage.remove();
        }
    }

    formatMessage(message) {
        return message
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // **bold**
            .replace(/\*(.*?)\*/g, '<em>$1</em>') // *italic*
            .replace(/\n/g, '<br>'); // 줄바꿈
    }

    displayCards(cards) {
        // 기존 "카드가 없습니다" 메시지 제거
        const noCards = this.cardsContainer.querySelector('.no-cards');
        if (noCards) {
            noCards.remove();
        }

        // 기존 카드들 제거
        this.cardsContainer.innerHTML = '';

        cards.forEach((card, index) => {
            const cardDiv = document.createElement('div');
            cardDiv.className = `card-item ${card.is_reversed ? 'reversed' : ''}`;

            const orientation = card.is_reversed ? '역방향' : '정방향';
            const orientationClass = card.is_reversed ? 'reversed' : 'upright';

            cardDiv.innerHTML = `
                <img src="/card_image/${card.local_image.split('/')[1]}"
                     alt="${card.name}"
                     class="card-image"
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iIzMzMzMzMyIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+VGFyb3QgQ2FyZDwvdGV4dD48L3N2Zz4='">
                <div class="card-name">${card.name_korean} (${card.name})</div>
                <div class="card-orientation ${orientationClass}">${orientation}</div>
            `;

            this.cardsContainer.appendChild(cardDiv);

            // 애니메이션을 위한 지연
            setTimeout(() => {
                cardDiv.style.opacity = '0';
                cardDiv.style.transform = 'translateY(20px)';
                cardDiv.style.transition = 'all 0.5s ease';

                setTimeout(() => {
                    cardDiv.style.opacity = '1';
                    cardDiv.style.transform = 'translateY(0)';
                }, 100 * index);
            }, 100);
        });
    }

    updateSendButton() {
        const hasMessage = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = this.isWaitingForResponse || !hasMessage;

        if (this.isWaitingForResponse) {
            this.sendButton.innerHTML = '<span class="loading-spinner"></span>응답 대기중...';
        } else {
            this.sendButton.textContent = '전송';
        }
    }

    updateConnectionStatus(connected) {
        if (connected) {
            this.connectionStatus.innerHTML = '✅ 연결됨';
            this.connectionStatus.className = 'connection-status connected';
        } else {
            this.connectionStatus.innerHTML = '❌ 연결 끊김';
            this.connectionStatus.className = 'connection-status disconnected';
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
}

// 앱 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.tarotApp = new TarotChatApp();
    console.log('타로 챗봇 앱이 초기화되었습니다.');
});