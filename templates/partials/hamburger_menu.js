        // Hamburger menu functionality
        const hamburgerMenu = document.getElementById('hamburgerMenu');
        const hamburgerIcon = hamburgerMenu.querySelector('.hamburger-icon');

        hamburgerIcon.addEventListener('click', () => {
            hamburgerMenu.classList.toggle('active');
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!hamburgerMenu.contains(e.target)) {
                hamburgerMenu.classList.remove('active');
            }
        });

        // Close menu when clicking on menu links
        const menuLinks = hamburgerMenu.querySelectorAll('.menu a');
        menuLinks.forEach(link => {
            link.addEventListener('click', () => {
                hamburgerMenu.classList.remove('active');
            });
        });
