// Global variables
let map;
let housesLayer;
let vacantLandLayer;
let opportunitiesLayer;
let allProperties = [];
let allOpportunities = [];
let landPriceFilter = 'all';
let landSizeFilter = 'all';

// Initialize map
async function initMap() {
    // Get config from API
    const config = await fetch('/api/config').then(r => r.json());

    // Create map
    map = L.map('map').setView([config.center.lat, config.center.lng], 11);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Create layer groups
    housesLayer = L.layerGroup().addTo(map);
    vacantLandLayer = L.layerGroup().addTo(map);
    opportunitiesLayer = L.layerGroup();

    // Load data
    await loadStats();
    await loadData();
}

// Load stats
async function loadStats() {
    try {
        const stats = await fetch('/api/stats').then(r => r.json());

        // Calculate houses and vacant land from loaded properties
        const housesCount = allProperties.filter(p => p.sqft > 100).length;
        const vacantCount = allProperties.filter(p => p.sqft <= 100).length;

        const statsHTML = `
            <div class="stat-item">🏠 Houses: ${housesCount.toLocaleString()}</div>
            <div class="stat-item" id="vacant-land-stat">🌳 Vacant Land: ${vacantCount.toLocaleString()}</div>
            <div class="stat-item">✅ Active: ${stats.active_properties.toLocaleString()}</div>
            <div class="stat-item">📦 Total: ${stats.properties.toLocaleString()}</div>
            <div class="stat-item">🔗 With URLs: ${stats.properties_with_url.toLocaleString()}</div>
            <div class="stat-item">🛣️ Streets: ${stats.streets}</div>
        `;

        document.getElementById('stats').innerHTML = statsHTML;
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('stats').innerHTML = '<div class="stat-item">⚠️ Error loading stats</div>';
    }
}

// Load all data
async function loadData() {
    try {
        // Load properties
        allProperties = await fetch('/api/properties').then(r => r.json());

        // Load opportunities
        allOpportunities = await fetch('/api/opportunities').then(r => r.json());

        // Update stats after loading data
        await loadStats();

        // Render markers
        renderMarkers();
    } catch (error) {
        console.error('Error loading data:', error);
        alert('Error loading data. Please check console.');
    }
}

// Render markers
function renderMarkers() {
    // Clear layers
    housesLayer.clearLayers();
    vacantLandLayer.clearLayers();
    opportunitiesLayer.clearLayers();

    // Get filters
    const showHouses = document.getElementById('toggle-houses').checked;
    const showVacantLand = document.getElementById('toggle-vacant-land').checked;
    const showOpportunities = document.getElementById('toggle-opportunities').checked;
    const urgencyFilter = document.getElementById('urgency-filter').value;
    const colorFilter = document.getElementById('color-filter').value;

    // Separate properties into houses and vacant land
    const houses = allProperties.filter(p => p.sqft > 100);
    let vacantLand = allProperties.filter(p => p.sqft <= 100);

    // Apply price filter to vacant land
    if (landPriceFilter !== 'all') {
        vacantLand = vacantLand.filter(prop => {
            const price = prop.price;
            if (!price) return false;
            return price <= landPriceFilter;
        });
    }

    // Apply size filter to vacant land
    if (landSizeFilter !== 'all') {
        vacantLand = vacantLand.filter(prop => {
            const lotSize = prop.lot_size;
            if (!lotSize) return false;
            const acres = lotSize / 43560; // Convert sqft to acres
            return acres >= landSizeFilter;
        });
    }

    // Add house markers
    if (showHouses) {
        houses.forEach(prop => {
            if (colorFilter !== 'all') {
                // Filter by color (need to get street analysis)
                // For now, show all
            }

            const marker = L.circleMarker([prop.lat, prop.lng], {
                radius: 5,
                fillColor: getPropertyColor(prop),
                color: '#fff',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            });

            marker.bindPopup(createPropertyPopup(prop));
            marker.addTo(housesLayer);
        });
    }

    // Add vacant land markers with different style
    if (showVacantLand) {
        vacantLand.forEach(prop => {
            // Create triangle marker for vacant land
            const marker = L.marker([prop.lat, prop.lng], {
                icon: L.divIcon({
                    html: '<div style="color: #8b4513; font-size: 20px; text-align: center;">▲</div>',
                    className: 'vacant-land-marker',
                    iconSize: [20, 20],
                    iconAnchor: [10, 20]
                })
            });

            marker.bindPopup(createVacantLandPopup(prop));
            marker.addTo(vacantLandLayer);
        });

        // Update filtered count display
        updateFilteredCount(vacantLand.length);
    }

    // Add opportunity markers
    if (showOpportunities) {
        allOpportunities.forEach(opp => {
            // Apply filters
            if (urgencyFilter !== 'all') {
                if (urgencyFilter === 'urgent' && opp.urgency_level !== 'urgent') return;
                if (urgencyFilter === 'good' && opp.urgency_level === 'normal') return;
            }

            if (colorFilter !== 'all' && opp.zone_color !== colorFilter) return;

            const marker = L.circleMarker([opp.lat, opp.lng], {
                radius: 8,
                fillColor: getUrgencyColor(opp.urgency_level),
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.9
            });

            marker.bindPopup(createOpportunityPopup(opp));
            marker.addTo(opportunitiesLayer);
        });
    }
}

