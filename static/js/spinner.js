document.addEventListener('DOMContentLoaded', () => {
    // Show spinner for charts page
    if (document.getElementById('spinner')) {
        setTimeout(() => {
            document.getElementById('spinner').classList.add('hidden');
        }, 1000); // Hide after 1 second (adjust based on chart rendering time)
    }

    // Show spinner on form submission
    const forms = document.querySelectorAll('#load-file-form, #search-form');
    forms.forEach(form => {
        form.addEventListener('submit', () => {
            const spinner = document.getElementById('spinner');
            if (spinner) {
                spinner.classList.remove('hidden');
            }
        });
    });
});

function showSpinner() {
    const spinner = document.getElementById('spinner');
    if (spinner) {
        spinner.classList.remove('hidden');
    }
}

function clearFilters() {
    const form = document.getElementById('search-form');
    form.querySelector('#question_intent').value = '';
    form.querySelector('#sub_intent').value = '';
    form.querySelector('#segment').value = '';
    form.querySelector('#per_page').value = '10'; // Reset to default
    showSpinner();
    form.submit();
}

// Show spinner when per_page dropdown changes
document.addEventListener('DOMContentLoaded', function() {
    const perPageSelect = document.getElementById('per_page');
    if (perPageSelect) {
        perPageSelect.addEventListener('change', showSpinner);
    }
});