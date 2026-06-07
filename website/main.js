import JSZip from 'jszip';

// ==========================================================================
// App State
// ==========================================================================
let state = {
  originalGlossaryText: '',
  glossaryTerms: [],
  sentencesData: { paths: [], sentences: [] },
  selectedTerm: null,
  unsavedChanges: false,
  
  // Filtering & Pagination
  searchQuery: '',
  statusFilter: 'all',
  groupFilter: 'all',
  currentPage: 1,
  pageSize: 50,
  sandboxRenderLimit: 50
};

// ==========================================================================
// Initialization & Loading
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  const progressBar = document.getElementById('progress-bar');
  const loadingStatus = document.getElementById('loading-status');
  
  try {
    // 1. Fetch glossary.md
    loadingStatus.textContent = 'Fetching glossary.md...';
    progressBar.style.width = '10%';
    
    const glossaryRes = await fetch('./glossary.md');
    if (!glossaryRes.ok) throw new Error('Failed to fetch glossary.md');
    state.originalGlossaryText = await glossaryRes.text();
    state.glossaryTerms = parseGlossary(state.originalGlossaryText);
    
    progressBar.style.width = '20%';
    
    // 2. Fetch sentences.json with progressive download tracking
    loadingStatus.textContent = 'Downloading sentences index (28MB)...';
    
    const sentencesRes = await fetch('./sentences.json');
    if (!sentencesRes.ok) throw new Error('Failed to fetch sentences.json');
    
    // Read stream to show progress
    const contentLength = sentencesRes.headers.get('content-length');
    const totalBytes = contentLength ? parseInt(contentLength, 10) : 0;
    
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
        loadingStatus.textContent = `Downloading sentences index: ${mbLoaded}MB loaded...`;
      }
    }
    
    // Combine chunks
    loadingStatus.textContent = 'Parsing database in memory...';
    progressBar.style.width = '95%';
    
    let allChunks = new Uint8Array(loadedBytes);
    let position = 0;
    for (let chunk of chunks) {
      allChunks.set(chunk, position);
      position += chunk.length;
    }
    
    const decoder = new TextDecoder('utf-8');
    const jsonText = decoder.decode(allChunks);
    state.sentencesData = JSON.parse(jsonText);
    
    // Done Loading
    progressBar.style.width = '100%';
    loadingStatus.textContent = 'Done!';
    
    document.getElementById('total-terms-count').textContent = state.glossaryTerms.length;
    document.getElementById('total-sentences-count').textContent = state.sentencesData.sentences.length;
    
    // Hide Loading Screen
    setTimeout(() => {
      document.getElementById('loading-screen').classList.add('fade-out');
      document.getElementById('download-btn').removeAttribute('disabled');
    }, 400);
    
    // Setup UI listeners & Render
    setupUI();
    renderTermsTable();
    
  } catch (error) {
    console.error(error);
    loadingStatus.textContent = `Error: ${error.message}. Please reload the page.`;
    loadingStatus.style.color = '#ef4444';
  }
}

