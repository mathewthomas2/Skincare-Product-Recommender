let currentPage = 1;
const pages = ['uploadPage', 'questionnairePage', 'recommendationsPage'];
let imageUploaded = false;

// Handle file upload area
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const imagePreview = document.getElementById('imagePreview');
const imagePreviewContainer = document.getElementById('imagePreviewContainer');
let currentImageUrl = null;
let uploadInProgress = false;

// Force image reload when needed
function forceImageRefresh(imgElement) {
    // Add a timestamp parameter to force a refresh
    if (imgElement.src && imgElement.src.startsWith('data:')) {
        // Don't modify data URLs
        return;
    }
    
    const timestamp = new Date().getTime();
    if (imgElement.src.indexOf('?') !== -1) {
        imgElement.src = imgElement.src.split('?')[0] + '?' + timestamp;
    } else {
        imgElement.src = imgElement.src + '?' + timestamp;
    }
}

uploadArea.addEventListener('click', () => {
    fileInput.click();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.backgroundColor = 'rgba(135, 206, 235, 0.2)';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.backgroundColor = 'rgba(135, 206, 235, 0.05)';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.backgroundColor = 'rgba(135, 206, 235, 0.05)';
    const files = e.dataTransfer.files;
    handleFiles(files);
});

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

async function handleFiles(files) {
    if (files.length > 0 && !uploadInProgress) {
        const file = files[0];
        
        // Reset error message
        document.getElementById('uploadErrorMessage').style.display = 'none';
        
        if (file.type.startsWith('image/')) {
            try {
                uploadInProgress = true;
                showLoadingState();

                // Show preview first
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.style.display = 'block';
                };
                reader.readAsDataURL(file);

                const formData = new FormData();
                formData.append('file', file);

                // Check server connection first
                try {
                    const response = await fetch('http://localhost:8000/analyze-skin', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Error analyzing image');
                    }

                    const result = await response.json();
                    
                    // Success case
                    imageUploaded = true;
                    document.getElementById('uploadErrorMessage').style.display = 'none';
                    handleSkinTypeResponse(result);

                } catch (error) {
                    if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                        // Server connection error
                        document.getElementById('uploadErrorMessage').textContent = 
                            'Cannot connect to analysis server. Please ensure the server is running.';
                    } else {
                        // Other errors
                        document.getElementById('uploadErrorMessage').textContent = 
                            error.message || 'Error processing image. Please try again.';
                    }
                    document.getElementById('uploadErrorMessage').style.display = 'block';
                    imageUploaded = false;
                }
            } finally {
                hideLoadingState();
                uploadInProgress = false;
            }
        } else {
            document.getElementById('uploadErrorMessage').textContent = 
                'Please upload a valid image file (JPG or PNG)';
            document.getElementById('uploadErrorMessage').style.display = 'block';
        }
    }
}

// Add this helper function to check server status
async function checkServerStatus() {
    try {
        const response = await fetch('http://localhost:8000/');
        return response.ok;
    } catch {
        return false;
    }
}

function getSkinTypeLabel(type) {
    switch(type) {
        case 'D':
            return 'Dry';
        case 'O':
            return 'Oily';
        case 'C':
            return 'Combination';
        default:
            return 'Unknown';
    }
}

