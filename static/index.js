document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fallbackFile = document.getElementById('fallback-file');
    const fallbackFolder = document.getElementById('fallback-folder');
    const companySelect = document.getElementById('company-select');
    
    // UI States
    const manualUploadRow = document.querySelector('.manual-upload-row');
    const selectedFilesDiv = document.getElementById('selected-files');
    const fileList = document.getElementById('file-list');
    const selectionTitle = document.getElementById('selection-title');
    const loadingState = document.getElementById('loading-state');
    const resultState = document.getElementById('result-state');
    const btnProcess = document.getElementById('btn-process');
    const btnReset = document.getElementById('btn-reset');
    
    let currentFiles = [];

    // --- Core UI Functions ---
    
    function showState(state) {
        // Reset all specific blocks
        dropZone.classList.remove('hidden');
        manualUploadRow.classList.remove('hidden');
        selectedFilesDiv.classList.add('hidden');
        loadingState.classList.add('hidden');
        resultState.classList.add('hidden');
        
        switch(state) {
            case 'selection':
                selectedFilesDiv.classList.remove('hidden');
                dropZone.classList.add('hidden');
                manualUploadRow.classList.add('hidden');
                break;
            case 'loading':
                dropZone.classList.add('hidden');
                manualUploadRow.classList.add('hidden');
                loadingState.classList.remove('hidden');
                break;
            case 'result':
                dropZone.classList.add('hidden');
                manualUploadRow.classList.add('hidden');
                resultState.classList.remove('hidden');
                break;
            case 'default':
            default:
                currentFiles = [];
                fileInput.value = '';
                fallbackFile.value = '';
                fallbackFolder.value = '';
                break;
        }
    }

    function handleFiles(filesArray) {
        if (!filesArray || filesArray.length === 0) return;
        
        currentFiles = Array.from(filesArray);
        
        // Build list
        fileList.innerHTML = '';
        currentFiles.slice(0, 10).forEach(f => {
            const li = document.createElement('li');
            // f.webkitRelativePath will have the path if uploaded via folder drop/select
            const displayPath = f.webkitRelativePath || f.name;
            li.textContent = "📄 " + displayPath;
            fileList.appendChild(li);
        });
        
        if (currentFiles.length > 10) {
            const li = document.createElement('li');
            li.textContent = `... and ${currentFiles.length - 10} more files`;
            fileList.appendChild(li);
        }
        
        if (currentFiles.length === 1 && currentFiles[0].name.toLowerCase().endsWith('.zip')) {
            selectionTitle.textContent = "Selected ZIP Archive";
        } else if (currentFiles.length > 1) {
            selectionTitle.textContent = `Selected Folder Structure (${currentFiles.length} items)`;
        } else {
            selectionTitle.textContent = "Selected Document";
        }

        showState('selection');
    }

    // --- Drag and Drop Handlers ---
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-active'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-active'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        // Handle drops - e.dataTransfer.files might not have relative paths directly
        // We use webkitGetAsEntry to recursively get files if a folder is dropped
        let items = e.dataTransfer.items;
        if (items && items.length > 0) {
            let promises = [];
            let files = [];
            
            for (let i=0; i<items.length; i++) {
                let item = items[i].webkitGetAsEntry();
                if (item) {
                    promises.push(traverseFileTree(item, item.name, files));
                }
            }
            
            Promise.all(promises).then(() => {
                handleFiles(files);
            });
        } else {
            handleFiles(e.dataTransfer.files);
        }
    });

    // Helper to recursively traverse folders when dropped
    function traverseFileTree(item, path, fileList) {
        return new Promise((resolve) => {
            if (item.isFile) {
                item.file(file => {
                    // Create a pseudo-file with the webkitRelativePath set
                    // so our backend loop logic receives the path
                    Object.defineProperty(file, 'webkitRelativePath', {
                        value: path
                    });
                    fileList.push(file);
                    resolve();
                });
            } else if (item.isDirectory) {
                let dirReader = item.createReader();
                let entries = [];
                
                const readEntries = () => {
                    dirReader.readEntries(results => {
                        if (!results.length) {
                            let promises = entries.map(entry => traverseFileTree(entry, path + "/" + entry.name, fileList));
                            Promise.all(promises).then(resolve);
                        } else {
                            entries = entries.concat(Array.from(results));
                            readEntries(); // Keep reading until empty
                        }
                    });
                };
                readEntries();
            }
        });
    }

    // --- Input Change Handlers ---
    
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
    fallbackFile.addEventListener('change', (e) => handleFiles(e.target.files));
    fallbackFolder.addEventListener('change', (e) => handleFiles(e.target.files));

    // --- Submit Flow ---
    
    btnProcess.addEventListener('click', async () => {
        if (!currentFiles.length) return;
        
        showState('loading');
        const company = companySelect.value;
        
        const formData = new FormData();
        formData.append('company', company);
        
        const paths = [];
        currentFiles.forEach(file => {
            formData.append('files', file);
            paths.push(file.webkitRelativePath || file.name);
        });
        
        formData.append('paths', paths.join(','));

        try {
            const response = await fetch('/api/extract', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Server error occurred');
            }

            const data = await response.json();
            console.log("Success:", data);
            showState('result');
            
        } catch (error) {
            console.error(error);
            alert("Extraction failed: " + error.message);
            showState('selection'); // Go back to selection on error
        }
    });

    btnReset.addEventListener('click', () => {
        showState('default');
    });

});
