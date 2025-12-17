// Race Timing System - Main JavaScript

// API Base URL
const API_BASE = '/api';

// Utility Functions
function formatTime(seconds) {
    if (!seconds) return '-';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;

    const container = document.querySelector('.container') || document.body;
    container.insertBefore(alertDiv, container.firstChild);

    setTimeout(() => alertDiv.remove(), 5000);
}

// API Client
const API = {
    // Events
    async getEvents() {
        const response = await fetch(`${API_BASE}/events`);
        return response.json();
    },

    async getEvent(id) {
        const response = await fetch(`${API_BASE}/events/${id}`);
        return response.json();
    },

    async createEvent(data) {
        const response = await fetch(`${API_BASE}/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async deleteEvent(id) {
        const response = await fetch(`${API_BASE}/events/${id}`, {
            method: 'DELETE'
        });
        return response.json();
    },

    // Races
    async getRaces() {
        const response = await fetch(`${API_BASE}/races`);
        return response.json();
    },

    async getRace(id) {
        const response = await fetch(`${API_BASE}/races/${id}`);
        return response.json();
    },

    async createRace(data) {
        const response = await fetch(`${API_BASE}/races`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async deleteRace(id) {
        const response = await fetch(`${API_BASE}/races/${id}`, {
            method: 'DELETE'
        });
        return response.json();
    },

    async addTimingPoint(raceId, data) {
        const response = await fetch(`${API_BASE}/races/${raceId}/timing-points`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async deleteTimingPoint(raceId, tpId) {
        const response = await fetch(`${API_BASE}/races/${raceId}/timing-points/${tpId}`, {
            method: 'DELETE'
        });
        return response.json();
    },

    async updateAgeGroups(raceId, ageGroups) {
        const response = await fetch(`${API_BASE}/races/${raceId}/age-groups`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ age_groups: ageGroups })
        });
        return response.json();
    },

    // Participants
    async getParticipants(raceId = null) {
        const url = raceId ? `${API_BASE}/participants?race_id=${raceId}` : `${API_BASE}/participants`;
        const response = await fetch(url);
        return response.json();
    },

    async createParticipant(data) {
        const response = await fetch(`${API_BASE}/participants`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async updateParticipant(participantId, data) {
        const response = await fetch(`${API_BASE}/participants/${participantId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async registerParticipant(participantId, data) {
        const response = await fetch(`${API_BASE}/participants/${participantId}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async updateRFID(participantId, rfidTag) {
        const response = await fetch(`${API_BASE}/participants/${participantId}/rfid`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rfid_tag: rfidTag })
        });
        return response.json();
    },

    async getAgeGroups() {
        const response = await fetch(`${API_BASE}/age-groups`);
        return response.json();
    },

    // Race Control
    async startLLRP(raceId, readerHost, readerPort = 5084) {
        const response = await fetch(`${API_BASE}/races/${raceId}/control/start-llrp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reader_host: readerHost, reader_port: readerPort })
        });
        return response.json();
    },

    async stopLLRP(raceId) {
        const response = await fetch(`${API_BASE}/races/${raceId}/control/stop-llrp`, {
            method: 'POST'
        });
        return response.json();
    },

    async startRace(raceId) {
        const response = await fetch(`${API_BASE}/races/${raceId}/start`, {
            method: 'POST'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start race');
        }
        return response.json();
    },

    async updateRaceStartTime(raceId, startTime) {
        const response = await fetch(`${API_BASE}/races/${raceId}/start-time`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start_time: startTime })
        });
        return response.json();
    },

    async recordTime(raceId, data) {
        const response = await fetch(`${API_BASE}/races/${raceId}/control/time`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async markDNF(raceId, bibNumber, notes = '') {
        const response = await fetch(`${API_BASE}/races/${raceId}/control/dnf`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bib_number: bibNumber, notes })
        });
        return response.json();
    },

    async markDNS(raceId, bibNumber, notes = '') {
        const response = await fetch(`${API_BASE}/races/${raceId}/control/dns`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bib_number: bibNumber, notes })
        });
        return response.json();
    },

    // Time Records
    async getTimeRecords(raceId) {
        const response = await fetch(`${API_BASE}/races/${raceId}/time-records`);
        return response.json();
    },

    async createTimeRecord(raceId, data) {
        const response = await fetch(`${API_BASE}/races/${raceId}/time-records`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async updateTimeRecord(recordId, data) {
        const response = await fetch(`${API_BASE}/time-records/${recordId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    },

    async deleteTimeRecord(recordId) {
        const response = await fetch(`${API_BASE}/time-records/${recordId}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete time record');
        }
        return response.json();
    },

    async recalculateResults(raceId) {
        const response = await fetch(`${API_BASE}/races/${raceId}/recalculate`, {
            method: 'POST'
        });
        return response.json();
    },


    // Results
    async getResults(raceId) {
        const response = await fetch(`${API_BASE}/races/${raceId}/results`);
        return response.json();
    },

    async getLeaderboard(raceId, limit = 20) {
        const response = await fetch(`${API_BASE}/races/${raceId}/leaderboard?limit=${limit}`);
        return response.json();
    }
};

// Real-time Updates
function connectToStream(raceId, callback) {
    const eventSource = new EventSource(`${API_BASE}/races/${raceId}/stream`);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        callback(data);
    };

    eventSource.onerror = (error) => {
        console.error('Stream error:', error);
        eventSource.close();
    };

    return eventSource;
}

