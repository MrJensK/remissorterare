// JavaScript för Remissorterare Web App

let socket = null;
let currentSessionId = null;

// Initiera app när sidan laddas
document.addEventListener('DOMContentLoaded', function() {
    initDragAndDrop();
    initFileInput();
    loadStatistik();
    initSocket();
    laddaOsakertRemisser();
    laddaAIStatus();
    laddaVerksamheter();
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
            
            showResultat(resultat);
            document.getElementById('resultat-section').style.display = 'block';
            loadStatistik(); // Uppdatera statistik
        })
        .catch(error => {
            console.error('Resultat error:', error);
            showToast(`Kunde inte ladda resultat: ${error.message}`, 'error');
        });
}

// Visa resultat
function showResultat(data) {
    const resultatSection = document.getElementById('resultat-section');
    const resultatContent = document.getElementById('resultat-content');
    
    let html = `
        <div class="row">
            <div class="col-md-6">
                <h6>Filinformation</h6>
                <p><strong>Filnamn:</strong> ${data.filnamn}</p>
                <p><strong>Status:</strong> 
                    <span class="badge bg-${data.status === 'sorterad' ? 'success' : 'warning'}">
                        ${data.status}
                    </span>
                </p>
                <p><strong>Verksamhet:</strong> ${data.verksamhet}</p>
                <p><strong>Sannolikhet:</strong> ${data.sannolikhet}%</p>
            </div>
            <div class="col-md-6">
                <h6>Extraherad data</h6>
                <p><strong>Personnummer:</strong> ${data.personnummer || 'Ej hittat'}</p>
                <p><strong>Remissdatum:</strong> ${data.remissdatum || 'Ej hittat'}</p>
                <p><strong>Textlängd:</strong> ${data.text_längd} tecken</p>
                <p><strong>Mål-mapp:</strong> ${data.mål_mapp}</p>
            </div>
        </div>
        <div class="mt-3">
            <button class="btn btn-primary" onclick="loadStatistik()">
                <i class="fas fa-sync-alt me-2"></i>Uppdatera statistik
            </button>
        </div>
    `;
    
    resultatContent.innerHTML = html;
    resultatSection.style.display = 'block';
    
    // Uppdatera statistik automatiskt
    loadStatistik();
}

// Denna funktion är ersatt av showResultat

// Ladda statistik
function loadStatistik() {
    fetch('/api/statistik')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayStatistik(data.statistik);
            } else {
                console.error('Fel vid laddning av statistik:', data.error);
            }
        })
        .catch(error => {
            console.error('Fel vid laddning av statistik:', error);
        });
}

// Ladda osakert remisser
function laddaOsakertRemisser() {
    const osakertContent = document.getElementById('osakert-content');
    osakertContent.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Laddar...</span>
            </div>
            <p class="mt-2">Laddar osakert remisser...</p>
        </div>
    `;
    
    fetch('/api/osakert_remisser')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayOsakertRemisser(data.remisser);
            } else {
                osakertContent.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Fel vid laddning: ${data.error}
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Fel vid laddning av osakert remisser:', error);
            osakertContent.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Fel vid laddning: ${error.message}
                </div>
            `;
        });
}