// Force the function to show more descriptive error messages
function handleSkinTypeResponse(result) {
    console.log("Handling skin type response:", result);
    
    try {
        // Get the skin type from the backend response
        const skinType = result.skin_type; 
        
        if (!skinType || skinType.length < 2) {
            console.error("Invalid skin type format:", skinType);
            throw new Error("Invalid skin type format in response");
        }
        
        // First character indicates Dry (D) or Oily (O) 
        const skinTypeChar = skinType[0];
        document.getElementById('skinType1').checked = skinTypeChar === 'D';
        document.getElementById('skinType2').checked = skinTypeChar === 'O';        
        // Second character indicates Resistant (R) or Sensitive (S)
        const isSensitive = skinType.charAt(1) === 'S';
        document.getElementById('sensitiveSkinYes').checked = isSensitive;
        document.getElementById('sensitiveSkinNo').checked = !isSensitive;

        // Display the short info if available
        // Remove any existing info container first
        const existingInfo = document.querySelector('.skin-type-info');
        if (existingInfo) {
            existingInfo.remove();
        }
            
        const infoContainer = document.createElement('div');
        infoContainer.className = 'skin-type-info';
        infoContainer.innerHTML = `
            <div class="skin-analysis-results">
                <h3>Your Skin Analysis Results</h3>
                <div class="result-item">
                    <span class="label">Skin Type:</span>
                    <span class="value">${getSkinTypeLabel(skinTypeChar)}</span>
                </div>
                <div class="result-item">
                    <span class="label">Sensitivity:</span>
                    <span class="value">${isSensitive ? 'Sensitive' : 'Resistant'}</span>
                </div>
                <div class="result-item">
                    <span class="label">Pigmentation:</span>
                    <span class="value">${skinType[2] === 'P' ? 'Pigmented' : 'Non-pigmented'}</span>
                </div>
                ${result.skin_percentage ? `
                    <div class="result-item">
                        <span class="label">Skin Detection:</span>
                        <span class="value">${result.skin_percentage.toFixed(1)}%</span>
                    </div>
                ` : ''}
                <div class="result-info">
                    <p>${result.short_info || ''}</p>
                </div>
            </div>
        `;
        document.querySelector('.form-group').insertAdjacentElement('afterend', infoContainer);
        
    } catch (error) {
        console.error("Error in handleSkinTypeResponse:", error);
        throw error;
    }
}

// Make entire radio/checkbox option clickable
document.querySelectorAll('.radio-option, .checkbox-option').forEach(option => {
    option.addEventListener('click', function(e) {
        // Prevent clicks on the input itself from triggering this twice
        if (e.target !== this.querySelector('input')) {
            const input = this.querySelector('input');
            if (input.type === 'radio') {
                input.checked = true;
            } else if (input.type === 'checkbox') {
                input.checked = !input.checked;
            }
        }
    });
});

document.addEventListener('DOMContentLoaded', function() {
    // Make entire checkbox option clickable
    document.querySelectorAll('.checkbox-option').forEach(option => {
        option.addEventListener('click', function(e) {
            // Prevent clicks on the input itself from triggering this twice
            if (e.target !== this.querySelector('input')) {
                const input = this.querySelector('input');
                input.checked = !input.checked;
                
                // Trigger any validation or event listeners if needed
                const event = new Event('change', { bubbles: true ,cancelable: true });
                input.dispatchEvent(event);

                 // Add visual feedback
                 this.classList.toggle('selected', input.checked);
            }
        });
    });
});


document.getElementById('changeImageBtn').addEventListener('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    
    // Clear file input to ensure change event triggers even with same file
    fileInput.value = '';
    
    // Remove any skin type info that was displayed
    const existingInfo = document.querySelector('.skin-type-info');
    if (existingInfo) {
        existingInfo.remove();
    }
    
    fileInput.click();
});

// Validation functions
async function validateAndNextPage() {
    if (imageUploaded && imagePreview.complete && imagePreview.src) {
        nextPage();
    } else {
        document.getElementById('uploadErrorMessage').textContent = 'Please upload an image to continue';
        document.getElementById('uploadErrorMessage').style.display = 'block';
    }
}

function validateFormAndNextPage() {
    let isValid = true;
    
    // Validate skin type
    const skinTypeSelected = document.querySelector('input[name="skinType"]:checked');
    if (!skinTypeSelected) {
        document.getElementById('skinTypeErrorMessage').style.display = 'block';
        isValid = false;
    } else {
        document.getElementById('skinTypeErrorMessage').style.display = 'none';
    }
    
    // Validate skin concerns (at least one must be selected)
    const concernsSelected = document.querySelectorAll('input[name="concerns"]:checked');
    if (concernsSelected.length === 0) {
        document.getElementById('concernsErrorMessage').style.display = 'block';
        isValid = false;
    } else {
        document.getElementById('concernsErrorMessage').style.display = 'none';
    }
    
    // Validate product type
    const productTypeSelected = document.querySelector('input[name="productType"]:checked');
    if (!productTypeSelected) {
        document.getElementById('productTypeErrorMessage').style.display = 'block';
        isValid = false;
    } else {
        document.getElementById('productTypeErrorMessage').style.display = 'none';
    }
    
    if (isValid) {
        nextPage();
    }
}