// Form Helpers
function getFormData(formId) {
    const form = document.getElementById(formId);
    const formData = new FormData(form);
    const data = {};

    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }

    return data;
}

function resetForm(formId) {
    document.getElementById(formId).reset();
}

// Table Helpers
function createTableRow(data, columns) {
    const tr = document.createElement('tr');

    columns.forEach(col => {
        const td = document.createElement('td');
        if (typeof col.render === 'function') {
            td.innerHTML = col.render(data);
        } else {
            td.textContent = data[col.key] || '-';
        }
        tr.appendChild(td);
    });

    return tr;
}

function populateTable(tableId, data, columns) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    tbody.innerHTML = '';

    data.forEach(item => {
        tbody.appendChild(createTableRow(item, columns));
    });
}

// Status Badge Helper
function getStatusBadge(status) {
    const badges = {
        'registered': '<span class="badge badge-secondary">Registered</span>',
        'started': '<span class="badge badge-primary">Started</span>',
        'finished': '<span class="badge badge-success">Finished</span>',
        'dnf': '<span class="badge badge-danger">DNF</span>',
        'dns': '<span class="badge badge-warning">DNS</span>'
    };
    return badges[status] || status;
}

// Race Type Icons
function getRaceTypeIcon(type) {
    const icons = {
        'triathlon': '🏊🚴🏃',
        'duathlon': '🏃🚴🏃',
        'aquathlon': '🏊🏃',
        'running': '🏃',
        'cycling': '🚴'
    };
    return icons[type] || '🏁';
}

// Age Group Calculation
// Age Group Calculation
function getAgeGroup(age, gender = null, customGroups = null) {
    if (!age) return 'Unknown';

    if (customGroups && Array.isArray(customGroups) && customGroups.length > 0) {
        for (const group of customGroups) {
            // Handle gender-specific groups if specified
            if (group.gender && group.gender !== 'All' && group.gender !== gender) {
                continue;
            }

            if (age >= group.min && age <= group.max) {
                return group.name;
            }
        }
        // If no custom group matches, fall back to default or return 'Other'
        // Let's fall back to default for now to be safe, or maybe 'Unknown'
    }

    let bracket;
    if (age < 20) bracket = 'Under 20';
    else if (age < 30) bracket = '20-29';
    else if (age < 40) bracket = '30-39';
    else if (age < 50) bracket = '40-49';
    else if (age < 60) bracket = '50-59';
    else bracket = '60+';

    if (gender) {
        const genderPrefix = gender.toUpperCase() === 'M' ? 'Open' :
            gender.toUpperCase() === 'F' ? 'Female' : '';
        if (genderPrefix) {
            return `${genderPrefix} ${bracket}`;
        }
    }

    return bracket;
}