// ==========================================================================
// Glossary Parsing & Generation
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
      // Skip table header and separator lines
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
            group: currentGroup,
            originalKey: enKey // For tracking rename edits
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
        outputLines.push(line); // push `<term_registry group="... ">`
        
        // Read header and divider from original
        i++;
        while (i < lines.length) {
          const subLine = lines[i];
          outputLines.push(subLine);
          if (subLine.trim().includes(':---')) {
            break;
          }
          i++;
        }
        
        // Output all terms for this group
        const groupTerms = terms.filter(t => t.group === group);
        for (const term of groupTerms) {
          // Format row: 4 spaces indent, key, thai, status, rules
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
// UI Rendering
// ==========================================================================
function getFilteredTerms() {
  return state.glossaryTerms.filter(term => {
    // 1. Text Search Filter
    const query = state.searchQuery.toLowerCase();
    const matchesQuery = !query || 
      term.key.toLowerCase().includes(query) || 
      term.thai.toLowerCase().includes(query) || 
      term.rules.toLowerCase().includes(query);
      
    // 2. Status Filter
    const matchesStatus = state.statusFilter === 'all' || term.status === state.statusFilter;
    
    // 3. Group Filter
    const matchesGroup = state.groupFilter === 'all' || term.group === state.groupFilter;
    
    return matchesQuery && matchesStatus && matchesGroup;
  });
}

function renderTermsTable() {
  const tbody = document.getElementById('terms-list-body');
  const countSpan = document.getElementById('terms-shown-count');
  
  const filtered = getFilteredTerms();
  
  // Sort terms alphabetically by EN Key
  filtered.sort((a, b) => a.key.localeCompare(b.key));
  
  // Pagination calculation
  const totalTerms = filtered.length;
  const totalPages = Math.ceil(totalTerms / state.pageSize) || 1;
  
  // Clamp current page
  if (state.currentPage > totalPages) state.currentPage = totalPages;
  if (state.currentPage < 1) state.currentPage = 1;
  
  const startIndex = (state.currentPage - 1) * state.pageSize;
  const endIndex = Math.min(startIndex + state.pageSize, totalTerms);
  const pageTerms = filtered.slice(startIndex, endIndex);
  
  tbody.innerHTML = '';
  
  if (pageTerms.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-dim); padding: 2rem;">No terms match the current filters.</td></tr>`;
  } else {
    pageTerms.forEach(term => {
      const tr = document.createElement('tr');
      if (state.selectedTerm && state.selectedTerm.key === term.key && state.selectedTerm.group === term.group) {
        tr.classList.add('selected');
      }
      
      const badgeClass = term.status === 'APPROVED' ? 'badge-approved' : 'badge-auto-learned';
      
      tr.innerHTML = `
        <td class="term-en-key" title="${term.key}">${escapeHtml(term.key)}</td>
        <td title="${term.thai}">${escapeHtml(term.thai)}</td>
        <td><span class="badge ${badgeClass}">${escapeHtml(term.status)}</span></td>
      `;
      
      tr.addEventListener('click', () => selectTerm(term));
      tbody.appendChild(tr);
    });
  }
  
  // Show count and render pagination buttons
  countSpan.innerHTML = `Showing <strong>${startIndex + 1}-${endIndex}</strong> of <strong>${totalTerms}</strong> terms`;
  
  // Add pagination controls if total pages > 1
  renderPaginationControls(totalPages);
}

function renderPaginationControls(totalPages) {
  const container = document.getElementById('terms-shown-count').parentNode;
  
  // Remove existing pagination controls if any
  const existingControls = container.querySelector('.pagination-controls');
  if (existingControls) {
    existingControls.remove();
  }
  
  if (totalPages <= 1) return;
  
  const controlsDiv = document.createElement('div');
  controlsDiv.className = 'pagination-controls';
  controlsDiv.style.display = 'flex';
  controlsDiv.style.gap = '0.3rem';
  controlsDiv.style.alignItems = 'center';
  
  const prevBtn = document.createElement('button');
  prevBtn.className = 'btn btn-secondary btn-sm';
  prevBtn.style.padding = '0.2rem 0.5rem';
  prevBtn.innerHTML = '&larr;';
  prevBtn.disabled = state.currentPage === 1;
  prevBtn.addEventListener('click', () => {
    state.currentPage--;
    renderTermsTable();
  });
  
  const pageLabel = document.createElement('span');
  pageLabel.style.fontSize = '0.75rem';
  pageLabel.style.color = 'var(--text-muted)';
  pageLabel.style.margin = '0 0.2rem';
  pageLabel.textContent = `${state.currentPage} / ${totalPages}`;
  
  const nextBtn = document.createElement('button');
  nextBtn.className = 'btn btn-secondary btn-sm';
  nextBtn.style.padding = '0.2rem 0.5rem';
  nextBtn.innerHTML = '&rarr;';
  nextBtn.disabled = state.currentPage === totalPages;
  nextBtn.addEventListener('click', () => {
    state.currentPage++;
    renderTermsTable();
  });
  
  controlsDiv.appendChild(prevBtn);
  controlsDiv.appendChild(pageLabel);
  controlsDiv.appendChild(nextBtn);
  
  container.appendChild(controlsDiv);
}

