/**
 * NyayaDepaaAI 4.0 — Premium Women Safety Legal Advisor
 * Client: sidebar, landing/chat views, clarification buttons, history
 */

(() => {
    'use strict';

    // ── State ─────────────────────────────────────────────
    const state = {
        sessionId: null,
        stage: 'intro',
        isLoading: false,
        messages: [],
        lastQuery: '',
        view: 'welcome', // 'welcome' | 'chat'
        history: JSON.parse(localStorage.getItem('nd_history') || '[]'),
    };

    // ── DOM ───────────────────────────────────────────────
    const $ = (s) => document.querySelector(s);
    const $$ = (s) => document.querySelectorAll(s);

    const sidebar = $('#sidebar');
    const overlay = $('#sidebar-overlay');
    const btnHamburger = $('#btn-hamburger');
    const btnNewSession = $('#btn-new-session');
    const btnStartChat = $('#btn-start-chat');
    const btnHowWorks = $('#btn-how-works');
    const btnCtaChat = $('#btn-cta-chat');
    const btnCtaLearn = $('#btn-cta-learn');
    const statusText = $('#status-text');
    const statusPill = $('#status-pill');
    const languageSelect = $('#language-select');

    const welcomeView = $('#welcome-view');
    const historyList = $('#history-list');
    const consultingDom = $('#consulting-domain');

    // ── API ───────────────────────────────────────────────
    async function apiChat(query) {
        const res = await fetch(`${CHAT_API}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, session_id: state.sessionId, language: languageSelect.value }),
        });
        if (!res.ok) throw new Error(`Server ${res.status}`);
        return res.json();
    }

    async function apiClarify(originalQuery, intent) {
        const res = await fetch(`${CHAT_API}/api/clarify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                original_query: originalQuery,
                selected_intent: intent,
                language: languageSelect.value,
            }),
        });
        if (!res.ok) throw new Error(`Server ${res.status}`);
        return res.json();
    }

    // ── Sidebar ───────────────────────────────────────────
    function openSidebar() { sidebar.classList.add('open'); overlay.classList.add('active'); }
    function closeSidebar() { sidebar.classList.remove('open'); overlay.classList.remove('active'); }
    function toggleSidebar() { sidebar.classList.contains('open') ? closeSidebar() : openSidebar(); }

    // ── Markdown ──────────────────────────────────────────
    function md(text) {
        if (!text) return '';
        let h = text
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

        h = h.replace(/^---$/gm, '<hr>');
        h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        h = h.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
        h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');
        h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
        h = h.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
        h = h.replace(/<\/blockquote>\n<blockquote>/g, '<br>');

        // Tables
        h = h.replace(/^\|(.+)\|$/gm, (match) => {
            const cells = match.split('|').filter(c => c.trim());
            if (cells.every(c => /^[\s\-:]+$/.test(c))) return '';
            const tag = cells.some(c => c.trim().startsWith('**')) ? 'th' : 'td';
            return '<tr>' + cells.map(c => `<${tag}>${c.trim().replace(/\*\*/g, '')}</${tag}>`).join('') + '</tr>';
        });
        h = h.replace(/((?:<tr>.*<\/tr>\n?)+)/g, '<table>$1</table>');

        // Lists
        h = h.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
        h = h.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
        h = h.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

        // Paragraphs
        h = h.split('\n\n').map(b => {
            b = b.trim();
            if (!b || /^<(h[23]|ul|ol|table|blockquote|hr|tr|li)/.test(b)) return b;
            return `<p>${b.replace(/\n/g, '<br>')}</p>`;
        }).join('\n');

        return h;
    }

    // ── UI Helpers ────────────────────────────────────────
    function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
    function trunc(s, n) { return !s ? '' : s.length > n ? s.substring(0, n) + '…' : s; }

    function setStatus(type, text) {
        const dot = statusPill.querySelector('.status-dot-live');
        if (type === 'thinking') {
            dot.style.background = '#a855f7';
            dot.style.boxShadow = '0 0 6px rgba(168,85,247,0.5)';
        } else if (type === 'error') {
            dot.style.background = '#ef4444';
            dot.style.boxShadow = '0 0 6px rgba(239,68,68,0.5)';
        } else {
            dot.style.background = '#22c55e';
            dot.style.boxShadow = '0 0 6px rgba(34,197,94,0.5)';
        }
        statusText.textContent = text;
    }

    // ── History ───────────────────────────────────────────
    function saveToHistory(query) {
        const title = query.length > 40 ? query.substring(0, 40) + '…' : query;
        const entry = { title, time: new Date().toLocaleString(), query };
        state.history.unshift(entry);
        if (state.history.length > 10) state.history.pop();
        localStorage.setItem('nd_history', JSON.stringify(state.history));
        renderHistory();
    }

    function renderHistory() {
        if (!state.history.length) {
            historyList.innerHTML = '<div class="history-empty">No conversations yet</div>';
            return;
        }
        historyList.innerHTML = state.history.map((h, i) => `
            <div class="history-item" data-idx="${i}">
                <div class="history-item-title">${esc(h.title)}</div>
                <div class="history-item-time">${h.time}</div>
            </div>
        `).join('');

        historyList.querySelectorAll('.history-item').forEach(el => {
            el.addEventListener('click', () => {
                const idx = parseInt(el.dataset.idx);
                const q = state.history[idx]?.query;
                if (q) {
                    closeSidebar();
                    if (!cbState.open) cbToggle();
                    if (cbState.stage === 'ready') {
                        setTimeout(() => { cbInput.value = q; cbSendMessage(); }, 400);
                    }
                }
            });
        });
    }

    // ── Events ────────────────────────────────────────────
    btnHamburger.addEventListener('click', toggleSidebar);
    overlay.addEventListener('click', closeSidebar);
    btnNewSession.addEventListener('click', () => { closeSidebar(); if (!cbState.open) cbToggle(); });

    btnStartChat.addEventListener('click', () => { if (!cbState.open) cbToggle(); });
    btnCtaChat.addEventListener('click', () => { if (!cbState.open) cbToggle(); });
    btnHowWorks.addEventListener('click', () => { if (!cbState.open) cbToggle(); });
    btnCtaLearn.addEventListener('click', () => { if (!cbState.open) cbToggle(); });

    // Sidebar topic buttons → open chatbot and send query
    $$('.topic-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const q = btn.dataset.query;
            if (q) {
                closeSidebar();
                if (!cbState.open) cbToggle();
                // If name flow is done, send query directly
                if (cbState.stage === 'ready') {
                    setTimeout(() => { cbInput.value = q; cbSendMessage(); }, 400);
                }
            }
        });
    });

    // Landing topic cards → open chatbot and send query
    $$('.topic-card').forEach(card => {
        card.addEventListener('click', () => {
            const q = card.dataset.query;
            if (q) {
                if (!cbState.open) cbToggle();
                if (cbState.stage === 'ready') {
                    setTimeout(() => { cbInput.value = q; cbSendMessage(); }, 400);
                }
            }
        });
    });

    // Init
    renderHistory();

    // ══════════════════════════════════════════════════════
    //  FLOATING CHATBOT WIDGET
    // ══════════════════════════════════════════════════════
    const cbLauncher = $('#chatbot-launcher');
    const cbPanel = $('#chatbot-panel');
    const cbClose = $('#chatbot-close');
    const cbMessages = $('#chatbot-messages');
    const cbInput = $('#chatbot-input');
    const cbSendBtn = $('#chatbot-send');

    // PDF Modal Elements
    const chatbotBlurOverlay = $('#chatbot-blur-overlay');
    const pdfModal = $('#pdf-modal');
    const btnPdfDownload = $('#btn-pdf-download');
    const btnPdfClose = $('#btn-pdf-close');
    const btnPdfCancel = $('#btn-pdf-cancel');

    const cbState = {
        open: false,
        sessionId: null,
        isLoading: false,
        initialized: false,
        // ── Auth gate state ──
        loggedIn: false,
        userName: '',
        userAge: 0,
        userLanguage: 'English',
        authToken: '',
        userId: '',
    };

    // Auth API: Render backend in production, localhost:8001 for local dev
    const AUTH_API = window.location.hostname === 'localhost'
        ? 'http://localhost:8001/api'
        : 'https://nyayadepaaai-api.onrender.com/api';

    // Chat API: Render AI service in production, localhost:8000 for local dev
    const CHAT_API = window.location.hostname === 'localhost'
        ? ''
        : 'https://nyayadepaaai-chat.onrender.com';

    // ── Login overlay elements ──
    const cbLoginOverlay = $('#cb-login-overlay');
    const cbLoginForm = $('#cb-login-form');
    const cbLoginBtn = $('#cb-login-btn');
    const cbLoginError = $('#cb-login-error');
    const cbLoginNameInput = $('#cb-login-name');
    const cbLoginAgeInput = $('#cb-login-age');
    const cbLoginCityInput = $('#cb-login-city');
    const cbLoginLangSelect = $('#cb-login-lang');
    const cbInputBar = $('#chatbot-input-bar');
    const cbLoginCloseBtn = $('#cb-login-close-btn');

    // ── Helpers ──
    function cbTimeStr() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function cbScrollBottom() {
        requestAnimationFrame(() => { cbMessages.scrollTop = cbMessages.scrollHeight; });
    }

    function cbAddBotMessage(text, options = [], multiSelect = false) {
        const div = document.createElement('div');
        div.className = 'cb-msg cb-msg-bot';

        let html = `<div class="cb-bubble">${text}</div><div class="cb-time">${cbTimeStr()}</div>`;

        if (options && options.length > 0) {
            html += `<div class="cb-inline-actions${multiSelect ? ' cb-multi-select' : ''}">`;
            options.forEach((opt, idx) => {
                const label = typeof opt === 'string' ? opt : opt.label;
                const query = typeof opt === 'string' ? opt : (opt.query || opt.label);
                html += `<button class="cb-inline-chip" data-idx="${idx}" data-query="${esc(query)}">${esc(label)}</button>`;
            });
            if (multiSelect) {
                html += `<button class="cb-multi-submit">Submit Selected</button>`;
            }
            html += `</div>`;
        }

        div.innerHTML = html;
        cbMessages.appendChild(div);

        if (options && options.length > 0) {
            const chips = div.querySelectorAll('.cb-inline-chip');
            const submitBtn = div.querySelector('.cb-multi-submit');

            if (multiSelect && submitBtn) {
                // Add a hidden text input for "Other" option
                const otherInput = document.createElement('input');
                otherInput.type = 'text';
                otherInput.className = 'cb-other-input';
                otherInput.placeholder = 'Type your evidence here...';
                otherInput.style.display = 'none';
                // Insert before the submit button
                submitBtn.parentNode.insertBefore(otherInput, submitBtn);

                // Multi-select mode: toggle chips, submit sends all selected
                chips.forEach(btn => {
                    btn.addEventListener('click', () => {
                        if (cbState.isLoading) return;
                        btn.classList.toggle('selected');
                        // Toggle the text input when "Other" chip is selected
                        if (btn.dataset.query.toLowerCase().includes('other')) {
                            otherInput.style.display = btn.classList.contains('selected') ? 'block' : 'none';
                            if (btn.classList.contains('selected')) otherInput.focus();
                        }
                    });
                });
                submitBtn.addEventListener('click', () => {
                    if (cbState.isLoading) return;
                    const selected = [];
                    chips.forEach(b => {
                        if (b.classList.contains('selected')) {
                            // Skip "Other" chip label — use the typed text instead
                            if (!b.dataset.query.toLowerCase().includes('other')) {
                                selected.push(b.dataset.query);
                            }
                        }
                    });
                    // Include free-text from "Other" input
                    const otherText = otherInput.value.trim();
                    if (otherText) selected.push(otherText);

                    if (selected.length === 0) {
                        selected.push('No evidence yet');
                    }
                    // Disable all chips and submit
                    chips.forEach(b => { b.disabled = true; });
                    submitBtn.disabled = true;
                    otherInput.disabled = true;
                    submitBtn.textContent = 'Submitted \u2713';
                    cbInput.value = selected.join(', ');
                    cbSendMessage();
                });
            } else {
                // Single-select mode (original behavior)
                chips.forEach(btn => {
                    btn.addEventListener('click', () => {
                        if (cbState.isLoading) return;
                        chips.forEach(b => {
                            b.disabled = true;
                            if (b === btn) b.classList.add('selected');
                        });
                        const q = btn.dataset.query;
                        cbInput.value = q;
                        cbSendMessage();
                    });
                });
            }
        }

        cbScrollBottom();
    }

    function cbAddUserMessage(text) {
        const div = document.createElement('div');
        div.className = 'cb-msg cb-msg-user';
        div.innerHTML = `<div class="cb-bubble">${esc(text)}</div><div class="cb-time">${cbTimeStr()}</div>`;
        cbMessages.appendChild(div);
        cbScrollBottom();
    }

    function cbShowTyping() {
        const div = document.createElement('div');
        div.className = 'cb-typing';
        div.id = 'cb-typing';
        div.innerHTML = '<span></span><span></span><span></span>';
        cbMessages.appendChild(div);
        cbScrollBottom();
    }

    function cbHideTyping() {
        document.getElementById('cb-typing')?.remove();
    }

    // ── Toggle ──
    function promptCloseChat() {
        if (!cbState.open) return;
        pdfModal.classList.add('active');
    }

    function doCloseChat() {
        pdfModal.classList.remove('active');
        cbState.open = false;
        cbPanel.classList.remove('open');
        cbPanel.classList.remove('login-mode');
        cbLauncher.classList.remove('active');
        chatbotBlurOverlay.classList.remove('active');

        // Swap back to original avatar icon
        const iconOpen = document.getElementById('chatbot-icon-open');
        const iconNamaste = document.getElementById('chatbot-icon-namaste');
        if (iconOpen) iconOpen.style.display = 'block';
        if (iconNamaste) iconNamaste.style.display = 'none';

        // Reset PDF button text just in case
        btnPdfDownload.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            Download PDF & End
        `;
    }

    function cbToggle() {
        if (cbState.open) {
            promptCloseChat();
            return;
        }

        cbState.open = true;
        cbPanel.classList.add('open');
        cbLauncher.classList.add('active');
        chatbotBlurOverlay.classList.add('active');

        // Swap to namaste icon
        const iconOpen = document.getElementById('chatbot-icon-open');
        const iconNamaste = document.getElementById('chatbot-icon-namaste');
        if (iconOpen) iconOpen.style.display = 'none';
        if (iconNamaste) iconNamaste.style.display = 'block';

        if (!cbState.loggedIn) {
            // Show login gate — hide chat & input, compact mode
            cbPanel.classList.add('login-mode');
            cbLoginOverlay.style.display = 'flex';
            cbMessages.style.display = 'none';
            cbInputBar.style.display = 'none';
            setTimeout(() => cbLoginNameInput.focus(), 350);
        } else {
            // Already logged in — show chat, full mode
            cbPanel.classList.remove('login-mode');
            cbLoginOverlay.style.display = 'none';
            cbMessages.style.display = 'flex';
            cbInputBar.style.display = 'flex';
            if (!cbState.initialized) {
                cbState.initialized = true;
                cbInitSession();
            }
            setTimeout(() => cbInput.focus(), 350);
        }
    }

    // ── Login form handler ──
    cbLoginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = cbLoginNameInput.value.trim();
        const age = parseInt(cbLoginAgeInput.value, 10);
        const city = cbLoginCityInput.value.trim();
        const lang = cbLoginLangSelect.value;

        if (!name || name.length < 2) {
            cbLoginError.textContent = 'Please enter a valid name (at least 2 characters).';
            cbLoginError.style.display = 'block';
            return;
        }
        if (!age || age < 1 || age > 150) {
            cbLoginError.textContent = 'Please enter a valid age.';
            cbLoginError.style.display = 'block';
            return;
        }
        if (!city || city.length < 2) {
            cbLoginError.textContent = 'Please enter your city (at least 2 characters).';
            cbLoginError.style.display = 'block';
            return;
        }

        cbLoginBtn.disabled = true;
        cbLoginBtn.innerHTML = 'Connecting… <span class="cb-login-spinner"></span>';
        cbLoginError.style.display = 'none';

        try {
            const res = await fetch(`${AUTH_API}/auth/guest-login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, age, city }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Server error ${res.status}`);
            }
            const data = await res.json();

            // Store auth state
            cbState.loggedIn = true;
            cbState.userName = data.user.name;
            cbState.userAge = data.user.age;
            cbState.userLanguage = lang;
            cbState.authToken = data.access_token;
            cbState.userId = data.user.id;
            localStorage.setItem('nd_auth_token', data.access_token);
            localStorage.setItem('nd_user_name', data.user.name);

            // Sync the hidden language select so legacy code stays compatible
            languageSelect.value = lang;

            // Hide login overlay, show chat — expand to full mode
            cbLoginOverlay.style.display = 'none';
            cbPanel.classList.remove('login-mode');
            cbMessages.style.display = 'flex';
            cbInputBar.style.display = 'flex';

            // Init session passing name + language so backend skips greeting & lang question
            if (!cbState.initialized) {
                cbState.initialized = true;
                await cbInitSession();
            }

            setTimeout(() => cbInput.focus(), 350);
        } catch (err) {
            cbLoginError.textContent = err.message || 'Connection failed. Please try again.';
            cbLoginError.style.display = 'block';
        } finally {
            cbLoginBtn.disabled = false;
            cbLoginBtn.innerHTML = 'Start Consultation <span class="cb-login-arrow">→</span>';
        }
    });

    cbLauncher.addEventListener('click', () => {
        if (cbState.open) promptCloseChat();
        else cbToggle();
    });
    cbClose.addEventListener('click', promptCloseChat);

    // Close button inside login overlay (closes without PDF prompt)
    if (cbLoginCloseBtn) {
        cbLoginCloseBtn.addEventListener('click', () => {
            doCloseChat();
        });
    }

    // ── Initialize Session ──
    async function cbInitSession() {
        cbState.isLoading = true;
        cbShowTyping();

        try {
            const res = await fetch(`${CHAT_API}/api/new_session`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: cbState.userName || undefined,
                    language: cbState.userLanguage || 'English',
                }),
            });
            if (!res.ok) throw new Error(`Server ${res.status}`);
            const result = await res.json();
            cbState.sessionId = result.session_id;

            cbHideTyping();

            const options = result.options || result.suggestions || [];
            const multiSelect = result.multi_select || false;
            cbAddBotMessage(md(result.response), options, multiSelect);
        } catch (err) {
            cbHideTyping();
            cbAddBotMessage(`⚠️ Sorry, something went wrong. Please try again.<br><small>${esc(err.message)}</small>`);
        }

        cbState.isLoading = false;
        if (cbState.open) cbInput.focus();
    }

    // ── Send Message ──
    async function cbSendMessage(isSilent = false) {
        const text = cbInput.value.trim();
        if (!text || cbState.isLoading) return;

        cbInput.value = '';
        if (!isSilent) {
            cbAddUserMessage(text);
        }

        cbState.isLoading = true;
        cbShowTyping();

        try {
            const res = await fetch(`${CHAT_API}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: text,
                    session_id: cbState.sessionId,
                    language: cbState.userLanguage || languageSelect.value,
                }),
            });
            if (!res.ok) throw new Error(`Server ${res.status}`);
            const result = await res.json();
            cbState.sessionId = result.session_id;

            cbHideTyping();

            // Pass options if the API returns them
            const options = result.options || result.suggestions || [];
            const multiSelect = result.multi_select || false;

            // Split multi-section responses into separate chat bubbles
            const responseText = result.response || '';
            const sectionCount = (responseText.match(/^### /gm) || []).length;

            if (sectionCount >= 2) {
                const sections = responseText
                    .split(/(?=^### )/m)
                    .map(s => s.replace(/^---\s*$/gm, '').trim())
                    .filter(s => s.length > 0);

                sections.forEach((section, i) => {
                    const isLast = i === sections.length - 1;
                    cbAddBotMessage(md(section), isLast ? options : [], isLast ? multiSelect : false);
                });
            } else {
                cbAddBotMessage(md(responseText), options, multiSelect);
            }

            // Log query + response to auth DB for admin visibility
            logQueryToAuthDB(text, responseText);
        } catch (err) {
            cbHideTyping();
            cbAddBotMessage(`⚠️ Sorry, something went wrong. Please try again.<br><small>${esc(err.message)}</small>`);
        }

        cbState.isLoading = false;
        if (cbState.open) cbInput.focus();
    }

    cbSendBtn.addEventListener('click', cbSendMessage);
    cbInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); cbSendMessage(); }
    });

    // ── Log chatbot query+response to auth DB for admin ──
    async function logQueryToAuthDB(inputText, responseText) {
        if (!cbState.authToken) return;
        try {
            await fetch(`${AUTH_API}/ai/log-chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${cbState.authToken}`,
                },
                body: JSON.stringify({ input_text: inputText, response_text: responseText }),
            });
        } catch (_) { /* silent — don't break chat for logging failure */ }
    }

    // ── PDF Generation Logic ──
    btnPdfDownload.addEventListener('click', () => {
        const element = document.createElement('div');

        // ── Extract all messages from the live chat DOM ──────────────────
        const allMsgs = Array.from(cbMessages.querySelectorAll('.cb-msg'));

        // Try to pick up the user's name from the first user bubble
        let userName = 'User';
        const firstUserBubble = cbMessages.querySelector('.cb-msg-user .cb-bubble');
        if (firstUserBubble) {
            const txt = firstUserBubble.textContent.trim();
            const nameMatch = txt.match(/(?:my name is|i am|call me)\s+([a-zA-Z]+)/i);
            if (nameMatch) userName = nameMatch[1];
            else if (txt.split(/\s+/).length <= 3 && txt.length < 25) userName = txt;
        }

        // Session ID for reference
        const sessionRef = (cbState.sessionId || 'N/A').substring(0, 8).toUpperCase();
        const now = new Date();
        const dateStr = now.toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
        const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

        // ── Build message rows ────────────────────────────────────────────
        let msgIdx = 0;
        const messagesHtml = allMsgs.map(msg => {
            const isUser = msg.classList.contains('cb-msg-user');
            const bubble = msg.querySelector('.cb-bubble');
            const timeEl = msg.querySelector('.cb-time');
            const bubbleHtml = bubble ? bubble.innerHTML : '';
            const timeText = timeEl ? timeEl.textContent : '';

            if (isUser) {
                // User message — right-aligned purple bubble
                msgIdx++;
                return `
                <div style="margin-bottom:18px; display:flex; justify-content:flex-end;">
                    <div style="max-width:78%;">
                        <div style="font-size:11px; color:#9ca3af; text-align:right; margin-bottom:4px;">
                            You &nbsp;·&nbsp; ${timeText}
                        </div>
                        <div style="background:#7c3aed; color:#fff; padding:12px 16px; border-radius:16px 16px 4px 16px; font-size:14px; line-height:1.6;">
                            ${bubbleHtml}
                        </div>
                    </div>
                </div>`;
            } else {
                // Bot message — left-aligned with NyayaDepaaAI label
                return `
                <div style="margin-bottom:22px; display:flex; align-items:flex-start; gap:12px;">
                    <div style="flex-shrink:0; width:34px; height:34px; background:linear-gradient(135deg,#7c3aed,#a855f7); border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; font-size:13px; font-weight:700;">N</div>
                    <div style="max-width:85%;">
                        <div style="font-size:11px; color:#9ca3af; margin-bottom:4px;">
                            NyayaDepaaAI &nbsp;·&nbsp; ${timeText}
                        </div>
                        <div style="background:#f9fafb; border:1px solid #e5e7eb; color:#111827; padding:14px 18px; border-radius:4px 16px 16px 16px; font-size:14px; line-height:1.7;">
                            ${bubbleHtml}
                        </div>
                    </div>
                </div>`;
            }
        }).join('');

        // ── Assemble full legal report ────────────────────────────────────
        element.innerHTML = `
        <div style="font-family:'Segoe UI',Helvetica,Arial,sans-serif; max-width:800px; margin:0 auto; padding:32px; color:#111827;">

            <!-- Header -->
            <div style="border-bottom:3px solid #7c3aed; padding-bottom:18px; margin-bottom:28px;">
                <div style="display:flex; align-items:center; gap:14px; margin-bottom:10px;">
                    <div style="width:46px; height:46px; background:linear-gradient(135deg,#7c3aed,#a855f7); border-radius:12px; display:flex; align-items:center; justify-content:center; color:white; font-size:22px; font-weight:900;">N</div>
                    <div>
                        <h1 style="margin:0; font-size:22px; font-weight:800; color:#6d28d9;">NyayaDepaaAI — Legal Consultation Report</h1>
                        <p style="margin:2px 0 0 0; font-size:13px; color:#9ca3af;">AI-Powered Women Safety Legal Advisor · India</p>
                    </div>
                </div>
                <table style="width:100%; font-size:13px; color:#374151; border-collapse:collapse;">
                    <tr>
                        <td style="padding:3px 0; width:50%;"><strong>Client Name:</strong> ${userName}</td>
                        <td style="padding:3px 0;"><strong>Session Ref:</strong> #${sessionRef}</td>
                    </tr>
                    <tr>
                        <td style="padding:3px 0;"><strong>Date:</strong> ${dateStr}</td>
                        <td style="padding:3px 0;"><strong>Time:</strong> ${timeStr}</td>
                    </tr>
                </table>
                <div style="margin-top:10px; padding:8px 12px; background:#fef3c7; border-left:4px solid #f59e0b; border-radius:4px; font-size:12px; color:#92400e;">
                    ⚠️ <strong>Confidentiality Notice:</strong> This document contains personal legal information. It is intended solely for the named recipient. This is AI-generated guidance and does not constitute legal advice. Please consult a qualified advocate for your specific situation.
                </div>
            </div>

            <!-- Conversation -->
            <h2 style="font-size:16px; font-weight:700; color:#374151; border-bottom:1px solid #e5e7eb; padding-bottom:8px; margin-bottom:20px;">
                📋 Full Legal Consultation Transcript
            </h2>
            ${messagesHtml}

            <!-- Footer -->
            <div style="margin-top:36px; padding-top:16px; border-top:1px solid #e5e7eb; font-size:11px; color:#9ca3af; text-align:center;">
                Generated by NyayaDepaaAI · ${dateStr} · ${timeStr}<br>
                This document is confidential. For legal advice, contact a registered advocate.<br>
                Women Helpline: <strong>181</strong> &nbsp;|&nbsp; Police: <strong>100</strong> &nbsp;|&nbsp; NCW WhatsApp: <strong>7217735372</strong> &nbsp;|&nbsp; Cyber Crime: <strong>1930</strong>
            </div>
        </div>`;

        const opt = {
            margin: [10, 8, 10, 8],
            filename: `NyayaDepaaAI_Report_${userName.replace(/\s+/g, '_')}_${now.toISOString().slice(0, 10)}.pdf`,
            image: { type: 'jpeg', quality: 0.97 },
            html2canvas: { scale: 2, useCORS: true, logging: false },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
        };

        if (window.html2pdf) {
            btnPdfDownload.innerHTML = 'Generating PDF...';
            html2pdf().set(opt).from(element).save().then(() => {
                btnPdfDownload.innerHTML = 'Downloaded ✅';
                setTimeout(() => doCloseChat(), 1000);
            });
        } else {
            alert("PDF library is still loading. Please try again in a moment.");
            doCloseChat();
        }
    });

    btnPdfClose.addEventListener('click', doCloseChat);
    btnPdfCancel.addEventListener('click', () => {
        pdfModal.classList.remove('active');
    });

})();
