// Aurora background animation
const aurora = document.getElementById("aurora");
const colors = ["#3f3381", "#cba3ea", "#2868c6", "#60519b", "#bfc0d1"];

function createWave() {
  const wave = document.createElement("div");
  wave.classList.add("wave");
  const scheme = [];
  while (scheme.length < 3) {
    const c = colors[Math.floor(Math.random() * colors.length)];
    if (!scheme.includes(c)) scheme.push(c);
  }
  wave.style.background = `radial-gradient(circle at 50% 50%, ${scheme[0]}88, ${scheme[1]}66, ${scheme[2]}44, transparent 70%)`;
  aurora.appendChild(wave);
  let x = -200, y = 20 + Math.random() * 50, speedX = 0.3 + Math.random() * 0.5, driftY = (Math.random() * 0.2 + 0.05) * (Math.random() < 0.5 ? -1 : 1);
  function animate() {
    x += speedX; y += driftY;
    if (y < 10 || y > 80) driftY *= -1;
    wave.style.transform = `translate(${x}vw, ${y}vh)`;
    if (x > 200) { x = -200; y = 20 + Math.random() * 50; driftY = (Math.random() * 0.2 + 0.05) * (Math.random() < 0.5 ? -1 : 1); }
    requestAnimationFrame(animate);
  }
  animate();
}
for (let i = 0; i < 8; i++) createWave();

let currentResultId = null, currentResultFormats = null;