// Visa osakert remisser
function displayOsakertRemisser(remisser) {
    const osakertContent = document.getElementById('osakert-content');
    
    if (remisser.length === 0) {
        osakertContent.innerHTML = `
            <div class="alert alert-success">
                <i class="fas fa-check-circle me-2"></i>
                Inga osakert remisser hittades!
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>PDF-fil</th>
                        <th>Storlek</th>
                        <th>Skapad</th>
                        <th>Verksamhet</th>
                        <th>Åtgärd</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    remisser.forEach(remiss => {
        const verksamheter = Object.keys(VERKSAMHETER);
        const verksamhetOptions = verksamheter.map(v => 
            `<option value="${v}">${v}</option>`
        ).join('');
        
        html += `
            <tr>
                <td>
                    <strong>${remiss.pdf_namn}</strong>
                    ${remiss.dat_fil ? `<br><small class="text-muted">${remiss.dat_fil.substring(0, 100)}...</small>` : ''}
                </td>
                <td>${formatFileSize(remiss.storlek)}</td>
                <td>${remiss.skapad}</td>
                <td>
                    <select class="form-select form-select-sm" id="verksamhet-${remiss.pdf_namn.replace(/[^a-zA-Z0-9]/g, '_')}">
                        <option value="">Välj verksamhet...</option>
                        ${verksamhetOptions}
                    </select>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-primary" onclick="omfördelaRemiss('${remiss.pdf_namn}', '${remiss.pdf_namn.replace(/[^a-zA-Z0-9]/g, '_')}')">
                            <i class="fas fa-arrow-right me-1"></i>Omdirigera
                        </button>
                        <button class="btn btn-sm btn-info" onclick="fåAIFörslagFrånPDF('${remiss.pdf_namn}')" title="Få AI-förslag på verksamhet">
                            <i class="fas fa-robot me-1"></i>AI-förslag
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        <div class="mt-3">
            <button class="btn btn-success" onclick="tränaMLMedOmfördelningsdata()">
                <i class="fas fa-brain me-2"></i>Träna ML med omfördelningsdata
            </button>
        </div>
    `;
    
    osakertContent.innerHTML = html;
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

// Omdirigera remiss
function omfördelaRemiss(pdfNamn, verksamhetId) {
    const verksamhetSelect = document.getElementById(`verksamhet-${verksamhetId}`);
    const nyVerksamhet = verksamhetSelect.value;
    
    if (!nyVerksamhet) {
        showToast('Välj en verksamhet först', 'warning');
        return;
    }
    
    if (!confirm(`Är du säker på att du vill omfördela "${pdfNamn}" till "${nyVerksamhet}"?`)) {
        return;
    }
    
    fetch('/api/omfördela_remiss', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            pdf_namn: pdfNamn,
            ny_verksamhet: nyVerksamhet
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.meddelande, 'success');
            // Uppdatera listan
            laddaOsakertRemisser();
            // Uppdatera statistik
            loadStatistik();
        } else {
            showToast(`Fel: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Fel vid omfördelningsprocessen:', error);
        showToast('Fel vid omfördelningsprocessen', 'error');
    });
}

// Träna ML med omfördelningsdata
function tränaMLMedOmfördelningsdata() {
    if (!confirm('Vill du träna ML-modellen med data från omfördelningsprocesser? Detta kan ta några minuter.')) {
        return;
    }
    
    // Samla in omfördelningsdata från tabellen
    const omfördelningsdata = [];
    const rows = document.querySelectorAll('#osakert-content tbody tr');
    
    rows.forEach(row => {
        const pdfNamn = row.querySelector('td:first-child strong').textContent;
        const verksamhetSelect = row.querySelector('select');
        const verksamhet = verksamhetSelect.value;
        
        if (verksamhet) {
            omfördelningsdata.push([pdfNamn, verksamhet]);
        }
    });
    
    if (omfördelningsdata.length === 0) {
        showToast('Ingen omfördelningsdata att träna på', 'warning');
        return;
    }
    
    showToast(`Tränar ML-modell med ${omfördelningsdata.length} omfördelningsdata...`, 'info');
    
    fetch('/api/träna_ml_med_omfördelningsdata', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            omfördelningsdata: omfördelningsdata
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.meddelande, 'success');
        } else {
            showToast(`Fel: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Fel vid ML-träning:', error);
        showToast('Fel vid ML-träning', 'error');
    });
}

// Analysera text
function analyseraText() {
    const textInput = document.getElementById('text-input');
    const text = textInput.value.trim();
    
    if (!text) {
        showToast('Ange text att analysera', 'warning');
        return;
    }
    
    const resultatDiv = document.getElementById('textanalys-resultat');
    const contentDiv = document.getElementById('textanalys-content');
    
    resultatDiv.style.display = 'block';
    contentDiv.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Analyserar...</span>
            </div>
            <p class="mt-2">Analyserar text...</p>
        </div>
    `;
    
    fetch('/api/analysera_text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            contentDiv.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <strong>Identifierad verksamhet:</strong><br>
                        <span class="badge bg-primary fs-6">${data.verksamhet}</span>
                    </div>
                    <div class="col-md-6">
                        <strong>Sannolikhet:</strong><br>
                        <span class="badge bg-${data.sannolikhet >= 90 ? 'success' : data.sannolikhet >= 70 ? 'warning' : 'danger'} fs-6">
                            ${data.sannolikhet.toFixed(1)}%
                        </span>
                    </div>
                </div>
                <hr>
                <div class="mt-2">
                    <strong>Analyserad text:</strong><br>
                    <small class="text-muted">${data.analyserad_text}</small>
                </div>
            `;
        } else {
            contentDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Fel vid analys: ${data.error}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Fel vid textanalys:', error);
        contentDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Fel vid analys: ${error.message}
            </div>
        `;
    });
}