// Get property color
function getPropertyColor(prop) {
    if (!prop.price_sqft) return '#999';

    if (prop.price_sqft >= 350) return '#10b981'; // green
    if (prop.price_sqft >= 300) return '#86efac'; // light green
    if (prop.price_sqft >= 220) return '#fbbf24'; // yellow
    return '#ef4444'; // red
}

// Get urgency color
function getUrgencyColor(level) {
    switch(level) {
        case 'urgent': return '#dc2626';
        case 'good': return '#f59e0b';
        default: return '#3b82f6';
    }
}

// Create vacant land popup
function createVacantLandPopup(prop) {
    const price = prop.price ? `$${prop.price.toLocaleString()}` : 'N/A';
    const lotSize = prop.lot_size ? `${prop.lot_size.toLocaleString()} sqft (${(prop.lot_size/43560).toFixed(2)} acres)` : 'N/A';
    const pricePerSqft = prop.price_sqft ? `$${prop.price_sqft}/sqft` : 'N/A';
    const urlLink = prop.url ?
        `<br><strong>Listing:</strong> <a href="${prop.url}" target="_blank" style="color: #0066cc; text-decoration: underline;">View on Redfin →</a>` :
        `<br><strong>Listing:</strong> <span style="color: #999;">Not available</span>`;

    return `
        <div class="popup-content">
            <div class="popup-title">🌳 Vacant Land</div>
            <div class="popup-info">
                <strong>Address:</strong> ${prop.address}<br>
                <strong>City:</strong> ${prop.city}<br>
                <strong>Price:</strong> ${price}<br>
                <strong>Lot Size:</strong> ${lotSize}<br>
                <strong>Price Zone:</strong> ${getZoneColor(prop.price_sqft)}<br>
                <strong>Status:</strong> ${prop.status}${urlLink}
            </div>
        </div>
    `;
}

// Get zone color based on price per sqft
function getZoneColor(priceSqft) {
    if (!priceSqft) return 'Unknown';
    if (priceSqft >= 350) return '🟢 Green Zone ($350+)';
    if (priceSqft >= 220) return '🟡 Yellow Zone ($220-350)';
    return '🔴 Red Zone (<$220)';
}

// Create property popup
function createPropertyPopup(prop) {
    const price = prop.price ? `$${prop.price.toLocaleString()}` : 'N/A';
    const pricePerSqft = prop.price_sqft ? `$${prop.price_sqft.toFixed(2)}/sqft` : 'N/A';
    const urlLink = prop.url ?
        `<br><strong>Listing:</strong> <a href="${prop.url}" target="_blank" style="color: #0066cc; text-decoration: underline;">View on Redfin →</a>` :
        `<br><strong>Listing:</strong> <span style="color: #999;">Not available</span>`;

    return `
        <div class="popup-title">🏠 ${prop.address}</div>
        <div class="popup-info">
            <strong>City:</strong> ${prop.city}<br>
            <strong>Price:</strong> ${price}<br>
            <strong>Price/sqft:</strong> ${pricePerSqft}<br>
            <strong>Sqft:</strong> ${prop.sqft ? prop.sqft.toLocaleString() : 'N/A'}<br>
            <strong>Status:</strong> ${prop.status}${urlLink}
        </div>
    `;
}

