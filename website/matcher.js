import './matcher.css';

// Global State
let appData = null;
let filteredDialogues = [];
let currentPage = 1;
const ITEMS_PER_PAGE = 50;

// DOM Elements
const totalDialoguesEl = document.getElementById('stat-total-dialogues');
const uniqueKeysEl = document.getElementById('stat-unique-keys');
const matchStandardEl = document.getElementById('stat-match-standard');
const matchImprovedEl = document.getElementById('stat-match-improved');
const improvedCountEl = document.getElementById('stat-improved-count');

// Controls
const searchInput = document.getElementById('search-input');
const statusSelect = document.getElementById('filter-status');
const patchSelect = document.getElementById('filter-patch');
const speakerSelect = document.getElementById('filter-speaker');
const resultsCountEl = document.getElementById('results-count');

// Table Body
const tbody = document.getElementById('dialogue-tbody');

// Pagination
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const pageInfo = document.getElementById('page-info');

// Load Data
async function loadDashboardData() {
    try {
        const response = await fetch('./data.json');
        appData = await response.json();
        
        initializeStats();
        initializeFilterOptions();
        setupTabSwitching();
        
        // Default list setup
        filteredDialogues = [...appData.dialogues];
        currentPage = 1;
        renderDialogues();
        
        // Attach Event Listeners
        searchInput.addEventListener('input', handleFiltersChange);
        statusSelect.addEventListener('change', handleFiltersChange);
        patchSelect.addEventListener('change', handleFiltersChange);
        speakerSelect.addEventListener('change', handleFiltersChange);
        
        btnPrev.addEventListener('click', () => changePage(-1));
        btnNext.addEventListener('click', () => changePage(1));
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        tbody.innerHTML = `<tr><td colspan="4" class="loading-cell" style="color: var(--accent-red)">Error loading data.json database. Make sure analyze_keys_v2.py ran successfully.</td></tr>`;
    }
}

// Stats Animation & Initialization
function initializeStats() {
    const s = appData.summary;
    
    // Animate numbers
    animateValue(totalDialoguesEl, 0, s.total_dialogues, 1000);
    animateValue(uniqueKeysEl, 0, s.unique_keys, 1000);
    
    matchStandardEl.textContent = s.match_rate_standard;
    matchImprovedEl.textContent = s.match_rate_overall || s.match_rate_improved;
    
    const pronounCount = s.matched_improved || 0;
    const alignedCount = s.matched_aligned || 0;
    improvedCountEl.textContent = `+${pronounCount} pronoun, +${alignedCount} aligned`;
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.textContent = Math.floor(progress * (end - start) + start).toLocaleString();
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// Tab switching logic for Case Studies
function setupTabSwitching() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            // Remove active class from all buttons and contents
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked button and target tab content
            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });
}

// Dropdown Setup
function initializeFilterOptions() {
    // Patches
    const patches = appData.top_patches.map(item => item[0]);
    patches.sort();
    patches.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = `Patch ${p}`;
        patchSelect.appendChild(opt);
    });
    
    // Speakers
    const speakers = appData.top_speakers.map(item => item[0]);
    speakers.sort();
    speakers.forEach(spk => {
        const opt = document.createElement('option');
        opt.value = spk;
        opt.textContent = spk;
        speakerSelect.appendChild(opt);
    });
}

// Filter Logic
function handleFiltersChange() {
    const query = searchInput.value.toLowerCase().trim();
    const status = statusSelect.value;
    const patch = patchSelect.value;
    const speaker = speakerSelect.value;
    
    filteredDialogues = appData.dialogues.filter(item => {
        // Status filter
        if (status !== 'all' && item.status !== status) return false;
        
        // Patch filter
        if (patch !== 'all' && item.patch !== patch) return false;
        
        // Speaker filter
        if (speaker !== 'all' && item.speaker !== speaker) return false;
        
        // Search query
        if (query) {
            const matchesText = item.text_en.toLowerCase().includes(query) || 
                                item.text_th.toLowerCase().includes(query) || 
                                item.voice_key.toLowerCase().includes(query) || 
                                (item.speaker && item.speaker.toLowerCase().includes(query));
            if (!matchesText) return false;
        }
        
        return true;
    });
    
    currentPage = 1;
    renderDialogues();
}

