import JSZip from 'jszip';

// ==========================================================================
// Page State
// ==========================================================================
let state = {
  originalGlossaryText: '',
  localTerms: [],
  sentencesData: { paths: [], sentences: [] },
  sheetTerms: [],
  comparisonResults: [], // Array of { key, oldThai, newThai, oldStatus, newStatus, oldRules, newRules, group, action, checked }
  
  // Scanned replacements state
  affectedQuests: new Set(),
  affectedSentencesCount: 0,
  replacementsToApply: [] // Array of { path, key, oldTh, newTh }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initPage();
  });
} else {
  initPage();
}

async function initPage() {
  console.log('[Sync Init] initPage started.');
  const progressBar = document.getElementById('progress-bar');
  const loadingStatus = document.getElementById('loading-status');
  
  try {
    // 1. Fetch glossary.md
    console.log('[Sync Init] Fetching glossary.md...');
    loadingStatus.textContent = 'Fetching local glossary.md...';
    progressBar.style.width = '10%';
    
    const glossaryRes = await fetch('./glossary.md');
    if (!glossaryRes.ok) throw new Error('Failed to fetch glossary.md');
    state.originalGlossaryText = await glossaryRes.text();
    console.log('[Sync Init] glossary.md fetched successfully, parsing...');
    state.localTerms = parseGlossary(state.originalGlossaryText);
    console.log('[Sync Init] Local glossary terms parsed:', state.localTerms.length);
    
    progressBar.style.width = '20%';
    
    // 2. Fetch sentences.json with download tracking
    console.log('[Sync Init] Fetching sentences.json...');
    loadingStatus.textContent = 'Downloading sentences index (28MB)...';
    
    const sentencesRes = await fetch('./sentences.json');
    if (!sentencesRes.ok) throw new Error('Failed to fetch sentences.json');
    console.log('[Sync Init] sentences.json request completed, processing response...');
    
    const contentLength = sentencesRes.headers.get('content-length');
    const totalBytes = contentLength ? parseInt(contentLength, 10) : 0;
    console.log('[Sync Init] sentences.json size:', totalBytes, 'bytes');
    
    let jsonText;
    if (sentencesRes.body && typeof sentencesRes.body.getReader === 'function') {
      console.log('[Sync Init] Streams supported. Initializing stream reader...');
      const reader = sentencesRes.body.getReader();
      let loadedBytes = 0;
      let chunks = [];
      
      while(true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        chunks.push(value);
        loadedBytes += value.length;
        
        if (totalBytes > 0) {
          const percent = 20 + Math.round((loadedBytes / totalBytes) * 70);
          progressBar.style.width = `${percent}%`;
          const mbLoaded = (loadedBytes / (1024 * 1024)).toFixed(1);
          const mbTotal = (totalBytes / (1024 * 1024)).toFixed(1);
          loadingStatus.textContent = `Downloading sentences index: ${mbLoaded}MB / ${mbTotal}MB (${Math.round((loadedBytes/totalBytes)*100)}%)`;
        } else {
          const mbLoaded = (loadedBytes / (1024 * 1024)).toFixed(1);
          loadingStatus.textContent = `Downloading sentences: ${mbLoaded}MB...`;
        }
      }
      
      console.log('[Sync Init] Streaming finished, combining chunks. Total loaded:', loadedBytes, 'bytes');
      loadingStatus.textContent = 'Parsing database in memory...';
      progressBar.style.width = '95%';
      
      let allChunks = new Uint8Array(loadedBytes);
      let position = 0;
      for (let chunk of chunks) {
        allChunks.set(chunk, position);
        position += chunk.length;
      }
      
      console.log('[Sync Init] Text decoding starting...');
      const decoder = new TextDecoder('utf-8');
      jsonText = decoder.decode(allChunks);
      console.log('[Sync Init] JSON parsing starting...');
      state.sentencesData = JSON.parse(jsonText);
      console.log('[Sync Init] JSON parsing complete. Sentences loaded:', state.sentencesData.sentences.length);
    } else {
      console.warn('[Sync Init] Streams not supported. Using fallback json() reader...');
      loadingStatus.textContent = 'Downloading sentences index (fallback)...';
      state.sentencesData = await sentencesRes.json();
      console.log('[Sync Init] JSON loading complete (fallback). Sentences loaded:', state.sentencesData.sentences.length);
    }
    
    progressBar.style.width = '100%';
    loadingStatus.textContent = 'Done!';
    
    document.getElementById('total-terms-count').textContent = state.localTerms.length;
    document.getElementById('total-sentences-count').textContent = state.sentencesData.sentences.length;
    
    // Attempt to load saved Sheet URL from localStorage
    const savedUrl = localStorage.getItem('glossary_sheet_url');
    if (savedUrl) {
      document.getElementById('sheet-url').value = savedUrl;
    }
    
    // Hide loading
    console.log('[Sync Init] Initialization complete. Fading out loading screen...');
    setTimeout(() => {
      document.getElementById('loading-screen').classList.add('fade-out');
    }, 400);
    
    setupUI();
    console.log('[Sync Init] UI Setup completed successfully.');
    
  } catch (error) {
    console.error('[Sync Init] Fatal initialization error:', error);
    loadingStatus.textContent = `Error: ${error.message}. Please reload the page.`;
    loadingStatus.style.color = '#ef4444';
  }
}

