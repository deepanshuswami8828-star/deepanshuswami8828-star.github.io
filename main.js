document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------
    // 1. Initializations & Setup
    // -------------------------------------------------------------
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // Shrink header on scroll
    const header = document.querySelector('.main-header');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 40) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });

    // Mobile Navigation Menu Toggle
    const menuToggle = document.querySelector('.menu-toggle');
    const navLinksContainer = document.querySelector('.nav-links');
    const navLinks = document.querySelectorAll('.nav-link');

    menuToggle.addEventListener('click', () => {
        const expanded = menuToggle.getAttribute('aria-expanded') === 'true';
        menuToggle.setAttribute('aria-expanded', !expanded);
        menuToggle.classList.toggle('active');
        navLinksContainer.classList.toggle('active');
    });

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            menuToggle.setAttribute('aria-expanded', 'false');
            menuToggle.classList.remove('active');
            navLinksContainer.classList.remove('active');
        });
    });

    // -------------------------------------------------------------
    // 2. Light Ambient Particle Canvas
    // -------------------------------------------------------------
    const canvas = document.getElementById('ambient-canvas');
    const ctx = canvas.getContext('2d');

    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    window.addEventListener('resize', () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
        initParticles();
    });

    let particles = [];
    const maxParticles = Math.min(60, Math.floor((width * height) / 30000));

    class Particle {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.35;
            this.vy = (Math.random() - 0.5) * 0.35;
            this.radius = Math.random() * 1.5 + 0.5;
        }
        update() {
            this.x += this.vx;
            this.y += this.vy;

            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;
        }
        draw() {
            ctx.fillStyle = 'rgba(148, 163, 184, 0.15)'; // Muted slate-grey particles
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    function initParticles() {
        particles = [];
        for (let i = 0; i < maxParticles; i++) {
            particles.push(new Particle());
        }
    }

    function animateParticles() {
        ctx.clearRect(0, 0, width, height);

        // Draw connections first
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.04)';
        ctx.lineWidth = 0.8;
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dist = Math.hypot(particles[i].x - particles[j].x, particles[i].y - particles[j].y);
                if (dist < 120) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }

        // Draw particles
        particles.forEach(p => {
            p.update();
            p.draw();
        });

        requestAnimationFrame(animateParticles);
    }

    // Respect reduced motion setting
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!prefersReducedMotion) {
        initParticles();
        animateParticles();
    }

    // -------------------------------------------------------------
    // 3. Scroll Reveal Observer
    // -------------------------------------------------------------
    const revealElements = document.querySelectorAll('[data-reveal]');
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                revealObserver.unobserve(entry.target);
            }
        });
    }, {
        root: null,
        rootMargin: '0px',
        threshold: 0.12
    });

    if (!prefersReducedMotion) {
        revealElements.forEach(el => revealObserver.observe(el));
    } else {
        revealElements.forEach(el => el.classList.add('revealed'));
    }

    // -------------------------------------------------------------
    // 4. Project Specs Dialog Controller
    // -------------------------------------------------------------
    const projectModal = document.getElementById('project-modal');
    const closeProjBtn = document.getElementById('close-project-btn');
    const closeProjFooterBtn = document.getElementById('close-project-footer-btn');
    const projModalContent = document.getElementById('project-modal-content');
    const projModalTitle = document.getElementById('project-modal-title');
    
    // Last focused element to return focus to when modal closes
    let previousActiveElement = null;

    const projectData = {
        'dost-ai': {
            title: "Dost AI System Specifications",
            specs: {
                "Platform": "Android OS (Kotlin / Java SDK)",
                "ML Library": "TensorFlow Lite (Quantized SSD-MobileNet)",
                "Interface": "Offline Text-to-Speech Voice Engine",
                "Operations": "Fully offline (no internet required)"
            },
            desc: "Designed to assist visually impaired individuals. Dost AI runs a local computer vision object detection model on live camera feeds. The app coordinates spatial cues and relays descriptions of detected elements directly via spoken voice synthesis locally.",
            flow: "Camera Feed --> Frame Downsampler --> TFLite Interpreter --> Class Label Router --> Offline Text-To-Speech Output"
        },
        'vehicle-lock': {
            title: "AI Vehicle Lock System Specifications",
            specs: {
                "Controller": "Arduino Microcontroller board (C++)",
                "CV Script": "Python + OpenCV Facial Recognizer",
                "Comms Link": "Serial RS232 COM link",
                "Actuators": "5V Solenoid Switch Relay locks"
            },
            desc: "Biometric security ignition override. A computer-connected camera captures video frames. If local facial recognition registers a matched profile, a binary signal is written over the serial connection to actuate the Arduino physical switch, unlocking the vehicle.",
            flow: "CMOS Camera --> OpenCV Capture --> Python Face Matcher --> Serial Trigger (COM Port) --> Arduino Relay Actuator"
        },
        'attendance': {
            title: "Attendance Monitoring System Specifications",
            specs: {
                "Language": "Kotlin",
                "Database": "Firebase Realtime Database",
                "Design Pattern": "Model-View-ViewModel (MVVM)",
                "Performance": "Real-time sync supporting 200+ profiles"
            },
            desc: "Digital classroom ledger replacement. Tracks active courses and student profiles. The sync adapter coordinates localized checkins and push notifications, replacing manual paperwork grids.",
            flow: "User Registry UI --> ViewModel Cache --> Firebase Realtime Sync Adapter --> Admin Dashboard Console"
        },
        'tuition': {
            title: "Tuition Centre App Specifications",
            specs: {
                "Language": "Kotlin",
                "Database": "Firebase Cloud Firestore",
                "FCM Alert Core": "Firebase Cloud Messaging",
                "Architecture": "Clean Architecture Repository model"
            },
            desc: "Android application containing class schedules, payment grids, and teacher logs. Features push notices dispatched via Firebase Cloud Functions for immediate student alerts.",
            flow: "Admin Course Panel --> Firestore Update --> Cloud Functions Script --> Firebase Messaging (FCM) --> Mobile Notification"
        },
        'medicine': {
            title: "IoT Medicine Reminder Specifications",
            specs: {
                "Processor": "Arduino ATMega microcontroller core",
                "Sensors": "Ultrasonic distance sensor, RTC clock module",
                "Indicators": "Liquid Crystal Display, Active Piezo Buzzer",
                "Language": "Embedded C++"
            },
            desc: "Elderly patient medication box reminder. When RTC thresholds match medication intervals, it sounds an alarm, updating the visual LCD grid. Sensors track compartment extraction to verify dosage compliance.",
            flow: "RTC Clock Threshold Match --> Arduino Controller Alert --> Buzzer + LCD Alert Trigger --> Ultrasonic Sensor Verification"
        }
    };

    function openProjectModal(projId, triggerElement) {
        const data = projectData[projId];
        if (!data) return;

        previousActiveElement = triggerElement;

        projModalTitle.textContent = data.title;
        
        let specsHtml = '<ul class="spec-list">';
        for (const [key, val] of Object.entries(data.specs)) {
            specsHtml += `<li><span class="spec-key">${key}</span><span class="spec-val">${val}</span></li>`;
        }
        specsHtml += '</ul>';

        projModalContent.innerHTML = `
            <div>
                <h4>System Architecture</h4>
                ${specsHtml}
            </div>
            <div>
                <h4>Description</h4>
                <p>${data.desc}</p>
            </div>
            <div>
                <h4>Signal Flow Schematic</h4>
                <div class="schematic-box">${data.flow}</div>
            </div>
        `;

        projectModal.style.display = 'flex';
        // Force reflow
        projectModal.offsetHeight;
        projectModal.classList.add('active');
        document.body.classList.add('modal-open');
        
        // Accessibility: Trap focus in modal
        closeProjBtn.focus();
        document.addEventListener('keydown', trapModalFocus);
    }

    function closeProjectModal() {
        projectModal.classList.remove('active');
        document.body.classList.remove('modal-open');
        
        setTimeout(() => {
            projectModal.style.display = 'none';
        }, 300);

        document.removeEventListener('keydown', trapModalFocus);
        
        if (previousActiveElement) {
            previousActiveElement.focus();
        }
    }

    function trapModalFocus(e) {
        if (e.key === 'Tab') {
            const focusables = projectModal.querySelectorAll('button, [tabindex="0"]');
            const first = focusables[0];
            const last = focusables[focusables.length - 1];

            if (e.shiftKey) {
                if (document.activeElement === first) {
                    last.focus();
                    e.preventDefault();
                }
            } else {
                if (document.activeElement === last) {
                    first.focus();
                    e.preventDefault();
                }
            }
        } else if (e.key === 'Escape') {
            closeProjectModal();
        }
    }

    // Bind click events to project cards
    const projCards = document.querySelectorAll('.project-card');
    projCards.forEach(card => {
        const trigger = card.querySelector('.project-spec-btn');
        const projId = card.getAttribute('data-project');
        
        if (trigger && projId) {
            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                openProjectModal(projId, trigger);
            });
        }
    });

    if (closeProjBtn) closeProjBtn.addEventListener('click', closeProjectModal);
    if (closeProjFooterBtn) closeProjFooterBtn.addEventListener('click', closeProjectModal);
    
    projectModal.addEventListener('click', (e) => {
        if (e.target === projectModal) closeProjectModal();
    });

    // -------------------------------------------------------------
    // 5. Contact Form Submittal Feedback
    // -------------------------------------------------------------
    const contactForm = document.getElementById('contact-form');
    const formStatus = document.getElementById('form-status');

    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            formStatus.textContent = "Transmitting message...";
            formStatus.className = "form-status-message";

            // Simulate form submission success
            setTimeout(() => {
                formStatus.textContent = "Message sent successfully. Thank you!";
                formStatus.className = "form-status-message success";
                contactForm.reset();
            }, 1000);
        });
    }
});