// Export Functions
window.RaceTimingApp = {
    API,
    formatTime,
    formatDate,
    showAlert,
    connectToStream,
    getFormData,
    resetForm,
    populateTable,
    getStatusBadge,
    getRaceTypeIcon,
    getAgeGroup,

    // Collapsible card functionality
    initCollapsibleCards() {
        document.querySelectorAll('.card-header').forEach(header => {
            // Skip if already initialized
            if (header.dataset.collapsibleInit) return;
            header.dataset.collapsibleInit = 'true';

            // Add collapse icon if not present
            if (!header.querySelector('.collapse-icon')) {
                const icon = document.createElement('span');
                icon.className = 'collapse-icon';
                icon.innerHTML = '▼';
                header.appendChild(icon);
            }

            // Add click handler
            header.addEventListener('click', function (e) {
                // Don't collapse if clicking on buttons or inputs
                if (e.target.tagName === 'BUTTON' || e.target.tagName === 'A' ||
                    e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
                    return;
                }

                const card = this.closest('.card');
                const body = card.querySelector('.card-body');
                const icon = this.querySelector('.collapse-icon');

                this.classList.toggle('collapsed');
                body.classList.toggle('collapsed');

                // Save state to localStorage
                const cardId = card.id || this.textContent.trim().substring(0, 50);
                if (cardId) {
                    localStorage.setItem(`card-${cardId}-collapsed`, this.classList.contains('collapsed'));
                }
            });

            // Restore collapsed state from localStorage
            const card = header.closest('.card');
            const cardId = card.id || header.textContent.trim().substring(0, 50);
            if (cardId && localStorage.getItem(`card-${cardId}-collapsed`) === 'true') {
                header.classList.add('collapsed');
                const body = card.querySelector('.card-body');
                if (body) body.classList.add('collapsed');
            }
        });
    }
};

// Initialize collapsible cards when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.RaceTimingApp && window.RaceTimingApp.initCollapsibleCards) {
        window.RaceTimingApp.initCollapsibleCards();
    }
});

// Re-initialize collapsible cards when new content is added
const cardObserver = new MutationObserver(() => {
    if (window.RaceTimingApp && window.RaceTimingApp.initCollapsibleCards) {
        window.RaceTimingApp.initCollapsibleCards();
    }
});
cardObserver.observe(document.body, { childList: true, subtree: true });

// Searchable Select Component
class SearchableSelect {
    constructor(containerId, options, onSelect) {
        this.container = document.getElementById(containerId);
        this.options = options || []; // [{value, label}]
        this.onSelect = onSelect;
        this.selectedValue = null;

        this.render();
    }

    render() {
        this.container.classList.add('searchable-select');
        this.container.innerHTML = `
            <input type="text" class="form-control search-input" placeholder="Search...">
            <span class="clear-btn" style="display:none;">&times;</span>
            <div class="options-list"></div>
        `;

        this.searchInput = this.container.querySelector('.search-input');
        this.optionsList = this.container.querySelector('.options-list');
        this.clearBtn = this.container.querySelector('.clear-btn');

        this.searchInput.addEventListener('input', () => this.filterOptions());
        this.searchInput.addEventListener('focus', () => {
            this.filterOptions();
            this.optionsList.classList.add('show');
        });

        // Close on click outside
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.optionsList.classList.remove('show');
            }
        });

        this.clearBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.clear();
        });
    }

    filterOptions() {
        const term = this.searchInput.value.toLowerCase();
        const filtered = this.options.filter(opt => opt.label.toLowerCase().includes(term));

        this.optionsList.innerHTML = '';

        if (filtered.length === 0) {
            this.optionsList.innerHTML = '<div class="no-results">No results found</div>';
        } else {
            filtered.forEach(opt => {
                const div = document.createElement('div');
                div.className = 'option';
                if (opt.value === this.selectedValue) div.classList.add('selected');
                div.textContent = opt.label;
                div.onclick = () => this.select(opt);
                this.optionsList.appendChild(div);
            });
        }
    }

    select(option) {
        this.selectedValue = option.value;
        this.searchInput.value = option.label;
        this.optionsList.classList.remove('show');
        this.clearBtn.style.display = 'block';
        if (this.onSelect) this.onSelect(option.value);
    }

    clear() {
        this.selectedValue = null;
        this.searchInput.value = '';
        this.clearBtn.style.display = 'none';
        if (this.onSelect) this.onSelect(null);
    }

    setValue(value) {
        const option = this.options.find(opt => opt.value == value);
        if (option) {
            this.select(option);
        } else {
            this.clear();
        }
    }

    setOptions(options) {
        this.options = options;
    }
}

window.SearchableSelect = SearchableSelect;
