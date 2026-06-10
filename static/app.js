document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const fileNameDisplay = document.getElementById('file-name');
    
    const uploadSection = document.getElementById('upload-section');
    const configSection = document.getElementById('config-section');
    const progressSection = document.getElementById('progress-section');
    const transcriptSection = document.getElementById('transcript-section');
    const resultsSection = document.getElementById('results-section');
    
    const generateBtn = document.getElementById('generate-btn');
    const progressFill = document.getElementById('progress-fill');
    const progressStage = document.getElementById('progress-stage');
    const resultsGrid = document.getElementById('results-grid');
    const resetBtn = document.getElementById('reset-btn');
    
    const toggleTranscriptBtn = document.getElementById('toggle-transcript');
    const transcriptContent = document.getElementById('transcript-content');

    const numShortsSelect = document.getElementById('num-shorts');
    const durationSelect = document.getElementById('clip-duration');

    let selectedFile = null;

    // --- Drag and Drop Logic ---

    dropZone.addEventListener('click', () => fileInput.click());
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        handleFiles(dt.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'video/mp4') {
                selectedFile = file;
                fileNameDisplay.textContent = `Selected: ${file.name}`;
                configSection.classList.remove('hidden');
            } else {
                alert('Please upload an MP4 video.');
            }
        }
    }

    // --- Transcript Toggle ---

    toggleTranscriptBtn.addEventListener('click', () => {
        const isHidden = transcriptContent.classList.toggle('hidden');
        toggleTranscriptBtn.textContent = isHidden ? 'Show Transcript' : 'Hide Transcript';
    });

    // --- Generation Logic ---

    generateBtn.addEventListener('click', () => {
        uploadSection.classList.add('hidden');
        configSection.classList.add('hidden');
        progressSection.classList.remove('hidden');

        simulateProcessing();
    });

    const stages = [
        { progress: 10, text: "Extracting audio..." },
        { progress: 30, text: "Transcribing with Whisper..." },
        { progress: 50, text: "Analyzing highlights..." },
        { progress: 70, text: "Generating clips..." },
        { progress: 90, text: "Applying effects..." },
        { progress: 100, text: "Finalizing..." }
    ];

    function simulateProcessing() {
        let currentStageIndex = 0;
        
        const interval = setInterval(() => {
            if (currentStageIndex < stages.length) {
                const stage = stages[currentStageIndex];
                progressStage.textContent = stage.text;
                progressFill.style.width = `${stage.progress}%`;
                
                // Show transcript section once transcription stage starts
                if (stage.progress >= 30) {
                    transcriptSection.classList.remove('hidden');
                }

                currentStageIndex++;
            } else {
                clearInterval(interval);
                setTimeout(showResults, 800);
            }
        }, 1200);
    }

    function showResults() {
        progressSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');

        const numShorts = parseInt(numShortsSelect.value);
        const duration = durationSelect.value;
        resultsGrid.innerHTML = '';

        for (let i = 1; i <= numShorts; i++) {
            const card = document.createElement('div');
            card.className = 'result-card';
            
            card.innerHTML = `
                <div class="thumbnail-placeholder">Thumbnail</div>
                <div class="result-info">
                    <h3>Short #${i}</h3>
                    <p>Duration: ${duration}s</p>
                </div>
                <button class="download-icon-btn" title="Download">↓</button>
            `;
            
            resultsGrid.appendChild(card);
        }
    }

    // --- Reset Logic ---

    resetBtn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        fileNameDisplay.textContent = '';
        progressFill.style.width = '0%';
        progressStage.textContent = 'Initializing...';
        
        resultsSection.classList.add('hidden');
        transcriptSection.classList.add('hidden');
        transcriptContent.classList.add('hidden');
        toggleTranscriptBtn.textContent = 'Show Transcript';
        
        uploadSection.classList.remove('hidden');
        configSection.classList.add('hidden');
    });
});