// Debug verksamhetsidentifiering
function debugVerksamhetsidentifiering() {
    const textInput = document.getElementById('text-input');
    const text = textInput.value.trim();
    
    if (!text) {
        showToast('Ange text att analysera', 'warning');
        return;
    }
    
    const debugDiv = document.getElementById('debug-resultat');
    const debugContent = document.getElementById('debug-content');
    
    debugDiv.style.display = 'block';
    debugContent.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-warning" role="status">
                <span class="visually-hidden">Debuggar...</span>
            </div>
            <p class="mt-2">Debuggar verksamhetsidentifiering...</p>
        </div>
    `;
    
    fetch('/api/debug_verksamhetsidentifiering', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const debugInfo = data.debug_info;
            let html = `
                <div class="mb-3">
                    <strong>Text:</strong> ${debugInfo.text_preview}<br>
                    <strong>Längd:</strong> ${debugInfo.text_längd} tecken
                </div>
            `;
            
            // Visa analyssteg
            debugInfo.analys_steg.forEach(steg => {
                html += `
                    <div class="mb-3">
                        <h6 class="text-primary">${steg.steg}</h6>
                        <div class="ms-3">
                            <strong>Status:</strong> 
                            <span class="badge bg-${steg.status === 'hittad' || steg.status === 'hittade' || steg.status === 'beräknad' ? 'success' : 'secondary'}">
                                ${steg.status}
                            </span>
                        </div>
                `;
                
                if (steg.resultat) {
                    if (steg.steg === 'Mottagarfraser' && steg.resultat) {
                        html += `
                            <div class="ms-3">
                                <strong>Hittad fras:</strong> "${steg.resultat.fras}"<br>
                                <strong>Kontext:</strong> "${steg.resultat.kontext}"<br>
                                <strong>Position:</strong> ${steg.resultat.position}
                            </div>
                        `;
                    } else if (steg.steg === 'Nyckelordsanalys') {
                        html += '<div class="ms-3">';
                        Object.entries(steg.resultat).forEach(([verksamhet, nyckelord]) => {
                            html += `<strong>${verksamhet}:</strong><br>`;
                            nyckelord.forEach(n => {
                                html += `&nbsp;&nbsp;• ${n.nyckel} (${n.antal} gånger)<br>`;
                            });
                        });
                        html += '</div>';
                    } else if (steg.steg === 'Poängberäkning') {
                        html += '<div class="ms-3">';
                        Object.entries(steg.resultat).forEach(([verksamhet, data]) => {
                            html += `<strong>${verksamhet}:</strong> ${data.poäng} poäng (${data.sannolikhet}%)<br>`;
                        });
                        html += '</div>';
                    }
                }
                
                html += '</div>';
            });
            
            // Visa slutresultat
            html += `
                <div class="alert alert-success">
                    <h6>Slutresultat:</h6>
                    <strong>Verksamhet:</strong> ${debugInfo.slutresultat.verksamhet}<br>
                    <strong>Sannolikhet:</strong> ${debugInfo.slutresultat.sannolikhet}%
                </div>
            `;
            
            debugContent.innerHTML = html;
        } else {
            debugContent.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Fel vid debug-analys: ${data.error}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Fel vid debug-analys:', error);
        debugContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Fel vid debug-analys: ${error.message}
            </div>
        `;
    });
}