function selectTerm(term) {
  state.selectedTerm = term;
  
  // Highlight in table
  const rows = document.querySelectorAll('#terms-list-body tr');
  const filtered = getFilteredTerms();
  filtered.sort((a, b) => a.key.localeCompare(b.key));
  const startIndex = (state.currentPage - 1) * state.pageSize;
  
  rows.forEach((row, idx) => {
    const termAtRow = filtered[startIndex + idx];
    if (termAtRow && termAtRow.key === term.key && termAtRow.group === term.group) {
      row.classList.add('selected');
    } else {
      row.classList.remove('selected');
    }
  });
  
  // Update workspace form
  document.getElementById('form-action').value = 'edit';
  document.getElementById('form-original-en').value = term.key;
  document.getElementById('workspace-title').textContent = 'Edit Glossary Term';
  document.getElementById('workspace-group-badge').textContent = term.group;
  
  // Status badge style
  const badge = document.getElementById('workspace-group-badge');
  badge.className = 'badge';
  if (term.group === 'locations') badge.classList.add('badge-locations');
  else if (term.group === 'skills') badge.classList.add('badge-skills');
  else badge.classList.add('badge-approved');
  
  // Fill inputs
  document.getElementById('form-en-key').value = term.key;
  document.getElementById('form-en-key').readOnly = true; // Lock key on edit
  document.getElementById('form-th-translation').value = term.thai;
  document.getElementById('form-status').value = term.status;
  document.getElementById('form-group-select').value = term.group;
  document.getElementById('form-group-select').disabled = true; // Lock group on edit
  document.getElementById('form-rules').value = term.rules;
  
  // Fill sandbox inputs
  document.getElementById('sandbox-old-th').value = term.thai;
  document.getElementById('sandbox-new-th').value = term.thai; // Default to same, user will change
  
  // Show Workspace
  document.getElementById('no-term-selected').style.display = 'none';
  document.getElementById('term-workspace').style.display = 'flex';
  
  // Trigger preview update
  state.sandboxRenderLimit = 50;
  updateSandboxPreview();
}

function showAddTermForm() {
  state.selectedTerm = null;
  
  // Clear selected row styling
  document.querySelectorAll('#terms-list-body tr').forEach(r => r.classList.remove('selected'));
  
  // Update workspace form
  document.getElementById('form-action').value = 'add';
  document.getElementById('form-original-en').value = '';
  document.getElementById('workspace-title').textContent = 'Add New Glossary Term';
  document.getElementById('workspace-group-badge').textContent = 'NEW';
  document.getElementById('workspace-group-badge').className = 'badge badge-auto-learned';
  
  // Setup inputs
  document.getElementById('form-en-key').value = '';
  document.getElementById('form-en-key').readOnly = false;
  document.getElementById('form-th-translation').value = '';
  document.getElementById('form-status').value = 'APPROVED';
  document.getElementById('form-group-select').value = 'global';
  document.getElementById('form-group-select').disabled = false;
  document.getElementById('form-rules').value = '';
  
  // Setup Sandbox inputs
  document.getElementById('sandbox-old-th').value = '';
  document.getElementById('sandbox-new-th').value = '';
  
  // Show Workspace
  document.getElementById('no-term-selected').style.display = 'none';
  document.getElementById('term-workspace').style.display = 'flex';
  
  document.getElementById('form-en-key').focus();
  
  state.sandboxRenderLimit = 50;
  updateSandboxPreview();
}