// Create opportunity popup
function createOpportunityPopup(opp) {
    const price = opp.price ? `$${opp.price.toLocaleString()}` : 'N/A';
    const lotSize = opp.lot_size ? `${opp.lot_size.toFixed(2)} acres` : 'N/A';

    const urgencyClass = `urgency-${opp.urgency_level}`;
    const urgencyText = opp.urgency_level.toUpperCase();

    return `
        <div class="popup-title">🏞️ LAND OPPORTUNITY</div>
        <div class="popup-info">
            <strong>Address:</strong> ${opp.address}<br>
            <strong>Price:</strong> ${price}<br>
            <strong>Lot Size:</strong> ${lotSize}<br>
            <strong>Zone:</strong> ${opp.zone_color.replace('_', ' ')}<br>
            <strong>Market:</strong> ${opp.market_status}<br>
            <strong>Score:</strong> ${opp.urgency_score}/100<br>
            <span class="urgency-badge ${urgencyClass}">${urgencyText}</span>
            ${opp.notes ? `<br><br><em>${opp.notes}</em>` : ''}
        </div>
    `;
}

// Refresh map
async function refreshMap() {
    document.getElementById('stats').innerHTML = 'Loading...';
    await loadStats();
    await loadData();
}

// Event listeners
document.getElementById('toggle-houses').addEventListener('change', renderMarkers);
document.getElementById('toggle-vacant-land').addEventListener('change', renderMarkers);
document.getElementById('toggle-opportunities').addEventListener('change', renderMarkers);
document.getElementById('urgency-filter').addEventListener('change', renderMarkers);
document.getElementById('color-filter').addEventListener('change', renderMarkers);

// Import modal functions
function showImportModal() {
    document.getElementById('importModal').style.display = 'flex';
    document.getElementById('importStatus').style.display = 'none';
    document.getElementById('importResults').style.display = 'none';
    document.getElementById('csvFile').value = '';
}

function closeImportModal() {
    document.getElementById('importModal').style.display = 'none';
}

// Import CSV function
async function importCSV() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];

    if (!file) {
        alert('Please select a CSV file to import');
        return;
    }

    if (!file.name.endsWith('.csv')) {
        alert('Please select a valid CSV file');
        return;
    }

    // Prepare form data
    const formData = new FormData();
    formData.append('file', file);

    // Show status
    document.getElementById('importStatus').style.display = 'block';
    document.getElementById('importResults').style.display = 'none';

    const statusMessage = document.querySelector('.status-message');
    const progressFill = document.querySelector('.progress-fill');

    statusMessage.textContent = 'Uploading and processing file...';
    progressFill.style.width = '50%';

    try {
        // Send file to server
        const response = await fetch('/api/import', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Show success
            progressFill.style.width = '100%';
            statusMessage.textContent = 'Import complete!';

            // Show results
            setTimeout(() => {
                document.getElementById('importStatus').style.display = 'none';
                document.getElementById('importResults').style.display = 'block';

                const resultsStats = document.querySelector('.results-stats');
                resultsStats.innerHTML = `
                    <p><strong>Import Summary:</strong></p>
                    <p>✅ New properties imported: ${result.imported}</p>
                    <p>🔄 Existing properties updated: ${result.updated}</p>
                    <p>📊 Total rows processed: ${result.total_processed}</p>
                    ${result.errors && result.errors.length > 0 ?
                        `<p>⚠️ Errors: ${result.errors.length}</p>` : ''}
                `;

                // Reload stats
                loadStats();
            }, 1000);
        } else {
            // Show error
            statusMessage.textContent = `Error: ${result.error || 'Import failed'}`;
            progressFill.style.width = '0%';
            progressFill.style.background = '#ef4444';
        }
    } catch (error) {
        console.error('Import error:', error);
        statusMessage.textContent = `Error: ${error.message}`;
        progressFill.style.width = '0%';
        progressFill.style.background = '#ef4444';
    }
}

