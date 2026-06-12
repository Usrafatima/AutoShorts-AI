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

    let currentJobId = null;

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

    // 2. Generate (Real Connection)
    generateBtn.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) return;

        settingsSection.classList.add('hidden');
        generateSection.classList.add('hidden');
        progressSection.classList.remove('hidden');
        
        statusText.textContent = 'Uploading video...';
        progressFill.style.width = '10%';

        const formData = new FormData();
        formData.append('video', file);
        formData.append('num_shorts', document.getElementById('shorts-count').value);
        formData.append('model_size', document.getElementById('whisper-model').value);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.job_id) {
                currentJobId = data.job_id;
                startPolling(currentJobId);
            } else {
                statusText.textContent = 'Upload failed: ' + (data.error || 'Unknown error');
            }
        } catch (error) {
            statusText.textContent = 'Network error during upload.';
            console.error(error);
        }
    });

    function startPolling(jobId) {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/status/${jobId}`);
                const data = await response.json();

                if (data.status === 'processing') {
                    statusText.textContent = 'AI is processing your video... (Transcribing & Scoring)';
                    progressFill.style.width = '50%';
                    transcriptSection.classList.remove('hidden');
                } else if (data.status === 'completed') {
                    clearInterval(interval);
                    progressFill.style.width = '100%';
                    statusText.textContent = 'Success! Shorts generated.';
                    setTimeout(() => showResults(data.shorts), 1000);
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    statusText.textContent = 'Error: ' + data.error;
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 3000);
    }

    function showResults(shorts) {
        progressSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        
        shortsGrid.innerHTML = shorts.map((filename, index) => `
            <div class="short-card">
                <div class="thumbnail-placeholder">VIDEO</div>
                <div class="short-info">
                    <h4>Short #${index + 1}</h4>
                    <p>${filename}</p>
                </div>
                <a href="/download/${filename}" class="btn-small" target="_blank">Download</a>
            </div>
        `).join('');
    }

    newJobBtn.addEventListener('click', () => location.reload());
});