// ==========================================================================
// Parsing & Comparing Glossary Markdown
// ==========================================================================
function parseGlossary(text) {
  const lines = text.split('\n');
  let currentGroup = null;
  const terms = [];
  
  for (let line of lines) {
    const trimmed = line.trim();
    
    if (trimmed.startsWith('<term_registry')) {
      const match = trimmed.match(/group="([^"]+)"/);
      if (match) {
        currentGroup = match[1];
      }
      continue;
    }
    
    if (trimmed.startsWith('</term_registry>')) {
      currentGroup = null;
      continue;
    }
    
    if (currentGroup && trimmed.startsWith('|')) {
      if (trimmed.includes('EN Key') || trimmed.includes(':---')) {
        continue;
      }
      
      const parts = line.split('|');
      if (parts.length >= 4) {
        const enKey = parts[1].trim();
        const thpe = parts[2].trim();
        const status = parts[3].trim();
        const rules = parts[4] ? parts[4].trim() : '';
        
        if (enKey || thpe) {
          terms.push({
            key: enKey,
            thai: thpe,
            status: status,
            rules: rules,
            group: currentGroup
          });
        }
      }
    }
  }
  return terms;
}

function generateMarkdown(originalText, terms) {
  const lines = originalText.split('\n');
  const outputLines = [];
  let i = 0;
  
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    
    if (trimmed.startsWith('<term_registry')) {
      const match = trimmed.match(/group="([^"]+)"/);
      if (match) {
        const group = match[1];
        outputLines.push(line);
        
        // Skip header and dividers
        i++;
        while (i < lines.length) {
          const subLine = lines[i];
          outputLines.push(subLine);
          if (subLine.trim().includes(':---')) {
            break;
          }
          i++;
        }
        
        // Write all terms for this group sorted alphabetically by key
        const groupTerms = terms.filter(t => t.group === group);
        groupTerms.sort((a, b) => a.key.localeCompare(b.key));
        
        for (const term of groupTerms) {
          const row = `    | ${term.key} | ${term.thai} | ${term.status} | ${term.rules} |`;
          outputLines.push(row);
        }
        
        // Skip original terms until </term_registry>
        i++;
        while (i < lines.length) {
          const subLine = lines[i];
          if (subLine.trim().startsWith('</term_registry>')) {
            outputLines.push(subLine);
            break;
          }
          i++;
        }
      } else {
        outputLines.push(line);
      }
    } else {
      outputLines.push(line);
    }
    i++;
  }
  
  return outputLines.join('\n');
}

// ==========================================================================
// Google Sheets Fetch & CSV Parsing
// ==========================================================================
function parseSpreadsheetUrl(urlOrId) {
  const trimmed = urlOrId.trim();
  if (!trimmed) return null;
  
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    if (trimmed.includes('/pub') && (trimmed.includes('output=csv') || trimmed.includes('output=tsv'))) {
      return { fetchUrl: trimmed, id: 'published', gid: 'published' };
    }
    
    const idMatch = trimmed.match(/\/d\/([a-zA-Z0-9-_]+)/);
    if (!idMatch) return null;
    const id = idMatch[1];
    
    let gid = '0';
    const gidMatch = trimmed.match(/gid=([0-9]+)/);
    if (gidMatch) {
      gid = gidMatch[1];
    }
    
    return {
      id,
      gid,
      fetchUrl: `https://docs.google.com/spreadsheets/d/${id}/export?format=csv&gid=${gid}`
    };
  } else {
    return {
      id: trimmed,
      gid: '0',
      fetchUrl: `https://docs.google.com/spreadsheets/d/${trimmed}/export?format=csv&gid=0`
    };
  }
}

function detectDelimiter(text) {
  const firstLine = text.split('\n')[0];
  const commaCount = (firstLine.match(/,/g) || []).length;
  const tabCount = (firstLine.match(/\t/g) || []).length;
  return tabCount > commaCount ? '\t' : ',';
}

