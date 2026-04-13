        // Print functions
        function printStandard() {
            document.body.classList.remove('print-card-mode');
            // Remove card page style if it exists
            const cardStyle = document.getElementById('card-print-style');
            if (cardStyle) cardStyle.remove();
            window.print();
        }

        function printRecipeCard() {
            document.body.classList.add('print-card-mode');

            // Inject @page rule for card size
            const style = document.createElement('style');
            style.id = 'card-print-style';
            style.textContent = '@media print { @page { size: 6in 4in landscape; margin: 0.25in; } }';
            document.head.appendChild(style);

            window.print();

            // Clean up after print dialog closes
            setTimeout(() => {
                document.body.classList.remove('print-card-mode');
                style.remove();
            }, 100);
        }
