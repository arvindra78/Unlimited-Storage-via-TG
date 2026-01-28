async function uploadFile() {
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const progressBar = document.getElementById('progress-bar');
    const progressContainer = document.getElementById('progress-container');
    const statusText = document.getElementById('upload-status');

    if (!fileInput.files.length) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    uploadBtn.disabled = true;
    uploadBtn.innerText = 'Initializing...';
    statusText.innerText = 'Initializing handshake...';
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Upload handshake failed');

        const data = await response.json();
        const fileId = data.file_id;
        
        statusText.innerText = 'Transmitting chunks...';
        pollStatus(fileId);

    } catch (e) {
        console.error(e);
        statusText.innerText = 'Error: ' + e.message;
        uploadBtn.disabled = false;
        uploadBtn.innerText = 'Transmit';
        progressBar.style.backgroundColor = 'var(--danger)';
    }
}

async function pollStatus(fileId) {
    const progressBar = document.getElementById('progress-bar');
    const statusText = document.getElementById('upload-status');
    const uploadBtn = document.getElementById('upload-btn');

    let errorCount = 0;

    const interval = setInterval(async () => {
        try {
            const res = await fetch(`/check_status/${fileId}`);
            if (!res.ok) throw new Error('Status check failed');
            
            const data = await res.json();
            
            if (data.status === 'failed') {
                clearInterval(interval);
                statusText.innerText = 'Transmission Terminated';
                statusText.style.color = 'var(--danger)';
                progressBar.style.backgroundColor = 'var(--danger)';
                uploadBtn.disabled = false;
                uploadBtn.innerText = 'Retry';
                return;
            }

            if (data.status === 'completed') {
                clearInterval(interval);
                progressBar.style.width = '100%';
                statusText.innerText = 'Transmission Complete';
                statusText.style.color = 'var(--success)';
                // Reload after short delay to show file
                setTimeout(() => window.location.reload(), 1000);
                return;
            }

            // Update Progress
            if (data.total > 0) {
                const percent = (data.uploaded / data.total) * 100;
                progressBar.style.width = `${percent}%`;
                statusText.innerText = `Transmitting chunk ${data.uploaded} of ${data.total} ...`;
            } else {
                statusText.innerText = 'Analyzing content...';
            }

        } catch (e) {
            console.error(e);
            errorCount++;
            if (errorCount > 10) {
                clearInterval(interval);
                statusText.innerText = 'Connection Lost';
            }
        }
    }, 1000);
}

async function deleteFile(fileId) {
    if (!confirm('Are you sure you want to purge this file from the cloud? This cannot be undone.')) return;

    try {
        const res = await fetch(`/files/${fileId}/delete`, {
            method: 'POST'
        });
        
        if (res.ok) {
            const row = document.getElementById(`file-row-${fileId}`);
            row.style.opacity = '0';
            setTimeout(() => row.remove(), 300);
        } else {
            alert('Purge failed');
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}