// ==========================================================================
// Sandbox & Diff Preview Logic
// ==========================================================================
function updateSandboxPreview() {
  const enKey = document.getElementById('form-en-key').value.trim();
  const oldTh = document.getElementById('sandbox-old-th').value.trim();
  const newTh = document.getElementById('sandbox-new-th').value.trim();
  const listContainer = document.getElementById('sentences-list-container');
  const matchTitle = document.getElementById('sandbox-match-title');
  const downloadAllBtn = document.getElementById('download-all-changed-btn');
  
  if (!enKey && !oldTh) {
    listContainer.innerHTML = '<div class="no-sentences-match">Type an English key or Thai translation to see matching sentences.</div>';
    matchTitle.textContent = 'Sentences containing term (0 matches)';
    downloadAllBtn.style.display = 'none';
    return;
  }
  
  const focusOnlyChanged = document.getElementById('sandbox-focus-changed').checked;
  const searchThaiDirectly = document.getElementById('sandbox-search-thai').checked;
  
  // Search sentences
  let matches = [];
  if (searchThaiDirectly && oldTh) {
    matches = state.sentencesData.sentences.filter(s => s[2].includes(oldTh));
  } else if (enKey) {
    const searchRegex = new RegExp(escapeRegex(enKey), 'i');
    if (focusOnlyChanged && oldTh) {
      matches = state.sentencesData.sentences.filter(s => searchRegex.test(s[1]) && s[2].includes(oldTh));
    } else {
      matches = state.sentencesData.sentences.filter(s => searchRegex.test(s[1]));
    }
  } else if (oldTh) {
    matches = state.sentencesData.sentences.filter(s => s[2].includes(oldTh));
  }
  
  if (matches.length === 0) {
    listContainer.innerHTML = '<div class="no-sentences-match">No sentences in the "th" folder match your search query.</div>';
    matchTitle.textContent = 'Sentences containing term (0 matches)';
    downloadAllBtn.style.display = 'none';
    return;
  }
  
  const hasReplacement = oldTh && newTh && oldTh !== newTh;
  
  // Group by quest path
  const questGroups = new Map();
  matches.forEach(sentenceArray => {
    const [pathIdx, textEn, textTh, diagIdx] = sentenceArray;
    const path = state.sentencesData.paths[pathIdx];
    const isReplaced = hasReplacement && textTh.includes(oldTh);
    
    if (!questGroups.has(path)) {
      questGroups.set(path, {
        path,
        pathIdx,
        sentences: [],
        changedCount: 0,
        hasChanges: false
      });
    }
    
    const group = questGroups.get(path);
    group.sentences.push(sentenceArray);
    if (isReplaced) {
      group.changedCount++;
      group.hasChanges = true;
    }
  });
  
  const totalChangedQuests = Array.from(questGroups.values()).filter(g => g.hasChanges).length;
  
  // Filter groups if focusOnlyChanged is active
  const groupsToRender = Array.from(questGroups.values()).filter(g => {
    if (hasReplacement && focusOnlyChanged) {
      return g.hasChanges;
    }
    return true;
  });
  
  // Update titles
  if (hasReplacement && focusOnlyChanged) {
    matchTitle.textContent = `Changed files: ${totalChangedQuests} of ${questGroups.size} total matching quests`;
  } else if (enKey && (!searchThaiDirectly || !oldTh)) {
    matchTitle.textContent = `Sentences containing "${enKey}" (${matches.length} match${matches.length === 1 ? '' : 'es'} in ${questGroups.size} quest${questGroups.size === 1 ? '' : 's'})`;
  } else {
    matchTitle.textContent = `Sentences containing Thai "${oldTh}" (${matches.length} match${matches.length === 1 ? '' : 'es'} in ${questGroups.size} quest${questGroups.size === 1 ? '' : 's'})`;
  }
  
  // Update download all button visibility
  if (hasReplacement && totalChangedQuests > 0) {
    downloadAllBtn.style.display = 'inline-flex';
  } else {
    downloadAllBtn.style.display = 'none';
  }
  
  listContainer.innerHTML = '';
  
  if (groupsToRender.length === 0) {
    listContainer.innerHTML = '<div class="no-sentences-match">No quest files meet the current "Focus only on files changed" filter.</div>';
    return;
  }
  
  // Limit rendered groups to prevent DOM freezing
  const renderLimit = state.sandboxRenderLimit || 50;
  const itemsToRender = groupsToRender.slice(0, renderLimit);
  
  if (groupsToRender.length > renderLimit) {
    const limitNotice = document.createElement('div');
    limitNotice.style.padding = '0.75rem 1rem';
    limitNotice.style.background = 'rgba(245, 158, 11, 0.1)';
    limitNotice.style.border = '1px solid rgba(245, 158, 11, 0.2)';
    limitNotice.style.borderRadius = 'var(--radius-sm)';
    limitNotice.style.color = 'var(--color-auto-learned)';
    limitNotice.style.fontSize = '0.8rem';
    limitNotice.style.marginBottom = '1rem';
    limitNotice.style.display = 'flex';
    limitNotice.style.justifyContent = 'space-between';
    limitNotice.style.alignItems = 'center';
    limitNotice.style.gap = '1rem';
    
    const textSpan = document.createElement('span');
    textSpan.textContent = `Showing first ${renderLimit} of ${groupsToRender.length} quests.`;
    
    const showAllBtn = document.createElement('button');
    showAllBtn.className = 'btn btn-secondary btn-sm';
    showAllBtn.style.padding = '0.2rem 0.5rem';
    showAllBtn.style.fontSize = '0.75rem';
    showAllBtn.textContent = 'Show all quests';
    showAllBtn.addEventListener('click', () => {
      state.sandboxRenderLimit = Infinity;
      updateSandboxPreview();
    });
    
    limitNotice.appendChild(textSpan);
    limitNotice.appendChild(showAllBtn);
    listContainer.appendChild(limitNotice);
  }
  
  itemsToRender.forEach(group => {
    const groupDiv = document.createElement('div');
    groupDiv.className = 'quest-group-container';
    
    // Header
    const headerDiv = document.createElement('div');
    headerDiv.className = 'quest-group-header';
    
    const infoSpan = document.createElement('span');
    infoSpan.className = 'quest-group-title';
    
    const changesMetaText = hasReplacement 
      ? `(${group.sentences.length} sentences, ${group.changedCount} changed)`
      : `(${group.sentences.length} sentences)`;
      
    infoSpan.innerHTML = `${escapeHtml(group.path)} <span class="quest-group-meta">${changesMetaText}</span>`;
    
    const downloadQuestBtn = document.createElement('button');
    downloadQuestBtn.className = 'btn btn-secondary btn-sm btn-download-quest';
    
    // Disable download if there are no actual changes
    if (hasReplacement && !group.hasChanges) {
      downloadQuestBtn.disabled = true;
    } else if (!hasReplacement) {
      downloadQuestBtn.disabled = true;
    }
    
    downloadQuestBtn.innerHTML = `
      <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 0.3rem;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
      Download JSON
    `;
    
    downloadQuestBtn.addEventListener('click', () => downloadQuestJson(group.path));
    
    headerDiv.appendChild(infoSpan);
    headerDiv.appendChild(downloadQuestBtn);
    groupDiv.appendChild(headerDiv);
    
    // List container
    const sentencesContainer = document.createElement('div');
    sentencesContainer.className = 'quest-sentences-list';
    
    group.sentences.forEach(sentenceArray => {
      const [pathIdx, textEn, textTh, diagIdx] = sentenceArray;
      
      const sentenceDiv = document.createElement('div');
      sentenceDiv.className = 'sentence-item-inline';
      
      // Highlight English term if enKey is provided
      let highlightedEn = escapeHtml(textEn);
      if (enKey) {
        const escapedEnKey = escapeHtml(enKey);
        const enHighlightRegex = new RegExp(`(${escapeRegex(escapedEnKey)})`, 'gi');
        highlightedEn = highlightedEn.replace(enHighlightRegex, '<span class="term-highlight">$1</span>');
      }
      
      // Diff Thai translation
      let highlightedTh = escapeHtml(textTh);
      
      if (hasReplacement && textTh.includes(oldTh)) {
        const escapedOld = escapeHtml(oldTh);
        const escapedNew = escapeHtml(newTh);
        const diffMarkup = `<span class="diff-removed">${escapedOld}</span><span class="diff-added">${escapedNew}</span>`;
        
        const replRegex = new RegExp(escapeRegex(escapedOld), 'g');
        highlightedTh = highlightedTh.replace(replRegex, diffMarkup);
      } else if (newTh && textTh.includes(newTh)) {
        const escapedNew = escapeHtml(newTh);
        const highlightMarkup = `<span class="diff-added">${escapedNew}</span>`;
        const replRegex = new RegExp(escapeRegex(escapedNew), 'g');
        highlightedTh = highlightedTh.replace(replRegex, highlightMarkup);
      }
      
      sentenceDiv.innerHTML = `
        <div class="sentence-item-line-num">Line ${diagIdx + 1}</div>
        <div class="sentence-row sentence-row-en">
          <div class="sentence-text sentence-text-en">${highlightedEn}</div>
        </div>
        <div class="sentence-row">
          <div class="sentence-text sentence-text-th">${highlightedTh}</div>
        </div>
      `;
      
      sentencesContainer.appendChild(sentenceDiv);
    });
    
    groupDiv.appendChild(sentencesContainer);
    listContainer.appendChild(groupDiv);
  });
}