// Testa AI
function testaAI() {
    const textInput = document.getElementById('text-input');
    const text = textInput.value.trim();
    
    if (!text) {
        showToast('Ange text att analysera', 'warning');
        return;
    }
    
    const aiDiv = document.getElementById('ai-resultat');
    const aiContent = document.getElementById('ai-content');
    
    aiDiv.style.display = 'block';
    aiContent.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-success" role="status">
                <span class="visually-hidden">AI analyserar...</span>
            </div>
            <p class="mt-2">AI analyserar text...</p>
        </div>
    `;
    
    fetch('/api/testa_ai', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const aiResultat = data.ai_resultat;
            aiContent.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <strong>AI-identifierad verksamhet:</strong><br>
                        <span class="badge bg-success fs-6">${aiResultat.verksamhet}</span>
                    </div>
                    <div class="col-md-6">
                        <strong>AI-sannolikhet:</strong><br>
                        <span class="badge bg-${aiResultat.sannolikhet >= 90 ? 'success' : aiResultat.sannolikhet >= 70 ? 'warning' : 'danger'} fs-6">
                            ${aiResultat.sannolikhet.toFixed(1)}%
                        </span>
                    </div>
                </div>
                <hr>
                <div class="mt-2">
                    <strong>AI-analys:</strong><br>
                    <small class="text-muted">AI:n analyserade texten och identifierade verksamhet baserat på innehåll och kontext.</small>
                </div>
            `;
        } else {
            aiContent.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Fel vid AI-analys: ${data.error}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Fel vid AI-analys:', error);
        aiContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Fel vid AI-analys: ${error.message}
            </div>
        `;
    });
}

// Ladda AI-status
function laddaAIStatus() {
    const aiStatusContent = document.getElementById('ai-status-content');
    aiStatusContent.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Laddar...</span>
            </div>
            <p class="mt-2">Laddar AI-status...</p>
        </div>
    `;
    
    fetch('/api/ai_status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const aiStatus = data.ai_status;
                
                if (aiStatus.error) {
                    aiStatusContent.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <strong>AI-status:</strong> ${aiStatus.error}
                        </div>
                        <div class="mt-3">
                            <p><strong>För att aktivera AI:</strong></p>
                            <ol>
                                <li>Skaffa en OpenAI API-nyckel från <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI</a></li>
                                <li>Sätt miljövariabeln: <code>export OPENAI_API_KEY="din-nyckel-här"</code></li>
                                <li>Starta om applikationen</li>
                            </ol>
                        </div>
                    `;
                } else {
                    aiStatusContent.innerHTML = `
                        <div class="alert alert-success">
                            <i class="fas fa-check-circle me-2"></i>
                            <strong>AI-status:</strong> ${aiStatus.status}<br>
                            <strong>Modell:</strong> ${aiStatus.modell}<br>
                            <strong>Användning:</strong> ${aiStatus.användning}
                        </div>
                        <div class="mt-3">
                            <p><strong>AI är aktiverat och redo att användas!</strong></p>
                            <p>AI kommer nu att användas som primär metod för verksamhetsidentifiering, med fallback till regelbaserade metoder om AI misslyckas.</p>
                        </div>
                    `;
                }
            } else {
                aiStatusContent.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Fel vid hämtning av AI-status: ${data.error}
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Fel vid hämtning av AI-status:', error);
            aiStatusContent.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Fel vid hämtning av AI-status: ${error.message}
                </div>
            `;
        });
    
    // Kontrollera om det är lokal AI
    laddaLokalAIStatus();
}