function parseCSV(text, delimiter = ',') {
  const result = [];
  let row = [];
  let insideQuote = false;
  let entry = '';
  
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const nextChar = text[i + 1];
    
    if (insideQuote) {
      if (char === '"') {
        if (nextChar === '"') {
          entry += '"';
          i++;
        } else {
          insideQuote = false;
        }
      } else {
        entry += char;
      }
    } else {
      if (char === '"') {
        insideQuote = true;
      } else if (char === delimiter) {
        row.push(entry);
        entry = '';
      } else if (char === '\n' || char === '\r') {
        row.push(entry);
        entry = '';
        if (char === '\r' && nextChar === '\n') {
          i++;
        }
        if (row.length > 0 && (row.length > 1 || row[0] !== '')) {
          result.push(row);
        }
        row = [];
      } else {
        entry += char;
      }
    }
  }
  if (row.length > 0 || entry !== '') {
    row.push(entry);
    result.push(row);
  }
  return result;
}

function detectColumns(headers) {
  let keyIdx = -1;
  let thaiIdx = -1;
  let statusIdx = -1;
  let rulesIdx = -1;
  let groupIdx = -1;
  
  headers.forEach((h, idx) => {
    const header = h.toLowerCase().trim();
    if (header.includes('key') || header.includes('english') || header === 'en' || header === 'word') {
      if (keyIdx === -1) keyIdx = idx;
    } else if (header.includes('better') || header.includes('new') || header.includes('latest') || header.includes('update') || header.includes('thai') || header.includes('thpe') || header === 'th' || header.includes('แปล') || header.includes('คำแปล')) {
      if (thaiIdx === -1 || header.includes('better') || header.includes('new') || header.includes('latest')) {
        thaiIdx = idx;
      }
    } else if (header.includes('status') || header.includes('สถานะ') || header === 'state') {
      if (statusIdx === -1) statusIdx = idx;
    } else if (header.includes('rule') || header.includes('desc') || header.includes('คำอธิบาย') || header.includes('note') || header.includes('linter')) {
      if (rulesIdx === -1) rulesIdx = idx;
    } else if (header.includes('group') || header.includes('category') || header.includes('หมวด') || header.includes('type')) {
      if (groupIdx === -1) groupIdx = idx;
    }
  });
  
  // Fallbacks based on typical spreadsheet structures
  if (keyIdx === -1) keyIdx = 0;
  if (thaiIdx === -1) thaiIdx = headers.length > 1 ? 1 : 0;
  if (statusIdx === -1) {
    statusIdx = headers.findIndex((h, idx) => idx !== keyIdx && idx !== thaiIdx && h.toLowerCase().includes('stat'));
  }
  if (rulesIdx === -1) {
    rulesIdx = headers.findIndex((h, idx) => idx !== keyIdx && idx !== thaiIdx && idx !== statusIdx && (h.toLowerCase().includes('rule') || h.toLowerCase().includes('desc') || h.toLowerCase().includes('note')));
  }
  if (groupIdx === -1) {
    groupIdx = headers.findIndex((h, idx) => idx !== keyIdx && idx !== thaiIdx && idx !== statusIdx && idx !== rulesIdx && h.toLowerCase().includes('group'));
  }
  
  return { keyIdx, thaiIdx, statusIdx, rulesIdx, groupIdx };
}

