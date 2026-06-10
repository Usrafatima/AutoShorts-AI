document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const uploadPrompt = document.getElementById('upload-prompt');
    const selectedFileName = document.getElementById('selected-file-name');
    
    const settingsSection = document.getElementById('settings-section');
    const generateSection = document.getElementById('generate-section');
    const generateBtn = document.getElementById('generate-btn');
    
    const progressSection = document.getElementById('progress-section');
    const progressFill = document.getElementById('progress-fill');
    const statusText = document.getElementById('status-text');
    
    const transcriptSection = document.getElementById('transcript-section');
    const resultsSection = document.getElementById('results-section');
    const shortsGrid = document.getElementById('shorts-grid');
    const newJobBtn = document.getElementById('new-job-btn');

    // 1. Selection
    browseBtn.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });
    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) showFileReady(e.target.files[0].name);
    });

    function showFileReady(name) {
        uploadPrompt.classList.add('hidden');
        selectedFileName.textContent = name;
        selectedFileName.classList.remove('hidden');
        settingsSection.classList.remove('hidden');
        generateSection.classList.remove('hidden');
    }

    // 2. Generate (Simulated)
    generateBtn.addEventListener('click', () => {
        settingsSection.classList.add('hidden');
        generateSection.classList.add('hidden');
        progressSection.classList.remove('hidden');
        
        const stages = [
            { p: 20, t: 'Uploading...' },
            { p: 50, t: 'Transcribing...' },
            { p: 80, t: 'Generating clips...' },
            { p: 100, t: 'Done.' }
        ];

        let i = 0;
        const interval = setInterval(() => {
            if (i < stages.length) {
                progressFill.style.width = `${stages[i].p}%`;
                statusText.textContent = stages[i].t;
                if (stages[i].p === 50) transcriptSection.classList.remove('hidden');
                i++;
            } else {
                clearInterval(interval);
                setTimeout(showResults, 500);
            }
        }, 1000);
    });

    function showResults() {
        progressSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        shortsGrid.innerHTML = `
            <div class="short-card">
                <div class="thumbnail-placeholder">MOCK</div>
                <div class="short-info"><h4>Short #1</h4><p>Duration: 15s</p></div>
                <a href="#" class="btn-small" onclick="return false;">Download</a>
            </div>
            <div class="short-card">
                <div class="thumbnail-placeholder">MOCK</div>
                <div class="short-info"><h4>Short #2</h4><p>Duration: 30s</p></div>
                <a href="#" class="btn-small" onclick="return false;">Download</a>
            </div>
        `;
    }

    newJobBtn.addEventListener('click', () => location.reload());
});