// Ladda lokal AI-status
function laddaLokalAIStatus() {
    fetch('/api/lokal_ai_status')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.ai_type === 'lokal') {
                // Visa lokal AI-kontroller
                document.getElementById('lokal-ai-kontroller').style.display = 'block';
                
                // Sätt rätt modell i dropdown
                const modellVal = document.getElementById('modell-val');
                modellVal.value = data.modell;
                
                // Visa modellinfo
                if (data.modell_info && !data.modell_info.error) {
                    const aiStatusContent = document.getElementById('ai-status-content');
                    aiStatusContent.innerHTML = `
                        <div class="alert alert-success">
                            <i class="fas fa-robot me-2"></i>
                            <strong>Lokal AI aktiverat!</strong><br>
                            <strong>Modell:</strong> ${data.modell_info.namn}<br>
                            <strong>Typ:</strong> ${data.modell_info.typ}<br>
                            <strong>Status:</strong> ${data.modell_info.status}<br>
                            <strong>Verksamheter:</strong> ${data.modell_info.verksamheter}<br>
                            <strong>Testad:</strong> ${data.modell_info.testad ? 'Ja' : 'Nej'}
                        </div>
                        <div class="mt-3">
                            <p><strong>Lokal AI är aktiverat och redo att användas!</strong></p>
                            <p>AI:n körs lokalt på din dator utan internetanslutning. Modellerna laddas ner automatiskt vid första användningen.</p>
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('Fel vid hämtning av lokal AI-status:', error);
        });
}

// Byt lokal AI-modell
function bytLokalAIModell() {
    const modellVal = document.getElementById('modell-val');
    const nyModell = modellVal.value;
    
    if (!nyModell) {
        showToast('Välj en modell först', 'warning');
        return;
    }
    
    if (!confirm(`Är du säker på att du vill byta till modell: ${nyModell}? Detta kan ta några minuter.`)) {
        return;
    }
    
    showToast(`Bytter till modell: ${nyModell}...`, 'info');
    
    fetch('/api/byt_lokal_ai_modell', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ modell: nyModell })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.meddelande, 'success');
            // Uppdatera status
            setTimeout(() => {
                laddaLokalAIStatus();
            }, 2000);
            
            // Uppdatera modellvalet baserat på svaret
            if (data.ny_modell) {
                modellVal.value = data.ny_modell;
            }
        } else {
            showToast(`Fel: ${data.error}`, 'error');
            // Återställ till tidigare modell om byte misslyckades
            setTimeout(() => {
                laddaLokalAIStatus();
            }, 1000);
        }
    })
    .catch(error => {
        console.error('Fel vid byte av modell:', error);
        showToast('Fel vid byte av modell', 'error');
    });
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

// Initiera SocketIO
function initSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Ansluten till servern');
        showToast('Ansluten till servern', 'success');
    });
    
    socket.on('connected', function(data) {
        console.log('Session ID:', data.session_id);
        currentSessionId = data.session_id;
        
        // Anslut till session om vi har en
        if (currentSessionId) {
            socket.emit('join_session', { session_id: currentSessionId });
        }
    });
    
    socket.on('status_update', function(data) {
        console.log('Status uppdatering:', data);
        updateProgress(data.progress, data.meddelande);
        
        if (data.status === 'slutförd') {
            showToast(`Bearbetning av ${data.fil} slutförd`, 'success');
            setTimeout(() => {
                loadStatistik();
                laddaOsakertRemisser();
            }, 1000);
        } else if (data.status === 'fel') {
            showToast(`Fel vid bearbetning av ${data.fil}: ${data.meddelande}`, 'error');
        }
    });
    
    socket.on('bearbetning_slutförd', function(data) {
        console.log('Bearbetning slutförd:', data);
        showResultat(data);
    });
    
    socket.on('bearbetning_fel', function(data) {
        console.log('Bearbetning fel:', data);
        showToast(`Fel vid bearbetning av ${data.filnamn}: ${data.fel}`, 'error');
    });
    
    socket.on('disconnect', function() {
        console.log('Frånkopplad från servern');
        showToast('Frånkopplad från servern', 'warning');
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

// Lägg till VERKSAMHETER-objekt för JavaScript
const VERKSAMHETER = {
    "Ortopedi": ["ortopedi", "ortopedisk", "led", "leder", "knä", "höft", "rygg", "ryggrad"],
    "Kirurgi": ["kirurgi", "kirurgisk", "operation", "operera", "kirurg", "snitt"],
    "Kardiologi": ["kardiologi", "kardiologisk", "hjärta", "hjärt", "kardiak", "arytmi"],
    "Neurologi": ["neurologi", "neurologisk", "hjärna", "hjärn", "nerv", "neurolog"],
    "Gastroenterologi": ["gastroenterologi", "gastroenterologisk", "mage", "mag", "tarm", "lever"],
    "Endokrinologi": ["endokrinologi", "endokrinologisk", "diabetes", "socker", "glukos", "insulin"],
    "Dermatologi": ["dermatologi", "dermatologisk", "hud", "hud", "eksem", "psoriasis"],
    "Urologi": ["urologi", "urologisk", "urin", "urinblåsa", "prostata", "njure"],
    "Gynekologi": ["gynekologi", "gynekologisk", "gynekolog", "livmoder", "äggstockar"],
    "Oftalmologi": ["oftalmologi", "oftalmologisk", "öga", "ögon", "syn", "katarakt"],
    "Otorinolaryngologi": ["otorinolaryngologi", "ent", "öra", "näsa", "hals", "tonsillit"]
};

// Verksamhetshantering
function laddaVerksamheter() {
    const contentDiv = document.getElementById('verksamheter-content');
    
    contentDiv.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Laddar...</span>
            </div>
            <p class="mt-2">Laddar verksamheter...</p>
        </div>
    `;
    
    fetch('/api/verksamheter')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayVerksamheter(data.verksamheter);
            } else {
                contentDiv.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Fel vid laddning av verksamheter: ${data.error}
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Fel vid laddning av verksamheter:', error);
            contentDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Fel vid laddning av verksamheter: ${error.message}
                </div>
            `;
        });
}

function displayVerksamheter(verksamheter) {
    const contentDiv = document.getElementById('verksamheter-content');
    
    if (Object.keys(verksamheter).length === 0) {
        contentDiv.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Inga verksamheter konfigurerade än.
            </div>
        `;
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-striped">';
    html += '<thead><tr><th>Verksamhet</th><th>Nyckelord</th><th>Antal filer</th><th>Åtgärder</th></tr></thead><tbody>';
    
    Object.entries(verksamheter).forEach(([namn, nyckelord]) => {
        const nyckelordText = Array.isArray(nyckelord) ? nyckelord.join(', ') : nyckelord;
        html += `
            <tr>
                <td><strong>${namn}</strong></td>
                <td><small class="text-muted">${nyckelordText}</small></td>
                <td>
                    <span class="badge bg-secondary">Kontrollera...</span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="taBortVerksamhet('${namn}')">
                        <i class="fas fa-trash me-1"></i>Ta bort
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    contentDiv.innerHTML = html;
    
    // Uppdatera antal filer för varje verksamhet
    Object.keys(verksamheter).forEach(namn => {
        updateVerksamhetFilAntal(namn);
    });
}

function updateVerksamhetFilAntal(verksamhetNamn) {
    // Hitta raden för denna verksamhet
    const rows = document.querySelectorAll('#verksamheter-content tbody tr');
    rows.forEach(row => {
        const verksamhetCell = row.querySelector('td:first-child strong');
        if (verksamhetCell && verksamhetCell.textContent === verksamhetNamn) {
            const antalCell = row.querySelector('td:nth-child(3)');
            if (antalCell) {
                // Kontrollera om mappen finns och räkna filer
                fetch(`/api/verksamhet_fil_antal?verksamhet=${encodeURIComponent(verksamhetNamn)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            antalCell.innerHTML = `<span class="badge bg-primary">${data.antal} filer</span>`;
                        } else {
                            antalCell.innerHTML = `<span class="badge bg-secondary">0 filer</span>`;
                        }
                    })
                    .catch(() => {
                        antalCell.innerHTML = `<span class="badge bg-secondary">0 filer</span>`;
                    });
            }
        }
    });
}