// ==========================================================================
// Quest Modification & Download Helpers
// ==========================================================================
async function getModifiedQuestJson(path, oldTh, newTh) {
  const response = await fetch(`./th/${path}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch original quest file: th/${path}`);
  }
  const questData = await response.json();
  
  const enKey = document.getElementById('form-en-key').value.trim();
  const searchThaiDirectly = document.getElementById('sandbox-search-thai').checked;
  const searchRegex = (enKey && !searchThaiDirectly) ? new RegExp(escapeRegex(enKey), 'i') : null;
  
  let modifiedCount = 0;
  if (questData.dialogues && oldTh && newTh && oldTh !== newTh) {
    for (let dialogue of questData.dialogues) {
      const textEn = dialogue.text_en || '';
      const textTh = dialogue.text || '';
      
      // Match English key (if provided) and check if Thai contains the old word
      const matchesEn = !searchRegex || searchRegex.test(textEn);
      if (matchesEn && textTh.includes(oldTh)) {
        // Replace all occurrences of oldTh with newTh
        dialogue.text = textTh.split(oldTh).join(newTh);
        modifiedCount++;
      }
    }
  }
  
  return { questData, modifiedCount };
}

async function downloadQuestJson(path) {
  const oldTh = document.getElementById('sandbox-old-th').value.trim();
  const newTh = document.getElementById('sandbox-new-th').value.trim();
  
  try {
    const { questData } = await getModifiedQuestJson(path, oldTh, newTh);
    const jsonString = JSON.stringify(questData, null, 2);
    const filename = path.split('/').pop();
    
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (error) {
    console.error(error);
    alert(`Error downloading quest file: ${error.message}`);
  }
}

async function downloadAllChanged() {
  const oldTh = document.getElementById('sandbox-old-th').value.trim();
  const newTh = document.getElementById('sandbox-new-th').value.trim();
  
  if (!oldTh || !newTh || oldTh === newTh) {
    alert('Please enter different Old and New translations to generate changes.');
    return;
  }
  
  const enKey = document.getElementById('form-en-key').value.trim();
  const searchThaiDirectly = document.getElementById('sandbox-search-thai').checked;
  const searchRegex = (enKey && !searchThaiDirectly) ? new RegExp(escapeRegex(enKey), 'i') : null;
  const questGroups = new Map();
  
  state.sentencesData.sentences.forEach(s => {
    const [pathIdx, textEn, textTh, idx] = s;
    const matchesEn = !searchRegex || searchRegex.test(textEn);
    if (matchesEn && textTh.includes(oldTh)) {
      const path = state.sentencesData.paths[pathIdx];
      questGroups.set(path, true);
    }
  });
  
  const changedPaths = Array.from(questGroups.keys());
  if (changedPaths.length === 0) {
    alert('No files have changes to download.');
    return;
  }
  
  const downloadAllBtn = document.getElementById('download-all-changed-btn');
  const origText = downloadAllBtn.innerHTML;
  
  // Custom spin style
  downloadAllBtn.innerHTML = `Zipping...`;
  downloadAllBtn.disabled = true;
  
  try {
    const zip = new JSZip();
    
    for (const path of changedPaths) {
      const { questData } = await getModifiedQuestJson(path, oldTh, newTh);
      const jsonString = JSON.stringify(questData, null, 2);
      zip.file(path, jsonString);
    }
    
    const content = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(content);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = 'th_changes.zip';
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (error) {
    console.error(error);
    alert(`Error generating ZIP: ${error.message}`);
  } finally {
    downloadAllBtn.innerHTML = origText;
    downloadAllBtn.disabled = false;
  }
}

// ==========================================================================
// Setup UI Listeners
// ==========================================================================
function setupUI() {
  const searchInput = document.getElementById('glossary-search');
  const clearSearchBtn = document.getElementById('clear-search');
  
  searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value;
    state.currentPage = 1;
    clearSearchBtn.style.display = state.searchQuery ? 'block' : 'none';
    renderTermsTable();
  });
  
  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    state.searchQuery = '';
    state.currentPage = 1;
    clearSearchBtn.style.display = 'none';
    renderTermsTable();
    searchInput.focus();
  });
  
  document.getElementById('status-filters').addEventListener('click', (e) => {
    if (e.target.classList.contains('pill')) {
      document.querySelectorAll('#status-filters .pill').forEach(p => p.classList.remove('active'));
      e.target.classList.add('active');
      state.statusFilter = e.target.dataset.filter;
      state.currentPage = 1;
      renderTermsTable();
    }
  });
  
  document.getElementById('group-filters').addEventListener('click', (e) => {
    if (e.target.classList.contains('pill')) {
      document.querySelectorAll('#group-filters .pill').forEach(p => p.classList.remove('active'));
      e.target.classList.add('active');
      state.groupFilter = e.target.dataset.filter;
      state.currentPage = 1;
      renderTermsTable();
    }
  });
  
  document.getElementById('add-term-btn').addEventListener('click', showAddTermForm);
  
  document.getElementById('cancel-edit-btn').addEventListener('click', () => {
    if (state.selectedTerm) {
      selectTerm(state.selectedTerm);
    } else {
      document.getElementById('term-workspace').style.display = 'none';
      document.getElementById('no-term-selected').style.display = 'flex';
    }
  });
  
  const debouncedUpdateSandbox = debounce(updateSandboxPreview, 300);

  document.getElementById('form-en-key').addEventListener('input', () => {
    state.sandboxRenderLimit = 50;
    debouncedUpdateSandbox();
  });
  
  document.getElementById('form-th-translation').addEventListener('input', (e) => {
    const val = e.target.value.trim();
    document.getElementById('sandbox-new-th').value = val;
    state.sandboxRenderLimit = 50;
    debouncedUpdateSandbox();
  });
  
  document.getElementById('sandbox-old-th').addEventListener('input', () => {
    state.sandboxRenderLimit = 50;
    debouncedUpdateSandbox();
  });
  document.getElementById('sandbox-new-th').addEventListener('input', () => {
    state.sandboxRenderLimit = 50;
    debouncedUpdateSandbox();
  });
  document.getElementById('sandbox-focus-changed').addEventListener('change', () => {
    state.sandboxRenderLimit = 50;
    updateSandboxPreview();
  });
  document.getElementById('sandbox-search-thai').addEventListener('change', () => {
    state.sandboxRenderLimit = 50;
    updateSandboxPreview();
  });
  document.getElementById('download-all-changed-btn').addEventListener('click', downloadAllChanged);
  
  document.getElementById('save-term-btn').addEventListener('click', saveTerm);
  document.getElementById('download-btn').addEventListener('click', downloadGlossary);
  
  document.getElementById('quick-test-btn').addEventListener('click', () => {
    showAddTermForm();
    document.getElementById('workspace-title').textContent = 'Interactive Replacement Sandbox';
    document.getElementById('save-term-btn').textContent = 'Test Only';
    document.getElementById('save-term-btn').style.opacity = '0.5';
  });
}