document.addEventListener('DOMContentLoaded', () => {
  // --- Element Selectors ---
  const urlToggleBtn = document.getElementById('urlToggleBtn'), urlPanel = document.getElementById('urlPanel');
  const submitUrlBtn = document.getElementById('submitUrl'), urlInput = document.getElementById('fileUrl');
  const uploadBox = document.querySelector('.upload-box'), fileInput = document.getElementById('fileInput');
  const uploadButton = document.getElementById('uploadButton'), clearHistoryBtn = document.getElementById('clearHistoryBtn');
  const historySearch = document.getElementById('historySearch'), copyAllBtn = document.getElementById('copyAllBtn');
  const downloadBtn = document.getElementById('downloadBtn'), logoutButton = document.getElementById('logoutButton');
  const accuracySelect = document.getElementById('accuracySelect');
  const languageSelect = document.getElementById('languageSelect');
  const historyList = document.getElementById('historyList');
  const historyEmpty = document.getElementById('historyEmpty');

  // --- Initial Load ---
  loadHistory(); 

  // --- Event Listeners ---
  if(logoutButton) logoutButton.addEventListener('click', () => { fetch('/logout').then(() => window.location.href = '/login'); });
  if(uploadButton) uploadButton.addEventListener('click', () => fileInput.click());
  if(fileInput) fileInput.addEventListener('change', (e) => { if (e.target.files.length > 0) uploadFiles(e.target.files); });
  
  if(uploadBox) {
    uploadBox.addEventListener('dragover', (e) => { e.preventDefault(); uploadBox.classList.add('drag-over'); });
    uploadBox.addEventListener('dragleave', () => uploadBox.classList.remove('drag-over'));
    uploadBox.addEventListener('drop', (e) => { 
        e.preventDefault(); 
        uploadBox.classList.remove('drag-over'); 
        if (e.dataTransfer.files.length > 0) uploadFiles(e.dataTransfer.files); 
    });
  }

  if(historySearch) {
    historySearch.addEventListener('input', function() {
      const searchTerm = this.value.toLowerCase();
      document.querySelectorAll('.history-item').forEach(item => {
        const name = item.querySelector('.history-name').textContent.toLowerCase();
        const preview = item.querySelector('.history-preview').textContent.toLowerCase();
        item.style.display = (name.includes(searchTerm) || preview.includes(searchTerm)) ? 'block' : 'none';
      });
    });
  }
  
  if(clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', function() {
        if (document.querySelectorAll('.history-item').length === 0) {
            alert("History is already empty.");
            return;
        }
        if (confirm('Are you sure you want to clear all history?')) {
            fetch('/history/clear_all', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadHistory();
                    showUploadView();
                } else {
                    alert('Error: ' + (data.error || 'Could not clear history.'));
                }
            })
            .catch(error => console.error('Error clearing history:', error));
        }
    });
  }

  // --- Core Functions ---

  function createOptimisticHistoryItem(fileName) {
    historyEmpty.style.display = 'none';
    const tempId = `temp-${Date.now()}`;
    const optimisticItem = document.createElement('div');
    optimisticItem.className = 'history-item';
    optimisticItem.setAttribute('data-id', tempId);
    optimisticItem.innerHTML = `
      <div class="history-item-header">
        <span class="history-name">${fileName}</span>
        <span class="history-date">Just now</span>
      </div>
      <div class="history-preview">
        <i class="fas fa-spinner fa-spin"></i> Processing...
      </div>
      <div class="history-actions">
        </div>
    `;
    historyList.prepend(optimisticItem); // Add to the top of the list
    return tempId;
  }

  function checkJobStatus(jobId, fileName) {
    const interval = setInterval(() => {
      fetch(`/job_status/${jobId}`)
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            if (data.status === 'completed') {
              clearInterval(interval);
              showResultsView('result', fileName, data.data, jobId);
              loadHistory();
              uploadButton.innerHTML = 'Upload Audio';
              uploadButton.disabled = false;
            } else if (data.status === 'failed') {
              clearInterval(interval);
              loadHistory();
              alert('Error during processing: ' + data.error);
              uploadButton.innerHTML = 'Upload Audio';
              uploadButton.disabled = false;
            }
          } else {
            clearInterval(interval);
            alert('Error checking job status: ' + data.error);
            uploadButton.innerHTML = 'Upload Audio';
            uploadButton.disabled = false;
          }
        })
        .catch(error => {
          clearInterval(interval);
          console.error('Error:', error);
          alert('An error occurred while checking job status.');
          uploadButton.innerHTML = 'Upload Audio';
          uploadButton.disabled = false;
        });
    }, 3000);
  }

  function uploadFiles(files) {
    const originalFileName = files[0].name;
    createOptimisticHistoryItem(originalFileName);

    const formData = new FormData();
    formData.append('file', files[0]);
    formData.append('accuracy', accuracySelect.value);
    formData.append('language', languageSelect.value);

    uploadButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    uploadButton.disabled = true;

    fetch('/upload_audio', { method: 'POST', body: formData })
      .then(response => response.json())
      .then(data => {
        if (data.success && data.job_id) {
          loadHistory();
          checkJobStatus(data.job_id, originalFileName);
        } else {
          loadHistory(); // Remove optimistic item on failure
          alert('Error: ' + (data.error || 'Unknown error during upload.'));
          uploadButton.innerHTML = 'Upload Audio';
          uploadButton.disabled = false;
        }
      })
      .catch(error => {
        console.error('Error:', error);
        loadHistory();
        alert('An error occurred during upload.');
        uploadButton.innerHTML = 'Upload Audio';
        uploadButton.disabled = false;
      })
      .finally(() => { fileInput.value = ''; });
  }
  
  function loadHistory() {
    fetch('/history')
      .then(response => response.json())
      .then(data => {
        historyList.querySelectorAll('.history-item').forEach(item => item.remove());

        if (data.length === 0) {
          historyEmpty.style.display = 'block';
        } else {
          historyEmpty.style.display = 'none';
          data.forEach(item => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.setAttribute('data-id', item.id);
            
            historyItem.innerHTML = `
              <div class="history-item-header">
                <span class="history-name">${item.name}</span>
                <span class="history-date">${formatDate(item.date)}</span>
              </div>
              <div class="history-preview">${item.preview}</div>
              <div class="history-actions">
                <button class="action-btn copy-btn" title="Copy text"><i class="fas fa-copy"></i></button>
                <button class="action-btn download-btn" title="Download"><i class="fas fa-download"></i></button>
                <button class="action-btn delete-btn" title="Delete"><i class="fas fa-trash"></i></button>
              </div>
            `;

            historyItem.addEventListener('click', (e) => {
                if (!e.target.closest('.history-actions')) {
                    if (item.status === 'completed') {
                        showResultsView('result', item.name, item.formats, item.id);
                    } else {
                        alert(`Job status: ${item.status}. Please wait for completion to view results.`);
                    }
                }
            });
            
            historyItem.querySelector('.copy-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                const textToCopy = item.formats?.transcription?.cleanedTranscript || "No text available to copy.";
                copyToClipboard(textToCopy);
                e.currentTarget.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => { e.currentTarget.innerHTML = '<i class="fas fa-copy"></i>'; }, 1000);
            });

            historyItem.querySelector('.download-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                const textToDownload = item.formats?.summary?.fullReport || "No summary to download.";
                const filename = `${item.name.split('.')[0]}_summary.txt`;
                downloadTextAsFile(textToDownload, filename);
            });
            
            historyItem.querySelector('.delete-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm('Are you sure you want to delete this item?')) {
                    fetch(`/history/delete/${item.id}`, { method: 'DELETE' })
                    .then(response => response.json())
                    .then(data => {
                        if(data.success) {
                            historyItem.remove();
                            if (document.querySelectorAll('.history-item').length === 0) {
                                historyEmpty.style.display = 'block';
                            }
                        } else {
                            alert('Error: ' + (data.error || 'Could not delete item.'));
                        }
                    })
                    .catch(error => console.error('Error deleting item:', error));
                }
            });
            historyList.appendChild(historyItem);
          });
        }
      })
      .catch(error => console.error('Error loading history:', error));
  }

  window.showResultsView = function(type, title, resultsData, itemId) {
    document.getElementById('uploadView').style.display = 'none';
    document.getElementById('resultsView').style.display = 'flex';
    document.getElementById('resultsTitle').textContent = title;
    
    currentResultId = itemId;
    const transcription = resultsData.transcription || {};
    const summary = resultsData.summary || {};

    currentResultFormats = {
        rawTranscript: transcription.rawTranscript,
        cleanedTranscript: transcription.cleanedTranscript,
        fullReport: summary.fullReport,
        translatedReport: summary.translatedReport ? summary.translatedReport.text : "Translation was not requested for this job.",
    };
    
    document.querySelectorAll('.format-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector('.format-btn[data-format="fullReport"]').classList.add('active');
    showFormat('fullReport');
  };

  function showFormat(format) {
    const resultsContent = document.getElementById('resultsContent');
    const formatData = currentResultFormats[format] || "Content not available for this format.";

    if (format === 'fullReport' && window.marked) {
      resultsContent.innerHTML = marked.parse(formatData);
    } else {
      resultsContent.innerHTML = `<div class="transcription-text"><pre>${formatData}</pre></div>`;
    }
  }
  
  function showUploadView() {
    document.getElementById('resultsView').style.display = 'none';
    document.getElementById('uploadView').style.display = 'block';
    currentResultId = null;
    currentResultFormats = null;
  }

  if(document.getElementById('backButton')) {
    document.getElementById('backButton').addEventListener('click', showUploadView);
  }

  document.querySelectorAll('.format-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      showFormat(this.dataset.format);
    });
  });

  if(copyAllBtn) copyAllBtn.addEventListener('click', function() {
    const activeFormat = document.querySelector('.format-btn.active').dataset.format;
    let textToCopy;
    if (activeFormat === 'fullReport') {
      textToCopy = document.getElementById('resultsContent').innerText;
    } else {
      textToCopy = currentResultFormats[activeFormat];
    }
    copyToClipboard(textToCopy);
    this.innerHTML = '<i class="fas fa-check"></i>';
    setTimeout(() => { this.innerHTML = '<i class="fas fa-copy"></i>'; }, 1000);
  });

  function downloadTextAsFile(text, filename) {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  if(downloadBtn) downloadBtn.addEventListener('click', function() {
    if (!currentResultId) return;
    const activeFormat = document.querySelector('.format-btn.active').dataset.format;
    let textToDownload;
    if (activeFormat === 'fullReport') {
        textToDownload = document.getElementById('resultsContent').innerText;
    } else {
        textToDownload = currentResultFormats[activeFormat];
    }
    const filename = `${document.getElementById('resultsTitle').textContent.split('.')[0]}_${activeFormat}.txt`;
    downloadTextAsFile(textToDownload, filename);
  });

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).catch(err => {
      console.error('Fallback copy: ', err);
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    });
  }
  
  /**
   * **FIXED & FINAL**: Correctly formats the UTC date string from the server to the user's local time.
   * This function now robustly handles timezone conversion for accurate "Today" and "Yesterday" display.
   */
  function formatDate(dateString) {
      // Create a Date object from the ISO string. JS automatically converts it to the browser's local timezone.
      const localDate = new Date(dateString);
      const now = new Date();

      // Get the start of the day for both dates in the local timezone.
      const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const startOfYesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
      const startOfJobDate = new Date(localDate.getFullYear(), localDate.getMonth(), localDate.getDate());

      const timeFormat = { hour: '2-digit', minute: '2-digit' };

      if (startOfJobDate.getTime() === startOfToday.getTime()) {
          // The job was created today (in the user's timezone)
          return 'Today, ' + localDate.toLocaleTimeString([], timeFormat);
      }
      
      if (startOfJobDate.getTime() === startOfYesterday.getTime()) {
          // The job was created yesterday (in the user's timezone)
          return 'Yesterday, ' + localDate.toLocaleTimeString([], timeFormat);
      }
      
      // For older dates, show the full local date and time.
      return localDate.toLocaleDateString() + ', ' + localDate.toLocaleTimeString([], timeFormat);
  }


  if(urlToggleBtn) urlToggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    urlPanel.classList.toggle('active');
  });

  if(submitUrlBtn) submitUrlBtn.addEventListener('click', () => {
    const url = urlInput.value.trim();
    if (!url) {
      alert('Please enter a URL');
      return;
    }
    
    createOptimisticHistoryItem(url);
    const originalHtml = submitUrlBtn.innerHTML;
    submitUrlBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    submitUrlBtn.disabled = true;
    
    const payload = { url, accuracy: accuracySelect.value, language: languageSelect.value };

    fetch('/upload_url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success && data.job_id) {
        loadHistory();
        checkJobStatus(data.job_id, url); 
        urlInput.value = '';
        urlPanel.classList.remove('active');
      } else {
        loadHistory();
        alert('Error: ' + (data.error || 'Unknown error processing URL.'));
      }
    })
    .catch(error => {
      console.error('Error:', error);
      loadHistory();
      alert('An error occurred while processing the URL.');
    })
    .finally(() => {
      submitUrlBtn.innerHTML = originalHtml;
      submitUrlBtn.disabled = false;
    });
  });

  if(urlInput) urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') submitUrlBtn.click();
  });
});