// ==========================================================================
// Comparison Logic
// ==========================================================================
async function fetchAndCompare() {
  const urlInput = document.getElementById('sheet-url').value;
  const customGid = '0';
  const defaultGroup = 'global';
  const fetchBtn = document.getElementById('fetch-sheet-btn');
  
  if (!urlInput.trim()) {
    alert('Please enter a Google Spreadsheet URL or ID.');
    return;
  }
  
  // Save URL in localStorage
  localStorage.setItem('glossary_sheet_url', urlInput);
  
  const sheetInfo = parseSpreadsheetUrl(urlInput);
  if (!sheetInfo) {
    alert('Could not parse Google Sheets URL. Please check the format.');
    return;
  }
  
  let targetUrl = sheetInfo.fetchUrl;
  // Override GID if customGid is specified and it's not a published CSV url
  if (customGid && sheetInfo.gid !== 'published' && sheetInfo.gid !== customGid) {
    targetUrl = `https://docs.google.com/spreadsheets/d/${sheetInfo.id}/export?format=csv&gid=${customGid}`;
  }
  
  fetchBtn.disabled = true;
  fetchBtn.textContent = 'Fetching Sheet...';
  
  try {
    const response = await fetch(targetUrl);
    if (!response.ok) throw new Error('Spreadsheet fetch failed. Make sure it is shared publicly.');
    
    const csvText = await response.text();
    const delimiter = detectDelimiter(csvText);
    const rows = parseCSV(csvText, delimiter);
    
    if (rows.length < 2) {
      throw new Error('Spreadsheet appears to be empty or has no data rows.');
    }
    
    const headers = rows[0];
    const cols = detectColumns(headers);
    
    // Parse terms from sheet
    state.sheetTerms = [];
    for (let r = 1; r < rows.length; r++) {
      const row = rows[r];
      if (row.length <= cols.keyIdx) continue;
      
      const rawKey = row[cols.keyIdx] || '';
      const key = rawKey.trim(); // Keep case for matching, we check key.toLowerCase() for existence
      if (!key) continue; // Skip empty keys
      
      const thai = cols.thaiIdx !== -1 && row[cols.thaiIdx] ? row[cols.thaiIdx].trim() : '';
      let status = cols.statusIdx !== -1 && row[cols.statusIdx] ? row[cols.statusIdx].trim().toUpperCase() : 'APPROVED';
      if (status !== 'APPROVED' && status !== 'AUTO_LEARNED') {
        status = 'APPROVED'; // normalize
      }
      
      const rules = cols.rulesIdx !== -1 && row[cols.rulesIdx] ? row[cols.rulesIdx].trim() : 'บันทึกจาก Google Sheets';
      
      // Determine registry group
      let group = defaultGroup;
      if (cols.groupIdx !== -1 && row[cols.groupIdx]) {
        const sheetGrp = row[cols.groupIdx].trim().toLowerCase();
        if (['global', 'locations', 'skills'].includes(sheetGrp)) {
          group = sheetGrp;
        }
      } else {
        // Look up if this term already exists in our local glossary, and preserve its group
        const existing = state.localTerms.find(t => t.key.toLowerCase() === key.toLowerCase());
        if (existing) {
          group = existing.group;
        }
      }
      
      state.sheetTerms.push({ key, thai, status, rules, group });
    }
    
    performComparison(cols);
    renderDiffTable();
    
    // Enable other action buttons
    document.getElementById('run-preview-btn').disabled = false;
    document.getElementById('download-zip-btn').disabled = false;
    
  } catch (error) {
    console.error(error);
    alert(`Error: ${error.message}\n\nTips:\n1. Open your Google Sheet, click 'Share' in the top right, and set to 'Anyone with the link can view'.\n2. Or click File -> Share -> Publish to Web -> Web page -> CSV, and paste that URL.`);
  } finally {
    fetchBtn.disabled = false;
    fetchBtn.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 0.5rem;"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
      Fetch & Compare Glossary
    `;
  }
}

function performComparison(cols) {
  state.comparisonResults = [];
  
  // Maps to track sheets terms by key + group
  const sheetMap = new Map();
  state.sheetTerms.forEach(t => {
    sheetMap.set(`${t.key.toLowerCase()}::${t.group}`, t);
  });
  
  // Maps for local terms
  const localMap = new Map();
  state.localTerms.forEach(t => {
    localMap.set(`${t.key.toLowerCase()}::${t.group}`, t);
  });
  
  // 1. Check Sheet terms (Additions and Updates)
  state.sheetTerms.forEach(sheetTerm => {
    const mapKey = `${sheetTerm.key.toLowerCase()}::${sheetTerm.group}`;
    const localTerm = localMap.get(mapKey);
    
    if (localTerm) {
      // If columns are missing in the sheet, inherit from local registry
      if (cols.rulesIdx === -1) {
        sheetTerm.rules = localTerm.rules;
      }
      if (cols.statusIdx === -1) {
        sheetTerm.status = localTerm.status;
      }
      if (cols.groupIdx === -1) {
        sheetTerm.group = localTerm.group;
      }

      // Exists in both, check if anything changed
      const thaiChanged = localTerm.thai !== sheetTerm.thai;
      const statusChanged = localTerm.status !== sheetTerm.status;
      const rulesChanged = localTerm.rules !== sheetTerm.rules;
      
      if (thaiChanged || statusChanged || rulesChanged) {
        state.comparisonResults.push({
          key: sheetTerm.key,
          oldThai: localTerm.thai,
          newThai: sheetTerm.thai,
          oldStatus: localTerm.status,
          newStatus: sheetTerm.status,
          oldRules: localTerm.rules,
          newRules: sheetTerm.rules,
          group: sheetTerm.group,
          action: 'update',
          checked: true // apply by default
        });
      } else {
        state.comparisonResults.push({
          key: sheetTerm.key,
          oldThai: localTerm.thai,
          newThai: sheetTerm.thai,
          oldStatus: localTerm.status,
          newStatus: sheetTerm.status,
          oldRules: localTerm.rules,
          newRules: sheetTerm.rules,
          group: sheetTerm.group,
          action: 'unchanged',
          checked: false
        });
      }
    } else {
      // Exists in sheet, not in local
      state.comparisonResults.push({
        key: sheetTerm.key,
        oldThai: '',
        newThai: sheetTerm.thai,
        oldStatus: '',
        newStatus: sheetTerm.status,
        oldRules: '',
        newRules: sheetTerm.rules,
        group: sheetTerm.group,
        action: 'add',
        checked: true // apply by default
      });
    }
  });
  
  // 2. Check Local terms (Deletions)
  state.localTerms.forEach(localTerm => {
    const mapKey = `${localTerm.key.toLowerCase()}::${localTerm.group}`;
    if (!sheetMap.has(mapKey)) {
      state.comparisonResults.push({
        key: localTerm.key,
        oldThai: localTerm.thai,
        newThai: '',
        oldStatus: localTerm.status,
        newStatus: '',
        oldRules: localTerm.rules,
        newRules: '',
        group: localTerm.group,
        action: 'remove',
        checked: false // do not remove by default (safer)
      });
    }
  });
  
  // Update stats counts
  updateStatsCounters();
}

function updateStatsCounters() {
  const added = state.comparisonResults.filter(r => r.action === 'add').length;
  const updated = state.comparisonResults.filter(r => r.action === 'update').length;
  const removed = state.comparisonResults.filter(r => r.action === 'remove').length;
  const unchanged = state.comparisonResults.filter(r => r.action === 'unchanged').length;
  
  document.getElementById('count-added').textContent = added;
  document.getElementById('count-updated').textContent = updated;
  document.getElementById('count-removed').textContent = removed;
  document.getElementById('count-unchanged').textContent = unchanged;
}

// ==========================================================================
// UI Rendering for Glossary Table
// ==========================================================================
function renderDiffTable() {
  const tbody = document.getElementById('diff-list-body');
  tbody.innerHTML = '';
  
  const showUnchanged = document.getElementById('show-unchanged').checked;
  const showRemoved = document.getElementById('show-removed').checked;
  
  // Filter comparison results
  const filtered = state.comparisonResults.filter(r => {
    if (r.action === 'unchanged' && !showUnchanged) return false;
    if (r.action === 'remove' && !showRemoved) return false;
    return true;
  });
  
  // Sort: Additions first, then updates, then removals, then unchanged
  // Inside each category, sort alphabetically by key
  const actionPriority = { 'add': 1, 'update': 2, 'remove': 3, 'unchanged': 4 };
  filtered.sort((a, b) => {
    if (a.action !== b.action) {
      return actionPriority[a.action] - actionPriority[b.action];
    }
    return a.key.localeCompare(b.key);
  });
  
  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 3rem;">No terms meet the display filters.</td></tr>`;
    return;
  }
  
  filtered.forEach((r, idx) => {
    const tr = document.createElement('tr');
    
    let actionBadge = '';
    let thCell = '';
    
    if (r.action === 'add') {
      actionBadge = `<span class="action-badge add">Add</span>`;
      thCell = `<div class="th-diff-cell"><span class="new-val">${escapeHtml(r.newThai)}</span></div>`;
    } else if (r.action === 'update') {
      actionBadge = `<span class="action-badge update">Update</span>`;
      const thaiDiff = r.oldThai !== r.newThai 
        ? `<span class="old-val">${escapeHtml(r.oldThai)}</span><span class="new-val" style="color: var(--color-auto-learned);">${escapeHtml(r.newThai)}</span>`
        : `<span class="new-val">${escapeHtml(r.newThai)}</span>`;
      thCell = `<div class="th-diff-cell">${thaiDiff}</div>`;
    } else if (r.action === 'remove') {
      actionBadge = `<span class="action-badge remove">Remove</span>`;
      thCell = `<div class="th-diff-cell"><span class="old-val">${escapeHtml(r.oldThai)}</span></div>`;
    } else {
      actionBadge = `<span class="action-badge unchanged">Unchanged</span>`;
      thCell = `<div class="th-diff-cell"><span class="new-val">${escapeHtml(r.newThai)}</span></div>`;
    }
    
    const groupBadgeClass = r.group === 'locations' ? 'badge-locations' : (r.group === 'skills' ? 'badge-skills' : 'badge-approved');
    const statusVal = r.action === 'remove' ? r.oldStatus : r.newStatus;
    const statusBadgeClass = statusVal === 'APPROVED' ? 'badge-approved' : 'badge-auto-learned';
    
    tr.innerHTML = `
      <td class="checkbox-cell"><input type="checkbox" class="term-checkbox" data-index="${idx}" ${r.checked ? 'checked' : ''}></td>
      <td style="font-weight: 500;">${escapeHtml(r.key)}</td>
      <td>
        <div style="display: flex; flex-direction: column; gap: 0.25rem; align-items: flex-start;">
          <span class="badge ${groupBadgeClass}">${escapeHtml(r.group)}</span>
          <span class="badge ${statusBadgeClass}" style="font-size: 0.65rem; padding: 0.1rem 0.3rem;">${escapeHtml(statusVal)}</span>
        </div>
      </td>
      <td>${thCell}</td>
      <td>${actionBadge}</td>
    `;
    
    // Add event listener to checkbox
    const checkbox = tr.querySelector('.term-checkbox');
    checkbox.addEventListener('change', (e) => {
      r.checked = e.target.checked;
    });
    
    tbody.appendChild(tr);
  });
}

