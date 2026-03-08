const chatHistory = document.getElementById('chat-history');
const chatInput = document.getElementById('chat-input');
const typingIndicator = document.getElementById('typing-indicator');
const catSprite = document.getElementById('cat-sprite');
const toggleMusicBtn = document.getElementById('toggle-music');
const bgMusic = document.getElementById('bg-music');
const sfxPurr = document.getElementById('sfx-purr');
const sfxMeow = document.getElementById('sfx-meow');

// Audio toggle
let musicPlaying = false;
toggleMusicBtn.addEventListener('click', () => {
    if (musicPlaying) {
        bgMusic.pause();
        toggleMusicBtn.innerText = "🔊 Play Music";
    } else {
        bgMusic.play();
        toggleMusicBtn.innerText = "🔇 Pause Music";
    }
    musicPlaying = !musicPlaying;
});

// Auto-resize textarea
chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// WebSocket Connection
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

ws.onopen = () => {
    console.log('Connected to AI server');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'chat') {
        appendMessage(data.text, data.sender);
    } else if (data.type === 'typing') {
        if (data.state) {
            typingIndicator.classList.remove('hidden');
            scrollToBottom();
        } else {
            typingIndicator.classList.add('hidden');
        }
    } else if (data.type === 'action') {
        setCatAction(data.action);
    } else if (data.type === 'sound') {
        if (data.sound === 'purr') {
            sfxPurr.currentTime = 0;
            sfxPurr.play();
        } else if (data.sound === 'meow') {
            sfxMeow.currentTime = 0;
            sfxMeow.play();
        }
    }
};

ws.onclose = () => {
    appendMessage("Connection lost. Please refresh.", "error");
};

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (text) {
            appendMessage(text, "user");
            ws.send(JSON.stringify({ type: 'chat', text: text }));
            chatInput.value = '';
            chatInput.style.height = 'auto';
        }
    }
});

function appendMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message msg-${sender}`;
    
    let prefix = "";
    if (sender === 'user') prefix = "You: ";
    else if (sender === 'eve') prefix = "Eve: ";
    
    // Cleanup prefix if backend sent it
    if (sender === 'eve') text = text.replace("WhiteCar: ", "");
    
    if (prefix) {
        const span = document.createElement('span');
        span.className = 'msg-prefix';
        span.innerText = prefix;
        div.appendChild(span);
    }
    
    // Preserve newlines
    const textNode = document.createTextNode(text);
    div.appendChild(textNode);
    div.innerHTML = div.innerHTML.replace(/\n/g, '<br>');
    
    chatHistory.appendChild(div);
    scrollToBottom();
}

function scrollToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

const ACTIONS = ["idle", "run", "rush", "damage", "die"];
function setCatAction(actionId) {
    const actionName = ACTIONS[actionId] || "idle";
    catSprite.className = `cat-${actionName}`;
}

// Interactive clicking on game area
const gameArea = document.getElementById('game-area');
gameArea.addEventListener('mousedown', () => {
    ws.send(JSON.stringify({ type: 'pet' }));
    setCatAction(3); // damage/pet animation locally for instant feedback
});
gameArea.addEventListener('mouseup', () => {
    setCatAction(0);
});
