// JavaScript för Remissorterare Web App

let socket = null;
let currentSessionId = null;

// Initiera app när sidan laddas
document.addEventListener('DOMContentLoaded', function() {
    initDragAndDrop();
    initFileInput();
    loadStatistik();
    initSocket();
});

// Initiera drag and drop
function initDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight(e) {
        dropZone.classList.add('dragover');
    }
    
    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }
    
    dropZone.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
}

// Initiera file input
function initFileInput() {
    const fileInput = document.getElementById('file-input');
    fileInput.addEventListener('change', function(e) {
        handleFiles(e.target.files);
    });
}

// Hantera filer
function handleFiles(files) {
    if (files.length === 0) return;
    
    // Kontrollera att alla filer är PDF:er
    const pdfFiles = Array.from(files).filter(file => 
        file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    );
    
    if (pdfFiles.length === 0) {
        showToast('Inga PDF-filer hittades', 'error');
        return;
    }
    
    uploadFiles(pdfFiles);
}

// Ladda upp filer
function uploadFiles(files) {
    const formData = new FormData();
    
    files.forEach(file => {
        formData.append('files[]', file);
    });
    
    // Visa status-sektion
    document.getElementById('status-section').style.display = 'block';
    document.getElementById('resultat-section').style.display = 'none';
    
    // Uppdatera progress
    updateProgress(0, 'Laddar upp filer...');
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        currentSessionId = data.session_id;
        showToast(`Uppladdning lyckades: ${data.antal_filer} filer`, 'success');
        
        // Starta status-uppdatering
        startStatusPolling();
        
        // Anslut till WebSocket
        if (socket) {
            socket.emit('join', { session_id: currentSessionId });
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showToast(`Uppladdning misslyckades: ${error.message}`, 'error');
        updateProgress(0, 'Fel vid uppladdning');
    });
}

// Starta status-polling
function startStatusPolling() {
    if (!currentSessionId) return;
    
    const pollInterval = setInterval(() => {
        fetch(`/status/${currentSessionId}`)
            .then(response => response.json())
            .then(status => {
                if (status.status === 'bearbetar') {
                    updateProgress(status.progress, status.meddelande);
                } else if (status.status === 'slutförd') {
                    updateProgress(100, 'Bearbetning slutförd');
                    clearInterval(pollInterval);
                    loadResultat();
                } else if (status.status === 'fel') {
                    updateProgress(0, status.meddelande);
                    clearInterval(pollInterval);
                    showToast(`Bearbetning misslyckades: ${status.meddelande}`, 'error');
                }
            })
            .catch(error => {
                console.error('Status polling error:', error);
                clearInterval(pollInterval);
            });
    }, 1000);
}

// Uppdatera progress
function updateProgress(progress, message) {
    const progressBar = document.getElementById('progress-bar');
    const statusText = document.getElementById('status-text');
    
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);
    statusText.textContent = message;
}

// Ladda resultat
function loadResultat() {
    if (!currentSessionId) return;
    
    fetch(`/resultat/${currentSessionId}`)
        .then(response => response.json())
        .then(resultat => {
            if (resultat.error) {
                throw new Error(resultat.error);
            }
            
            displayResultat(resultat);
            document.getElementById('resultat-section').style.display = 'block';
            loadStatistik(); // Uppdatera statistik
        })
        .catch(error => {
            console.error('Resultat error:', error);
            showToast(`Kunde inte ladda resultat: ${error.message}`, 'error');
        });
}