// ==========================================================================
// Dialog Scanning & Previewing
// ==========================================================================
function updateDialoguePreview() {
  const container = document.getElementById('preview-sentences-list');
  const questCountEl = document.getElementById('affected-quests-count');
  const sentenceCountEl = document.getElementById('affected-sentences-count');
  const strictMatching = document.getElementById('sync-search-thai').checked;
  
  container.innerHTML = '<div style="text-align: center; padding: 3rem;"><div class="spinner"></div><p style="margin-top: 1rem; color: var(--text-muted);">Scanning 79,996 translation dialogues in memory...</p></div>';
  
  // Reset scanned state
  state.affectedQuests.clear();
  state.affectedSentencesCount = 0;
  state.replacementsToApply = [];
  
  // Find checked updates that change the Thai translation
  const updatesToApply = state.comparisonResults.filter(r => 
    r.checked && 
    r.action === 'update' && 
    r.oldThai && 
    r.newThai && 
    r.oldThai !== r.newThai
  );
  
  if (updatesToApply.length === 0) {
    container.innerHTML = '<div class="no-sentences-match">No updated glossary translation terms are currently checked to apply search-and-replace.</div>';
    questCountEl.textContent = '0';
    sentenceCountEl.textContent = '0';
    return;
  }
  
  // Process matching dialogue sentences
  const matchedSentences = []; // Array of { path, textEn, textTh, lineIdx, term, oldVal, newVal }
  
  // Build a list of regex/strings for fast lookup
  const scanners = updatesToApply.map(u => ({
    term: u,
    regexEn: new RegExp(escapeRegex(u.key), 'i'),
    oldThai: u.oldThai,
    newThai: u.newThai
  }));
  
  // Loop through sentences
  state.sentencesData.sentences.forEach(s => {
    const [pathIdx, textEn, textTh, idx] = s;
    const path = state.sentencesData.paths[pathIdx];
    
    scanners.forEach(sc => {
      // Condition:
      // If strictMatching: English must contain Key AND Thai must contain Old Translation
      // Else: Thai contains Old Translation (global search/replace)
      const matchesEn = !strictMatching || sc.regexEn.test(textEn);
      
      if (matchesEn && textTh.includes(sc.oldThai)) {
        state.affectedQuests.add(path);
        state.affectedSentencesCount++;
        
        matchedSentences.push({
          path,
          textEn,
          textTh,
          lineIdx: idx,
          key: sc.term.key,
          oldTh: sc.oldThai,
          newTh: sc.newThai
        });
        
        // Add to our zip replacement queue
        state.replacementsToApply.push({
          path,
          key: sc.term.key,
          oldTh: sc.oldThai,
          newTh: sc.newThai
        });
      }
    });
  });
  
  // Update UI stats
  questCountEl.textContent = state.affectedQuests.size;
  sentenceCountEl.textContent = state.affectedSentencesCount;
  
  if (matchedSentences.length === 0) {
    container.innerHTML = '<div class="no-sentences-match">No dialogue sentences match the checked glossary translation changes.</div>';
    return;
  }
  
  // Group matches by quest
  const questGroups = new Map();
  matchedSentences.forEach(m => {
    if (!questGroups.has(m.path)) {
      questGroups.set(m.path, []);
    }
    questGroups.get(m.path).push(m);
  });
  
  container.innerHTML = '';
  
  // Render first 50 quests to avoid rendering slowdowns
  const keys = Array.from(questGroups.keys()).slice(0, 50);
  
  if (questGroups.size > 50) {
    const limitNotice = document.createElement('div');
    limitNotice.style.padding = '0.75rem 1rem';
    limitNotice.style.background = 'rgba(245, 158, 11, 0.1)';
    limitNotice.style.border = '1px solid rgba(245, 158, 11, 0.2)';
    limitNotice.style.borderRadius = 'var(--radius-sm)';
    limitNotice.style.color = 'var(--color-auto-learned)';
    limitNotice.style.fontSize = '0.8rem';
    limitNotice.style.marginBottom = '1rem';
    limitNotice.textContent = `Showing first 50 of ${questGroups.size} affected quests. All ${matchedSentences.length} replacements will be applied in the download package.`;
    container.appendChild(limitNotice);
  }
  
  keys.forEach(path => {
    const groupMatches = questGroups.get(path);
    
    const groupDiv = document.createElement('div');
    groupDiv.className = 'quest-group-container';
    
    const headerDiv = document.createElement('div');
    headerDiv.className = 'quest-group-header';
    headerDiv.innerHTML = `<span class="quest-group-title">${escapeHtml(path)} <span class="quest-group-meta">(${groupMatches.length} change${groupMatches.length === 1 ? '' : 's'})</span></span>`;
    groupDiv.appendChild(headerDiv);
    
    const sentencesListDiv = document.createElement('div');
    sentencesListDiv.className = 'quest-sentences-list';
    
    groupMatches.forEach(m => {
      const sentenceDiv = document.createElement('div');
      sentenceDiv.className = 'sentence-item-inline';
      
      // Highlight English key
      const escapedEn = escapeHtml(m.textEn);
      const enRegex = new RegExp(`(${escapeRegex(escapeHtml(m.key))})`, 'gi');
      const highlightedEn = escapedEn.replace(enRegex, '<span class="term-highlight">$1</span>');
      
      // Diff Thai
      const escapedTh = escapeHtml(m.textTh);
      const escapedOld = escapeHtml(m.oldTh);
      const escapedNew = escapeHtml(m.newTh);
      
      const combo1 = escapedOld + escapedNew;
      const combo2 = escapedNew + escapedOld;
      
      let highlightedTh = escapedTh;
      if (escapedTh.includes(combo1)) {
        const diffMarkup = `<span class="diff-removed">${combo1}</span><span class="diff-added">${escapedNew}</span>`;
        highlightedTh = escapedTh.split(combo1).join(diffMarkup);
      } else if (escapedTh.includes(combo2)) {
        const diffMarkup = `<span class="diff-removed">${combo2}</span><span class="diff-added">${escapedNew}</span>`;
        highlightedTh = escapedTh.split(combo2).join(diffMarkup);
      } else {
        const diffMarkup = `<span class="diff-removed">${escapedOld}</span><span class="diff-added">${escapedNew}</span>`;
        highlightedTh = escapedTh.split(escapedOld).join(diffMarkup);
      }
      
      sentenceDiv.innerHTML = `
        <div class="sentence-item-line-num">Line ${m.lineIdx + 1} <span style="color: var(--text-dim)">[Term: ${m.key}]</span></div>
        <div class="sentence-row sentence-row-en">
          <div class="sentence-text sentence-text-en">${highlightedEn}</div>
        </div>
        <div class="sentence-row">
          <div class="sentence-text sentence-text-th">${highlightedTh}</div>
        </div>
      `;
      
      sentencesListDiv.appendChild(sentenceDiv);
    });
    
    groupDiv.appendChild(sentencesListDiv);
    container.appendChild(groupDiv);
  });
}

