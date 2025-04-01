document.addEventListener('DOMContentLoaded', function() {
    // Store original button texts
    const originalButtonTexts = new Map();
    document.querySelectorAll('form button[type="submit"]').forEach(button => {
        originalButtonTexts.set(button, button.innerHTML);
    });

    // Enhanced form handling
    document.querySelectorAll('form').forEach(form => {
        // File validation
        const fileInput = form.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.addEventListener('change', function() {
                const maxSize = 16 * 1024 * 1024; // 16MB
                if (this.files[0]?.size > maxSize) {
                    alert('File size exceeds 16MB limit!');
                    this.value = '';
                }
            });
        }

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const button = this.querySelector('button[type="submit"]');
            const errorDisplay = this.querySelector('.error-message');
            if (errorDisplay) errorDisplay.textContent = '';
            
            button.disabled = true;
            button.innerHTML = 'Processing... <span class="spinner"></span>';

            try {
                const response = await fetch(this.action, {
                    method: this.method,
                    body: new FormData(this)
                });

                if (!response.ok) {
                    const error = await response.text();
                    
                    // User-friendly error messages
                    const errorMap = {
                        "only one page": "This PDF has just one page - nothing to split",
                        "no splitting needed": "Your selection includes all pages",
                        "No valid pages": "Please enter valid page numbers"
                    };
                    
                    const userMessage = Object.entries(errorMap).find(([key]) => 
                        error.includes(key))?.[1] || error;
                    
                    if (errorDisplay) {
                        errorDisplay.textContent = userMessage;
                    } else {
                        alert(userMessage);
                    }
                    return;
                }

                // Handle successful download
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = response.headers.get('content-disposition')
                    ?.split('filename=')[1]
                    ?.replace(/"/g, '') || 'download.pdf';
                a.click();
                URL.revokeObjectURL(url);

            } catch (error) {
                console.error('Error:', error);
                if (errorDisplay) {
                    errorDisplay.textContent = "An error occurred. Please try again.";
                } else {
                    alert("An error occurred. Please try again.");
                }
            } finally {
                button.disabled = false;
                button.innerHTML = originalButtonTexts.get(button);
            }
        });
    });

    // Split PDF page validation
    const splitForm = document.querySelector('form[action="/split"]');
    if (splitForm) {
        const pagesInput = splitForm.querySelector('input[name="pages"]');
        pagesInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^\d,\-]/g, '');
        });
    }
});