// Visa resultat
function displayResultat(resultat) {
    const resultatContent = document.getElementById('resultat-content');
    
    const statusClass = resultat.status === 'sorterad' ? 'sorterad' : 
                       resultat.status === 'osakert' ? 'osakert' : 'fel';
    
    const statusBadge = resultat.status === 'sorterad' ? 'badge-sorterad' : 
                       resultat.status === 'osakert' ? 'badge-osakert' : 'badge-fel';
    
    resultatContent.innerHTML = `
        <div class="resultat-item ${statusClass} fade-in">
            <div class="row">
                <div class="col-md-8">
                    <h6><i class="fas fa-file-pdf me-2"></i>${resultat.filnamn}</h6>
                    <div class="row mt-3">
                        <div class="col-md-6">
                            <strong>Verksamhet:</strong> ${resultat.verksamhet}<br>
                            <strong>Sannolikhet:</strong> ${resultat.sannolikhet}%<br>
                            <strong>Status:</strong> <span class="badge ${statusBadge}">${resultat.status}</span>
                        </div>
                        <div class="col-md-6">
                            <strong>Personnummer:</strong> ${resultat.personnummer || 'Ej hittat'}<br>
                            <strong>Remissdatum:</strong> ${resultat.remissdatum || 'Ej hittat'}<br>
                            <strong>Textlängd:</strong> ${resultat.text_längd} tecken
                        </div>
                    </div>
                </div>
                <div class="col-md-4 text-end">
                    <small class="text-muted">Bearbetad: ${new Date(resultat.bearbetningstid).toLocaleString('sv-SE')}</small><br>
                    <small class="text-muted">Mål: ${resultat.mål_mapp}</small>
                </div>
            </div>
        </div>
    `;
}

// Ladda statistik
function loadStatistik() {
    fetch('/statistik')
        .then(response => response.json())
        .then(statistik => {
            if (statistik.error) {
                throw new Error(statistik.error);
            }
            
            displayStatistik(statistik);
        })
        .catch(error => {
            console.error('Statistik error:', error);
            document.getElementById('statistik-content').innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Kunde inte ladda statistik: ${error.message}
                </div>
            `;
        });
}

// Visa statistik
function displayStatistik(statistik) {
    const statistikContent = document.getElementById('statistik-content');
    
    if (Object.keys(statistik).length === 0) {
        statistikContent.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-chart-bar fa-3x mb-3"></i>
                <p>Ingen statistik tillgänglig än</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="statistik-grid">';
    
    Object.entries(statistik).forEach(([verksamhet, data]) => {
        html += `
            <div class="statistik-item">
                <div class="statistik-nummer">${data.pdf_filer}</div>
                <div class="statistik-label">${verksamhet}</div>
                <small class="text-muted">${data.dat_filer} .dat-filer</small>
            </div>
        `;
    });
    
    html += '</div>';
    statistikContent.innerHTML = html;
}

// Träna ML-modell
function tränaML() {
    const button = event.target;
    const originalText = button.innerHTML;
    
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Tränar...';
    
    fetch('/träna_ml', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        showToast(data.meddelande, 'success');
    })
    .catch(error => {
        console.error('ML training error:', error);
        showToast(`ML-träning misslyckades: ${error.message}`, 'error');
    })
    .finally(() => {
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

// Initiera WebSocket
function initSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocket connected');
    });
    
    socket.on('status_update', function(data) {
        updateProgress(data.progress, data.meddelande);
    });
    
    socket.on('bearbetning_slutförd', function(data) {
        displayResultat(data);
        document.getElementById('resultat-section').style.display = 'block';
        loadStatistik();
        showToast('Bearbetning slutförd!', 'success');
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
    });
}

// Visa toast-meddelande
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastBody = document.getElementById('toast-body');
    
    // Ta bort tidigare klasser
    toast.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'bg-info');
    
    // Lägg till rätt klass baserat på typ
    switch(type) {
        case 'success':
            toast.classList.add('bg-success', 'text-white');
            break;
        case 'error':
            toast.classList.add('bg-danger', 'text-white');
            break;
        case 'warning':
            toast.classList.add('bg-warning', 'text-dark');
            break;
        default:
            toast.classList.add('bg-info', 'text-white');
    }
    
    toastBody.textContent = message;
    
    // Visa toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Hjälpfunktioner
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString('sv-SE');
}