// ==========================================================================
// Quest file modification & download
// ==========================================================================
async function getModifiedQuestJson(path, replacements) {
  const response = await fetch(`./th/${path}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch original quest file: th/${path}`);
  }
  const questData = await response.json();
  
  let modifiedCount = 0;
  
  if (questData.dialogues && replacements && replacements.length > 0) {
    // Group replacements for this path by key
    const pathRepls = replacements.filter(r => r.path === path);
    
    for (let dialogue of questData.dialogues) {
      const textEn = dialogue.text_en || '';
      const textTh = dialogue.text || '';
      
      let currentTh = textTh;
      let matchedAny = false;
      
      pathRepls.forEach(r => {
        const strictMatching = document.getElementById('sync-search-thai').checked;
        const matchesEn = !strictMatching || new RegExp(escapeRegex(r.key), 'i').test(textEn);
        
        if (matchesEn) {
          let updated = false;
          const combo1 = r.oldTh + r.newTh;
          const combo2 = r.newTh + r.oldTh;
          
          if (currentTh.includes(combo1)) {
            currentTh = currentTh.split(combo1).join(r.newTh);
            updated = true;
          }
          if (currentTh.includes(combo2)) {
            currentTh = currentTh.split(combo2).join(r.newTh);
            updated = true;
          }
          if (currentTh.includes(r.oldTh)) {
            currentTh = currentTh.split(r.oldTh).join(r.newTh);
            updated = true;
          }
          
          if (updated) {
            matchedAny = true;
          }
        }
      });
      
      if (matchedAny) {
        dialogue.text = currentTh;
        modifiedCount++;
      }
    }
  }
  
  return { questData, modifiedCount };
}

