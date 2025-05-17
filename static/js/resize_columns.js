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
        header.style.position = 'relative';

        header.addEventListener('mousedown', (e) => {
            // Trigger resize only if clicking near the right edge
            if (e.offsetX > header.offsetWidth - 10) {
                e.preventDefault();
                const startX = e.pageX;
                const tableWidth = table.offsetWidth;
                const startWidth = header.offsetWidth;
                const startPercent = (startWidth / tableWidth) * 100;

                const onMouseMove = (moveEvent) => {
                    const deltaX = moveEvent.pageX - startX;
                    const deltaPercent = (deltaX / tableWidth) * 100;
                    let newPercent = startPercent + deltaPercent;

                    // Enforce minimum width (50px)
                    const minPercent = (50 / tableWidth) * 100;
                    if (newPercent < minPercent) newPercent = minPercent;

                    // Adjust this column's width
                    savedWidths[index] = `${newPercent}%`;
                    header.style.width = savedWidths[index];

                    // Redistribute remaining width to other columns
                    const otherIndices = Array.from({ length: headers.length }, (_, i) => i).filter(i => i !== index);
                    const totalOtherPercent = otherIndices.reduce((sum, i) => sum + parseFloat(savedWidths[i]), 0);
                    const newTotalOtherPercent = 100 - newPercent;
                    const scaleFactor = newTotalOtherPercent / totalOtherPercent;

                    otherIndices.forEach(i => {
                        const currentPercent = parseFloat(savedWidths[i]);
                        const adjustedPercent = currentPercent * scaleFactor;
                        savedWidths[i] = `${adjustedPercent}%`;
                        headers[i].style.width = savedWidths[i];
                    });
                };

                const onMouseUp = () => {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    // Save widths to localStorage
                    localStorage.setItem(storageKey, JSON.stringify(savedWidths));
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            }
        });
    });
});