// Render Table
function renderDialogues() {
    tbody.innerHTML = '';
    
    const totalItems = filteredDialogues.length;
    resultsCountEl.textContent = `Showing ${totalItems.toLocaleString()} of ${appData.dialogues.length.toLocaleString()} items`;
    
    if (totalItems === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="loading-cell">No matching dialogue lines found. Try adjusting filters or search term.</td></tr>`;
        updatePagination(0);
        return;
    }
    
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, totalItems);
    const pageItems = filteredDialogues.slice(startIndex, endIndex);
    
    pageItems.forEach(item => {
        const tr = document.createElement('tr');
        
        // Status Badge cell
        let badgeLabel = 'Unmatched';
        if (item.status === 'matched_standard') badgeLabel = 'Standard Match';
        if (item.status === 'matched_improved') badgeLabel = 'Improved Match';
        if (item.status === 'matched_aligned') badgeLabel = 'Aligned Match';
        
        const badgeCell = `
            <td>
                <span class="status-badge ${item.status}">${badgeLabel}</span>
            </td>
        `;
        
        // Metadata / Speaker cell
        const questList = item.quests.join(', ');
        const speakerMarkup = item.speaker 
            ? `<span class="meta-speaker">${item.speaker}</span>` 
            : `<span class="meta-speaker" style="color: var(--text-muted)">NPC</span>`;
            
        const patchBadge = item.patch 
            ? `<div class="meta-patch-badge">Patch ${item.patch}</div>` 
            : '';
            
        const metaCell = `
            <td>
                <div class="meta-block">
                    ${speakerMarkup}
                    <span class="meta-quest">${questList}</span>
                    ${patchBadge}
                </div>
            </td>
        `;
        
        // English sentence cell
        const gameRawTextMarkup = item.game_en 
            ? `<div class="text-raw-game">Game Raw: "${item.game_en}"</div>` 
            : '';
            
        const englishCell = `
            <td>
                <div class="translation-texts">
                    <span class="text-translation-en">"${item.text_en}"</span>
                    ${gameRawTextMarkup}
                    ${item.voice_key ? `<span style="font-size:0.75rem; color: var(--text-muted); font-family: monospace;">Key: ${item.voice_key}</span>` : ''}
                </div>
            </td>
        `;
        
        // Thai translation cell
        const thaiCell = `
            <td>
                <div class="text-translation-th">${item.text_th}</div>
            </td>
        `;
        
        tr.innerHTML = badgeCell + metaCell + englishCell + thaiCell;
        tbody.appendChild(tr);
    });
    
    updatePagination(totalItems);
}

// Pagination Controls
function updatePagination(totalItems) {
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE) || 1;
    
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    btnPrev.disabled = currentPage === 1;
    btnNext.disabled = currentPage === totalPages;
}

function changePage(direction) {
    const totalPages = Math.ceil(filteredDialogues.length / ITEMS_PER_PAGE) || 1;
    currentPage += direction;
    
    if (currentPage < 1) currentPage = 1;
    if (currentPage > totalPages) currentPage = totalPages;
    
    renderDialogues();
    // Scroll to table header
    document.querySelector('.dialogues-section').scrollIntoView({ behavior: 'smooth' });
}

// Init Dashboard
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadDashboardData);
} else {
    loadDashboardData();
}

// Tab Switching between Glossary and Matcher
function initTabSwitching() {
    const navGlossary = document.getElementById('nav-btn-glossary');
    const navMatcher = document.getElementById('nav-btn-matcher');
    const glossaryView = document.getElementById('glossary-view');
    const matcherView = document.getElementById('matcher-view');

    if (navGlossary && navMatcher && glossaryView && matcherView) {
        navGlossary.addEventListener('click', () => {
            navGlossary.classList.add('active');
            navMatcher.classList.remove('active');
            glossaryView.style.display = 'flex';
            matcherView.style.display = 'none';
        });
        
        navMatcher.addEventListener('click', () => {
            navMatcher.classList.add('active');
            navGlossary.classList.remove('active');
            glossaryView.style.display = 'none';
            matcherView.style.display = 'flex';
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTabSwitching);
} else {
    initTabSwitching();
}
