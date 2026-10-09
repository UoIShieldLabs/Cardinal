CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    price DECIMAL(10, 2),
    description TEXT,
    category VARCHAR(100)
);

CREATE TABLE recommendations (
    product_id INT REFERENCES products(id),
    related_product_id INT REFERENCES products(id)
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    product_id INT REFERENCES products(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert seed data (Product 1 will be our "viral" item)
INSERT INTO products (name, price, description, category) VALUES
('Viral Item', 19.99, 'The target of the flash crowd.', 'Electronics'),
('Normal Item', 9.99, 'A standard catalog item.', 'Books'),
('Niche Item', 45.00, 'Rarely purchased item.', 'Home');

INSERT INTO recommendations (product_id, related_product_id) VALUES
(1, 2), (2, 3), (3, 1);