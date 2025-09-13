document.addEventListener('DOMContentLoaded', () => {

    const API_BASE_URL = "https://chatbotapi.quandoiai.vn";

    let sessionId = null;
    let customerId = null;
    
    function createImageModal() {
        const modalHTML = `
            <div id="chatbot-image-modal">
                <span class="chatbot-modal-close">&times;</span>
                <img class="chatbot-modal-content">
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const modal = document.getElementById('chatbot-image-modal');
        const closeBtn = document.querySelector('.chatbot-modal-close');

        closeBtn.onclick = () => modal.style.display = "none";
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.style.display = "none";
            }
        };
    }

    function loadSession() {
        const storedSession = sessionStorage.getItem('chatbot_session_id');
        if (storedSession) {
            sessionId = storedSession;
        } else {
            sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            sessionStorage.setItem('chatbot_session_id', sessionId);
        }
    }

    function createChatbotUI(settings) {
        const container = document.getElementById('chatbot-container');
        if (!container) return;

        const iconUrl = settings?.chatbot_icon_url || 'https://chatbot.quandoiai.vn/icon2.png';
        const calloutMessage = settings?.chatbot_callout || '👋 Chào anh/chị, em là trợ lý AI của Hoàng Mai Mobile!';
        const defaultMessage = settings?.chatbot_message_default || 'Xin chào anh/chị, em là trợ lý AI của Hoàng Mai Mobile luôn sẵn sàng hỗ trợ anh/chị ạ!';

        container.innerHTML = `
            <div class="chatbot-button-container">
                <div class="chatbot-callout">
                    ${calloutMessage}
                </div>
                <div class="chatbot-launcher">
                    <img src="${iconUrl}" alt="Chatbot Icon">
                </div>
            </div>
            <div class="chatbot-window">
                <div class="chatbot-header">
                    Hoàng Mai Mobile
                    <span class="chatbot-minimize-btn">–</span>
                </div>
                <div class="chatbot-messages">
                     <div class="message bot-message">${defaultMessage}</div>
                </div>
                <form class="chatbot-input-form">
                    <input type="text" class="chatbot-input" placeholder="Nhập tin nhắn..." required>
                    <button type="submit" class="chatbot-send-btn">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                    </button>
                </form>
            </div>
        `;
    }

    function attachEventListeners() {
        const launcher = document.querySelector('.chatbot-launcher');
        const chatWindow = document.querySelector('.chatbot-window');
        const minimizeBtn = document.querySelector('.chatbot-minimize-btn');
        const form = document.querySelector('.chatbot-input-form');
        const input = document.querySelector('.chatbot-input');
        const callout = document.querySelector('.chatbot-callout');
    
        launcher.addEventListener('click', () => {
            chatWindow.classList.toggle('open');
            callout.classList.toggle('hidden');
        });
        minimizeBtn.addEventListener('click', () => {
            chatWindow.classList.remove('open');
            callout.classList.remove('hidden');
        });
    
        form.addEventListener('submit', (event) => {
            event.preventDefault();
            const messageText = input.value.trim();
            if (messageText) {
                displayUserMessage(messageText);
                sendMessageToApi(messageText);
                input.value = '';
            }
        });
        
        const messagesContainer = document.querySelector('.chatbot-messages');
        messagesContainer.addEventListener('click', (event) => {
            if (event.target.classList.contains('zoomable-image')) {
                const modal = document.getElementById('chatbot-image-modal');
                const modalImg = document.querySelector('.chatbot-modal-content');
                
                modal.style.display = "flex";
                modalImg.src = event.target.src;
            }
        });
    }

    function displayUserMessage(text) {
        const messagesContainer = document.querySelector('.chatbot-messages');
        const messageElement = document.createElement('div');
        messageElement.className = 'message user-message';
        messageElement.textContent = text;
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        saveMessagesToSession();
    }

    function linkify(text) {
        const urlRegex = /(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig;
        return text.replace(urlRegex, function(url) {
            return '<a href="' + url + '" target="_blank">' + url + '</a>';
        });
    }
    
    function displayBotResponse(data) {
        const messagesContainer = document.querySelector('.chatbot-messages');
        const botMessageElement = document.createElement('div');
        botMessageElement.className = 'message bot-message';

        if (data.reply) {
            const textElement = document.createElement('p');
            const linkedText = linkify(data.reply);
            textElement.innerHTML = linkedText.replace(/\n/g, '<br>');
            botMessageElement.appendChild(textElement);
        }

        if (data.has_images && data.images && data.images.length > 0) {
            const imagesContainer = document.createElement('div');
            imagesContainer.className = 'bot-images-container';

            data.images.forEach(product => {
                const productCard = document.createElement('div');
                productCard.className = 'product-card';

                const productImage = document.createElement('img');
                productImage.className = 'product-image zoomable-image';
                productImage.src = product.image_url;
                productImage.alt = product.product_name;

                const productLink = document.createElement('a');
                productLink.className = 'product-link';
                productLink.href = product.product_link;
                productLink.target = '_blank';
                productLink.textContent = product.product_name;

                productCard.appendChild(productImage);
                productCard.appendChild(productLink);
                imagesContainer.appendChild(productCard);
            });
            botMessageElement.appendChild(imagesContainer);
        }

        messagesContainer.appendChild(botMessageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        saveMessagesToSession();
    }

    async function fetchChatbotSettings() {
        const container = document.getElementById('chatbot-container');
        customerId = container.getAttribute('data-customer-id');
        if (!customerId) {
            console.error('Customer ID not found on chatbot container');
            return null;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/settings/${customerId}`);
            if (!response.ok) {
                console.error('Failed to fetch chatbot settings');
                return null;
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching chatbot settings:', error);
            return null;
        }
    }

    async function sendMessageToApi(messageText) {
        const messagesContainer = document.querySelector('.chatbot-messages');
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'message bot-message typing-indicator';
        typingIndicator.innerHTML = '● ● ●';
        messagesContainer.appendChild(typingIndicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const response = await fetch(`${API_BASE_URL}/chat?session_id=${sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: messageText, model_choice: "gemini", mode: "json" })
            });

            typingIndicator.remove();
            const responseData = await response.json();

            if (!response.ok) {
                const errorMessage = responseData.detail?.[0]?.msg || 'Lỗi không xác định';
                displayBotResponse({ reply: `Có lỗi xảy ra: ${errorMessage}` });
                return;
            }
            if (responseData.action_data && responseData.action_data.action === 'redirect') {
                displayBotResponse(responseData);
                sessionStorage.setItem('chatbot_should_be_open', 'true');
                setTimeout(() => {
                    window.location.href = responseData.action_data.url;
                }, 300);
    
                return;
            }
            
            displayBotResponse(responseData);
        } catch (error) {
            if(document.querySelector('.typing-indicator')) {
                document.querySelector('.typing-indicator').remove();
            }
            displayBotResponse({ reply: 'Xin lỗi, đã có lỗi kết nối. Vui lòng thử lại.' });
        }
    }

    function saveMessagesToSession() {
        const messagesContainer = document.querySelector('.chatbot-messages');
        const messages = [];
        messagesContainer.querySelectorAll('.message').forEach(messageElement => {
            if (messageElement.classList.contains('typing-indicator')) {
                return;
            }

            let messageData;
            if (messageElement.classList.contains('user-message')) {
                messageData = {
                    type: 'user',
                    text: messageElement.textContent
                };
            } else if (messageElement.classList.contains('bot-message')) {
                messageData = {
                    type: 'bot',
                    html: messageElement.innerHTML
                };
            }

            if (messageData) {
                messages.push(messageData);
            }
        });
        sessionStorage.setItem('chatbot_messages', JSON.stringify(messages));
    }

    function loadMessagesFromSession() {
        const messagesContainer = document.querySelector('.chatbot-messages');
        const savedMessagesJSON = sessionStorage.getItem('chatbot_messages');

        if (savedMessagesJSON) {
            const savedMessages = JSON.parse(savedMessagesJSON);
            if (savedMessages.length > 0) {
                messagesContainer.innerHTML = '';
                savedMessages.forEach(msg => {
                    const messageElement = document.createElement('div');
                    messageElement.className = `message ${msg.type}-message`;
                    if (msg.type === 'user') {
                        messageElement.textContent = msg.text;
                    } else if (msg.type === 'bot') {
                        messageElement.innerHTML = msg.html;
                    }
                    messagesContainer.appendChild(messageElement);
                });
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
    }

    async function initChatbot() {
        const settings = await fetchChatbotSettings();
        createChatbotUI(settings);
        createImageModal();
        loadSession();
        attachEventListeners();
        loadMessagesFromSession();
        if (sessionStorage.getItem('chatbot_should_be_open') === 'true') {
            document.querySelector('.chatbot-window').classList.add('open');
            sessionStorage.removeItem('chatbot_should_be_open');
        }
    }

    initChatbot();
});