// Refresh map data
async function refreshMap() {
    await loadStats();
    await loadData();
}

// Close modal on click outside
window.onclick = function(event) {
    const modal = document.getElementById('importModal');
    if (event.target == modal) {
        closeImportModal();
    }
}

// Filter handler functions
function handleLandPriceFilter() {
    const selectElement = document.getElementById('land-price-filter');
    const customInput = document.getElementById('custom-price-filter');
    const applyBtn = document.getElementById('apply-custom-btn');

    if (selectElement.value === 'custom') {
        // Show custom input fields
        customInput.style.display = 'inline-block';
        applyBtn.style.display = 'inline-block';
        customInput.focus();
    } else {
        // Hide custom input fields
        customInput.style.display = 'none';
        applyBtn.style.display = 'none';

        // Apply the selected filter
        if (selectElement.value === 'all') {
            landPriceFilter = 'all';
        } else {
            landPriceFilter = parseInt(selectElement.value);
        }
        renderMarkers();
    }
}

function applyCustomPrice() {
    const customInput = document.getElementById('custom-price-filter');
    const value = parseInt(customInput.value);

    if (value && value > 0) {
        landPriceFilter = value;
        renderMarkers();
    } else {
        alert('Please enter a valid price');
    }
}

function handleLandSizeFilter() {
    const selectElement = document.getElementById('land-size-filter');
    const customInput = document.getElementById('custom-size-filter');
    const applyBtn = document.getElementById('apply-size-btn');

    if (selectElement.value === 'custom') {
        // Show custom input fields
        customInput.style.display = 'inline-block';
        applyBtn.style.display = 'inline-block';
        customInput.focus();
    } else {
        // Hide custom input fields
        customInput.style.display = 'none';
        applyBtn.style.display = 'none';

        // Apply the selected filter
        if (selectElement.value === 'all') {
            landSizeFilter = 'all';
        } else {
            landSizeFilter = parseFloat(selectElement.value);
        }
        renderMarkers();
    }
}

function applyCustomSize() {
    const customInput = document.getElementById('custom-size-filter');
    const value = parseFloat(customInput.value);

    if (value && value > 0) {
        landSizeFilter = value;
        renderMarkers();
    } else {
        alert('Please enter a valid size in acres');
    }
}

// Update filtered count display
function updateFilteredCount(count) {
    // Find or create filtered count element
    let filteredElement = document.getElementById('filtered-count');
    if (!filteredElement) {
        const statsDiv = document.getElementById('stats');
        if (statsDiv) {
            // Add filtered count if filters are active
            if (landPriceFilter !== 'all' || landSizeFilter !== 'all') {
                const filterInfo = [];
                if (landPriceFilter !== 'all') {
                    filterInfo.push(`< $${(landPriceFilter/1000).toFixed(0)}k`);
                }
                if (landSizeFilter !== 'all') {
                    filterInfo.push(`> ${landSizeFilter} acres`);
                }

                const filteredHTML = `<div id="filtered-count" class="stat-item" style="background: rgba(139,69,19,0.3); border: 1px solid #8b4513;">🔍 Filtered Land: ${count} (${filterInfo.join(', ')})</div>`;
                statsDiv.innerHTML += filteredHTML;
            }
        }
    } else {
        // Update existing element
        if (landPriceFilter === 'all' && landSizeFilter === 'all') {
            // Remove filter indicator if no filters active
            filteredElement.remove();
        } else {
            const filterInfo = [];
            if (landPriceFilter !== 'all') {
                filterInfo.push(`< $${(landPriceFilter/1000).toFixed(0)}k`);
            }
            if (landSizeFilter !== 'all') {
                filterInfo.push(`> ${landSizeFilter} acres`);
            }
            filteredElement.innerHTML = `🔍 Filtered Land: ${count} (${filterInfo.join(', ')})`;
        }
    }
}

// Initialize on page load
window.addEventListener('load', initMap);