function läggTillVerksamhet() {
    const namnInput = document.getElementById('ny-verksamhet-namn');
    const nyckelordInput = document.getElementById('ny-verksamhet-nyckelord');
    
    const namn = namnInput.value.trim();
    const nyckelordText = nyckelordInput.value.trim();
    
    if (!namn) {
        showToast('Ange verksamhetsnamn', 'warning');
        return;
    }
    
    if (!nyckelordText) {
        showToast('Ange minst ett nyckelord', 'warning');
        return;
    }
    
    // Konvertera kommaseparerade nyckelord till array
    const nyckelord = nyckelordText.split(',').map(k => k.trim()).filter(k => k.length > 0);
    
    if (nyckelord.length === 0) {
        showToast('Ange minst ett nyckelord', 'warning');
        return;
    }
    
    // Kontrollera om verksamheten redan finns
    if (VERKSAMHETER[namn]) {
        showToast(`Verksamhet "${namn}" finns redan`, 'warning');
        return;
    }
    
    showToast(`Lägger till verksamhet "${namn}"...`, 'info');
    
    fetch('/api/lägg_till_verksamhet', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            namn: namn,
            nyckelord: nyckelord
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.meddelande, 'success');
            
            // Rensa input-fälten
            namnInput.value = '';
            nyckelordInput.value = '';
            
            // Uppdatera VERKSAMHETER-objektet
            VERKSAMHETER[namn] = nyckelord;
            
            // Uppdatera listan
            laddaVerksamheter();
            
            // Uppdatera statistik
            loadStatistik();
            
            // Uppdatera osakert-remisser (kan ha nya verksamheter att välja mellan)
            laddaOsakertRemisser();
        } else {
            showToast(`Fel: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Fel vid tillägg av verksamhet:', error);
        showToast('Fel vid tillägg av verksamhet', 'error');
    });
}

function taBortVerksamhet(verksamhetNamn) {
    if (!confirm(`Är du säker på att du vill ta bort verksamheten "${verksamhetNamn}"?\n\nAlla filer i denna verksamhet kommer att flyttas till "osakert".`)) {
        return;
    }
    
    showToast(`Tar bort verksamhet "${verksamhetNamn}"...`, 'info');
    
    fetch('/api/ta_bort_verksamhet', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            namn: verksamhetNamn
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.meddelande, 'success');
            
            // Ta bort från VERKSAMHETER-objektet
            delete VERKSAMHETER[verksamhetNamn];
            
            // Uppdatera listan
            laddaVerksamheter();
            
            // Uppdatera statistik
            loadStatistik();
            
            // Uppdatera osakert-remisser
            laddaOsakertRemisser();
        } else {
            showToast(`Fel: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Fel vid borttagning av verksamhet:', error);
        showToast('Fel vid borttagning av verksamhet', 'error');
    });
}

