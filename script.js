javascript:(function(){
  const API_BASE = 'https://5b7a0633-a297-4047-b0ee-a4bde446805d-00-1ntphoomm251x.kirk.replit.dev'; // Change this to your server URL
  // Auth state
  const FREE_TIER_DAILY_LIMIT = 8;

  // Create and inject styles
  const style = document.createElement('style');
  style.textContent = `
    .qt-menu { 
      position: fixed; 
      top: 20px; 
      left: 20px; 
      z-index: 999999; 
      background: linear-gradient(145deg, rgba(25,25,25,0.98), rgba(15,15,15,0.98));
      border: 1px solid rgba(255,215,0,0.15);
      border-radius: 12px;
      padding: 15px;
      width: 320px;
      color: #fff;
      font-family: system-ui;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
      backdrop-filter: blur(12px);
      user-select: none;
      transition: transform 0.2s;
    }
    .qt-header { 
      display: flex; 
      justify-content: space-between; 
      align-items: center;
      margin: -15px -15px 15px -15px;
      padding: 15px;
      border-bottom: 1px solid rgba(255,215,0,0.1);
      cursor: move;
      background: rgba(255,215,0,0.02);
      border-radius: 12px 12px 0 0;
      position: relative;
    }
    .qt-balance {
      position: absolute;
      top: 15px;
      right: 50px;
      color: rgba(100, 255, 100, 0.8);
      font-size: 14px;
      font-weight: 500;
    }
    .qt-usage {
      font-size: 11px;
      color: rgba(255,215,0,0.6);
      text-align: right;
      margin-top: 4px;
    }
    .qt-title {
      color: rgba(255,215,0,0.9);
      font-weight: 500;
      font-size: 14px;
    }
    .qt-btn { 
      background: rgba(255,215,0,0.1);
      border: 1px solid rgba(255,215,0,0.2);
      color: rgba(255,215,0,0.8);
      padding: 8px 12px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 13px;
      transition: all 0.2s;
    }
    .qt-btn:hover { 
      background: rgba(255,215,0,0.2);
      transform: translateY(-1px);
    }
    .qt-result { 
      margin-top: 15px;
      padding: 12px;
      background: rgba(255,215,0,0.05);
      border-radius: 8px;
      font-size: 13px;
      line-height: 1.5;
    }
    .qt-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 15px;
    }
    .qt-tab {
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      color: rgba(255,215,0,0.6);
      transition: all 0.2s;
    }
    .qt-tab.active {
      background: rgba(255,215,0,0.1);
      color: rgba(255,215,0,0.9);
    }
    .qt-tab-content {
      display: none;
    }
    .qt-tab-content.active {
      display: block;
    }
    .qt-login {
      position: absolute;
      inset: 0;
      background: rgba(0,0,0,0.95);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border-radius: 12px;
      z-index: 2;
      padding: 20px;
    }
    .qt-login-title {
      color: rgba(255,215,0,0.9);
      font-size: 18px;
      font-weight: 500;
      margin-bottom: 15px;
    }
    .qt-login-form {
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .qt-input {
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,215,0,0.2);
      padding: 8px 12px;
      border-radius: 6px;
      color: white;
      font-size: 13px;
    }
    .qt-input::placeholder {
      color: rgba(255,255,255,0.5);
    }
    .qt-highlight { 
      outline: 2px solid orange !important;
      outline-offset: 2px !important;
      cursor: pointer !important;
    }
    .qt-selected { 
      outline: 2px solid #4CAF50 !important;
      outline-offset: 2px !important;
    }
    .qt-confidence {
      margin-top: 10px;
      height: 4px;
      background: rgba(255,215,0,0.1);
      border-radius: 2px;
      overflow: hidden;
    }
    .qt-confidence-fill {
      height: 100%;
      background: rgba(255,215,0,0.8);
      border-radius: 2px;
      width: 0%;
      transition: width 0.3s ease;
    }
    .qt-loading {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255,215,0,0.3);
      border-top: 2px solid rgba(255,215,0,0.9);
      border-radius: 50%;
      animation: qt-spin 1s linear infinite;
      margin-right: 8px;
    }
    @keyframes qt-spin {
      to { transform: rotate(360deg); }
    }
    .qt-error {
      color: #ff6b6b;
      font-size: 12px;
      margin-top: 8px;
      text-align: center;
    }
  `;
  document.head.appendChild(style);

  // Create menu
  const menu = document.createElement('div');
  menu.className = 'qt-menu';
  menu.innerHTML = `
    <div class="qt-header">
      <div class="qt-title">Question Solver</div>
      <div class="qt-balance">$0.00</div>
      <div class="qt-usage"></div>
      <button class="qt-btn" style="padding:4px 8px" onclick="this.parentElement.parentElement.remove()">×</button>
    </div>
    <div class="qt-tabs">
      <div class="qt-tab active" data-tab="solve">Solve</div>
      <div class="qt-tab" data-tab="config">Settings</div>
    </div>
    <div class="qt-tab-content active" data-tab="solve">
      <button class="qt-btn" id="qt-select">Select Question</button>
      <div id="qt-result" class="qt-result" style="display:none"></div>
      <div class="qt-confidence">
        <div class="qt-confidence-fill"></div>
      </div>
    </div>
    <div class="qt-tab-content" data-tab="config">
      <div class="qt-config-group">
        <select class="qt-input" id="qt-model">
          <option value="gpt4o-mini">GPT-4O-Mini (Default)</option>
          <option value="gpt4o">GPT-4O (Advanced)</option>
          <option value="claude">Claude 3.5 (Best)</option>
        </select>
      </div>
      <div style="margin-top:8px">
        <label class="qt-checkbox">
          <input type="checkbox" id="qt-autofill" checked>
          Auto-fill answers
        </label>
      </div>
    </div>
    <div class="qt-login">
      <div class="qt-login-title">Login Required</div>
      <form class="qt-login-form" id="qt-login-form">
        <input type="text" class="qt-input" placeholder="Username" id="qt-username" required>
        <input type="password" class="qt-input" placeholder="Password" id="qt-password" required>
        <button type="submit" class="qt-btn">Login</button>
        <div class="qt-error" style="display:none"></div>
      </form>
    </div>
  `;

  // Add menu to page
  document.body.appendChild(menu);

  // Auth state
  let authToken = null;
  let userInfo = null;
  let usageCount = 0;
  const DAILY_LIMIT = 8;

  // Get DOM elements
  const loginForm = menu.querySelector('#qt-login-form');
  const loginError = menu.querySelector('.qt-error');
  const loginSection = menu.querySelector('.qt-login');
  const balanceDisplay = menu.querySelector('.qt-balance');
  const usageDisplay = menu.querySelector('.qt-usage');
  const titleDisplay = menu.querySelector('.qt-title');
  const selectBtn = menu.querySelector('#qt-select');
  const modelSelect = menu.querySelector('#qt-model');
  const resultDisplay = menu.querySelector('#qt-result');
  const confidenceFill = menu.querySelector('.qt-confidence-fill');

  // Make menu draggable
  let isDragging = false;
  const header = menu.querySelector('.qt-header');
  header.addEventListener('mousedown', e => {
    if (e.target.tagName === 'BUTTON') return;
    isDragging = true;
    const rect = menu.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;

    function onMouseMove(e) {
      if (!isDragging) return;
      menu.style.left = (e.clientX - offsetX) + 'px';
      menu.style.top = (e.clientY - offsetY) + 'px';
    }

    function onMouseUp() {
      isDragging = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    }

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });

  // Tab switching
  menu.querySelectorAll('.qt-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      menu.querySelectorAll('.qt-tab').forEach(t => t.classList.remove('active'));
      menu.querySelectorAll('.qt-tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      menu.querySelector(`.qt-tab-content[data-tab="${tab.dataset.tab}"]`).classList.add('active');
    });
  });

  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.querySelector('#qt-username').value;
    const password = document.querySelector('#qt-password').value;

    try {
      const response = await fetch(`${API_BASE}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        throw new Error('Invalid credentials');
      }

      const data = await response.json();
      authToken = data.token;
      userInfo = data.user;

      // Update UI
      if (userInfo.is_free_tier) {
        balanceDisplay.textContent = `Free Tier`;
      } else {
        balanceDisplay.textContent = `$${userInfo.credits.toFixed(2)}`;
      }
      titleDisplay.textContent = `Question Solver (${username})`;
      loginSection.style.display = 'none';

      // Reset usage counter
      usageCount = 0;
      updateUsageDisplay();

    } catch (error) {
      loginError.textContent = error.message;
      loginError.style.display = 'block';
    }
  });

  function updateUsageDisplay() {
    if (userInfo?.is_free_tier) {
      usageDisplay.textContent = `Free Usage: ${usageCount}/${FREE_TIER_DAILY_LIMIT}`;
    } else {
      usageDisplay.textContent = ``;
    }
  }


  // Selection handling
  let selecting = false;
  let selected = null;

  selectBtn.addEventListener('click', () => {
    if (!authToken) {
      loginError.textContent = 'Please login first';
      loginError.style.display = 'block';
      return;
    }

    if (userInfo.is_free_tier && usageCount >= DAILY_LIMIT) {
      alert('Daily usage limit reached. Please upgrade your account.');
      return;
    }

    selecting = !selecting;
    selectBtn.textContent = selecting ? 'Cancel' : 'Select Question';
  });

  // Hover effects
  document.addEventListener('mouseover', e => {
    if (!selecting) return;
    if (e.target === menu || menu.contains(e.target)) return;
    e.target.classList.add('qt-highlight');
  });

  document.addEventListener('mouseout', e => {
    if (!selecting) return;
    e.target.classList.remove('qt-highlight');
  });

  // Question selection and processing
  document.addEventListener('click', async e => {
    if (!selecting || !authToken) return;
    if (e.target === menu || menu.contains(e.target)) return;
    e.preventDefault();

    if (selected) selected.classList.remove('qt-selected');
    selected = e.target;
    selected.classList.add('qt-selected');
    selecting = false;
    selectBtn.textContent = 'Select Question';

    resultDisplay.style.display = 'block';
    resultDisplay.innerHTML = '<div class="qt-loading"></div>Analyzing...';

    try {
      const questionText = selected.innerText.trim();
      const model = modelSelect.value;

      const response = await fetch(`${API_BASE}/api/solve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ text: questionText, model })
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const data = await response.json();

      // Update usage and credits
      usageCount++;
      updateUsageDisplay();

      if (!userInfo.is_free_tier) {
        userInfo.credits -= data.cost;
        balanceDisplay.textContent = `$${userInfo.credits.toFixed(2)}`;
        balanceDisplay.style.color = userInfo.credits < 0.5 ? 'rgba(255,100,100,0.8)' : 'rgba(100,255,100,0.8)';
      }


      // Update confidence
      confidenceFill.style.width = data.response.confidence + '%';

      // Show result
      const content = document.createDocumentFragment();

      const answerDiv = document.createElement('div');
      answerDiv.innerHTML = '<strong>Answer:</strong> ' + data.response.answer;
      content.appendChild(answerDiv);

      const explainDiv = document.createElement('div');
      explainDiv.style.marginTop = '8px';
      explainDiv.innerHTML = '<strong>Explanation:</strong> ' + data.response.explanation;
      content.appendChild(explainDiv);

      const costDiv = document.createElement('div');
      costDiv.style.marginTop = '8px';
      costDiv.style.fontSize = '12px';
      costDiv.style.color = 'rgba(255,215,0,0.7)';
      costDiv.textContent = `Cost: ${data.cost.toFixed(4)}${data.cached ? ' (cached)' : ''}`;
      content.appendChild(costDiv);

      // Add apply button if auto-fill is enabled
      if (document.querySelector('#qt-autofill').checked) {
        const applyBtn = document.createElement('button');
        applyBtn.className = 'qt-btn';
        applyBtn.style.marginTop = '12px';
        applyBtn.style.width = '100%';
        applyBtn.textContent = 'Apply Answer';

        applyBtn.onclick = () => {
          // Find answer input field
          const inputs = [
            ...document.querySelectorAll('input[type="text"]'),
            ...document.querySelectorAll('textarea'),
            ...document.querySelectorAll('input.answer-text'),
            ...document.querySelectorAll('[contenteditable="true"]')
          ];

          const answerInput = inputs.find(input => {
            const rect = input.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && !input.disabled;
          });

          if (answerInput) {
            // Apply answer
            if (answerInput.isContentEditable) {
              answerInput.textContent = data.response.answer;
            } else {
              answerInput.value = data.response.answer;
              // Trigger events
              answerInput.dispatchEvent(new Event('input', { bubbles: true }));
              answerInput.dispatchEvent(new Event('change', { bubbles: true }));
            }

            // Find and click next/submit button
            setTimeout(() => {
              const buttons = Array.from(document.querySelectorAll('button, .btn, .button, [role="button"]'))
                .filter(btn => {
                  const text = btn.textContent.toLowerCase();
                  return text.includes('next') || text.includes('continue') || text.includes('submit');
                });

              if (buttons.length > 0) {
                buttons[0].click();
              }
            }, 500);
          }
        };

        content.appendChild(applyBtn);
        // Auto-click apply button
        setTimeout(() => applyBtn.click(), 100);
      }

      resultDisplay.textContent = '';
      resultDisplay.appendChild(content);

    } catch (error) {
      resultDisplay.innerHTML = `<div class="qt-error">Error: ${error.message}</div>`;
    }
    });

  // Cost estimation
  modelSelect.addEventListener('change', () => {
    const model = modelSelect.value;
    const costs = {
      'gpt4o': { input: 0.0025, output: 0.00125 },
      'gpt4o-mini': { input: 0.00015, output: 0.000075 },
      'claude': { input: 0.003, output: 0.00375 }
    };

    const selectedText = selected?.innerText.trim() || '';
    const chars = selectedText.length;
    const cost = costs[model];
    const totalCost = ((chars / 1000) * cost.input + (chars * 1.5 / 1000) * cost.output) * 5;

    const costDisplay = menu.querySelector('.qt-config-group');
    costDisplay.innerHTML += `<div style="font-size:11px;color:rgba(255,215,0,0.6);margin-top:4px">
      Estimated cost: ${totalCost.toFixed(4)}
    </div>`;
  });

  // Add keyboard shortcut (Alt + Q) to toggle selection
  document.addEventListener('keydown', e => {
    if (e.altKey && e.key === 'q' && authToken) {
      selectBtn.click();
    }
  });

  // Local storage for preferences
  const savedModel = localStorage.getItem('qt-model');
  if (savedModel) {
    modelSelect.value = savedModel;
  }
  modelSelect.addEventListener('change', () => {
    localStorage.setItem('qt-model', modelSelect.value);
  });

  // Check token validity periodically
  setInterval(async () => {
    if (authToken) {
      try {
        const response = await fetch(`${API_BASE}/api/verify`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) {
          authToken = null;
          loginSection.style.display = 'flex';
          loginError.textContent = 'Session expired. Please login again.';
          loginError.style.display = 'block';
        }
      } catch (error) {
        console.error('Token verification failed:', error);
      }
    }
  }, 300000); // Check every 5 minutes

  })();