async function downloadUpdatePackage() {
  const downloadBtn = document.getElementById('download-zip-btn');
  const origHtml = downloadBtn.innerHTML;
  
  downloadBtn.innerHTML = 'Generating ZIP...';
  downloadBtn.disabled = true;
  
  try {
    const zip = new JSZip();
    
    // 1. Construct the new list of glossary terms based on checks
    const finalTerms = [...state.localTerms];
    const forceApproved = document.getElementById('sync-force-approved').checked;
    const forceRules = document.getElementById('sync-force-rules-felyne').checked;
    
    state.comparisonResults.forEach(r => {
      if (r.checked) {
        let statusVal = r.newStatus;
        let rulesVal = r.newRules;
        if (forceApproved) {
          statusVal = 'APPROVED';
        }
        if (forceRules) {
          rulesVal = 'APPROVED BY Felyne Kitchen';
        }
        
        if (r.action === 'add') {
          // Add to array
          finalTerms.push({
            key: r.key,
            thai: r.newThai,
            status: statusVal,
            rules: rulesVal,
            group: r.group
          });
        } else if (r.action === 'update') {
          // Find and replace in array
          const idx = finalTerms.findIndex(t => t.key.toLowerCase() === r.key.toLowerCase() && t.group === r.group);
          if (idx !== -1) {
            finalTerms[idx] = {
              key: r.key,
              thai: r.newThai,
              status: statusVal,
              rules: rulesVal,
              group: r.group
            };
          }
        } else if (r.action === 'remove') {
          // Remove from array
          const idx = finalTerms.findIndex(t => t.key.toLowerCase() === r.key.toLowerCase() && t.group === r.group);
          if (idx !== -1) {
            finalTerms.splice(idx, 1);
          }
        }
      }
    });
    
    // 2. Generate and add glossary.md to zip
    const updatedMarkdown = generateMarkdown(state.originalGlossaryText, finalTerms);
    zip.file('glossary.md', updatedMarkdown);
    
    // 3. Find unique quest paths to modify and apply replacements
    const uniquePaths = Array.from(state.affectedQuests);
    
    if (uniquePaths.length > 0) {
      for (const path of uniquePaths) {
        const { questData } = await getModifiedQuestJson(path, state.replacementsToApply);
        const jsonString = JSON.stringify(questData, null, 2);
        zip.file('th/' + path, jsonString);
      }
    }
    
    // 4. Generate the ZIP blob and trigger download
    const content = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(content);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = 'sheet_sync_update.zip';
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Flash Success
    downloadBtn.innerHTML = '✓ Downloaded!';
    downloadBtn.style.backgroundColor = '#059669';
    
    setTimeout(() => {
      downloadBtn.innerHTML = origHtml;
      downloadBtn.style.backgroundColor = '';
      downloadBtn.disabled = false;
    }, 2000);
    
  } catch (error) {
    console.error(error);
    alert(`Error generating ZIP package: ${error.message}`);
    downloadBtn.innerHTML = origHtml;
    downloadBtn.disabled = false;
  }
}