// AI-förslag på verksamheter
let currentAIFörslag = null;

function fåAIFörslag() {
    // Använd text från textanalys-sektionen om den finns
    const textInput = document.getElementById('text-input');
    const text = textInput ? textInput.value.trim() : '';
    
    if (!text) {
        showToast('Ange text i textanalys-sektionen först, eller klistra in text från en remiss', 'warning');
        return;
    }
    
    showToast('Analyserar text med AI för att föreslå verksamheter...', 'info');
    
    fetch('/api/ai_förslag_verksamhet', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.förslag) {
                // Visa AI-förslag
                currentAIFörslag = data.förslag;
                displayAIFörslag(data);
                showToast(data.meddelande, 'success');
            } else {
                showToast(data.meddelande, 'info');
            }
        } else {
            showToast(`Fel: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Fel vid AI-förslag:', error);
        showToast('Fel vid AI-förslag', 'error');
    });
}

function displayAIFörslag(data) {
    const förslagSektion = document.getElementById('ai-förslag-sektion');
    const förslagContent = document.getElementById('ai-förslag-content');
    
    let html = `
        <div class="row">
            <div class="col-md-6">
                <h6>Föreslagen verksamhet:</h6>
                <p><strong>${data.ai_verksamhet}</strong> (${data.sannolikhet.toFixed(1)}% sannolikhet)</p>
                
                <h6>Motivering:</h6>
                <p>${data.förslag.motivering}</p>
                
                <h6>Matchande områden:</h6>
                <p>${data.förslag.matchande_områden.join(', ') || 'Inga specifika områden identifierade'}</p>
            </div>
            <div class="col-md-6">
                <h6>Föreslagna nyckelord:</h6>
                <div class="mb-2">
                    ${data.förslag.nyckelord.map(nyckelord => 
                        `<span class="badge bg-primary me-1 mb-1">${nyckelord}</span>`
                    ).join('')}
                </div>
                
                <h6>Medicinska termer hittade:</h6>
                <p><small class="text-muted">${data.förslag.medicinska_termer.join(', ') || 'Inga medicinska termer identifierade'}</small></p>
            </div>
        </div>
    `;
    
    förslagContent.innerHTML = html;
    förslagSektion.style.display = 'block';
}

function användAIFörslag() {
    if (!currentAIFörslag) {
        showToast('Inget AI-förslag tillgängligt', 'warning');
        return;
    }
    
    // Fyll i formuläret med AI-förslaget
    const namnInput = document.getElementById('ny-verksamhet-namn');
    const nyckelordInput = document.getElementById('ny-verksamhet-nyckelord');
    
    namnInput.value = currentAIFörslag.namn;
    nyckelordInput.value = currentAIFörslag.nyckelord.join(', ');
    
    // Dölj förslagssektionen
    döljAIFörslag();
    
    // Visa bekräftelse
    showToast(`AI-förslag använt: ${currentAIFörslag.namn}`, 'success');
    
    // Fokusera på namn-fältet
    namnInput.focus();
}

function döljAIFörslag() {
    const förslagSektion = document.getElementById('ai-förslag-sektion');
    förslagSektion.style.display = 'none';
    currentAIFörslag = null;
}

// AI-förslag från uppladdade PDF:er
let currentAIFörslagFrånPDF = null;

function fåAIFörslagFrånPDF(pdfNamn) {
    if (!pdfNamn) {
        showToast('PDF-filnamn saknas', 'warning');
        return;
    }
    
    showToast(`Analyserar PDF "${pdfNamn}" med AI för att föreslå verksamheter...`, 'info');
    
    fetch('/api/ai_förslag_från_pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pdf_namn: pdfNamn })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.förslag) {
                // Visa AI-förslag från PDF
                currentAIFörslagFrånPDF = data;
                displayAIFörslagFrånPDF(data);
                showToast(data.meddelande, 'success');
            } else {
                showToast(data.meddelande, 'info');
            }
        } else {
            showToast(`Fel: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Fel vid AI-förslag från PDF:', error);
        showToast('Fel vid AI-förslag från PDF', 'error');
    });
}