// Navigation functions
function updateProgressBar() {
    const steps = document.querySelectorAll('.step');
    steps.forEach((step, index) => {
        if (index + 1 <= currentPage) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    });
}

function showPage(pageId) {
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    const newPage = document.getElementById(pageId);
    newPage.classList.add('active');
    
    // Add animation
    setTimeout(() => {
        newPage.style.transform = 'translateY(0)';
        newPage.style.opacity = '1';
    }, 50);
}

function nextPage() {
    if (currentPage < 3) {
        currentPage++;
        updateProgressBar();
        showPage(pages[currentPage - 1]);
        if (currentPage === 3) {
            showLoadingAnimation();
            setTimeout(loadRecommendations, 1500);
        }
    }
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        updateProgressBar();
        showPage(pages[currentPage - 1]);
    }
}

function showLoadingAnimation() {
    const recommendationsContainer = document.getElementById('productRecommendations');
    recommendationsContainer.innerHTML = `
        <div style="text-align: center; padding: 2rem;">
            <div class="loading"></div>
            <p style="margin-top: 1rem; color: #666;">Analyzing your skin profile...</p>
        </div>
    `;
}

// Load recommendations
function loadRecommendations() {
    // Get form data
    const skinType = document.querySelector('input[name="skinType"]:checked').value;
    const allergiesInput = document.getElementById('allergiesInput').value;
    const concernsSelected = Array.from(document.querySelectorAll('input[name="concerns"]:checked')).map(el => el.value);
    const productType = document.querySelector('input[name="productType"]:checked').value;
    
    // Product database (in a real app, this would come from a backend API)
    const productDatabase = {
        cleanser: [
            {
                title: "Gentle Hydrating Cleanser",
                brand: "CeraVe",
                description: "Perfect for sensitive skin, this non-foaming cleanser removes impurities while maintaining skin barrier.",
                price: "$15.99",
                icon: "fas fa-soap",
                ingredients: ["ceramides", "hyaluronic acid", "glycerin"],
                skinTypes: ["dry","oil", "combination"],
                concerns: ["dryness","aging","pigmentation","redness","acne"]
            },
            {
                title: "Foaming Facial Cleanser",
                brand: "Neutrogena",
                description: "Removes excess oil, makeup and impurities without over-drying or irritating skin.",
                price: "$9.99",
                icon: "fas fa-soap",
                ingredients: ["glycerin", "sodium laureth sulfate", "cocamidopropyl betaine"],
                skinTypes: ["oily", "combination", "normal"],
                concerns: ["acne", "pigmentation"]
            },
            {
                title: "Soothing Cleanser",
                brand: "La Roche-Posay",
                description: "Gentle, soap-free cleanser that respects sensitive skin while effectively removing impurities.",
                price: "$14.99",
                icon: "fas fa-soap",
                ingredients: ["thermal spring water", "glycerin", "niacinamide"],
                skinTypes: ["dry", "normal"],
                concerns: ["redness", "dryness"]
            },
            {
                title: "Purifying Neem Face Wash",
                brand: "Himalaya",
                description: "Neem and turmeric-based cleanser that helps clear impurities and prevent acne.",
                price: "$5.99",
                icon: "fas fa-soap",
                ingredients: ["neem extract", "turmeric extract", "glycerin"],
                skinTypes: ["oily", "combination"],
                concerns: ["acne", "aging"]
            },
            {
                title: "Rice Water Bright Foaming Cleanser",
                brand: "The Face Shop",
                description: "Rice water-infused cleanser that brightens and moisturizes while removing impurities.",
                price: "$10.99",
                icon: "fas fa-soap",
                ingredients: ["rice extract", "moringa oil", "soapberry extract"],
                skinTypes: [ "combination", "dry"],
                concerns: ["pigmentation", "aging", "acne"]
            },
            {
                title: "Facial Cleansing Gel",
                brand: "Avene",
                description: "Soap-free cleansing gel formulated for sensitive skin that cleanses without disrupting the pH balance.",
                price: "$18.99",
                icon: "fas fa-soap",
                ingredients: ["thermal spring water", "glutamic acid", "glycerin"],
                skinTypes: ["combination", "oily", "dry"],
                concerns: ["dryness", "redness"]
            }
        ],
        moisturizer: [
            {
                title: "Daily Moisturizing Lotion",
                brand: "CeraVe",
                description: "Lightweight, oil-free moisturizer that helps hydrate the skin and restore its natural barrier.",
                price: "$12.99",
                icon: "fas fa-pump-soap",
                ingredients: ["ceramides", "hyaluronic acid", "niacinamide"],
                skinTypes: ["normal",  "combination"],
                concerns: ["dryness", "aging"]
            },
            {
                title: "Oil-Free Moisturizer",
                brand: "Neutrogena",
                description: "Lightweight water-based moisturizer that won't clog pores or cause breakouts.",
                price: "$8.99",
                icon: "fas fa-pump-soap",
                ingredients: ["glycerin", "dimethicone", "allantoin"],
                skinTypes: ["combination", "oily", "dry"],
                concerns: ["dryness", "redness"]
            },
            {
                title: "Rich Repair Cream",
                brand: "First Aid Beauty",
                description: "Intensive hydration for very dry or irritated skin with colloidal oatmeal.",
                price: "$24.00",
                icon: "fas fa-pump-soap",
                ingredients: ["colloidal oatmeal", "shea butter", "ceramides"],
                skinTypes: [ "combination", "dry"],
                concerns: ["pigmentation", "aging", "acne"]
            },
            {
                title: "Nourishing Vitamin E Cream",
                brand: "Himalaya",
                description: "Vitamin E enriched moisturizer that provides 24-hour hydration and protects from environmental damage.",
                price: "$7.99",
                icon: "fas fa-pump-soap",
                ingredients: ["vitamin E", "wheat germ oil", "sunflower oil"],
                skinTypes: [ "combination", "dry"],
                concerns: ["acne", "dryness" ]
            },
            {
                title: "Water Bank Blue Hyaluronic Cream",
                brand: "Laneige",
                description: "Moisture-locking cream with blue hyaluronic acid that provides long-lasting hydration.",
                price: "$39.99",
                icon: "fas fa-pump-soap",
                ingredients: ["blue hyaluronic acid", "green mineral water", "squalane"],
                skinTypes: ["dry", "combination"],
                concerns: ["dryness", "acne"]
            },
            {
                title: "Cica Repair Balm",
                brand: "Dr. Jart+",
                description: "Concentrated repair cream with centella asiatica that soothes and strengthens skin barrier.",
                price: "$48.00",
                icon: "fas fa-pump-soap",
                ingredients: ["centella asiatica", "madecassoside", "panthenol"],
                skinTypes: ["combination"],
                concerns: ["dryness", "acne"]
            }
        ],
        serum: [
            {
                title: "Vitamin C Brightening Serum",
                brand: "The Ordinary",
                description: "High-potency vitamin C serum that targets uneven skin tone and signs of aging.",
                price: "$19.99",
                icon: "fas fa-eye-dropper",
                ingredients: ["vitamin C", "hyaluronic acid", "ferulic acid"],
                skinTypes: ["oily", "combination"],
                concerns: ["dryness", "aging","pigmentation","acne"]
            },
            {
                title: "Niacinamide & Zinc Serum",
                brand: "The Inkey List",
                description: "Oil-controlling serum that reduces blemishes and minimizes the appearance of pores.",
                price: "$10.99",
                icon: "fas fa-eye-dropper",
                ingredients: ["niacinamide", "zinc", "glycerin"],
                skinTypes: ["dry", "combination"],
                concerns: ["dryness", "acne"]
            },
            {
                title: "Hyaluronic Acid Super Hydrator",
                brand: "La Roche-Posay",
                description: "Intense hydrating serum with pure hyaluronic acid for plump, dewy skin.",
                price: "$29.99",
                icon: "fas fa-eye-dropper",
                ingredients: ["hyaluronic acid", "glycerin", "vitamin B5"],
                skinTypes: ["oily", "dry"],
                concerns: ["acne", "dryness", "aging"]
            },
            {
                title: "Youth Infusing Serum",
                brand: "Himalaya",
                description: "Anti-aging serum enriched with herbs and antioxidants that reduces fine lines and improves elasticity.",
                price: "$13.99",
                icon: "fas fa-eye-dropper",
                ingredients: ["edelweiss extract", "woodfordia extract", "cipadessa baccifera"],
                skinTypes: [ "combination", "dry"],
                concerns: ["pigmentation", "aging", "acne"]
            },
            {
                title: "Buffet Peptide Serum",
                brand: "The Ordinary",
                description: "Multi-technology peptide serum targeting multiple signs of aging at once.",
                price: "$14.80",
                icon: "fas fa-eye-dropper",
                ingredients: ["matrixyl 3000", "syn-ake", "hyaluronic acid"],
                skinTypes: [ "combination", "dry"],
                concerns: ["pigmentation", "aging", "acne"]
            },
            {
                title: "Cica Clear Serum",
                brand: "Cosrx",
                description: "Centella-infused serum that calms irritation and reduces redness while promoting healing.",
                price: "$25.00",
                icon: "fas fa-eye-dropper",
                ingredients: ["centella asiatica", "niacinamide", "tea tree oil"],
                skinTypes: ["combination", "oily", "dry"],
                concerns: ["dryness", "redness"]
            }
        ],
        sunscreen: [
            {
                title: "Invisible Fluid SPF 50+",
                brand: "La Roche-Posay",
                description: "Ultra-light, invisible fluid with high protection against UVA/UVB rays.",
                price: "$29.99",
                icon: "fas fa-sun",
                ingredients: ["avobenzone", "homosalate", "octocrylene"],
                skinTypes: [ "combination", "dry"],
                concerns: ["pigmentation", "aging", "acne"]
            },
            {
                title: "Clear Face Oil-Free Sunscreen",
                brand: "Neutrogena",
                description: "Oil-free, non-comedogenic sunscreen that won't cause breakouts.",
                price: "$12.99",
                icon: "fas fa-sun",
                ingredients: ["avobenzone", "octisalate", "octocrylene"],
                skinTypes: ["oily", "combination", "oily"],
                concerns: ["acne", "dryness", "redness"]
            },
            {
                title: "Mineral Sensitive Skin Sunscreen",
                brand: "CeraVe",
                description: "Gentle physical sunscreen with zinc oxide for sensitive skin types.",
                price: "$15.99",
                icon: "fas fa-sun",
                ingredients: ["zinc oxide", "titanium dioxide", "ceramides"],
                skinTypes: ["dry", "oily"],
                concerns: ["aging", "redness"]
            },
            {
                title: "Protective Sunscreen Lotion SPF 30",
                brand: "Himalaya",
                description: "Lightweight, non-greasy sunscreen with natural ingredients that provides broad-spectrum protection.",
                price: "$8.99",
                icon: "fas fa-sun",
                ingredients: ["aloe vera", "cinnabloc", "grape seed extract"],
                skinTypes: ["all", "normal", "combination"],
                concerns: ["sun protection", "tanning", "photo-aging"]
            },
            {
                title: "Unseen Sunscreen SPF 40",
                brand: "Supergoop!",
                description: "Totally invisible, weightless, scentless formula that provides broad spectrum protection.",
                price: "$36.00",
                icon: "fas fa-sun",
                ingredients: ["avobenzone", "frankincense", "red algae"],
                skinTypes: ["all", "normal", "combination", "oily"],
                concerns: ["sun protection", "blue light protection", "makeup priming"]
            },
            {
                title: "UV Aqua Rich Watery Essence SPF 50+",
                brand: "Biore",
                description: "Ultra-lightweight, water-based sunscreen that feels like nothing on the skin.",
                price: "$15.00",
                icon: "fas fa-sun",
                ingredients: ["hyaluronic acid", "royal jelly extract", "citrus mix"],
                skinTypes: ["all", "normal", "combination", "oily"],
                concerns: ["sun protection", "pigmenation", "acne"]
            }
        ]
    };
    
    // Filter products based on user input
    const filteredProducts = productDatabase[productType].filter(product => {
        // Check if product suits user's skin type
        const suitsSkinType = product.skinTypes.includes(skinType) || product.skinTypes.includes("all");
        
        // Check if product addresses at least one of user's concerns
        const addressesConcerns = concernsSelected.some(concern => 
            product.concerns.includes(concern)
        );
        
        // Check for allergens (basic implementation - in real app would be more sophisticated)
        let containsAllergens = false;
        if (allergiesInput.trim() !== '') {
            const allergies = allergiesInput.toLowerCase().split(',').map(a => a.trim());
            containsAllergens = allergies.some(allergy => 
                product.ingredients.some(ingredient => 
                    ingredient.toLowerCase().includes(allergy)
                )
            );
        }
        
        return suitsSkinType && addressesConcerns && !containsAllergens;
    });
    
    // Display recommendations
    displayRecommendations(filteredProducts, productType);
}

