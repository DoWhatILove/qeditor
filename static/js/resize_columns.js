document.addEventListener('DOMContentLoaded', () => {
    const table = document.querySelector('table');
    const headers = table.querySelectorAll('th.resizable');
    const storageKey = 'columnWidths';

    // Initialize default widths (equal distribution)
    const defaultWidth = 100 / headers.length;
    let savedWidths = JSON.parse(localStorage.getItem(storageKey)) || 
        Array.from({ length: headers.length }, () => `${defaultWidth}%`);

    // Apply saved or default widths
    headers.forEach((header, index) => {
        header.style.width = savedWidths[index] || `${defaultWidth}%`;
    });

    headers.forEach((header, index) => {
        // Skip the last column (Actions) as it has no next column
        if (index === headers.length - 1) return;

        header.style.position = 'relative';

        // Mouse-based resizing
        header.addEventListener('mousedown', (e) => {
            if (e.offsetX > header.offsetWidth - 10) {
                e.preventDefault();
                const startX = e.pageX;
                const tableWidth = table.offsetWidth;
                const startWidth = header.offsetWidth;
                const nextHeader = headers[index + 1];
                const startNextWidth = nextHeader.offsetWidth;
                const startPercent = (startWidth / tableWidth) * 100;
                const startNextPercent = (startNextWidth / tableWidth) * 100;

                const onMouseMove = (moveEvent) => {
                    const deltaX = moveEvent.pageX - startX;
                    const deltaPercent = (deltaX / tableWidth) * 100;
                    let newPercent = startPercent + deltaPercent;
                    let newNextPercent = startNextPercent - deltaPercent;

                    // Enforce minimum width (50px)
                    const minPercent = (50 / tableWidth) * 100;
                    if (newPercent < minPercent) {
                        newPercent = minPercent;
                        newNextPercent = startPercent + startNextPercent - minPercent;
                    }
                    if (newNextPercent < minPercent) {
                        newNextPercent = minPercent;
                        newPercent = startPercent + startNextPercent - minPercent;
                    }

                    // Update widths
                    savedWidths[index] = `${newPercent}%`;
                    header.style.width = savedWidths[index];
                    savedWidths[index + 1] = `${newNextPercent}%`;
                    nextHeader.style.width = savedWidths[index + 1];
                };

                const onMouseUp = () => {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    localStorage.setItem(storageKey, JSON.stringify(savedWidths));
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            }
        });

        // Touch-based resizing
        header.addEventListener('touchstart', (e) => {
            if (e.touches[0].clientX > header.offsetLeft + header.offsetWidth - 10) {
                e.preventDefault();
                const startX = e.touches[0].pageX;
                const tableWidth = table.offsetWidth;
                const startWidth = header.offsetWidth;
                const nextHeader = headers[index + 1];
                const startNextWidth = nextHeader.offsetWidth;
                const startPercent = (startWidth / tableWidth) * 100;
                const startNextPercent = (startNextWidth / tableWidth) * 100;

                const onTouchMove = (moveEvent) => {
                    const deltaX = moveEvent.touches[0].pageX - startX;
                    const deltaPercent = (deltaX / tableWidth) * 100;
                    let newPercent = startPercent + deltaPercent;
                    let newNextPercent = startNextPercent - deltaPercent;

                    // Enforce minimum width (50px)
                    const minPercent = (50 / tableWidth) * 100;
                    if (newPercent < minPercent) {
                        newPercent = minPercent;
                        newNextPercent = startPercent + startNextPercent - minPercent;
                    }
                    if (newNextPercent < minPercent) {
                        newNextPercent = minPercent;
                        newPercent = startPercent + startNextPercent - minPercent;
                    }

                    // Update widths
                    savedWidths[index] = `${newPercent}%`;
                    header.style.width = savedWidths[index];
                    savedWidths[index + 1] = `${newNextPercent}%`;
                    nextHeader.style.width = savedWidths[index + 1];
                };

                const onTouchEnd = () => {
                    document.removeEventListener('touchmove', onTouchMove);
                    document.removeEventListener('touchend', onTouchEnd);
                    localStorage.setItem(storageKey, JSON.stringify(savedWidths));
                };

                document.addEventListener('touchmove', onTouchMove);
                document.addEventListener('touchend', onTouchEnd);
            }
        });
    });
});