function displayAIFörslagFrånPDF(data) {
    const förslagSektion = document.getElementById('ai-förslag-pdf-sektion');
    const förslagContent = document.getElementById('ai-förslag-pdf-content');
    const förslagNamn = document.getElementById('ai-förslag-pdf-namn');
    
    förslagNamn.textContent = data.pdf_namn;
    
    let html = `
        <div class="row">
            <div class="col-md-6">
                <h6>Föreslagen verksamhet:</h6>
                <p><strong>${data.ai_verksamhet}</strong> (${data.sannolikhet.toFixed(1)}% sannolikhet)</p>
                
                <h6>Motivering:</h6>
                <p>${data.förslag.motivering}</p>
                
                <h6>Matchande områden:</h6>
                <p>${data.förslag.matchande_områden.join(', ') || 'Inga specifika områden identifierade'}</p>
                
                <h6>Extraherad text (första 500 tecken):</h6>
                <div class="bg-light p-2 rounded">
                    <small class="text-muted">${data.extraherad_text}</small>
                </div>
            </div>
            <div class="col-md-6">
                <h6>Föreslagna nyckelord:</h6>
                <div class="mb-2">
                    ${data.förslag.nyckelord.map(nyckelord => 
                        `<span class="badge bg-primary me-1 mb-1">${nyckelord}</span>`
                    ).join('')}
                </div>
                
                <h6>Medicinska termer hittade:</h6>
                <p><small class="text-muted">${data.förslag.medicinska_termer.join(', ') || 'Inga medicinska termer identifierade'}</small></p>
            </div>
        </div>
    `;
    
    förslagContent.innerHTML = html;
    förslagSektion.style.display = 'block';
}

function användAIFörslagFrånPDF() {
    if (!currentAIFörslagFrånPDF) {
        showToast('Inget AI-förslag från PDF tillgängligt', 'warning');
        return;
    }
    
    // Fyll i formuläret med AI-förslaget
    const namnInput = document.getElementById('ny-verksamhet-namn');
    const nyckelordInput = document.getElementById('ny-verksamhet-nyckelord');
    
    namnInput.value = currentAIFörslagFrånPDF.förslag.namn;
    nyckelordInput.value = currentAIFörslagFrånPDF.förslag.nyckelord.join(', ');
    
    // Dölj förslagssektionen
    döljAIFörslagFrånPDF();
    
    // Visa bekräftelse
    showToast(`AI-förslag från PDF använt: ${currentAIFörslagFrånPDF.förslag.namn}`, 'success');
    
    // Fokusera på namn-fältet
    namnInput.focus();
    
    // Scrolla till verksamhetshanteringssektionen
    document.querySelector('#verksamhetshantering').scrollIntoView({ behavior: 'smooth' });
}

function döljAIFörslagFrånPDF() {
    const förslagSektion = document.getElementById('ai-förslag-pdf-sektion');
    förslagSektion.style.display = 'none';
    currentAIFörslagFrånPDF = null;
}
