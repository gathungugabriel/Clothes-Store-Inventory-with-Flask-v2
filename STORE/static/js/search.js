document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded and parsed');

    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const productTableBody = document.getElementById('productTableBody');
    const noResultsMessage = document.getElementById('noResultsMessage');
    const addDataButton = document.getElementById('addDataButton');

    // Function to hide flash messages after 2 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.display = 'none';
        }, 2000);
    });

    if (searchButton && searchInput) {
        searchButton.addEventListener('click', () => {
            console.log('Search button clicked');
            const searchTerm = searchInput.value.trim().toLowerCase();
            console.log('Search term:', searchTerm);
            if (searchTerm) {
                fetch('/filter_products', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ search_term: searchTerm }),
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Filtered products data:', data);
                    const { products } = data;
                    productTableBody.innerHTML = '';
                    if (products.length > 0) {
                        products.forEach(product => {
                            const row = `
                                <tr>
                                    <td>${product.code}</td>
                                    <td>${product.item}</td>
                                    <td>${product.category}</td>
                                    <td>${product.buying_price}</td>
                                    <td>${product.selling_price}</td>
                                    <td>${product.quantity}</td>
                                    <td>
                                        <button class="btn btn-info toggle-button" data-code="${product.code}">Expand</button>
                                    </td>
                                </tr>
                                <tr id="items_${product.code}" class="nested-table-container d-none">
                                    <td colspan="7"></td>
                                </tr>
                            `;
                            productTableBody.insertAdjacentHTML('beforeend', row);
                        });
                        noResultsMessage.classList.add('d-none');
                    } else {
                        noResultsMessage.classList.remove('d-none');
                    }
                    attachToggleEventListeners();
                })
                .catch(error => {
                    console.error('Error fetching filtered products:', error);
                });
            }
        });
    } else {
        console.error('Search input or button not found');
    }

    if (addDataButton) {
        addDataButton.addEventListener('click', function() {
            console.log('Add Data button clicked');
            fetch('/add_data_to_db')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Add data response:', data);
                    alert(data.message);
                })
                .catch(error => {
                    console.error('Error adding data to database:', error);
                    alert('Error adding data to database.');
                });
        });
    } else {
        console.error('Add Data button not found');
    }

    function attachToggleEventListeners() {
        console.log('Attaching toggle event listeners');
        const toggleButtons = document.querySelectorAll('.toggle-button');
        toggleButtons.forEach(button => {
            console.log('Attaching event listener to button:', button);
            button.addEventListener('click', (event) => {
                console.log('Toggle button clicked');
                const code = event.target.getAttribute('data-code');
                console.log('Code:', code);
                const nestedTableContainer = document.getElementById(`items_${code}`);
                console.log('Nested table container:', nestedTableContainer);
                if (nestedTableContainer) {
                    nestedTableContainer.classList.toggle('d-none');
                    if (!nestedTableContainer.classList.contains('d-none')) {
                        fetch('/expand_items', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ item: code }),
                        })
                        .then(response => {
                            if (!response.ok) {
                                throw new Error('Network response was not ok');
                            }
                            return response.json();
                        })
                        .then(data => {
                            console.log('Expanded items data:', data);
                            const { products } = data;
                            const nestedTableContent = products.map(product => `
                                <tr>
                                    <td>${product.code}</td>
                                    <td>${product.size}</td>
                                    <td>${product.type_material}</td>
                                    <td>${product.color}</td>
                                    <td>${product.description}</td>
                                    <td>${product.buying_price}</td>
                                    <td>${product.selling_price}</td>
                                    <td>${product.profit}</td>
                                    <td>
                                        <button class="btn btn-warning update-button" data-code="${product.code}">Update</button>
                                        <button class="btn btn-danger delete-button" data-code="${product.code}">Delete</button>
                                    </td>
                                </tr>
                            `).join('');
                            nestedTableContainer.querySelector('td').innerHTML = `
                                <table class="table table-bordered">
                                    <thead>
                                        <tr>
                                            <th>Code</th>
                                            <th>Size</th>
                                            <th>Type Material</th>
                                            <th>Color</th>
                                            <th>Description</th>
                                            <th>Buying Price</th>
                                            <th>Selling Price</th>
                                            <th>Profit</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${nestedTableContent}
                                    </tbody>
                                </table>
                            `;
                            attachUpdateDeleteEventListeners();
                        })
                        .catch(error => {
                            console.error('Error expanding items:', error);
                        });
                    }
                } else {
                    console.error(`Nested table container with ID items_${code} not found`);
                }
            });
        });
    }

    function attachUpdateDeleteEventListeners() {
        console.log('Attaching update and delete event listeners');
        const updateButtons = document.querySelectorAll('.update-button');
        const deleteButtons = document.querySelectorAll('.delete-button');

        updateButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                console.log('Update button clicked');
                const code = event.target.getAttribute('data-code');
                // Add your update logic here
            });
        });

        deleteButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                console.log('Delete button clicked');
                const code = event.target.getAttribute('data-code');
                // Add your delete logic here
            });
        });
    }

    function fetchProductDetails() {
        const codeInput = document.getElementById('code');
        const prefix = codeInput.value.slice(0, 2);
        if (prefix.length > 0) {
            fetch(`/get_product_details/${prefix}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error(data.error);
                        return;
                    }
                    document.getElementById('category').value = data.category;
                    document.getElementById('item').value = data.item;
                })
                .catch(error => console.error('Error fetching product details:', error));

            fetch(`/generate_product_code/${prefix}`)
                .then(response => response.json())
                .then(data => {
                    codeInput.value = data.code;
                })
                .catch(error => console.error('Error generating product code:', error));
        }
    }

    // Event listener for code input field
    const codeInput = document.getElementById('code');
    if (codeInput) {
        codeInput.addEventListener('input', fetchProductDetails);
    }
});