function displayRecommendations(products, productType) {
    const recommendationsContainer = document.getElementById('productRecommendations');
    
    // Handle case with no matching products
    if (products.length === 0) {
        recommendationsContainer.innerHTML = `
            <div class="no-results">
                <i class="fas fa-search"></i>
                <h3>No matching products found</h3>
                <p>Try adjusting your skin profile or concerns to get more recommendations.</p>
                <button class="button secondary-button" onclick="previousPage()">Go Back</button>
            </div>
        `;
        return;
    }
    
    // Sort products by rating (highest first)
    products.sort((a, b) => {
        const ratingA = parseFloat(a.rating);
        const ratingB = parseFloat(b.rating);
        return ratingB - ratingA;
    });
    
    // Create HTML for product cards
    let productsHTML = '';
    products.forEach(product => {
        // Extract numeric value from rating
        const ratingValue = parseFloat(product.rating);
        const fullStars = Math.floor(ratingValue);
        const hasHalfStar = ratingValue % 1 >= 0.5;
        
        // Generate star rating HTML
        let starsHTML = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= fullStars) {
                starsHTML += '<i class="fas fa-star"></i>';
            } else if (i === fullStars + 1 && hasHalfStar) {
                starsHTML += '<i class="fas fa-star-half-alt"></i>';
            } else {
                starsHTML += '<i class="far fa-star"></i>';
            }
        }
        
        // Generate ingredients list
        const ingredientsList = product.ingredients.map(ingredient => 
            `<span class="ingredient-tag">${ingredient}</span>`
        ).join('');
        
        // Create product card
        productsHTML += `
            <div class="product-card">
                <div class="product-icon">
                    <i class="${product.icon}"></i>
                </div>
                <div class="product-details">
                    <h3>${product.title}</h3>
                    <h4>${product.brand}</h4>
                    <div class="product-meta">
                        <span class="product-price">${product.price}</span>
                    </div>
                    <div class="product-ingredients">
                        <p>Key ingredients:</p>
                        <div class="ingredients-list">
                            ${ingredientsList}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    // Display product type heading
    const productTypeCapitalized = productType.charAt(0).toUpperCase() + productType.slice(1);
    
    // Update recommendations container - removed download button
    recommendationsContainer.innerHTML = `
        <div class="recommendations-header">
            <h2>Your Recommended ${productTypeCapitalized}s</h2>
            <p>Based on your skin profile and concerns</p>
        </div>
        <div class="product-grid">
            ${productsHTML}
        </div>
        <div class="recommendations-footer">
            <button class="button secondary-button" onclick="previousPage()">Adjust Profile</button>
        </div>
    `;
}

// Add loading state during image validation
function showLoadingState() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'block';
    document.querySelector('.button.secondary').disabled = true;
}

function hideLoadingState() {
    const loadingIndicator = document.getElementById('loadingIndicator');
    loadingIndicator.style.display = 'none';
    document.querySelector('.button.secondary').disabled = false;
}

// Add this helper function
function validateImage(file) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = function() {
            if (this.width < 200 || this.height < 200) {
                reject('Image resolution too low');
            }
            resolve(true);
        };
        img.onerror = function() {
            reject('Invalid image file');
        };
        img.src = URL.createObjectURL(file);
    });
}

// Simplified cleanup function
function cleanup() {
    // No need to revoke Data URLs, as they don't need cleanup
    // This function is now a no-op since we're using FileReader with readAsDataURL
    // which creates Data URLs that don't need to be manually revoked
}

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    updateProgressBar();
    showPage(pages[currentPage - 1]);
    
    // Add button event listeners
    document.getElementById('uploadNextButton').addEventListener('click', validateAndNextPage);
    document.getElementById('questionnaireBackButton').addEventListener('click', previousPage);
    document.getElementById('questionnaireNextButton').addEventListener('click', validateFormAndNextPage);
});