document.addEventListener('DOMContentLoaded', () => {
    // --- Smooth Scrolling for Navigation ---
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();

            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);

            if (targetElement) {
                // Close mobile menu if open
                const mainNav = document.querySelector('.main-nav');
                const menuToggle = document.querySelector('.menu-toggle');
                if (mainNav.classList.contains('active')) {
                    mainNav.classList.remove('active');
                    menuToggle.classList.remove('active');
                }

                // Scroll to section with offset for fixed header
                const headerOffset = document.querySelector('.main-header').offsetHeight;
                const elementPosition = targetElement.getBoundingClientRect().top + window.scrollY;
                const offsetPosition = elementPosition - headerOffset - 20; // Add some extra padding

                window.scrollTo({
                    top: offsetPosition,
                    behavior: "smooth"
                });

                // Update active class for nav items
                document.querySelectorAll('.main-nav ul li a').forEach(item => {
                    item.classList.remove('active');
                });
                this.classList.add('active');
            }
        });
    });

    // Global function to scroll to a section, callable from HTML onclick
    window.scrollToSection = function(id) {
        const targetElement = document.getElementById(id);
        if (targetElement) {
            const headerOffset = document.querySelector('.main-header').offsetHeight;
            const elementPosition = targetElement.getBoundingClientRect().top + window.scrollY;
            const offsetPosition = elementPosition - headerOffset - 20;

            window.scrollTo({
                top: offsetPosition,
                behavior: "smooth"
            });

            // Update active class in nav
            document.querySelectorAll('.main-nav ul li a').forEach(item => {
                item.classList.remove('active');
                if (item.getAttribute('href') === `#${id}`) {
                    item.classList.add('active');
                }
            });
        }
    };


    // --- Mobile Navigation Toggle ---
    const menuToggle = document.querySelector('.menu-toggle');
    const mainNav = document.querySelector('.main-nav');

    menuToggle.addEventListener('click', () => {
        mainNav.classList.toggle('active');
        menuToggle.classList.toggle('active'); // Animate the burger icon
    });

    // --- Observe sections for fade-in animations ---
    const fadeInElements = document.querySelectorAll('.fade-in-item');

    const observerOptions = {
        root: null, // viewport
        rootMargin: '0px',
        threshold: 0.1 // 10% of element visible to trigger animation
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target); // Stop observing once animated
            }
        });
    }, observerOptions);

    fadeInElements.forEach(element => {
        observer.observe(element);
    });

    // Staggered animation for hero section elements
    const heroElements = document.querySelectorAll('.hero-content .fade-in-item');
    heroElements.forEach((el, index) => {
        // Apply a transition delay based on index for a staggered effect
        el.style.transitionDelay = `${index * 0.2}s`;
    });

    // Trigger initial hero section animation on load
    setTimeout(() => {
        heroElements.forEach(el => el.classList.add('is-visible'));
    }, 100);


    // --- Form 16 Analyzer Tool Logic (Frontend UI only) ---
    const dropArea = document.getElementById('drop-area');
    const fileElem = document.getElementById('fileElem');
    const fileNameDisplay = document.getElementById('file-name');
    const processButton = document.getElementById('process-form16-button');
    const resultsDashboard = document.getElementById('results-dashboard');

    let uploadedFile = null; // To store the file object for processing

    // Prevent default drag behaviors to allow custom drop handling
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop area when dragging over
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.add('hover'), false);
    });

    // Remove highlight when dragging leaves or file is dropped
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove('hover'), false);
    });

    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    // Handle file selection via hidden input
    fileElem.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // Processes the selected files (from drag/drop or input)
    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'application/pdf') {
                uploadedFile = file;
                fileNameDisplay.textContent = `File selected: ${file.name}`;
                processButton.disabled = false; // Enable the process button
                fileNameDisplay.style.color = 'var(--primary-color)';
            } else {
                uploadedFile = null; // Clear file if not PDF
                fileNameDisplay.textContent = 'Please upload a PDF file.';
                fileNameDisplay.style.color = 'red';
                processButton.disabled = true; // Disable button for invalid file
            }
        }
    }

    // Process button click (This will trigger your backend API call)
    processButton.addEventListener('click', () => {
        if (uploadedFile) {
            fileNameDisplay.textContent = 'Processing... Please wait.';
            fileNameDisplay.style.color = 'var(--secondary-color)';
            processButton.disabled = true; // Disable button to prevent multiple clicks
            resultsDashboard.classList.add('hidden'); // Hide results while processing

            const formData = new FormData();
            formData.append('form16', uploadedFile); // 'form16' should match your backend's expected field name

            fetch('/api/analyze-form16', { // **** IMPORTANT: Replace with your actual backend endpoint ****
                method: 'POST',
                body: formData
            })
            .then(response => {
                // Check if the HTTP response was successful (status 200-299)
                if (!response.ok) {
                    // If not successful, try to read error message from backend response
                    return response.text().then(text => {
                        let errorMessage = `HTTP error! Status: ${response.status}.`;
                        try {
                            const errorJson = JSON.parse(text);
                            errorMessage += ` Message: ${errorJson.message || text}`;
                        } catch (e) {
                            errorMessage += ` Raw response: ${text}`;
                        }
                        throw new Error(errorMessage);
                    });
                }
                return response.json(); // Parse response as JSON
            })
            .then(data => {
                // Assuming `data` is the JSON object returned from your backend
                // Example expected `data` structure:
                // {
                //     "gross_salary": "2000000",
                //     "exemptions": "500000",
                //     "taxable_income": "1500000",
                //     "total_tax_due": "150000",
                //     "tax_paid_tds": "120000",
                //     "refund_payable": "30000",
                //     "claimed_deductions": {
                //         "80C": "150000",
                //         "80D": "25000"
                //     },
                //     "tax_saving_opportunities": [
                //         {"title": "NPS Investment", "description": "You can save an additional ₹50,000...", "link": "#tax-saving-options/nps"},
                //         {"title": "Savings Account Interest", "description": "Did you know you can claim up to ₹10,000...", "link": "#tax-saving-options/80tta"}
                //     ]
                // }

                updateResultsDashboard(data); // Populate the dashboard with received data
                resultsDashboard.classList.remove('hidden'); // Show the results dashboard
                fileNameDisplay.textContent = 'Analysis Complete!';
                fileNameDisplay.style.color = 'var(--accent-color)';
                processButton.disabled = false; // Re-enable the button
                // Scroll to the analyzer tool section to show results
                scrollToSection('analyzer-tool');
            })
            .catch(error => {
                // Handle any errors during fetch or data processing
                console.error('Error processing Form 16:', error);
                fileNameDisplay.textContent = `Error: ${error.message}. Please try again.`;
                fileNameDisplay.style.color = 'red';
                processButton.disabled = false; // Re-enable button on error
                resultsDashboard.classList.add('hidden'); // Ensure results are hidden on error
            });
        } else {
            alert('Please select a Form 16 PDF first.');
        }
    });

    // Function to update the results dashboard with data from the backend
    function updateResultsDashboard(data) {
        document.getElementById('gross-salary').textContent = `₹${formatIndianCurrency(data.gross_salary)}`;
        document.getElementById('exemptions').textContent = `₹${formatIndianCurrency(data.exemptions)}`;
        document.getElementById('taxable-income').textContent = `₹${formatIndianCurrency(data.taxable_income)}`;
        document.getElementById('total-tax-due').textContent = `₹${formatIndianCurrency(data.total_tax_due)}`;
        document.getElementById('tax-paid-tds').textContent = `₹${formatIndianCurrency(data.tax_paid_tds)}`;
        document.getElementById('refund-payable').textContent = `₹${formatIndianCurrency(data.refund_payable)}`;

        // Update claimed deductions list
        const claimedDeductionsList = document.getElementById('claimed-deductions-list');
        claimedDeductionsList.innerHTML = ''; // Clear existing list items
        if (data.claimed_deductions && Object.keys(data.claimed_deductions).length > 0) {
            for (const [section, amount] of Object.entries(data.claimed_deductions)) {
                const li = document.createElement('li');
                li.textContent = `Section ${section}: ₹${formatIndianCurrency(amount)}`;
                claimedDeductionsList.appendChild(li);
            }
        } else {
            claimedDeductionsList.innerHTML = '<li>No specific deductions found in Form 16.</li>';
        }

        // Update tax saving opportunities list
        const taxSavingOpportunitiesDiv = document.getElementById('tax-saving-opportunities');
        taxSavingOpportunitiesDiv.innerHTML = ''; // Clear existing opportunities
        if (data.tax_saving_opportunities && data.tax_saving_opportunities.length > 0) {
            data.tax_saving_opportunities.forEach(opportunity => {
                const opportunityCard = document.createElement('div');
                opportunityCard.classList.add('opportunity-card');
                opportunityCard.innerHTML = `
                    <h5>${opportunity.title}</h5>
                    <p>${opportunity.description}</p>
                    <a href="${opportunity.link || '#tax-saving-options'}" class="learn-more">Learn More &rarr;</a>
                `;
                taxSavingOpportunitiesDiv.appendChild(opportunityCard);
            });
        } else {
            taxSavingOpportunitiesDiv.innerHTML = '<p>No new tax-saving opportunities identified for your profile at this time, but always check our Learn section!</p>';
        }

        // Re-apply fade-in animation to results elements for a fresh appearance
        document.querySelectorAll('#results-dashboard .fade-in-item').forEach((el, index) => {
            el.classList.remove('is-visible'); // Remove to allow re-triggering
            el.style.transitionDelay = `${index * 0.1}s`; // Staggered delay
            // Use a small timeout to ensure the browser registers the class removal
            // before adding it back for the animation to play
            setTimeout(() => el.classList.add('is-visible'), 50);
        });
    }

    // Helper function for Indian currency formatting
    function formatIndianCurrency(amount) {
        // Ensure amount is a number, converting from string and removing commas if present
        if (typeof amount === 'string') {
            amount = parseFloat(amount.replace(/,/g, ''));
        }
        if (isNaN(amount)) {
            return 'N/A';
        }
        // Format as Indian Rupee without decimal places
        return amount.toLocaleString('en-IN', {
            maximumFractionDigits: 0
        });
    }


    // --- Active navigation link on scroll ---
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.main-nav ul li a');

    window.addEventListener('scroll', () => {
        let currentSectionId = '';
        const headerOffsetHeight = document.querySelector('.main-header').offsetHeight;

        sections.forEach(section => {
            // Adjust threshold for section visibility
            const sectionTop = section.offsetTop - headerOffsetHeight - 50;
            const sectionHeight = section.clientHeight;
            if (window.scrollY >= sectionTop && window.scrollY < sectionTop + sectionHeight) {
                currentSectionId = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active'); // Remove active from all links
            // If the link's href matches the current section's ID, add 'active'
            if (link.getAttribute('href') === `#${currentSectionId}`) {
                link.classList.add('active');
            }
        });
    });

    // Set initial active link based on URL hash or default to homepage
    // This runs once when the page loads
    const initialHash = window.location.hash;
    if (initialHash) {
        // Find the link whose href exactly matches the initial hash
        const initialActiveLink = document.querySelector(`.main-nav ul li a[href="${initialHash}"]`);
        if (initialActiveLink) {
            initialActiveLink.classList.add('active');
            // Smooth scroll to the section if linked via URL hash
            scrollToSection(initialHash.substring(1));
        }
    } else {
        // If no hash, activate the homepage link by default
        document.querySelector('.main-nav ul li a[href="#home"]').classList.add('active');
    }
});