// ==========================================================================
// Setup UI Event Listeners
// ==========================================================================
function setupUI() {
  document.getElementById('fetch-sheet-btn').addEventListener('click', fetchAndCompare);
  
  document.getElementById('show-unchanged').addEventListener('change', renderDiffTable);
  document.getElementById('show-removed').addEventListener('change', renderDiffTable);
  
  document.getElementById('select-all-btn').addEventListener('click', () => {
    state.comparisonResults.forEach(r => {
      if (r.action !== 'unchanged') r.checked = true;
    });
    renderDiffTable();
    // Also sync header checkbox
    document.getElementById('header-select-all').checked = true;
  });
  
  document.getElementById('deselect-all-btn').addEventListener('click', () => {
    state.comparisonResults.forEach(r => {
      r.checked = false;
    });
    renderDiffTable();
    document.getElementById('header-select-all').checked = false;
  });
  
  document.getElementById('header-select-all').addEventListener('change', (e) => {
    const checked = e.target.checked;
    const showUnchanged = document.getElementById('show-unchanged').checked;
    const showRemoved = document.getElementById('show-removed').checked;
    
    state.comparisonResults.forEach(r => {
      if (r.action === 'unchanged' && !showUnchanged) return;
      if (r.action === 'remove' && !showRemoved) return;
      r.checked = checked;
    });
    renderDiffTable();
  });
  
  document.getElementById('run-preview-btn').addEventListener('click', updateDialoguePreview);
  document.getElementById('download-zip-btn').addEventListener('click', downloadUpdatePackage);
}

// ==========================================================================
// Helpers
// ==========================================================================
function escapeHtml(string) {
  if (!string) return '';
  return string
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeRegex(string) {
  return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
}
