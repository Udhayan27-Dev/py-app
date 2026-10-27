// PlanMyStudy Chat Widget Logic

(function() {
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Session ID persistence
  let sessionId = localStorage.getItem('planmystudy_chat_session');
  if (!sessionId) {
    sessionId = 'sess_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
    localStorage.setItem('planmystudy_chat_session', sessionId);
  }

  document.addEventListener('DOMContentLoaded', function() {
    const chatBtn = document.getElementById('chat-toggle-btn');
    const chatContainer = document.getElementById('chat-widget-container');
    const closeBtn = document.getElementById('chat-close-btn');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const messagesContainer = document.getElementById('chat-messages');

    if (!chatBtn || !chatContainer) return;

    function toggleChat(show) {
      if (show === undefined) {
        chatContainer.classList.toggle('hidden');
      } else if (show) {
        chatContainer.classList.remove('hidden');
      } else {
        chatContainer.classList.add('hidden');
      }

      if (!chatContainer.classList.contains('hidden')) {
        chatInput.focus();
        scrollToBottom();
      }
    }

    chatBtn.addEventListener('click', function() {
      toggleChat();
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        toggleChat(false);
      });
    }

    function scrollToBottom() {
      if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    function formatMarkdown(text) {
      // Basic markdown parser for bold, lists, linebreaks
      let formatted = escapeHtml(text);
      formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      formatted = formatted.replace(/\n\n/g, '<br><br>');
      formatted = formatted.replace(/\n/g, '<br>');
      return formatted;
    }

    function appendUserMessage(text) {
      const div = document.createElement('div');
      div.className = 'flex justify-end mb-3 animate-fade-in';
      div.innerHTML = `
        <div class="bg-indigo-600 text-white rounded-2xl rounded-tr-none px-4 py-2.5 max-w-[85%] shadow-sm text-sm">
          ${escapeHtml(text)}
        </div>
      `;
      messagesContainer.appendChild(div);
      scrollToBottom();
    }

    function appendAssistantMessage(replyText, source, messageId) {
      const div = document.createElement('div');
      div.className = 'flex flex-col items-start mb-3 animate-fade-in';

      let sourceBadge = '';
      if (source === 'faq') {
        sourceBadge = '<span class="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-medium">FAQ Verified</span>';
      } else if (source === 'error_code') {
        sourceBadge = '<span class="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded font-medium">Error Docs</span>';
      } else if (source === 'ticket_created') {
        sourceBadge = '<span class="text-[10px] bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded font-medium">Ticket Created</span>';
      } else {
        sourceBadge = '<span class="text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-medium">AI Support</span>';
      }

      div.innerHTML = `
        <div class="flex items-center space-x-1.5 mb-1 text-xs text-gray-400 pl-1">
          <span class="font-medium text-gray-600">PlanMyStudy Assistant</span>
          ${sourceBadge}
        </div>
        <div class="bg-white border border-gray-100 text-gray-800 rounded-2xl rounded-tl-none px-4 py-3 max-w-[90%] shadow-sm text-sm leading-relaxed">
          ${formatMarkdown(replyText)}
        </div>
        <div class="flex items-center space-x-2 mt-1.5 pl-2 text-xs text-gray-400" id="feedback-row-${messageId}">
          <span>Helpful?</span>
          <button type="button" class="feedback-btn hover:text-emerald-600 transition-colors p-1" data-msg-id="${messageId}" data-rating="thumbs_up" title="Helpful">
            👍
          </button>
          <button type="button" class="feedback-btn hover:text-rose-600 transition-colors p-1" data-msg-id="${messageId}" data-rating="thumbs_down" title="Not helpful">
            👎
          </button>
          <span class="feedback-ack hidden text-[11px] text-emerald-600 font-medium">Thank you!</span>
        </div>
      `;
      messagesContainer.appendChild(div);
      scrollToBottom();
      bindFeedbackButtons(div);
    }

    function appendLoadingIndicator() {
      const id = 'chat-loading-' + Date.now();
      const div = document.createElement('div');
      div.id = id;
      div.className = 'flex items-center space-x-1 mb-3 text-gray-400 pl-2 text-xs animate-pulse';
      div.innerHTML = `
        <span>Thinking</span>
        <span class="inline-block animate-bounce">.</span>
        <span class="inline-block animate-bounce" style="animation-delay: 0.15s">.</span>
        <span class="inline-block animate-bounce" style="animation-delay: 0.3s">.</span>
      `;
      messagesContainer.appendChild(div);
      scrollToBottom();
      return id;
    }

    function removeLoadingIndicator(id) {
      const el = document.getElementById(id);
      if (el) el.remove();
    }

    function bindFeedbackButtons(container) {
      const btns = container.querySelectorAll('.feedback-btn');
      btns.forEach(btn => {
        btn.addEventListener('click', function() {
          const msgId = this.getAttribute('data-msg-id');
          const rating = this.getAttribute('data-rating');
          const row = document.getElementById('feedback-row-' + msgId);

          const csrfToken = getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '');

          fetch('/api/feedback/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
              session_id: sessionId,
              message_id: msgId,
              rating: rating
            })
          })
          .then(res => res.json())
          .then(() => {
            if (row) {
              const allBtns = row.querySelectorAll('.feedback-btn');
              allBtns.forEach(b => b.classList.add('hidden'));
              const ack = row.querySelector('.feedback-ack');
              if (ack) ack.classList.remove('hidden');
            }
          })
          .catch(err => console.error('Feedback submission failed:', err));
        });
      });
    }

    async function sendMessage(text) {
      const message = text || chatInput.value.trim();
      if (!message) return;

      appendUserMessage(message);
      chatInput.value = '';
      const loadingId = appendLoadingIndicator();

      const csrfToken = getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '');

      try {
        const response = await fetch('/api/chat/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            message: message,
            session_id: sessionId
          })
        });

        removeLoadingIndicator(loadingId);

        if (response.status === 429) {
          appendAssistantMessage("⚠️ Rate limit exceeded. Please wait a minute before sending more queries.", "error_code", "rate-limit-err");
          return;
        }

        const data = await response.json();
        if (data.reply) {
          appendAssistantMessage(data.reply, data.source, data.message_id || ('msg-' + Date.now()));
        } else if (data.error) {
          appendAssistantMessage("⚠️ " + data.error, "error_code", "err-" + Date.now());
        }
      } catch (err) {
        removeLoadingIndicator(loadingId);
        appendAssistantMessage("Unable to reach assistant right now. Please try again shortly.", "error_code", "network-err");
      }
    }

    if (chatForm) {
      chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        sendMessage();
      });
    }

    // Quick suggestions pills
    document.querySelectorAll('.chat-suggestion-pill').forEach(pill => {
      pill.addEventListener('click', function() {
        const prompt = this.getAttribute('data-prompt');
        if (prompt) {
          sendMessage(prompt);
        }
      });
    });

    // Global helper to open chat and prefill/send
    window.openChat = function(prefill, autoSend = true) {
      toggleChat(true);
      if (prefill) {
        if (autoSend) {
          sendMessage(prefill);
        } else {
          chatInput.value = prefill;
          chatInput.focus();
        }
      }
    };
  });
})();
