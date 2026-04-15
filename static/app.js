'use strict';

// ── State ────────────────────────────────────────────────────────────────────
let uploadedFiles = [];
let pollTimer     = null;

// ── Guiding questions ────────────────────────────────────────────────────────
function addQuestion(defaultValue) {
  const list = document.getElementById('questions-list');
  const row  = document.createElement('div');
  row.className = 'question-row';
  row.innerHTML = `
    <input type="text"
           placeholder="e.g. What are the ethical implications?"
           value="${defaultValue ? escapeAttr(defaultValue) : ''}" />
    <button class="btn-remove" title="Remove" onclick="removeQuestion(this)">×</button>
  `;
  list.appendChild(row);
  row.querySelector('input').focus();
}

function removeQuestion(btn) {
  btn.closest('.question-row').remove();
}

function getQuestions() {
  return Array.from(document.querySelectorAll('.question-row input'))
    .map(i => i.value.trim())
    .filter(Boolean);
}

// ── File handling ────────────────────────────────────────────────────────────
function setupFileUpload() {
  const zone  = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');

  zone.addEventListener('click', (e) => {
    // Prevent double-trigger if user clicked the browse link
    if (!e.target.classList.contains('upload-link')) input.click();
  });

  input.addEventListener('change', () => {
    addFiles(input.files);
    input.value = ''; // reset so same files can be re-added
  });

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });

  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));

  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    addFiles(e.dataTransfer.files);
  });
}

function addFiles(fileList) {
  const supported = new Set(['.pdf', '.docx', '.txt', '.md', '.markdown']);
  for (const f of fileList) {
    const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase();
    if (!supported.has(ext)) continue;
    // Deduplicate by name+size
    if (!uploadedFiles.some(u => u.name === f.name && u.size === f.size)) {
      uploadedFiles.push(f);
    }
  }
  renderFileList();
}

function removeFile(idx) {
  uploadedFiles.splice(idx, 1);
  renderFileList();
}

function renderFileList() {
  const list = document.getElementById('file-list');
  list.innerHTML = uploadedFiles.map((f, i) => `
    <div class="file-row">
      <div class="file-info">
        <span class="file-name">${escapeHtml(f.name)}</span>
        <span class="file-size">${fmtBytes(f.size)}</span>
      </div>
      <button class="btn-remove" title="Remove" onclick="removeFile(${i})">×</button>
    </div>
  `).join('');
}

function fmtBytes(b) {
  if (b < 1024)        return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(1)} MB`;
}

// ── Generation ───────────────────────────────────────────────────────────────
async function startGeneration() {
  const topic  = document.getElementById('topic').value.trim();
  const author = document.getElementById('author').value.trim();
  const format = document.querySelector('input[name="output-type"]:checked').value;

  if (!topic) {
    const inp = document.getElementById('topic');
    inp.focus();
    inp.style.borderColor = 'var(--error)';
    inp.style.boxShadow   = '0 0 0 3px rgba(201,55,44,0.14)';
    setTimeout(() => {
      inp.style.borderColor = '';
      inp.style.boxShadow   = '';
    }, 1800);
    return;
  }

  // Reset UI
  hide('result-area');
  hide('error-area');
  show('status-area');
  setText('status-text', 'Starting research…');
  setDisabled('generate-btn', true);

  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }

  const formData = new FormData();
  formData.append('topic', topic);
  formData.append('guiding_questions', JSON.stringify(getQuestions()));
  formData.append('output_type', format);
  formData.append('author', author || 'Research Studio');
  for (const f of uploadedFiles) formData.append('files', f);

  try {
    const res  = await fetch('/api/generate', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to start generation.');
    beginPolling(data.job_id);
  } catch (err) {
    showError(err.message);
  }
}

function beginPolling(jobId) {
  setText('status-text', 'Researching topic…');

  let tick = 0;
  const messages = [
    'Researching topic…',
    'Fetching sources…',
    'Building research brief…',
    'Generating artifact…',
  ];

  pollTimer = setInterval(async () => {
    tick++;
    const msgIdx = Math.min(Math.floor(tick / 2), messages.length - 1);
    setText('status-text', messages[msgIdx]);

    try {
      const res  = await fetch(`/api/status/${jobId}`);
      const data = await res.json();

      if (data.status === 'complete') {
        clearInterval(pollTimer);
        showResult(jobId, data.filename);
      } else if (data.status === 'error') {
        clearInterval(pollTimer);
        showError(data.error || 'Generation failed.');
      }
    } catch {
      clearInterval(pollTimer);
      showError('Lost connection to server.');
    }
  }, 5000);
}

function showResult(jobId, filename) {
  hide('status-area');
  setDisabled('generate-btn', false);

  show('result-area');
  setText('result-filename', filename);

  const link = document.getElementById('download-link');
  link.href     = `/api/download/${jobId}`;
  link.download = filename;
}

function showError(msg) {
  hide('status-area');
  setDisabled('generate-btn', false);

  show('error-area');
  setText('error-message', msg);
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function show(id)    { document.getElementById(id).style.display = ''; }
function hide(id)    { document.getElementById(id).style.display = 'none'; }
function setText(id, text) { document.getElementById(id).textContent = text; }
function setDisabled(id, val) { document.getElementById(id).disabled = val; }

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeAttr(str) {
  return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupFileUpload();

  // Submit on Enter in the topic field
  document.getElementById('topic').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') startGeneration();
  });

  // Live radio-card update (for browsers that don't support :has)
  document.querySelectorAll('input[name="output-type"]').forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.radio-card').forEach(card => {
        const inp = card.querySelector('input');
        if (inp.checked) {
          card.style.borderColor = 'var(--accent)';
          card.style.background  = 'rgba(35,131,226,0.04)';
          card.querySelector('.radio-card-icon').style.color = 'var(--accent)';
        } else {
          card.style.borderColor = '';
          card.style.background  = '';
          card.querySelector('.radio-card-icon').style.color = '';
        }
      });
    });
  });

  // Initial radio state for non-:has browsers
  const checked = document.querySelector('input[name="output-type"]:checked');
  if (checked) {
    const card = checked.closest('.radio-card');
    card.style.borderColor = 'var(--accent)';
    card.style.background  = 'rgba(35,131,226,0.04)';
    card.querySelector('.radio-card-icon').style.color = 'var(--accent)';
  }
});
