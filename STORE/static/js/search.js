document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const productTableBody = document.getElementById('productTableBody');
    const noResultsMessage = document.getElementById('noResultsMessage');

    // Function to hide flash messages after 2 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.display = 'none';
        }, 2000);
    });

    if (searchButton && searchInput) {
        searchButton.addEventListener('click', () => {
            const searchTerm = searchInput.value.trim().toLowerCase();
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

    function attachToggleEventListeners() {
        const toggleButtons = document.querySelectorAll('.toggle-button');
        toggleButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                const code = event.target.getAttribute('data-code');
                const nestedTableContainer = document.getElementById(`items_${code}`);
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
                        .then(response => response.json())
                        .then(data => {
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
        const updateButtons = document.querySelectorAll('.update-button');
        const deleteButtons = document.querySelectorAll('.delete-button');

        updateButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                const code = event.target.getAttribute('data-code');
                // Add your update logic here
            });
        });

        deleteButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                const code = event.target.getAttribute('data-code');
                // Add your delete logic here
            });
        });
    }
});