function saveTerm() {
  const enKey = document.getElementById('form-en-key').value.trim();
  const thTranslation = document.getElementById('form-th-translation').value.trim();
  const status = document.getElementById('form-status').value;
  const group = document.getElementById('form-group-select').value;
  const rules = document.getElementById('form-rules').value.trim();
  const action = document.getElementById('form-action').value;
  const originalKey = document.getElementById('form-original-en').value;
  
  if (!enKey || !thTranslation) {
    alert('Please fill out the EN Key and TH Translation fields.');
    return;
  }
  
  if (action === 'add') {
    // Check if key already exists in the same group
    const exists = state.glossaryTerms.some(t => t.key.toLowerCase() === enKey.toLowerCase() && t.group === group);
    if (exists) {
      alert(`The term "${enKey}" already exists in the "${group}" group.`);
      return;
    }
    
    const newTerm = {
      key: enKey,
      thai: thTranslation,
      status: status,
      rules: rules,
      group: group,
      originalKey: enKey
    };
    
    state.glossaryTerms.push(newTerm);
    state.selectedTerm = newTerm;
  } else {
    // Edit action
    const term = state.glossaryTerms.find(t => t.key === originalKey && t.group === state.selectedTerm.group);
    if (term) {
      term.thai = thTranslation;
      term.status = status;
      term.rules = rules;
      // Group and Key are locked during editing to avoid tree mismatches
      state.selectedTerm = term;
    }
  }
  
  // Set unsaved changes
  state.unsavedChanges = true;
  document.getElementById('unsaved-indicator').style.display = 'block';
  
  // Re-render
  renderTermsTable();
  
  // Select the term
  selectTerm(state.selectedTerm);
  
  // Flash Save Button success
  const saveBtn = document.getElementById('save-term-btn');
  const origText = saveBtn.innerHTML;
  saveBtn.innerHTML = '✓ Saved to Memory';
  saveBtn.classList.remove('btn-success');
  saveBtn.style.backgroundColor = '#059669';
  
  setTimeout(() => {
    saveBtn.innerHTML = origText;
    saveBtn.classList.add('btn-success');
    saveBtn.style.backgroundColor = '';
  }, 1500);
}

function downloadGlossary() {
  const updatedMarkdown = generateMarkdown(state.originalGlossaryText, state.glossaryTerms);
  
  const blob = new Blob([updatedMarkdown], { type: 'text/markdown;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = 'glossary.md';
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  // Re-sync State
  state.originalGlossaryText = updatedMarkdown;
  state.unsavedChanges = false;
  document.getElementById('unsaved-indicator').style.display = 'none';
}

// ==========================================================================
// Helper Utilities
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

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
